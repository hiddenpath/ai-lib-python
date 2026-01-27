# ai-lib-python 项目需求与开发计划

> **项目定位**: AI-Protocol 的 Python 运行时实现  
> **核心理念**: 一切逻辑皆算子，一切配置皆协议  
> **目标**: 充分发挥 Python 语言特性，构建 Pythonic、高性能、易扩展的 AI 基础设施库

---

## 一、项目背景与愿景

### 1.1 AI-Protocol 生态系统定位

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI-Protocol 生态系统                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐                                       │
│   │   ai-protocol       │  数据态规则书 (Data-State Rulebook)    │
│   │   (协议规范层)       │  • Provider 配置                      │
│   └──────────┬──────────┘  • Model 注册                         │
│              │             • 标准化事件/参数                      │
│              ▼                                                  │
│   ┌──────────────────────────────────────────────────┐          │
│   │           语言态运行时 (Language Runtimes)        │          │
│   ├─────────────────┬─────────────────┬──────────────┤          │
│   │  ai-lib-rust    │  ai-lib-python  │  ai-lib-ts   │          │
│   │  (已实现)        │  (本项目)        │  (规划中)    │          │
│   └─────────────────┴─────────────────┴──────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Python 实现的独特价值

Python 作为 AI/ML 领域的主导语言，具备以下不可替代的优势：

| 特性 | 对 ai-lib-python 的价值 |
|------|------------------------|
| **动态类型系统** | 运行时协议解析、灵活的配置映射 |
| **元编程能力** | 动态生成 Provider 适配器、装饰器模式 |
| **异步生态 (asyncio)** | 原生流式处理、高并发支持 |
| **类型提示 (typing)** | IDE 智能补全、静态分析兼容 |
| **Pydantic 生态** | 协议模型验证、自动序列化 |
| **Jupyter 集成** | 交互式开发、数据科学工作流 |
| **丰富的 HTTP 库** | httpx/aiohttp 异步支持 |

---

## 二、核心需求规格

### 2.1 功能性需求

#### 2.1.1 协议层 (Protocol Layer)

```python
# 目标 API 示例
from ai_lib_python import ProtocolLoader, ProtocolValidator

# 1. 协议加载 - 支持多种数据源
loader = ProtocolLoader()
manifest = await loader.load_provider("anthropic")
manifest = await loader.load_model("anthropic/claude-3-5-sonnet")

# 2. 协议验证 - 基于 JSON Schema
validator = ProtocolValidator()
result = validator.validate(manifest)

# 3. 热重载支持
loader = ProtocolLoader(hot_reload=True, watch_interval=5.0)
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| P-001 | 协议文件加载 | P0 | 支持本地路径、环境变量、GitHub URL |
| P-002 | JSON Schema 验证 | P0 | 使用 jsonschema 或 fastjsonschema |
| P-003 | 热重载机制 | P1 | watchdog 文件监控 + 缓存失效 |
| P-004 | 协议版本管理 | P1 | 支持 v1.x 稳定版和 v2-alpha 实验版 |
| P-005 | 嵌入式离线模式 | P2 | 内置 schema 确保离线可用 |

#### 2.1.2 类型层 (Types Layer)

```python
# 基于 Pydantic v2 的类型系统
from ai_lib_python.types import Message, MessageRole, ContentBlock
from ai_lib_python.types import ToolDefinition, ToolCall
from ai_lib_python.types import StreamingEvent

# 1. 消息构建 - Pythonic API
msg = Message.user("Hello, Claude!")
msg = Message.system("You are a helpful assistant.")
msg = Message.with_content(
    role=MessageRole.USER,
    content=[
        ContentBlock.text("Describe this image:"),
        ContentBlock.image_from_file("photo.jpg"),
    ]
)

# 2. 工具定义 - 支持 Python 函数装饰器
@tool
def get_weather(city: str, unit: str = "celsius") -> dict:
    """获取指定城市的天气信息"""
    ...

