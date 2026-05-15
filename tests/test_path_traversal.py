import pytest
import sys
import json
import asyncio
from unittest.mock import patch
from fastapi.responses import JSONResponse

sys.path.append('.')
from main import download_clip, preview_clip, delete_job

@pytest.mark.asyncio
async def test_download_clip_path_traversal():
    response = await download_clip("..", "..")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert json.loads(response.body.decode()) == {"error": "Access denied"}

@pytest.mark.asyncio
async def test_preview_clip_path_traversal():
    response = await preview_clip("..", "..")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert json.loads(response.body.decode()) == {"error": "Access denied"}

@pytest.mark.asyncio
async def test_delete_job_path_traversal():
    response = await delete_job("..")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert json.loads(response.body.decode()) == {"error": "Access denied"}

@pytest.mark.asyncio
async def test_download_clip_valid_path():
    response = await download_clip("valid_job", "valid_file.mp4")
    assert isinstance(response, JSONResponse)
    # File does not exist, but we didn't get 403
    assert response.status_code == 404
    assert json.loads(response.body.decode()) == {"error": "File not found"}
