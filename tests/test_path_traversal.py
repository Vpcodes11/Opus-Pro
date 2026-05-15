import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import os
import shutil
import sys
from unittest.mock import MagicMock

# Mock mediapipe to fix module errors
sys.modules['mediapipe'] = MagicMock()
sys.modules['cv2'] = MagicMock()

from main import app, OUTPUT_DIR, UPLOAD_DIR

client = TestClient(app)

@pytest.fixture
def setup_dirs():
    job_id = "test_job"
    filename = "test_file.mp4"

    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    out_file.touch()

    up_dir = UPLOAD_DIR / job_id
    up_dir.mkdir(parents=True, exist_ok=True)

    yield job_id, filename

    shutil.rmtree(out_dir, ignore_errors=True)
    shutil.rmtree(up_dir, ignore_errors=True)


def test_download_clip_valid(setup_dirs):
    job_id, filename = setup_dirs
    response = client.get(f"/api/download/{job_id}/{filename}")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_download_clip_path_traversal():
    # Attempt to go up to OUTPUT_DIR root or outside
    # FastAPI handles `../` in path by resolving it or throwing 404, so we test internal behavior by passing invalid path args directly
    from main import download_clip

    # We can mock the request by directly calling the async endpoint function
    # job_id="test_job", filename="../../config.py"
    response = await download_clip("test_job", "../../config.py")
    assert response.status_code == 400
    import json
    assert json.loads(response.body) == {'error': 'Invalid path'}

def test_preview_clip_valid(setup_dirs):
    job_id, filename = setup_dirs
    response = client.get(f"/api/preview/{job_id}/{filename}")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_preview_clip_path_traversal():
    from main import preview_clip

    response = await preview_clip("test_job", "../../config.py")
    assert response.status_code == 400
    import json
    assert json.loads(response.body) == {'error': 'Invalid path'}

def test_delete_job_valid(setup_dirs):
    job_id, filename = setup_dirs
    response = client.delete(f"/api/job/{job_id}")
    assert response.status_code == 200
    assert not (OUTPUT_DIR / job_id).exists()
    assert not (UPLOAD_DIR / job_id).exists()

def test_delete_job_path_traversal():
    # Attempt to delete the root OUTPUT_DIR or parent
    # Since fast api might not route this easily, let's just make sure job_id parameter parsing does not let it delete root
    # e.g., if job_id is '../', it would resolve to OUTPUT_DIR parent
    # In FastAPI, job_id comes directly from URL path. If we try to pass %2E%2E (..)

    # Let's directly test the delete_job endpoint function behavior for path traversal if called programmatically,
    # or by routing
    response = client.delete("/api/job/..%2F..%2F")
    # Actually if job_id is '..', job_dir resolves to OUTPUT_DIR parent.
    # Our logic says `job_dir.is_relative_to(base_dir.resolve())`. If we pass '..', it resolves outside base_dir.
    # It should not delete it.

    # We can check that config.py still exists
    assert Path("config.py").exists()
    assert response.status_code in (200, 404, 405) # 200 is returned by default when job is not found, but we ensure no dir is deleted.
