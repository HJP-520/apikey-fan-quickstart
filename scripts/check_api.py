#!/usr/bin/env python3
"""Zero-dependency API connectivity and latency checker for OpenAI/Anthropic gateways."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    """Structured result for a single API connectivity check."""

    mode: str
    ok: bool
    status_code: int | None
    latency_ms: float
    summary: str


def mask_secret(secret: str) -> str:
    """Return a redacted representation of an API key for safe terminal output."""
    cleaned = secret.strip()
    if not cleaned:
        return "<empty>"
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}...{cleaned[-4:]}"


def normalize_base_url(base_url: str) -> str:
    """Strip trailing slashes and redundant /v1 suffix so endpoint paths stay consistent."""
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[:-3]
    return cleaned


def load_dotenv(env_path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE pairs from a .env file without overwriting existing env vars."""
    parsed: dict[str, str] = {}
    if not env_path.is_file():
        return parsed

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            parsed[key] = value
    return parsed


def resolve_config(
    args: argparse.Namespace,
    env_file: Path | None = None,
) -> tuple[str, str, str, str]:
    """Resolve base URL, API key, and default models from CLI args, environment, and .env."""
    dotenv_values = load_dotenv(env_file or Path(".env"))

    def pick(cli_val: str | None, env_key: str, default: str = "") -> str:
        if cli_val:
            return cli_val.strip()
        if os.environ.get(env_key):
            return os.environ[env_key].strip()
        return dotenv_values.get(env_key, default).strip()

    base_url = normalize_base_url(pick(args.base_url, "API_BASE_URL", "https://apikey.fan"))
    api_key = pick(args.api_key, "API_KEY")
    chat_model = pick(args.model, "DEFAULT_MODEL", "gpt-4o-mini")
    anthropic_model = pick(args.model, "ANTHROPIC_TEST_MODEL", "claude-3-5-sonnet-latest")
    return base_url, api_key, chat_model, anthropic_model


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> tuple[int, dict[str, Any], float]:
    """Send an HTTP JSON request and return (status_code, decoded_json, latency_ms)."""
    req_headers = {"Accept": "application/json", "User-Agent": "apikey-fan-quickstart/1.0"}
    if headers:
        req_headers.update(headers)

    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            body_text = response.read().decode("utf-8", errors="replace")
            decoded = json.loads(body_text) if body_text.strip() else {}
            if not isinstance(decoded, dict):
                decoded = {"raw": decoded}
            return response.status, decoded, elapsed_ms
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {err_body[:300]}") from exc
    except urllib.error.URLError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        raise RuntimeError(f"Network error after {elapsed_ms:.1f} ms: {exc.reason}") from exc


def check_models(base_url: str, api_key: str, timeout: float) -> CheckResult:
    """Verify /v1/models endpoint and count returned models."""
    start = time.perf_counter()
    try:
        status, data, latency_ms = _request_json(
            f"{base_url}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        models = data.get("data", [])
        count = len(models) if isinstance(models, list) else 0
        sample = [m.get("id", "") for m in models[:5] if isinstance(m, dict)] if count else []
        sample_text = f" (sample: {', '.join(sample)})" if sample else ""
        return CheckResult("models", True, status, latency_ms, f"{count} models available{sample_text}")
    except (RuntimeError, json.JSONDecodeError) as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return CheckResult("models", False, None, elapsed_ms, str(exc))


def check_openai_chat(base_url: str, api_key: str, model: str, timeout: float) -> CheckResult:
    """Send a minimal OpenAI-compatible chat completion probe."""
    start = time.perf_counter()
    try:
        status, data, latency_ms = _request_json(
            f"{base_url}/v1/chat/completions",
            method="POST",
            headers={"Authorization": f"Bearer {api_key}"},
            payload={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with OK only."}],
                "max_tokens": 16,
                "temperature": 0,
            },
            timeout=timeout,
        )
        choices = data.get("choices", [])
        reply = ""
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            reply = str(message.get("content", "")).strip()
        return CheckResult("chat", True, status, latency_ms, f"model={model}, reply={reply!r}")
    except (RuntimeError, json.JSONDecodeError) as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return CheckResult("chat", False, None, elapsed_ms, str(exc))


def check_anthropic_messages(base_url: str, api_key: str, model: str, timeout: float) -> CheckResult:
    """Send a minimal Anthropic-compatible /v1/messages probe."""
    start = time.perf_counter()
    try:
        status, data, latency_ms = _request_json(
            f"{base_url}/v1/messages",
            method="POST",
            headers={
                "x-api-key": api_key,
                "Authorization": f"Bearer {api_key}",
                "anthropic-version": "2023-06-01",
            },
            payload={
                "model": model,
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "Reply with OK only."}],
            },
            timeout=timeout,
        )
        content_blocks = data.get("content", [])
        reply = ""
        if isinstance(content_blocks, list) and content_blocks:
            first = content_blocks[0]
            if isinstance(first, dict):
                reply = str(first.get("text", "")).strip()
        return CheckResult("anthropic", True, status, latency_ms, f"model={model}, reply={reply!r}")
    except (RuntimeError, json.JSONDecodeError) as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return CheckResult("anthropic", False, None, elapsed_ms, str(exc))


def build_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Check connectivity and latency for an OpenAI/Anthropic compatible API gateway."
    )
    parser.add_argument(
        "--mode",
        choices=("models", "chat", "anthropic", "all"),
        default="models",
        help="Check mode to run (default: models).",
    )
    parser.add_argument("--base-url", help="Gateway root URL, e.g. https://apikey.fan")
    parser.add_argument("--api-key", help="API key (defaults to API_KEY env var or .env)")
    parser.add_argument("--model", help="Model ID for chat or anthropic checks")
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    base_url, api_key, chat_model, anthropic_model = resolve_config(args)

    if not api_key or api_key == "your_apikey_fan_key_here":
        print(
            "Error: API_KEY is missing. Set API_KEY in environment, .env, or pass --api-key.",
            file=sys.stderr,
        )
        return 2

    print(f"Target : {base_url}")
    print(f"API Key: {mask_secret(api_key)}")

    results: list[CheckResult] = []
    if args.mode in ("models", "all"):
        results.append(check_models(base_url, api_key, args.timeout))
    if args.mode in ("chat", "all"):
        results.append(check_openai_chat(base_url, api_key, chat_model, args.timeout))
    if args.mode in ("anthropic", "all"):
        results.append(check_anthropic_messages(base_url, api_key, anthropic_model, args.timeout))

    all_ok = True
    for res in results:
        badge = "PASS" if res.ok else "FAIL"
        status_text = f"HTTP {res.status_code}" if res.status_code else "ERROR"
        print(f"[{badge}] {res.mode:<9} | {status_text:<8} | {res.latency_ms:7.1f} ms | {res.summary}")
        if not res.ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
