import os
import json
import redis
import math
from app.worker.celery_app import celery_app
from app.api.database import SessionLocal, engine, Base
from app.api.models import Job, User
from app.config import GROQ_API_KEY, DEFAULT_PROVIDER, DEFAULT_CAPTION_STYLE, OUTPUT_DIR, STORAGE_MODE
from app.core.transcriber import transcribe
from app.core.analyzer import analyze_transcript
from app.core.clipper import create_clip, generate_thumbnail, get_video_info
from app.core.downloader import download_video
from app.core.storage import storage

# Ensure tables exist for the worker
Base.metadata.create_all(bind=engine)

# Initialize Redis for progress broadcasting
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)

def broadcast_progress(job_id, message, progress):
    """Broadcast progress update via Redis Pub/Sub"""
    data = {
        'type': 'progress',
        'message': message,
        'progress': progress
    }
    redis_client.publish(f"job_progress_{job_id}", json.dumps(data))

@celery_app.task(name="tasks.process_video_job")
def process_video_job(job_id):
    """Celery task to run the full pipeline: transcribe → analyze → clip"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return f"Job {job_id} not found"

        job.status = 'processing'
        db.commit()

        # Local cache for processing
        video_path = job.video_path
        provider = job.provider or DEFAULT_PROVIDER
        caption_style = job.caption_style or DEFAULT_CAPTION_STYLE
        preset = job.preset or 'tiktok'

        def progress_cb(message, progress):
            db_cb = SessionLocal()
            try:
                j = db_cb.query(Job).filter(Job.id == job_id).first()
                if j:
                    j.message = message
                    j.progress = progress
                    db_cb.commit()
                broadcast_progress(job_id, message, progress)
            finally:
                db_cb.close()

        # Step 1: Transcribe
        transcript = transcribe(video_path, GROQ_API_KEY, progress_cb, provider)
        
        # Calculate duration for billing
        _, _, duration = get_video_info(video_path)
        minutes_used = math.ceil(duration / 60)
        
        transcript_data = {
            'segments': transcript['segments'],
            'full_text': transcript['full_text'],
            'duration': duration,
            'word_count': len(transcript['words']),
        }
        
        job.transcript = transcript_data
        db.commit()
        
        redis_client.publish(f"job_progress_{job_id}", json.dumps({
            'type': 'transcript',
            'transcript': transcript_data
        }))

        # Step 2: Analyze for viral moments
        clips_info = analyze_transcript(transcript, GROQ_API_KEY, progress_cb, provider)

        # Step 3: Create clips + thumbnails
        output_dir = OUTPUT_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        clip_results = []
        for i, clip_info in enumerate(clips_info):
            output_path = str(output_dir / f"clip_{i+1}.mp4")
            thumb_path = str(output_dir / f"thumb_{i+1}.jpg")

            create_clip(
                video_path, clip_info, transcript['words'],
                output_path, i, progress_cb,
                caption_style, preset
            )

            generate_thumbnail(video_path, clip_info['start_time'], thumb_path)

            if STORAGE_MODE == "cloud":
                progress_cb(f"Uploading clip {i+1} to cloud...", 90 + i)
                storage.upload_file(output_path, f"jobs/{job_id}/clip_{i+1}.mp4")
                storage.upload_file(thumb_path, f"jobs/{job_id}/thumb_{i+1}.jpg")

            clip_results.append({
                'filename': f"clip_{i+1}.mp4",
                'thumbnail': f"thumb_{i+1}.jpg",
                'title': clip_info['title'],
                'hook_caption': clip_info.get('hook_caption', ''),
                'virality_score': clip_info.get('virality_score', 0),
                'reason': clip_info.get('reason', ''),
                'category': clip_info.get('category', ''),
                'hashtags': clip_info.get('hashtags', []),
                'start_time': clip_info['start_time'],
                'end_time': clip_info['end_time'],
                'duration': round(clip_info['end_time'] - clip_info['start_time'], 1)
            })

        job.clips = clip_results
        job.status = 'complete'
        job.progress = 100
        job.message = f'Done! {len(clip_results)} viral clips created.'
        
        # Deduct minutes from user
        user = db.query(User).filter(User.id == job.user_id).first()
        if user:
            user.used_minutes += minutes_used
            
        db.commit()

        redis_client.publish(f"job_progress_{job_id}", json.dumps({
            'type': 'complete',
            'message': job.message,
            'clips': job.clips,
            'transcript': job.transcript
        }))

        return f"Job {job_id} completed successfully"

    except Exception as e:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = 'error'
            job.message = str(e)
            job.progress = 0
            db.commit()
        
        redis_client.publish(f"job_progress_{job_id}", json.dumps({
            'type': 'error',
            'message': str(e)
        }))
        return f"Job {job_id} failed: {str(e)}"
    finally:
        db.close()

@celery_app.task(name="tasks.download_and_process_job")
def download_and_process_job(job_id, url, job_dir):
    """Celery task to download video from URL, then process"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return f"Job {job_id} not found"

        def dl_progress(message, progress):
            db_cb = SessionLocal()
            try:
                j = db_cb.query(Job).filter(Job.id == job_id).first()
                if j:
                    j.message = message
                    j.progress = progress
                    db_cb.commit()
                broadcast_progress(job_id, message, progress)
            finally:
                db_cb.close()

        video_path = download_video(url, job_dir, dl_progress)
        
        if STORAGE_MODE == "cloud":
            dl_progress("Uploading original to cloud...", 10)
            filename = os.path.basename(video_path)
            storage.upload_file(video_path, f"jobs/{job_id}/source/{filename}")

        job.video_path = video_path
        job.status = 'queued'
        db.commit()
        
        process_video_job(job_id)

    except Exception as e:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = 'error'
            job.message = f"Download failed: {str(e)}"
            job.progress = 0
            db.commit()
        
        redis_client.publish(f"job_progress_{job_id}", json.dumps({
            'type': 'error',
            'message': f"Download failed: {str(e)}"
        }))
    finally:
        db.close()
