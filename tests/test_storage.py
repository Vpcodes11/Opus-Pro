import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import app.core.storage

@pytest.fixture
def mock_storage():
    with patch("app.core.storage.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        with patch("app.core.storage.STORAGE_MODE", "cloud"), \
             patch("app.core.storage.S3_BUCKET_NAME", "test-bucket"):
            storage = app.core.storage.CloudStorage()
            yield storage, mock_s3

def test_download_file_success(mock_storage):
    storage, mock_s3 = mock_storage

    result = storage.download_file("cloud/path.txt", "local/path.txt")

    assert result is True
    mock_s3.download_file.assert_called_once_with("test-bucket", "cloud/path.txt", "local/path.txt")

def test_download_file_client_error(mock_storage, capsys):
    storage, mock_s3 = mock_storage

    error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
    mock_s3.download_file.side_effect = ClientError(error_response, 'download_file')

    result = storage.download_file("cloud/path.txt", "local/path.txt")

    assert result is False
    mock_s3.download_file.assert_called_once_with("test-bucket", "cloud/path.txt", "local/path.txt")

    captured = capsys.readouterr()
    assert "Error downloading from S3:" in captured.out

def test_download_file_disabled():
    with patch("app.core.storage.STORAGE_MODE", "local"):
        storage = app.core.storage.CloudStorage()
        result = storage.download_file("cloud/path.txt", "local/path.txt")
        assert result is False
