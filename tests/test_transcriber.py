import pytest
from unittest.mock import patch
from app.core.transcriber import get_client, PROVIDERS

def test_get_client_groq_provider():
    api_key = "test_groq_key"
    with patch("app.core.transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key, provider="groq")

        mock_openai.assert_called_once_with(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["groq"]

def test_get_client_openai_provider():
    api_key = "test_openai_key"
    with patch("app.core.transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key, provider="openai")

        mock_openai.assert_called_once_with(
            api_key=api_key
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["openai"]

def test_get_client_unknown_provider_fallback():
    api_key = "test_unknown_key"
    with patch("app.core.transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key, provider="unknown_provider")

        mock_openai.assert_called_once_with(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["groq"]

def test_get_client_default_provider():
    api_key = "test_default_key"
    with patch("app.core.transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key)

        mock_openai.assert_called_once_with(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["groq"]

def test_extract_audio_success():
    video_path = "input_video.mp4"
    audio_path = "output_audio.mp3"

    with patch("app.core.transcriber.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        from app.core.transcriber import extract_audio
        extract_audio(video_path, audio_path)

        mock_run.assert_called_once_with(
            [
                'ffmpeg', '-i', video_path,
                '-vn', '-ac', '1', '-ab', '64k',
                '-f', 'mp3', '-y', audio_path
            ],
            capture_output=True, text=True
        )

def test_extract_audio_failure():
    video_path = "input_video.mp4"
    audio_path = "output_audio.mp3"

    with patch("app.core.transcriber.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "some error message here"

        from app.core.transcriber import extract_audio
        with pytest.raises(RuntimeError) as exc_info:
            extract_audio(video_path, audio_path)

        assert "Audio extraction failed:" in str(exc_info.value)
        assert "some error message here" in str(exc_info.value)