# 3. 流式事件 - 类型安全
event: StreamingEvent
match event:
    case StreamingEvent.PartialContentDelta(content=c):
        print(c, end="")
    case StreamingEvent.ToolCallStarted(tool_name=name):
        print(f"Calling tool: {name}")
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| T-001 | Pydantic v2 数据模型 | P0 | Message, ContentBlock, Tool 等核心类型 |
| T-002 | 流式事件枚举 | P0 | 与 ai-protocol 标准事件对齐 |
| T-003 | 工具装饰器 | P1 | 从 Python 函数自动生成 ToolDefinition |
| T-004 | 多模态支持 | P1 | 图像/音频 Base64 编码、URL 引用 |
| T-005 | 序列化/反序列化 | P0 | JSON/Dict 双向转换 |

#### 2.1.3 管道层 (Pipeline Layer) - 核心创新

```python
# 算子化管道设计
from ai_lib_python.pipeline import Pipeline, Decoder, Selector, Accumulator, EventMapper

# 1. 从协议配置构建管道
pipeline = Pipeline.from_manifest(manifest)

# 2. 可组合的算子链
pipeline = (
    Pipeline()
    .decode(SSEDecoder())
    .select(JsonPathSelector("exists($.choices)"))
    .accumulate(ToolCallAccumulator())
    .map(StandardEventMapper())
)

# 3. 流处理
async for event in pipeline.process(byte_stream):
    yield event
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| PL-001 | SSE 解码器 | P0 | Server-Sent Events 流解析 |
| PL-002 | JSON Lines 解码器 | P1 | 支持 NDJSON 格式 |
| PL-003 | JSONPath 选择器 | P0 | 基于 jsonpath-ng 的帧过滤 |
| PL-004 | 工具调用累加器 | P0 | 流式工具参数组装 |
| PL-005 | 事件映射器 | P0 | 协议驱动的事件归一化 |
| PL-006 | FanOut 算子 | P1 | 多候选场景支持 |

#### 2.1.4 传输层 (Transport Layer)

```python
from ai_lib_python.transport import HttpTransport

# 1. 基于 httpx 的异步传输
transport = HttpTransport(
    base_url="https://api.anthropic.com",
    timeout=30.0,
    proxy=os.getenv("AI_PROXY_URL"),
)

# 2. 流式响应
async with transport.stream_request(method, path, payload) as response:
    async for chunk in response.aiter_bytes():
        yield chunk

# 3. 自动 API Key 解析
# 优先级: 显式传入 > 环境变量 (PROVIDER_API_KEY) > keyring
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| TR-001 | httpx 异步客户端 | P0 | 流式/非流式统一支持 |
| TR-002 | 代理支持 | P1 | HTTP/HTTPS/SOCKS 代理 |
| TR-003 | 超时配置 | P0 | 连接/读取/写入超时分离 |
| TR-004 | API Key 管理 | P0 | 环境变量 + keyring 集成 |
| TR-005 | 重试中间件 | P1 | 可插拔的请求中间件 |

#### 2.1.5 客户端层 (Client Layer)

```python
from ai_lib_python import AiClient

# 1. 极简初始化
client = await AiClient.create("anthropic/claude-3-5-sonnet")

# 2. 链式 Builder API
response = await (
    client.chat()
    .messages([Message.user("Hello!")])
    .temperature(0.7)
    .max_tokens(1024)
    .execute()
)

# 3. 流式处理 - Python async generator
async for event in client.chat().messages(msgs).stream():
    match event:
        case StreamingEvent.PartialContentDelta(content=c):
            print(c, end="", flush=True)

# 4. 取消支持
handle = client.chat().messages(msgs).stream_with_cancel()
async for event in handle:
    if should_stop:
        await handle.cancel()
        break

# 5. 统计信息
response, stats = await client.chat().messages(msgs).execute_with_stats()
print(f"Latency: {stats.latency_ms}ms, Tokens: {stats.total_tokens}")
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| C-001 | AiClient 核心类 | P0 | 统一入口，协议驱动 |
| C-002 | ChatBuilder API | P0 | 流畅的链式调用 |
| C-003 | 流式执行 | P0 | async generator 模式 |
| C-004 | 非流式执行 | P0 | await 单次响应 |
| C-005 | 取消机制 | P1 | 优雅终止流式请求 |
| C-006 | 调用统计 | P1 | 延迟、Token、重试次数 |
| C-007 | 批量执行 | P2 | chat_batch / chat_batch_smart |

#### 2.1.6 弹性层 (Resilience Layer)

```python
from ai_lib_python import AiClient
from ai_lib_python.resilience import CircuitBreaker, RateLimiter

