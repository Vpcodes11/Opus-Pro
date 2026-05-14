import asyncio
import os
from main import process_job, jobs
from config import UPLOAD_DIR

async def run_test():
    job_id = "test_run"
    video_path = os.path.join(UPLOAD_DIR, "test_video.mp4")
    
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found!")
        return

    # Initialize job state
    jobs[job_id] = {
        'status': 'queued',
        'video_path': video_path,
        'provider': 'groq',
        'preset': 'landscape',
        'caption_style': 'typography_motion', # Using the new Typography Motion style!
        'progress': 0,
        'message': 'Starting test run...',
        'clips': [],
        'transcript': None,
        'source': 'test_video.mp4',
    }

    print(f"--- Starting Viral Pipeline Test for Job: {job_id} ---")
    print(f"Style: {jobs[job_id]['caption_style']}")
    print(f"Features: Typography (Cursive/CAPS), Landscape-on-Blur, Snap-Transitions")
    
    try:
        await process_job(job_id)
        print("\n--- Test Complete! ---")
        job = jobs[job_id]
        if job['status'] == 'complete':
            print(f"Success! Created {len(job['clips'])} clips.")
            for i, clip in enumerate(job['clips']):
                print(f"Clip {i+1}: {clip['title']} (Score: {clip['virality_score']})")
                print(f"Path: output/{job_id}/{clip['filename']}")
        else:
            print(f"Job failed: {job['message']}")
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
