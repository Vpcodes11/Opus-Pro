import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from app.core.storage import CloudStorage

def test_delete_file_disabled():
    with patch("app.core.storage.STORAGE_MODE", "local"):
        storage = CloudStorage()
        storage.enabled = False
        assert storage.delete_file("some_path") == False

def test_delete_file_success():
    with patch("app.core.storage.STORAGE_MODE", "cloud"):
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_boto.return_value = mock_client

            storage = CloudStorage()
            storage.enabled = True
            storage.s3 = mock_client
            storage.bucket = "test-bucket"

            assert storage.delete_file("test/path.txt") == True
            mock_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="test/path.txt")

def test_delete_file_client_error():
    with patch("app.core.storage.STORAGE_MODE", "cloud"):
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            error_response = {'Error': {'Code': '500', 'Message': 'Error'}}
            mock_client.delete_object.side_effect = ClientError(error_response, 'delete_object')
            mock_boto.return_value = mock_client

            storage = CloudStorage()
            storage.enabled = True
            storage.s3 = mock_client
            storage.bucket = "test-bucket"

            assert storage.delete_file("test/path.txt") == False