# 1. 构建时配置
client = await (
    AiClient.builder()
    .model("anthropic/claude-3-5-sonnet")
    .with_fallbacks(["openai/gpt-4o", "deepseek/deepseek-chat"])
    .max_inflight(10)
    .rate_limit(rps=5.0)
    .circuit_breaker(failure_threshold=5, cooldown_secs=30)
    .build()
)

# 2. 环境变量配置 (生产友好)
# AI_LIB_MAX_INFLIGHT=10
# AI_LIB_RPS=5
# AI_LIB_BREAKER_FAILURE_THRESHOLD=5
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| R-001 | 重试策略 | P0 | 指数退避 + Jitter |
| R-002 | 速率限制 | P1 | Token Bucket 算法 |
| R-003 | 自适应限流 | P1 | 基于响应头动态调整 |
| R-004 | 熔断器 | P1 | Closed/Open/Half-Open 状态机 |
| R-005 | Fallback 链 | P1 | 多模型降级策略 |
| R-006 | 背压控制 | P2 | Semaphore 限制并发 |

#### 2.1.7 错误处理

```python
from ai_lib_python.errors import (
    AiLibError,
    ProtocolError,
    TransportError,
    RateLimitedError,
    AuthenticationError,
)

try:
    response = await client.chat().messages(msgs).execute()
except RateLimitedError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except AuthenticationError:
    print("Invalid API key")
except AiLibError as e:
    print(f"Error: {e.error_class}, retryable: {e.retryable}")
```

**需求清单**:

| ID | 需求 | 优先级 | 说明 |
|----|------|--------|------|
| E-001 | 分层错误体系 | P0 | Protocol/Transport/Runtime 错误分类 |
| E-002 | 错误分类映射 | P0 | 13 种标准错误类（与协议对齐）|
| E-003 | 可重试判断 | P0 | retryable / fallbackable 属性 |
| E-004 | 错误上下文 | P1 | 结构化诊断信息 |

### 2.2 非功能性需求

#### 2.2.1 性能需求

| 指标 | 目标 | 说明 |
|------|------|------|
| 首包延迟 | < 50ms 额外开销 | 相对于原始 API 调用 |
| 流式吞吐 | > 10,000 events/s | 单连接处理能力 |
| 内存占用 | < 50MB 基础内存 | 空闲状态 |
| 协议加载 | < 100ms | 单个 Provider 加载 |

#### 2.2.2 兼容性需求

| 项目 | 要求 |
|------|------|
| Python 版本 | >= 3.10 (match 语法、类型联合) |
| 依赖策略 | 最小化核心依赖，可选扩展 |
| 类型检查 | mypy strict 模式通过 |
| 测试覆盖 | >= 80% 行覆盖率 |

#### 2.2.3 质量需求

| 项目 | 要求 |
|------|------|
| 代码风格 | ruff 格式化 + 静态检查 |
| 文档 | 100% 公共 API 文档覆盖 |
| 类型注解 | 100% 公共 API 类型注解 |
| 变更日志 | 语义化版本 + CHANGELOG |

---

