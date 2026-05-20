import pytest
from unittest.mock import patch, MagicMock
from app.core.storage import CloudStorage
from botocore.exceptions import ClientError

@patch('app.core.storage.boto3.client')
def test_upload_file_success(mock_boto_client):
    storage = CloudStorage()
    storage.enabled = True
    storage.bucket = "test-bucket"
    storage.s3 = MagicMock()

    result = storage.upload_file("local.txt", "cloud.txt")

    assert result is True
    storage.s3.upload_file.assert_called_once_with("local.txt", "test-bucket", "cloud.txt")

@patch('app.core.storage.boto3.client')
def test_upload_file_disabled(mock_boto_client):
    storage = CloudStorage()
    storage.enabled = False

    result = storage.upload_file("local.txt", "cloud.txt")

    assert result is False

@patch('app.core.storage.boto3.client')
def test_upload_file_client_error(mock_boto_client):
    storage = CloudStorage()
    storage.enabled = True
    storage.bucket = "test-bucket"
    storage.s3 = MagicMock()

    error_response = {'Error': {'Code': '500', 'Message': 'Error'}}
    storage.s3.upload_file.side_effect = ClientError(error_response, 'upload_file')

    result = storage.upload_file("local.txt", "cloud.txt")

    assert result is False
    storage.s3.upload_file.assert_called_once_with("local.txt", "test-bucket", "cloud.txt")
