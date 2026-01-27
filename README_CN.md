# ai-lib-python

**AI-Protocol 协议运行时** - 统一 AI 模型交互的 Python 实现。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://github.com/hiddenpath/ai-lib-python/actions/workflows/ci.yml/badge.svg)](https://github.com/hiddenpath/ai-lib-python/actions)

## 概述

`ai-lib-python` 是 [AI-Protocol](https://github.com/hiddenpath/ai-protocol) 规范的 Python 运行时实现。它体现了核心设计原则：

> **所有逻辑皆为算子，所有配置皆为协议。**

与传统的适配器库硬编码特定提供商逻辑不同，`ai-lib-python` 是一个**协议驱动的运行时**，执行 AI-Protocol 规范。

## 特性

- **协议驱动**: 所有行为由 YAML/JSON 协议文件驱动
- **统一接口**: 单一 API 支持所有 AI 提供商（OpenAI、Anthropic、Gemini、DeepSeek 等）
- **流式优先**: 原生异步流式处理，使用 Python 的 `async for`
- **类型安全**: 完整的类型注解，基于 Pydantic v2 模型
- **生产就绪**: 内置重试、限流、熔断和降级支持
- **易于扩展**: 通过协议配置轻松添加新提供商
- **多模态支持**: 支持文本、图像（base64/URL）和音频
- **遥测功能**: 结构化日志、指标收集和分布式追踪
- **Token 计数**: tiktoken 集成和成本估算
- **连接池**: 高效的 HTTP 连接管理
- **批处理**: 并发执行与并发控制

## 安装

```bash
pip install ai-lib-python
```

安装可选功能：

```bash
# 完整安装，包含所有功能
pip install ai-lib-python[full]

# 遥测功能（OpenTelemetry 集成）
pip install ai-lib-python[telemetry]

# Token 计数（tiktoken）
pip install ai-lib-python[tokenizer]

# Jupyter notebook 集成
pip install ai-lib-python[jupyter]

# 开发环境
pip install ai-lib-python[dev]
```

## 快速入门

### 基础用法

```python
import asyncio
from ai_lib_python import AiClient, Message

async def main():
    # 创建客户端
    client = await AiClient.create("openai/gpt-4o")
    
    # 简单的聊天补全
    response = await (
        client.chat()
        .user("你好！2+2 等于多少？")
        .execute()
    )
    print(response.content)
    # 输出: 2+2 等于 4。
    
    await client.close()

asyncio.run(main())
```

### 流式响应

```python
async def stream_example():
    client = await AiClient.create("anthropic/claude-3-5-sonnet")
    
    async for event in (
        client.chat()
        .system("你是一个乐于助人的助手。")
        .user("讲一个简短的故事。")
        .stream()
    ):
        if event.is_content_delta:
            print(event.as_content_delta.content, end="", flush=True)
    
    print()  # 末尾换行
    await client.close()
```

### 使用消息列表

```python
from ai_lib_python import Message

messages = [
    Message.system("你是一个 Python 专家。"),
    Message.user("如何在 Python 中读取文件？"),
]

response = await (
    client.chat()
    .messages(messages)
    .temperature(0.7)
    .max_tokens(1024)
    .execute()
)
```

### 工具调用（函数调用）

```python
from ai_lib_python import ToolDefinition

# 定义工具
weather_tool = ToolDefinition.from_function(
    name="get_weather",
    description="获取指定地点的当前天气",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "城市名称"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
        },
        "required": ["location"]
    }
)

# 在请求中使用工具
response = await (
    client.chat()
    .user("东京的天气怎么样？")
    .tools([weather_tool])
    .execute()
)

# 检查工具调用
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"调用 {tool_call.function_name}: {tool_call.arguments}")
```

### 多模态（图像）

```python
from ai_lib_python import Message, ContentBlock

# 通过 URL 传入图像
message = Message.user_with_image(
    "这张图片里有什么？",
    image_url="https://example.com/image.jpg"
)

# 通过 base64 传入图像
with open("photo.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

message = Message(
    role=MessageRole.USER,
    content=[
        ContentBlock.text("描述这张图片："),
        ContentBlock.image_base64(image_data, "image/jpeg"),
    ]
)

response = await client.chat().messages([message]).execute()
```

### 生产就绪配置

```python
from ai_lib_python import AiClient

# 启用所有弹性模式
client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .production_ready()  # 启用重试、限流、熔断
    .with_fallbacks(["anthropic/claude-3-5-sonnet"])
    .build()
)

# 检查弹性状态
print(f"熔断状态: {client.circuit_state}")
print(f"正在处理的请求: {client.current_inflight}")
print(client.get_resilience_stats())
```

### 自定义弹性配置

```python
from ai_lib_python import AiClient
from ai_lib_python.resilience import (
    RetryConfig,
    RateLimiterConfig,
    CircuitBreakerConfig,
)

client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .with_retry(RetryConfig(
        max_retries=5,
        min_delay_ms=1000,
        max_delay_ms=30000,
    ))
    .with_rate_limit(RateLimiterConfig.from_rps(10))
    .with_circuit_breaker(CircuitBreakerConfig(
        failure_threshold=5,
        cooldown_seconds=30,
    ))
    .max_inflight(20)
    .build()
)
```

### 上下文管理器

```python
async with await AiClient.create("openai/gpt-4o") as client:
    response = await client.chat().user("你好！").execute()
    print(response.content)
# 客户端自动关闭
```

## 支持的提供商

| 提供商 | 模型 | 流式 | 工具调用 | 视觉 |
|--------|------|------|----------|------|
| OpenAI | GPT-4o, GPT-4, GPT-3.5 | ✅ | ✅ | ✅ |
| Anthropic | Claude 3.5, Claude 3 | ✅ | ✅ | ✅ |
| Google | Gemini Pro, Gemini Flash | ✅ | ✅ | ✅ |
| DeepSeek | DeepSeek Chat, Coder | ✅ | ✅ | ❌ |
| 通义千问 | Qwen2.5, Qwen-Max | ✅ | ✅ | ✅ |
| Groq | Llama, Mixtral | ✅ | ✅ | ❌ |
| Mistral | Mistral Large, Medium | ✅ | ✅ | ❌ |

## API 参考

### 核心类

- **`AiClient`**: AI 模型交互的主入口
- **`Message`**: 表示聊天消息，包含角色和内容
- **`ContentBlock`**: 多模态消息的内容块
- **`ToolDefinition`**: 函数调用的工具/函数定义
- **`StreamingEvent`**: 流式响应的事件

### 弹性类

- **`RetryPolicy`**: 带抖动的指数退避重试
- **`RateLimiter`**: 令牌桶限流
- **`CircuitBreaker`**: 熔断器模式
- **`Backpressure`**: 并发限制
- **`FallbackChain`**: 多目标降级

### 错误类

- **`AiLibError`**: 基础错误类
- **`ProtocolError`**: 协议加载/验证错误
- **`TransportError`**: HTTP 传输错误
- **`RemoteError`**: 提供商返回的 API 错误

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                        AiClient                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ ChatRequest │  │  Resilience │  │    Protocol         │  │
│  │   Builder   │  │  Executor   │  │    Loader           │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼───────────────────┼──────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────┐ ┌──────────────┐ ┌─────────────────────┐
│   HttpTransport │ │   Pipeline   │ │  ProtocolManifest   │
│   (httpx)       │ │   (解码→    │ │  (YAML/JSON)        │
│                 │ │   选择→     │ │                     │
│                 │ │   映射)     │ │                     │
└─────────────────┘ └──────────────┘ └─────────────────────┘
```

## 开发

```bash
# 克隆仓库
git clone https://github.com/hiddenpath/ai-lib-python.git
cd ai-lib-python

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src/ai_lib_python

# 类型检查
mypy src

# 代码检查
ruff check src tests

# 格式化代码
ruff format src tests
```

## 项目结构

```
ai-lib-python/
├── src/ai_lib_python/
│   ├── __init__.py         # 包导出
│   ├── types/              # 类型定义
│   │   ├── message.py      # Message, ContentBlock
│   │   ├── tool.py         # ToolDefinition, ToolCall
│   │   └── events.py       # StreamingEvent 类型
│   ├── protocol/           # 协议层
│   │   ├── manifest.py     # ProtocolManifest 模型
│   │   ├── loader.py       # 协议加载
│   │   └── validator.py    # Schema 验证
│   ├── transport/          # HTTP 传输
│   │   ├── http.py         # HttpTransport
│   │   └── auth.py         # API 密钥解析
│   ├── pipeline/           # 流处理
│   │   ├── decode.py       # SSE/NDJSON 解码器
│   │   ├── select.py       # JSONPath 选择器
│   │   ├── accumulate.py   # 工具调用累积器
│   │   └── event_map.py    # 事件映射器
│   ├── resilience/         # 弹性模式
│   │   ├── retry.py        # 重试策略
│   │   ├── rate_limiter.py # 限流器
│   │   ├── circuit_breaker.py  # 熔断器
│   │   ├── backpressure.py # 背压控制
│   │   ├── fallback.py     # 降级链
│   │   └── executor.py     # 弹性执行器
│   ├── client/             # 用户 API
│   │   ├── core.py         # AiClient
│   │   ├── builder.py      # 构建器
│   │   └── response.py     # ChatResponse
│   └── errors/             # 错误层次
├── tests/
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── docs/                   # 文档
├── examples/               # 示例脚本
└── pyproject.toml
```

## 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | - |
| `GOOGLE_API_KEY` | Google AI API 密钥 | - |
| `AI_PROTOCOL_PATH` | 自定义协议目录 | - |
| `AI_HTTP_TIMEOUT_SECS` | HTTP 超时时间 | 60 |
| `AI_LIB_MAX_INFLIGHT` | 最大并发请求数 | 10 |

## 相关项目

- [AI-Protocol](https://github.com/hiddenpath/ai-protocol) - 协议规范
- [ai-lib-rust](https://github.com/hiddenpath/ai-lib-rust) - Rust 运行时实现

## 贡献

欢迎贡献！请阅读我们的 [贡献指南](CONTRIBUTING.md) 了解详情。

## 许可证

本项目采用以下任一许可证：

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) 或 http://www.apache.org/licenses/LICENSE-2.0)
- MIT License ([LICENSE-MIT](LICENSE-MIT) 或 http://opensource.org/licenses/MIT)

由您选择。