## 三、技术架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ai-lib-python 架构                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    用户接口层 (User Interface)                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │  │
│  │  │  AiClient   │  │ ChatBuilder │  │  @tool decorator        │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    弹性控制层 (Resilience)                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ Retry    │  │ Breaker  │  │ Limiter  │  │ Fallback Chain   │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    管道解释层 (Pipeline)                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ Decoder  │→ │ Selector │→ │Accumulate│→ │   EventMapper    │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    传输层 (Transport)                              │  │
│  │  ┌──────────────────┐  ┌──────────────────────────────────────┐  │  │
│  │  │   HttpTransport  │  │         Middleware Chain             │  │  │
│  │  │   (httpx-based)  │  │  (auth, logging, metrics, retry)     │  │  │
│  │  └──────────────────┘  └──────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    协议层 (Protocol)                               │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │  │
│  │  │  ProtocolLoader  │  │ProtocolValidator │  │ProtocolManifest│  │  │
│  │  └──────────────────┘  └──────────────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    类型层 (Types) - Pydantic v2                    │  │
│  │  ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────────────┐ │  │
│  │  │ Message │ │ ContentBlock│ │ToolCall  │ │  StreamingEvent    │ │  │
│  │  └─────────┘ └─────────────┘ └──────────┘ └────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块依赖关系

```
ai_lib_python/
├── __init__.py              # 公共 API 导出
├── py.typed                 # PEP 561 类型标记
│
├── types/                   # 类型层 (无外部依赖)
│   ├── __init__.py
│   ├── message.py           # Message, MessageRole, ContentBlock
│   ├── tool.py              # ToolDefinition, ToolCall
│   └── events.py            # StreamingEvent 枚举
│
├── protocol/                # 协议层
│   ├── __init__.py
│   ├── loader.py            # ProtocolLoader
│   ├── validator.py         # ProtocolValidator
│   ├── manifest.py          # ProtocolManifest (Pydantic model)
│   └── embedded/            # 内嵌 schema (离线支持)
│       └── schema_v1.json
│
├── pipeline/                # 管道层
│   ├── __init__.py
│   ├── base.py              # Transform, Mapper, Decoder 抽象
│   ├── decode.py            # SSEDecoder, JsonLinesDecoder
│   ├── select.py            # JsonPathSelector
│   ├── accumulate.py        # ToolCallAccumulator
│   ├── event_map.py         # EventMapper
│   └── fan_out.py           # FanOut 算子
│
├── transport/               # 传输层
│   ├── __init__.py
│   ├── http.py              # HttpTransport (httpx)
│   └── middleware.py        # 中间件链
│
├── resilience/              # 弹性层
│   ├── __init__.py
│   ├── retry.py             # 重试策略
│   ├── rate_limiter.py      # 速率限制
│   ├── circuit_breaker.py   # 熔断器
│   └── backpressure.py      # 背压控制
│
├── client/                  # 客户端层
│   ├── __init__.py
│   ├── core.py              # AiClient
│   ├── builder.py           # AiClientBuilder, ChatBuilder
│   ├── execution.py         # 执行逻辑
│   └── stats.py             # CallStats
│
├── errors/                  # 错误体系
│   ├── __init__.py
│   └── classification.py    # 错误分类
│
├── telemetry/               # 遥测 (可选)
│   ├── __init__.py
│   └── feedback.py          # FeedbackSink
│
└── utils/                   # 工具函数
    ├── __init__.py
    ├── json_path.py         # JSONPath 工具
    └── tool_decorator.py    # @tool 装饰器
```

### 3.3 核心依赖选型

| 功能 | 选型 | 理由 |
|------|------|------|
| HTTP 客户端 | `httpx` | 原生 async、流式支持、HTTP/2 |
| 数据模型 | `pydantic>=2.0` | 高性能验证、JSON Schema 集成 |
| JSON Schema | `fastjsonschema` | 编译后高性能验证 |
| JSONPath | `jsonpath-ng` | 完整 JSONPath 实现 |
| 文件监控 | `watchdog` (optional) | 热重载支持 |
| 密钥存储 | `keyring` (optional) | 跨平台密钥管理 |

