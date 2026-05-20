import pytest
import sys
from unittest.mock import MagicMock

# Mock dependencies before importing clipper
sys.modules['dotenv'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['mediapipe.python'] = MagicMock()
sys.modules['mediapipe.python.solutions'] = MagicMock()
sys.modules['cv2'] = MagicMock()

from clipper import format_ass_time, build_ffmpeg_command

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

def test_build_ffmpeg_command_tracking_tiktok():
    tracking = {
        'crop_w': 1080,
        'crop_h': 1920,
        'coords': {0: 500}
    }
    cmd = build_ffmpeg_command(
        video_path="test.mp4",
        start=0,
        duration=10,
        tracking=tracking,
        preset="tiktok",
        ass_escaped="subs.ass",
        src_w=1920,
        src_h=1080,
        tw=1080,
        th=1920,
        is_pro=True,
        output_path="out.mp4"
    )
    assert 'crop=1080:1920:500:0' in cmd[8] # filter_complex
    assert 'scale=1080:1920' in cmd[8]
    assert "[out]" in cmd[8]

def test_build_ffmpeg_command_landscape_blur():
    cmd = build_ffmpeg_command(
        video_path="test.mp4",
        start=0,
        duration=10,
        tracking=None,
        preset="tiktok",
        ass_escaped="subs.ass",
        src_w=1920,
        src_h=1080,
        tw=1080,
        th=1920,
        is_pro=False,
        output_path="out.mp4"
    )
    assert 'force_original_aspect_ratio=increase' in cmd[8]
    assert 'boxblur=25:5' in cmd[8]
    assert "Created with Opus Pro" in cmd[8]

def test_build_ffmpeg_command_standard_fit():
    cmd = build_ffmpeg_command(
        video_path="test.mp4",
        start=0,
        duration=10,
        tracking=None,
        preset="youtube_landscape",
        ass_escaped="subs.ass",
        src_w=1920,
        src_h=1080,
        tw=1920,
        th=1080,
        is_pro=True,
        output_path="out.mp4"
    )
    assert 'force_original_aspect_ratio=decrease' in cmd[8]
    assert 'pad=1920:1080' in cmd[8]
    assert "[out]" in cmd[8]
