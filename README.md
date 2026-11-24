[简体中文](README.md) | [English](README.en.md)

# apikey.fan 快速接入指南与连通性测试工具

面向开发者的 [`apikey.fan`](https://apikey.fan/)（OpenAI / Anthropic 标准兼容 API 中转网关）配置参考、常见客户端避坑指南与零依赖本地连通性测速脚本。

---

## 获取 API Key（含合规披露）

在使用本仓库的配置示例前，你需要先获取自己的 API Key：

- **官网直达**：https://apikey.fan/
- **邀请注册链接**：https://apikey.fan/register?aff=F4EUYEK8DRM5
- **邀请码**：`F4EUYEK8DRM5`

> **透明披露**：上方邀请链接包含个人推广标识（`aff=F4EUYEK8DRM5`）。如果你通过该邀请链接注册，作者可能会获得平台提供的推广返佣，但不会影响你的正常使用与费率；如介意，可直接访问官网直链注册。使用任何第三方 API 中转服务时，建议遵循最小权限原则，妥善保管密钥并按需充值。

---

## 客户端与 SDK 快速配置

### 1. Claude Code（Anthropic 兼容格式）

> ⚠️ **注意路径格式**：Claude Code 会自动在 `ANTHROPIC_BASE_URL` 末尾拼接 `/v1/messages`，因此填写根域名 `https://apikey.fan` 即可，**不要**额外加上 `/v1`，否则可能出现 `404 Not Found`（`/v1/v1/messages`）。

**方式 A：终端环境变量**

```bash
export ANTHROPIC_BASE_URL="https://apikey.fan"
export ANTHROPIC_AUTH_TOKEN="your_apikey_fan_key"
```

Windows PowerShell：

```powershell
$env:ANTHROPIC_BASE_URL = "https://apikey.fan"
$env:ANTHROPIC_AUTH_TOKEN = "your_apikey_fan_key"
```

**方式 B：写入 `~/.claude/settings.json`**

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://apikey.fan",
    "ANTHROPIC_AUTH_TOKEN": "your_apikey_fan_key"
  }
}
```

---

### 2. OpenAI 兼容客户端（Cherry Studio / Chatbox / Cursor / SDK）

多数支持自定义接口的客户端需要带 `/v1` 的 Base URL（部分客户端会自动补全 `/v1`，请以客户端输入框提示为准）：

- **API Base URL**：`https://apikey.fan/v1`
- **API Key**：在控制台创建的 `sk-...` 密钥

**Python（官方 `openai` SDK）示例：**

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

**cURL 快速验证：**

```bash
curl https://apikey.fan/v1/models \
  -H "Authorization: Bearer $API_KEY"
```

---

## 本地连通性与延迟测速脚本

本仓库内置零第三方依赖的 Python 脚本 [`scripts/check_api.py`](scripts/check_api.py)（仅使用 Python 3.9+ 标准库），可用于验证密钥有效性、拉取可用模型列表及测量对话接口响应耗时。

### 使用步骤

```bash
# 1. 克隆仓库
git clone https://github.com/HJP-520/apikey-fan-quickstart.git
cd apikey-fan-quickstart

# 2. 复制环境变量模板并填入你自己的密钥（.env 已被 .gitignore 忽略）
cp .env.example .env

# 3. 检查可用模型列表
python scripts/check_api.py --mode models

# 4. 测试 OpenAI 兼容对话接口延迟
python scripts/check_api.py --mode chat --model gpt-4o-mini

# 5. 测试 Anthropic 兼容消息接口延迟
python scripts/check_api.py --mode anthropic --model claude-3-5-sonnet-latest
```

更多参数可通过 `python scripts/check_api.py --help` 查看。

---

## 常见问题排查

| 现象 | 可能原因 | 建议排查方向 |
| --- | --- | --- |
| `401 Unauthorized` | API Key 填写错误、已禁用或余额不足 | 核对密钥是否完整复制、检查控制台令牌状态与额度 |
| `404 Not Found` | Base URL 多填或漏填 `/v1` | Claude Code 填 `https://apikey.fan`；多数 OpenAI SDK 填 `https://apikey.fan/v1` |
| `429 Too Many Requests` | 并发或频率触发限流 | 降低请求并发，或联系站点支持确认当前分组速率限制 |
| 连接超时 / SSL 异常 | 本地代理或系统网络环境影响 | 检查终端代理变量 `HTTP_PROXY` / `HTTPS_PROXY`，使用 `check_api.py` 复测 |

---

## 仓库目录结构

```text
.
├── docs/
│   └── index.html          # 可直接部署为 GitHub Pages 的双语交互指南页
├── scripts/
│   └── check_api.py        # 零依赖 API 连通性与延迟检测脚本
├── tests/
│   └── test_check_api.py   # 脚本单元测试
├── .env.example            # 环境变量示例（不含真实密钥）
├── .gitignore
├── LICENSE                 # MIT License
├── README.md               # 简体中文文档
└── README.en.md            # English documentation
```

## 开源协议

本项目代码与文档模板基于 [MIT License](LICENSE) 开源。