```toml
# pyproject.toml 依赖定义
[project]
dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.0",
    "fastjsonschema>=2.19",
    "jsonpath-ng>=1.6",
]

[project.optional-dependencies]
full = [
    "watchdog>=3.0",
    "keyring>=24.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.0",
    "mypy>=1.8",
    "ruff>=0.2",
]
```

---

## 四、Python 特色功能设计

### 4.1 工具装饰器 (Tool Decorator)

**充分利用 Python 的动态特性和类型提示**：

```python
from ai_lib_python import tool, AiClient
from typing import Annotated
from pydantic import Field

@tool
def get_weather(
    city: Annotated[str, Field(description="城市名称")],
    unit: Annotated[str, Field(description="温度单位", default="celsius")] = "celsius"
) -> dict:
    """获取指定城市的天气信息
    
    这个函数会查询实时天气数据并返回温度、湿度等信息。
    """
    return {"city": city, "temperature": 22, "unit": unit}

# 自动生成的 ToolDefinition
# {
#   "type": "function",
#   "function": {
#     "name": "get_weather",
#     "description": "获取指定城市的天气信息\n\n这个函数会查询实时天气数据并返回温度、湿度等信息。",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "city": {"type": "string", "description": "城市名称"},
#         "unit": {"type": "string", "description": "温度单位", "default": "celsius"}
#       },
#       "required": ["city"]
#     }
#   }
# }

# 使用装饰后的工具
client = await AiClient.create("anthropic/claude-3-5-sonnet")
response = await (
    client.chat()
    .messages([Message.user("北京今天天气怎么样？")])
    .tools([get_weather])  # 直接传入装饰后的函数
    .execute()
)
```

### 4.2 上下文管理器模式

```python
from ai_lib_python import AiClient

# 资源自动管理
async with AiClient.create("anthropic/claude-3-5-sonnet") as client:
    response = await client.chat().messages(msgs).execute()
# 自动关闭连接、清理资源

# 流式上下文
async with client.chat().messages(msgs).stream_context() as stream:
    async for event in stream:
        process(event)
# 自动处理取消和清理
```

### 4.3 Jupyter Notebook 集成

```python
from ai_lib_python import AiClient
from ai_lib_python.jupyter import display_stream

client = await AiClient.create("anthropic/claude-3-5-sonnet")

# 在 Notebook 中实时显示流式输出
await display_stream(
    client.chat()
    .messages([Message.user("写一首关于Python的诗")])
    .stream()
)
```

### 4.4 类型安全的模式匹配 (Python 3.10+)

```python
from ai_lib_python.types import StreamingEvent

async for event in stream:
    match event:
        case StreamingEvent.PartialContentDelta(content=c, sequence_id=seq):
            print(f"[{seq}] {c}", end="")
        
        case StreamingEvent.ToolCallStarted(tool_call_id=id, tool_name=name):
            print(f"\n🔧 Tool: {name} (id: {id})")
        
        case StreamingEvent.PartialToolCall(arguments=args, is_complete=True):
            result = execute_tool(args)
            
        case StreamingEvent.StreamEnd(finish_reason=reason):
            print(f"\n✅ Finished: {reason}")
        
        case StreamingEvent.StreamError(error=e):
            print(f"\n❌ Error: {e}")
```

### 4.5 配置驱动的 Provider 扩展

```python
from ai_lib_python.protocol import ProtocolLoader

# 自定义协议目录
loader = ProtocolLoader(
    base_path="./custom-protocols",
    fallback_to_github=True,
)

# 或通过环境变量
# AI_PROTOCOL_DIR=./custom-protocols

# 运行时添加自定义 Provider
loader.register_provider({
    "id": "custom-llm",
    "endpoint": {"base_url": "https://api.custom-llm.com"},
    "streaming": {...}
})
```

---

## 五、开发计划

