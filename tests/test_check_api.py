"""Unit and local mock-server tests for scripts/check_api.py."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "scripts"))

import check_api  # noqa: E402


class _MockGatewayHandler(BaseHTTPRequestHandler):
    """Minimal local HTTP handler simulating OpenAI and Anthropic endpoints."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "gpt-4o-mini"}, {"id": "claude-3-5-sonnet-latest"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        if self.path == "/v1/chat/completions":
            body = json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/v1/messages":
            body = json.dumps({"content": [{"type": "text", "text": "OK"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


class CheckApiTests(unittest.TestCase):
    """Tests for helper functions and mock HTTP probes."""

    def test_mask_secret(self) -> None:
        self.assertEqual(check_api.mask_secret(""), "<empty>")
        self.assertEqual(check_api.mask_secret("abcd"), "****")
        self.assertEqual(check_api.mask_secret("sk-1234567890abcd"), "sk-1...abcd")

    def test_normalize_base_url(self) -> None:
        self.assertEqual(check_api.normalize_base_url("https://apikey.fan/"), "https://apikey.fan")
        self.assertEqual(check_api.normalize_base_url("https://apikey.fan/v1/"), "https://apikey.fan")

    def test_load_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text('# comment\nAPI_BASE_URL="https://apikey.fan"\nAPI_KEY=sk-test-1234\n', encoding="utf-8")
            parsed = check_api.load_dotenv(env_file)
            self.assertEqual(parsed["API_BASE_URL"], "https://apikey.fan")
            self.assertEqual(parsed["API_KEY"], "sk-test-1234")

    def test_mock_gateway_endpoints(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _MockGatewayHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            models_res = check_api.check_models(base_url, "sk-mock-key", timeout=5.0)
            chat_res = check_api.check_openai_chat(base_url, "sk-mock-key", "gpt-4o-mini", timeout=5.0)
            anth_res = check_api.check_anthropic_messages(base_url, "sk-mock-key", "claude-3-5-sonnet-latest", timeout=5.0)

            self.assertTrue(models_res.ok)
            self.assertIn("2 models available", models_res.summary)
            self.assertTrue(chat_res.ok)
            self.assertIn("OK", chat_res.summary)
            self.assertTrue(anth_res.ok)
            self.assertIn("OK", anth_res.summary)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
