import pytest
from unittest.mock import patch
from transcriber import get_client, PROVIDERS

def test_get_client_groq_provider():
    api_key = "test_groq_key"
    with patch("transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key, provider="groq")

        mock_openai.assert_called_once_with(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["groq"]

@patch("transcriber.subprocess.run")
def test_get_audio_duration_success(mock_run):
    mock_run.return_value.stdout = '{"format": {"duration": "12.34"}}'

    # We must import from transcriber because the test mocks it that way
    from transcriber import get_audio_duration

    duration = get_audio_duration("test.mp3")
    assert duration == 12.34

    mock_run.assert_called_once_with([
        'ffprobe', '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'json', 'test.mp3'
    ], capture_output=True, text=True, check=True)

@patch("transcriber.subprocess.run")
def test_get_audio_duration_subprocess_error(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")

    from transcriber import get_audio_duration

    with pytest.raises(subprocess.CalledProcessError):
        get_audio_duration("test.mp3")

@patch("transcriber.subprocess.run")
def test_get_audio_duration_missing_keys(mock_run):
    mock_run.return_value.stdout = '{"format": {}}'

    from transcriber import get_audio_duration

    with pytest.raises(KeyError):
        get_audio_duration("test.mp3")

@patch("transcriber.subprocess.run")
def test_get_audio_duration_invalid_json(mock_run):
    mock_run.return_value.stdout = 'invalid json'

    import json
    from transcriber import get_audio_duration

    with pytest.raises(json.JSONDecodeError):
        get_audio_duration("test.mp3")

def test_get_client_openai_provider():
    api_key = "test_openai_key"
    with patch("transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key, provider="openai")

        mock_openai.assert_called_once_with(
            api_key=api_key
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["openai"]

def test_get_client_unknown_provider_fallback():
    api_key = "test_unknown_key"
    with patch("transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key, provider="unknown_provider")

        mock_openai.assert_called_once_with(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["groq"]

def test_get_client_default_provider():
    api_key = "test_default_key"
    with patch("transcriber.OpenAI") as mock_openai:
        client, config = get_client(api_key)

        mock_openai.assert_called_once_with(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        assert client == mock_openai.return_value
        assert config == PROVIDERS["groq"]