### 5.1 里程碑规划

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        ai-lib-python 开发路线图                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 1: 基础框架 (Foundation)                                          │
│  ═══════════════════════════════                                         │
│  • 项目脚手架搭建                                                         │
│  • 类型系统 (Pydantic models)                                            │
│  • 协议加载与验证                                                         │
│  • 基础传输层                                                             │
│                                                                          │
│  Phase 2: 核心功能 (Core Features)                                       │
│  ════════════════════════════════                                        │
│  • 管道解释器                                                             │
│  • 流式事件处理                                                           │
│  • AiClient 核心 API                                                     │
│  • 错误处理体系                                                           │
│                                                                          │
│  Phase 3: 生产就绪 (Production Ready)                                    │
│  ═════════════════════════════════════                                   │
│  • 弹性控制 (重试/熔断/限流)                                              │
│  • 多 Provider 支持                                                       │
│  • 性能优化                                                               │
│  • 完整测试覆盖                                                           │
│                                                                          │
│  Phase 4: 生态扩展 (Ecosystem)                                           │
│  ═══════════════════════════════                                         │
│  • 工具装饰器                                                             │
│  • Jupyter 集成                                                          │
│  • 文档与示例                                                             │
│  • PyPI 发布                                                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 详细任务分解

#### Phase 1: 基础框架 (Foundation)

| 任务 | 描述 | 交付物 |
|------|------|--------|
| 1.1 项目初始化 | pyproject.toml, 目录结构, CI/CD | 可构建的空项目 |
| 1.2 类型层实现 | Message, ContentBlock, ToolCall, StreamingEvent | `types/` 模块 |
| 1.3 协议模型 | ProtocolManifest Pydantic 模型 | `protocol/manifest.py` |
| 1.4 协议加载器 | 本地/远程加载, 缓存机制 | `protocol/loader.py` |
| 1.5 协议验证器 | JSON Schema 验证 | `protocol/validator.py` |
| 1.6 传输层 | httpx 封装, API Key 管理 | `transport/` 模块 |

#### Phase 2: 核心功能 (Core Features)

| 任务 | 描述 | 交付物 |
|------|------|--------|
| 2.1 解码器实现 | SSE, JSON Lines 解码 | `pipeline/decode.py` |
| 2.2 选择器实现 | JSONPath 帧过滤 | `pipeline/select.py` |
| 2.3 累加器实现 | 工具调用参数组装 | `pipeline/accumulate.py` |
| 2.4 事件映射器 | 协议驱动的事件转换 | `pipeline/event_map.py` |
| 2.5 管道组装 | Pipeline.from_manifest | `pipeline/__init__.py` |
| 2.6 AiClient | 核心客户端实现 | `client/core.py` |
| 2.7 ChatBuilder | 链式调用 API | `client/builder.py` |
| 2.8 错误体系 | 分层错误, 错误分类 | `errors/` 模块 |

#### Phase 3: 生产就绪 (Production Ready)

| 任务 | 描述 | 交付物 |
|------|------|--------|
| 3.1 重试策略 | 指数退避, Jitter | `resilience/retry.py` |
| 3.2 速率限制 | Token Bucket, 自适应 | `resilience/rate_limiter.py` |
| 3.3 熔断器 | 状态机实现 | `resilience/circuit_breaker.py` |
| 3.4 Fallback 链 | 多模型降级 | `client/fallback.py` |
| 3.5 多 Provider | OpenAI, Anthropic, DeepSeek, Gemini | 集成测试 |
| 3.6 性能优化 | 异步优化, 内存优化 | 性能测试报告 |
| 3.7 测试覆盖 | 单元测试, 集成测试 | 80%+ 覆盖率 |

#### Phase 4: 生态扩展 (Ecosystem)

| 任务 | 描述 | 交付物 |
|------|------|--------|
| 4.1 工具装饰器 | @tool 自动生成 | `utils/tool_decorator.py` |
| 4.2 Jupyter 集成 | display_stream, 富文本输出 | `jupyter/` 模块 |
| 4.3 热重载 | watchdog 集成 | `protocol/hot_reload.py` |
| 4.4 文档 | API 文档, 教程, 示例 | docs/ 目录 |
| 4.5 PyPI 发布 | 版本管理, 发布流程 | PyPI 包 |

