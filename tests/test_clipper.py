import pytest
import sys
from unittest.mock import MagicMock

# Mock dependencies before importing clipper
sys.modules['dotenv'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['mediapipe.python'] = MagicMock()
sys.modules['mediapipe.python.solutions'] = MagicMock()
sys.modules['cv2'] = MagicMock()

import subprocess
import json
from unittest.mock import patch

from app.core.clipper import format_ass_time, get_video_info

@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear lru_cache for get_video_info before each test to prevent state leakage."""
    get_video_info.cache_clear()

@pytest.mark.parametrize("seconds, expected", [
    (0, "0:00:00.00"),
    (-1, "0:00:00.00"),
    (5.5, "0:00:05.50"),
    (65.29, "0:01:05.29"),
    (0.29, "0:00:00.29"),
    (3661, "1:01:01.00"),
    (0.99, "0:00:00.99"),
    (0.999, "0:00:01.00"),
    (59.999, "0:01:00.00"),
    (3599.999, "1:00:00.00"),
])
def test_format_ass_time(seconds, expected):
    assert format_ass_time(seconds) == expected

@patch('app.core.clipper.subprocess.run')
def test_get_video_info_success(mock_run):
    """Test get_video_info with valid ffprobe output."""
    mock_run.return_value = MagicMock(
        stdout=json.dumps({
            "streams": [
                {"codec_type": "audio"},
                {"codec_type": "video", "width": 1280, "height": 720}
            ],
            "format": {"duration": "120.5"}
        }),
        returncode=0
    )

    width, height, duration = get_video_info("dummy.mp4")
    assert width == 1280
    assert height == 720
    assert duration == 120.5

@patch('app.core.clipper.subprocess.run')
def test_get_video_info_fallback(mock_run):
    """Test get_video_info when no video stream is found, should use fallback defaults."""
    mock_run.return_value = MagicMock(
        stdout=json.dumps({
            "streams": [
                {"codec_type": "audio"}
            ],
            "format": {"duration": "60.0"}
        }),
        returncode=0
    )

    width, height, duration = get_video_info("dummy2.mp4")
    assert width == 1920
    assert height == 1080
    assert duration == 60.0

@patch('app.core.clipper.subprocess.run')
def test_get_video_info_missing_fields(mock_run):
    """Test get_video_info when stream is video but missing width/height."""
    mock_run.return_value = MagicMock(
        stdout=json.dumps({
            "streams": [
                {"codec_type": "video"} # missing width and height
            ],
            "format": {} # missing duration
        }),
        returncode=0
    )

    width, height, duration = get_video_info("dummy3.mp4")
    assert width == 1920
    assert height == 1080
    assert duration == 0.0

@patch('app.core.clipper.subprocess.run')
def test_get_video_info_subprocess_error(mock_run):
    """Test get_video_info raises exception when subprocess fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')

    with pytest.raises(subprocess.CalledProcessError):
        get_video_info("dummy_error.mp4")

@patch('app.core.clipper.subprocess.run')
def test_get_video_info_invalid_json(mock_run):
    """Test get_video_info handles invalid JSON output."""
    mock_run.return_value = MagicMock(
        stdout="Invalid JSON Output",
        returncode=0
    )

    with pytest.raises(json.JSONDecodeError):
        get_video_info("dummy_invalid.mp4")
