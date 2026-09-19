import http.server
import socketserver
import argparse
import sys
import os
from pathlib import Path
import unittest
import tempfile

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Basic Site</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; background:#f0f0f0; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Welcome to the Basic HTML Site</h1>
    <p>This page is served by a simple Python HTTP server.</p>
</body>
</html>
"""

def ensure_index_html(directory: Path) -> Path:
    """Create an index.html file with basic content if it doesn't exist."""
    index_path = directory / "index.html"
    if not index_path.exists():
        try:
            index_path.write_text(HTML_CONTENT, encoding="utf-8")
            print(f"Created default index.html at {index_path}")
        except OSError as exc:
            sys.stderr.write(f"Failed to write index.html: {exc}\n")
            sys.exit(1)
    else:
        print(f"Using existing index.html at {index_path}")
    return index_path

def create_server(port: int, directory: Path) -> socketserver.TCPServer:
    """Create a threaded HTTP server bound to ``port`` serving ``directory``."""
    handler_class = http.server.SimpleHTTPRequestHandler
    # Python 3.7+ allows passing a directory to the handler
    handler = lambda *args, **kwargs: handler_class(*args, directory=str(directory), **kwargs)
    return socketserver.ThreadingTCPServer(("", port), handler)

def run_server(port: int, directory: Path):
    """Start an HTTP server serving the given directory."""
    httpd = create_server(port, directory)
    try:
        print(f"Serving HTTP on 0.0.0.0 port {port} (http://localhost:{port}/) ...")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except OSError as exc:
        sys.stderr.write(f"Server error: {exc}\n")
    finally:
        httpd.server_close()

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Launch a simple HTML website using Python's built‑in HTTP server.")
    parser.add_argument("-p", "--port", type=int, default=8000,
                        help="Port number to bind the HTTP server (default: 8000).")
    parser.add_argument("-d", "--directory", type=Path, default=Path.cwd(),
                        help="Directory containing the site files (default: current working directory).")
    parser.add_argument("--test", action="store_true",
                        help="Run the built‑in test suite and exit.")
    return parser.parse_args(argv)

# ------------------------------ Unit Tests ------------------------------

class TestLaunchServer(unittest.TestCase):
    def test_ensure_index_html_creates_file(self):
        with tempfile.TemporaryDirectory() as td:
            dir_path = Path(td)
            index_path = dir_path / "index.html"
            self.assertFalse(index_path.exists())
            result = ensure_index_html(dir_path)
            self.assertTrue(index_path.exists())
            self.assertEqual(result, index_path)
            self.assertEqual(index_path.read_text(encoding="utf-8"), HTML_CONTENT)

    def test_ensure_index_html_uses_existing(self):
        with tempfile.TemporaryDirectory() as td:
            dir_path = Path(td)
            custom_content = "<html>custom</html>"
            index_path = dir_path / "index.html"
            index_path.write_text(custom_content, encoding="utf-8")
            result = ensure_index_html(dir_path)
            self.assertTrue(index_path.exists())
            self.assertEqual(result, index_path)
            self.assertEqual(index_path.read_text(encoding="utf-8"), custom_content)

    def test_parse_args_defaults(self):
        args = parse_args([])
        self.assertEqual(args.port, 8000)
        self.assertEqual(args.directory, Path.cwd())
        self.assertFalse(args.test)

    def test_parse_args_custom(self):
        args = parse_args(["-p", "9090", "-d", "/tmp"])
        self.assertEqual(args.port, 9090)
        self.assertEqual(args.directory, Path("/tmp"))
        self.assertFalse(args.test)

    def test_create_server_bind(self):
        with tempfile.TemporaryDirectory() as td:
            dir_path = Path(td)
            # Use an unlikely high port to avoid collisions; OS will assign if 0.
            server = create_server(0, dir_path)
            try:
                self.assertTrue(server.server_address[1] > 0)
                # Ensure the server's handler serves from the correct directory
                handler = server.RequestHandlerClass
                # The handler is a lambda that returns SimpleHTTPRequestHandler with directory set
                # We verify that invoking it yields an instance with the expected directory attribute
                request = unittest.mock.MagicMock()
                client_address = ('127.0.0.1', 12345)
                server_instance = server
                handler_instance = handler(request, client_address, server_instance)
                self.assertEqual(handler_instance.directory, str(dir_path))
            finally:
                server.server_close()

# ------------------------------ Main Execution ------------------------------

if __name__ == "__main__":
    args = parse_args()
    if args.test:
        unittest.main(argv=[sys.argv[0]])
    else:
        target_dir = args.directory.resolve()
        if not target_dir.is_dir():
            sys.stderr.write(f"The specified directory does not exist: {target_dir}\\n")
            sys.exit(1)

        ensure_index_html(target_dir)
        run_server(args.port, target_dir)