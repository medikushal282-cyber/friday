import pytest
import socket
import time
from threading import Thread

# Import the functions/classes to be tested.
# Adjust the import path according to the actual project layout.
try:
    from launch_server import get_free_port, start_server, stop_server, ServerError
except ImportError as e:
    pytest.fail(f"Failed to import launch_server module: {e}")


@pytest.fixture
def free_port():
    """Provide a free TCP port for tests."""
    port = get_free_port()
    # Ensure the port is actually free before yielding.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            pytest.fail(f"Port {port} is not free")
    yield port
    # No explicit cleanup needed; the server fixture will close the socket.


@pytest.fixture
def running_server(free_port):
    """Start a server on a free port and ensure it is stopped after the test."""
    server = start_server(port=free_port)
    # Give the server a moment to bind.
    time.sleep(0.1)
    yield server
    try:
        stop_server(server)
    except Exception:
        pass  # Ensure teardown never fails the test suite.


def test_get_free_port_returns_valid_port():
    port = get_free_port()
    assert isinstance(port, int), "Port should be an integer"
    assert 1024 <= port <= 65535, "Port should be in the user‑space range"


def test_start_server_returns_object_with_port_attribute(running_server, free_port):
    assert hasattr(running_server, "port"), "Server object must expose its listening port"
    assert running_server.port == free_port, "Server should listen on the requested free port"


def test_server_responds_to_connection(running_server):
    """Simple connectivity test – the server should accept a TCP connection."""
    with socket.create_connection(("127.0.0.1", running_server.port), timeout=2) as client:
        # The exact protocol is not defined; just ensure the connection is established.
        assert client.fileno() != -1, "Socket should be open"


def test_start_server_invalid_port_raises():
    with pytest.raises(ValueError):
        start_server(port=-1)
    with pytest.raises(ValueError):
        start_server(port=0)  # Assuming 0 is disallowed in this implementation


def test_stop_server_closes_port(running_server):
    port = running_server.port
    stop_server(running_server)
    # After stopping, the port should be free for a new bind.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Attempt to bind; should succeed if the server truly released the port.
        sock.bind(("127.0.0.1", port))


def test_start_server_on_used_port_raises(free_port):
    # Occupy the port with a dummy socket.
    dummy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    dummy.bind(("127.0.0.1", free_port))
    dummy.listen(1)

    with pytest.raises(ServerError):
        start_server(port=free_port)

    dummy.close()


def test_server_startup_performance(free_port):
    """The server should start quickly (under 200 ms on a typical CI runner)."""
    start_time = time.perf_counter()
    server = start_server(port=free_port)
    elapsed = time.perf_counter() - start_time
    try:
        assert elapsed < 0.2, f"Server startup took too long: {elapsed:.3f}s"
    finally:
        stop_server(server)


def test_server_runs_in_background_thread():
    """Ensure that start_server spawns a background thread (or process) and returns immediately."""
    # Use a very short timeout to detect blocking behavior.
    start = time.perf_counter()
    server = start_server(port=0)  # 0 lets the OS pick a free port.
    elapsed = time.perf_counter() - start
    try:
        assert elapsed < 0.1, "start_server should not block the caller"
        # Verify that the server object has a thread attribute (implementation detail).
        assert isinstance(getattr(server, "thread", None), Thread), "Server should expose its background thread"
        assert server.thread.is_alive(), "Background thread should be running"
    finally:
        stop_server(server)