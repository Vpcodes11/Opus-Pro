import pytest
from app.core.downloader import is_valid_url

def test_is_valid_url_valid_youtube():
    assert is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_url("http://youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_url("https://youtu.be/dQw4w9WgXcQ") is True

def test_is_valid_url_valid_twitch():
    assert is_valid_url("https://www.twitch.tv/ninja") is True
    assert is_valid_url("https://twitch.tv/ninja") is True

def test_is_valid_url_valid_vimeo():
    assert is_valid_url("https://vimeo.com/123456789") is True
    assert is_valid_url("http://www.vimeo.com/123456789") is True

def test_is_valid_url_valid_dailymotion():
    assert is_valid_url("https://www.dailymotion.com/video/x80lpx") is True

def test_is_valid_url_valid_facebook():
    assert is_valid_url("https://www.facebook.com/username/videos/123456789/") is True
    assert is_valid_url("https://facebook.com/username/videos/123456789/") is True

def test_is_valid_url_valid_twitter_x():
    assert is_valid_url("https://twitter.com/username/status/123456789") is True
    assert is_valid_url("https://www.x.com/username/status/123456789") is True

def test_is_valid_url_valid_direct_files():
    assert is_valid_url("https://example.com/video.mp4") is True
    assert is_valid_url("http://example.com/video.mkv") is True
    assert is_valid_url("https://example.com/video.mov") is True
    assert is_valid_url("https://example.com/video.avi") is True
    assert is_valid_url("https://example.com/video.webm") is True

def test_is_valid_url_invalid_urls():
    assert is_valid_url("https://example.com/video.txt") is False
    assert is_valid_url("https://example.com/image.jpg") is False
    assert is_valid_url("not_a_url") is False
    assert is_valid_url("") is False
    assert is_valid_url("ftp://example.com/video.mp4") is False
    assert is_valid_url("https://youtube.com/user/channel") is False # Doesn't match /watch
    assert is_valid_url("https://google.com") is False
