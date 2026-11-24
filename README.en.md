[简体中文](README.md) | [English](README.en.md)

# apikey.fan Quickstart Guide & Connectivity Tester

A developer-focused setup reference, client troubleshooting guide, and zero-dependency connectivity test utility for [`apikey.fan`](https://apikey.fan/) (an OpenAI / Anthropic compatible API gateway).

---

## Getting an API Key (With Disclosure)

Before running the examples in this repository, create an account and generate your own API key:

- **Direct Homepage**: https://apikey.fan/
- **Referral Registration Link**: https://apikey.fan/register?aff=F4EUYEK8DRM5
- **Invite Code**: `F4EUYEK8DRM5`

> **Disclosure**: The referral link above contains an affiliate parameter (`aff=F4EUYEK8DRM5`). If you sign up through it, the maintainer may receive a referral reward at no extra cost to you. You are always welcome to use the direct homepage link above instead. Keep your API keys private and never commit `.env` files to version control.

---

## Client & SDK Configuration

### 1. Claude Code (Anthropic-Compatible Format)

> ⚠️ **Path Notice**: Claude Code automatically appends `/v1/messages` to `ANTHROPIC_BASE_URL`. Set the root domain `https://apikey.fan` **without** `/v1`, otherwise requests may hit `/v1/v1/messages` and return `404 Not Found`.

**Option A: Environment Variables**

```bash
export ANTHROPIC_BASE_URL="https://apikey.fan"
export ANTHROPIC_AUTH_TOKEN="your_apikey_fan_key"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_BASE_URL = "https://apikey.fan"
$env:ANTHROPIC_AUTH_TOKEN = "your_apikey_fan_key"
```

**Option B: `~/.claude/settings.json`**

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://apikey.fan",
    "ANTHROPIC_AUTH_TOKEN": "your_apikey_fan_key"
  }
}
```

---

### 2. OpenAI-Compatible Clients (Cherry Studio / Chatbox / Cursor / SDK)

Most OpenAI-compatible SDKs and desktop apps expect `/v1` in the base URL (verify whether your client appends `/v1` automatically):

- **API Base URL**: `https://apikey.fan/v1`
- **API Key**: Your `sk-...` token from the dashboard

**Python (`openai` SDK) Example:**

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://apikey.fan/v1",
    api_key=os.environ["API_KEY"],
)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp.choices[0].message.content)
```

**cURL Quick Check:**

```bash
curl https://apikey.fan/v1/models \
  -H "Authorization: Bearer $API_KEY"
```

---

## Local Connectivity & Latency Checker

This repository includes [`scripts/check_api.py`](scripts/check_api.py), a zero-dependency Python 3.9+ script (standard library only) to verify API keys, list available models, and measure response latency.

```bash
# 1. Clone the repository
git clone https://github.com/HJP-520/apikey-fan-quickstart.git
cd apikey-fan-quickstart

# 2. Copy the template and set your own API key (.env is git-ignored)
cp .env.example .env

# 3. Check available models
python scripts/check_api.py --mode models

# 4. Test OpenAI-compatible chat latency
python scripts/check_api.py --mode chat --model gpt-4o-mini

# 5. Test Anthropic-compatible messages latency
python scripts/check_api.py --mode anthropic --model claude-3-5-sonnet-latest
```

Run `python scripts/check_api.py --help` for all options.

---

## Troubleshooting

| Symptom | Likely Cause | Suggested Fix |
| --- | --- | --- |
| `401 Unauthorized` | Invalid, disabled, or depleted API key | Verify token string and balance in your dashboard |
| `404 Not Found` | Duplicate or missing `/v1` segment | Use `https://apikey.fan` for Claude Code; `https://apikey.fan/v1` for most OpenAI SDKs |
| `429 Too Many Requests` | Rate limit reached | Lower request concurrency or check tier limits |
| Timeout / SSL Error | Local proxy or network configuration | Check `HTTP_PROXY` / `HTTPS_PROXY` and re-test with `check_api.py` |

## License

Released under the [MIT License](LICENSE).
