"""Opus Pro — AI Video Clipper | FastAPI Server"""
import asyncio
import os
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import UPLOAD_DIR, OUTPUT_DIR, BASE_DIR, PRESETS, CAPTION_STYLES, GROQ_API_KEY, DEFAULT_PROVIDER, DEFAULT_CAPTION_STYLE
from transcriber import transcribe
from analyzer import analyze_transcript
from clipper import create_clip, generate_thumbnail
from downloader import is_valid_url, download_video

app = FastAPI(title="Opus Pro — AI Video Clipper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job state tracking
jobs = {}
ws_connections = {}

# Serve static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
async def root():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.get("/api/presets")
async def get_presets():
    """Return available export presets and caption styles"""
    return JSONResponse({
        "presets": PRESETS,
        "caption_styles": {k: {"name": k.replace("_", " ").title()} for k in CAPTION_STYLES},
    })


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(None),
    url: str = Form(None),
    provider: str = Form(None),
    preset: str = Form('landscape'),
    caption_style: str = Form('typography_motion'),
):
    """Accept video upload or URL and start processing pipeline"""
    # Use server-side API key and default provider
    api_key = GROQ_API_KEY
    if not provider:
        provider = DEFAULT_PROVIDER
    job_id = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    video_path = None

    if url and url.strip():
        # URL download mode
        jobs[job_id] = {
            'status': 'downloading',
            'video_path': None,
            'provider': provider,
            'preset': preset,
            'caption_style': caption_style,
            'progress': 0,
            'message': 'Downloading video from URL...',
            'clips': [],
            'transcript': None,
            'source': url.strip(),
        }
        asyncio.create_task(process_job_with_download(job_id, url.strip(), str(job_dir)))
    elif file:
        # File upload mode
        video_path = job_dir / file.filename
        with open(video_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        jobs[job_id] = {
            'status': 'queued',
            'video_path': str(video_path),
            'provider': provider,
            'preset': preset,
            'caption_style': caption_style,
            'progress': 0,
            'message': 'Upload complete, starting processing...',
            'clips': [],
            'transcript': None,
            'source': file.filename,
        }
        asyncio.create_task(process_job(job_id))
    else:
        return JSONResponse({'error': 'No file or URL provided'}, status_code=400)

    return JSONResponse({'job_id': job_id})


async def send_ws_update(job_id, data):
    """Send update to WebSocket client if connected"""
    ws = ws_connections.get(job_id)
    if ws:
        try:
            await ws.send_json(data)
        except Exception:
            pass


async def process_job_with_download(job_id, url, job_dir):
    """Download video from URL, then process"""
    job = jobs[job_id]
    loop = asyncio.get_running_loop()

    try:
        def dl_progress(message, progress):
            job['message'] = message
            job['progress'] = progress
            asyncio.run_coroutine_threadsafe(
                send_ws_update(job_id, {
                    'type': 'progress',
                    'message': message,
                    'progress': progress
                }),
                loop
            )

        video_path = await loop.run_in_executor(
            None, download_video, url, job_dir, dl_progress
        )
        job['video_path'] = video_path
        job['status'] = 'queued'
        await process_job(job_id)

    except Exception as e:
        job['status'] = 'error'
        job['message'] = f"Download failed: {str(e)}"
        job['progress'] = 0
        await send_ws_update(job_id, {'type': 'error', 'message': job['message']})


async def process_job(job_id):
    """Run the full pipeline: transcribe → analyze → clip"""
    job = jobs[job_id]
    job['status'] = 'processing'
    loop = asyncio.get_running_loop()

    try:
        def progress_cb(message, progress):
            job['message'] = message
            job['progress'] = progress
            asyncio.run_coroutine_threadsafe(
                send_ws_update(job_id, {
                    'type': 'progress',
                    'message': message,
                    'progress': progress
                }),
                loop
            )

        # Step 1: Transcribe
        provider = job.get('provider', DEFAULT_PROVIDER)
        transcript = await loop.run_in_executor(
            None, transcribe, job['video_path'], GROQ_API_KEY, progress_cb, provider
        )

        # Store transcript for frontend display
        job['transcript'] = {
            'segments': transcript['segments'],
            'full_text': transcript['full_text'],
            'duration': transcript.get('duration', 0),
            'word_count': len(transcript['words']),
        }

        await send_ws_update(job_id, {
            'type': 'transcript',
            'transcript': job['transcript']
        })

        # Step 2: Analyze for viral moments
        clips_info = await loop.run_in_executor(
            None, analyze_transcript, transcript, GROQ_API_KEY, progress_cb, provider
        )

        # Step 3: Create clips + thumbnails
        output_dir = OUTPUT_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        clip_results = []
        for i, clip_info in enumerate(clips_info):
            output_path = str(output_dir / f"clip_{i+1}.mp4")
            thumb_path = str(output_dir / f"thumb_{i+1}.jpg")

            await loop.run_in_executor(
                None, create_clip,
                job['video_path'], clip_info, transcript['words'],
                output_path, i, progress_cb,
                job.get('caption_style', DEFAULT_CAPTION_STYLE),
                job.get('preset', 'tiktok')
            )

            # Generate thumbnail
            await loop.run_in_executor(
                None, generate_thumbnail,
                job['video_path'], clip_info['start_time'], thumb_path
            )

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

        # Done!
        job['clips'] = clip_results
        job['status'] = 'complete'
        job['progress'] = 100
        job['message'] = f'Done! {len(clip_results)} viral clips created.'

        await send_ws_update(job_id, {
            'type': 'complete',
            'message': job['message'],
            'clips': clip_results,
            'transcript': job['transcript']
        })

    except Exception as e:
        job['status'] = 'error'
        job['message'] = str(e)
        job['progress'] = 0
        await send_ws_update(job_id, {
            'type': 'error',
            'message': str(e)
        })


@app.post("/api/reclip/{job_id}")
async def reclip(
    job_id: str,
    clip_index: int = Form(...),
    start_time: float = Form(...),
    end_time: float = Form(...),
    caption_style: str = Form('typography_motion'),
    preset: str = Form('landscape'),
):
    """Re-create a single clip with adjusted timing or style"""
    job = jobs.get(job_id)
    if not job or job['status'] != 'complete':
        return JSONResponse({'error': 'Job not found or not complete'}, status_code=404)

    if clip_index < 0 or clip_index >= len(job['clips']):
        return JSONResponse({'error': 'Invalid clip index'}, status_code=400)

    loop = asyncio.get_running_loop()
    output_dir = OUTPUT_DIR / job_id

    clip_info = job['clips'][clip_index].copy()
    clip_info['start_time'] = start_time
    clip_info['end_time'] = end_time

    # Re-transcribe to get words (we don't store them long-term)
    try:
        transcript = await loop.run_in_executor(
            None, transcribe, job['video_path'], GROQ_API_KEY, None, job.get('provider', DEFAULT_PROVIDER)
        )

        output_path = str(output_dir / f"clip_{clip_index+1}.mp4")
        await loop.run_in_executor(
            None, create_clip,
            job['video_path'], clip_info, transcript['words'],
            output_path, clip_index, None,
            caption_style, preset
        )

        # Update job state
        job['clips'][clip_index]['start_time'] = start_time
        job['clips'][clip_index]['end_time'] = end_time
        job['clips'][clip_index]['duration'] = round(end_time - start_time, 1)

        return JSONResponse({'success': True, 'clip': job['clips'][clip_index]})
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket for real-time progress updates"""
    await websocket.accept()
    ws_connections[job_id] = websocket

    # Send current state if job exists
    if job_id in jobs:
        job = jobs[job_id]
        msg = {
            'type': 'progress',
            'message': job['message'],
            'progress': job['progress']
        }
        if job['status'] == 'complete':
            msg = {
                'type': 'complete',
                'message': job['message'],
                'clips': job.get('clips', []),
                'transcript': job.get('transcript')
            }
        await websocket.send_json(msg)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections.pop(job_id, None)


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Polling fallback for progress updates"""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({'error': 'Job not found'}, status_code=404)
    return JSONResponse({
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'clips': job.get('clips', []),
        'transcript': job.get('transcript'),
    })


@app.get("/api/download/{job_id}/{filename}")
async def download_clip(job_id: str, filename: str):
    """Download a generated clip"""
    filepath = (OUTPUT_DIR / job_id / filename).resolve()
    if not filepath.is_relative_to(OUTPUT_DIR.resolve()):
        return JSONResponse({'error': 'Invalid path'}, status_code=400)

    if not filepath.exists():
        return JSONResponse({'error': 'File not found'}, status_code=404)
    return FileResponse(
        str(filepath),
        filename=filename,
        media_type='video/mp4'
    )


@app.get("/api/preview/{job_id}/{filename}")
async def preview_clip(job_id: str, filename: str):
    """Stream clip for in-browser preview"""
    filepath = (OUTPUT_DIR / job_id / filename).resolve()
    if not filepath.is_relative_to(OUTPUT_DIR.resolve()):
        return JSONResponse({'error': 'Invalid path'}, status_code=400)

    if not filepath.exists():
        return JSONResponse({'error': 'File not found'}, status_code=404)

    media_type = 'video/mp4'
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        media_type = 'image/jpeg'
    elif filename.endswith('.png'):
        media_type = 'image/png'

    return FileResponse(str(filepath), media_type=media_type)


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Clean up job data"""
    jobs.pop(job_id, None)

    # Clean up files
    for base_dir in [UPLOAD_DIR, OUTPUT_DIR]:
        job_dir = (base_dir / job_id).resolve()
        if job_dir.is_relative_to(base_dir.resolve()) and job_dir.exists() and job_dir != base_dir.resolve():
            shutil.rmtree(job_dir, ignore_errors=True)

    return JSONResponse({'success': True})