### 5.3 验收标准

#### 功能验收

```python
# 最小可用示例 (MVP)
from ai_lib_python import AiClient, Message

async def main():
    client = await AiClient.create("anthropic/claude-3-5-sonnet")
    
    # 非流式
    response = await (
        client.chat()
        .messages([Message.user("Hello!")])
        .execute()
    )
    print(response.content)
    
    # 流式
    async for event in client.chat().messages([Message.user("Hello!")]).stream():
        if hasattr(event, 'content'):
            print(event.content, end="")

asyncio.run(main())
```

#### 质量验收

| 检查项 | 标准 |
|--------|------|
| 类型检查 | `mypy --strict` 零错误 |
| 代码风格 | `ruff check && ruff format --check` 通过 |
| 测试覆盖 | `pytest --cov` >= 80% |
| 文档覆盖 | 所有公共 API 有 docstring |
| 性能基准 | 流式延迟 < 50ms 额外开销 |

---

## 六、风险与缓解策略

### 6.1 技术风险

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| httpx 异步兼容性 | 中 | 充分的异步测试，考虑 aiohttp 备选 |
| Pydantic v2 性能 | 低 | 按需启用 strict 模式，使用 TypeAdapter |
| JSONPath 复杂表达式 | 中 | 限制支持的 JSONPath 子集，提供清晰文档 |
| Provider API 变更 | 中 | 协议版本化，热重载支持 |

### 6.2 项目风险

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| ai-protocol 变更 | 中 | 紧密跟踪上游，参与协议讨论 |
| Python 版本碎片化 | 低 | 明确 3.10+ 最低版本要求 |
| 社区采用率 | 中 | 高质量文档，丰富示例，快速响应 Issue |

---

## 七、成功指标

### 7.1 定量指标

| 指标 | 目标 |
|------|------|
| PyPI 周下载量 | 发布后 3 个月 > 1,000 |
| GitHub Stars | 发布后 6 个月 > 500 |
| Issue 响应时间 | < 48 小时 |
| PR 合并时间 | < 1 周 |

### 7.2 定性指标

- 与 ai-lib-rust 功能对等
- Pythonic API 设计获得社区认可
- 被主流 AI 应用框架（如 LangChain、LlamaIndex）集成

---

## 八、附录

### A. 与 ai-lib-rust 的 API 对照

| 功能 | Rust API | Python API |
|------|----------|------------|
| 客户端创建 | `AiClient::new("provider/model")` | `await AiClient.create("provider/model")` |
| 消息构建 | `Message::user("text")` | `Message.user("text")` |
| 流式执行 | `execute_stream().await` | `async for event in stream()` |
| 协议加载 | `ProtocolLoader::new()` | `ProtocolLoader()` |
| 热重载 | `.with_hot_reload(true)` | `hot_reload=True` |

### B. 支持的 Provider 列表 (与 ai-protocol 同步)

- OpenAI (GPT-4o, GPT-4, GPT-3.5)
- Anthropic (Claude 3.5, Claude 3)
- Google (Gemini Pro, Gemini Flash)
- DeepSeek (DeepSeek Chat, DeepSeek Coder)
- Qwen (通义千问)
- Groq (LLaMA, Mixtral)
- Mistral
- Moonshot (Kimi)
- 更多...

### C. 参考资源

- [AI-Protocol 规范](https://github.com/hiddenpath/ai-protocol)
- [ai-lib-rust 实现](https://github.com/hiddenpath/ai-lib-rust)
- [Pydantic v2 文档](https://docs.pydantic.dev/)
- [httpx 文档](https://www.python-httpx.org/)

---

**文档版本**: 1.0  
**最后更新**: 2026-01-27  
**作者**: AI-Protocol Team
