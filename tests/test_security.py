import socket
import threading
import time
import pytest
import uvicorn
from main import app

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def server():
    port = get_free_port()
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to start by attempting to connect
    for _ in range(20):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            s.close()
            break
        except ConnectionRefusedError:
            time.sleep(0.1)

    yield port
    server.should_exit = True
    thread.join()

def test_preview_path_traversal(server):
    port = server
    # Testing path traversal using raw socket to avoid HTTP client URL normalization
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))
    s.sendall(b"GET /api/preview/../test.txt HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
    response = s.recv(1024).decode()
    s.close()

    assert "400 Bad Request" in response
    assert '{"error":"Invalid path"}' in response

def test_download_path_traversal(server):
    port = server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", port))
    s.sendall(b"GET /api/download/../test.txt HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
    response = s.recv(1024).decode()
    s.close()

    assert "400 Bad Request" in response
    assert '{"error":"Invalid path"}' in response
