import pytest
from main import secure_filename

def test_secure_filename_basic():
    assert secure_filename("my_video.mp4") == "my_video.mp4"
    assert secure_filename("VIDEO-123.mov") == "VIDEO-123.mov"

def test_secure_filename_path_traversal():
    assert secure_filename("../../../etc/passwd") == "passwd"
    assert secure_filename("..\\..\\..\\etc\\passwd") == "passwd"
    assert secure_filename("/var/www/html/upload.php") == "upload.php"

def test_secure_filename_special_chars():
    assert secure_filename("hello word!.mp4") == "hello_word_.mp4"
    assert secure_filename("!@#$%^&*().mp4") == "mp4"
    assert secure_filename("file_name_with_spaces.mp4") == "file_name_with_spaces.mp4"

def test_secure_filename_edge_cases():
    assert secure_filename("") == "unnamed_file"
    assert secure_filename(None) == "unnamed_file"
    assert secure_filename("...") == "unnamed_file"
    assert secure_filename("..") == "unnamed_file"
    assert secure_filename(".hidden") == "hidden"
    assert secure_filename("-flag") == "flag"
