# ai-lib-python

**AI-Protocol 官方 Python 运行时** - 统一 AI 模型交互的规范 Python 实现。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://github.com/hiddenpath/ai-lib-python/actions/workflows/ci.yml/badge.svg)](https://github.com/hiddenpath/ai-lib-python/actions)
[![PyPI](https://img.shields.io/pypi/v/ai-lib-python.svg)](https://pypi.org/project/ai-lib-python/)

## 概述

`ai-lib-python` 是 [AI-Protocol](https://github.com/hiddenpath/ai-protocol) 规范的**官方 Python 运行时**。作为 AI-Protocol 团队维护的规范 Python 实现，它体现了核心设计原则：

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
- **遥测功能**: 结构化日志、指标收集、分布式追踪和用户反馈收集
- **Token 计数**: tiktoken 集成和成本估算
- **连接池**: 高效的 HTTP 连接管理
- **批处理**: 并发执行与并发控制
- **模型路由**: 智能模型选择与负载均衡策略
- **向量嵌入**: 嵌入向量生成与向量运算
- **结构化输出**: JSON 模式与 Schema 验证
- **响应缓存**: 多后端缓存支持，带 TTL 管理
- **插件系统**: 可扩展的钩子和中间件架构
- **流式取消**: 流式操作的协作式取消

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

### Token 计数与成本估算

```python
from ai_lib_python.tokens import TokenCounter, estimate_cost, get_model_pricing

# 计算 Token 数量
counter = TokenCounter.for_model("gpt-4o")
token_count = counter.count("你好，最近怎么样？")
print(f"Token 数量: {token_count}")

# 计算消息 Token 数
messages = [Message.user("你好！"), Message.assistant("你好呀！")]
total_tokens = counter.count_messages(messages)

# 估算成本
cost = estimate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o")
print(f"预估成本: ${cost.total_cost:.4f}")

# 获取模型定价信息
pricing = get_model_pricing("gpt-4o")
print(f"输入价格: ${pricing.input_price_per_1k}/千 Token")
print(f"上下文窗口: {pricing.context_window} Token")
```

### 指标与遥测

```python
from ai_lib_python.telemetry import (
    get_logger,
    MetricsCollector,
    MetricLabels,
    Tracer,
)

# 结构化日志
logger = get_logger("my_app")
logger.info("请求开始", model="gpt-4o", tokens=100)

# 指标收集
collector = MetricsCollector()
labels = MetricLabels(provider="openai", model="gpt-4o")
collector.record_request(labels, latency=0.5, status="success", tokens_in=100, tokens_out=50)

# 获取指标快照
snapshot = collector.get_snapshot()
print(f"总请求数: {snapshot.total_requests}")
print(f"P99 延迟: {snapshot.latency_p99_ms:.2f}ms")

# 导出 Prometheus 格式
prometheus_metrics = collector.to_prometheus()

# 分布式追踪
tracer = Tracer("my_service")
with tracer.span("api_call") as span:
    span.set_attribute("model", "gpt-4o")
    # ... 执行操作
```

### 批量处理

```python
from ai_lib_python.batch import BatchExecutor, BatchConfig

# 并发执行多个请求
async def process_question(question: str) -> str:
    client = await AiClient.create("openai/gpt-4o")
    response = await client.chat().user(question).execute()
    await client.close()
    return response.content

questions = ["什么是 AI？", "什么是 Python？", "什么是异步编程？"]

executor = BatchExecutor(process_question, max_concurrent=5)
result = await executor.execute(questions)

print(f"成功: {result.successful_count}")
print(f"失败: {result.failed_count}")
for answer in result.get_successful_results():
    print(answer)
```

### 模型路由与选择

```python
from ai_lib_python.routing import (
    ModelManager, ModelInfo, create_openai_models, create_anthropic_models,
    CostBasedSelector, QualityBasedSelector,
)

# 创建预配置的模型管理器
manager = create_openai_models()
manager.merge(create_anthropic_models())

# 按能力筛选模型
code_models = manager.filter_by_capability("code_generation")
print(f"代码生成模型: {[m.name for m in code_models]}")

# 选择最便宜的模型
selector = CostBasedSelector()
cheapest = selector.select(manager.list_models())
print(f"最便宜: {cheapest.name} @ ${cheapest.pricing.input_cost_per_1k}/千Token")

# 选择最高质量的模型
quality_selector = QualityBasedSelector()
best = quality_selector.select(manager.list_models())
print(f"最高质量: {best.name}")

# 按用例推荐模型
recommended = manager.recommend_for("chat")
```

### 流式取消

```python
from ai_lib_python.client import create_cancel_pair, CancellableStream, CancelReason

async def cancellable_stream():
    client = await AiClient.create("openai/gpt-4o")
    
    # 创建取消令牌和句柄
    token, handle = create_cancel_pair()
    
    # 启动支持取消的流式处理
    stream = client.chat().user("写一个长故事...").stream()
    cancellable = CancellableStream(stream, token)
    
    # 在另一个任务中可以取消:
    # handle.cancel(CancelReason.USER_REQUEST)
    
    async for event in cancellable:
        if event.is_content_delta:
            print(event.as_content_delta.content, end="")
        
        # 检查是否已取消
        if token.is_cancelled:
            print("\n[已取消]")
            break
```

### 用户反馈收集

```python
from ai_lib_python.telemetry import (
    RatingFeedback, ThumbsFeedback, ChoiceSelectionFeedback,
    InMemoryFeedbackSink, set_feedback_sink, report_feedback,
)

# 设置反馈收集器
sink = InMemoryFeedbackSink(max_events=1000)
set_feedback_sink(sink)

# 报告用户反馈
await report_feedback(RatingFeedback(
    request_id="req-123",
    rating=5,
    category="helpfulness",
    comment="回复很棒！"
))

await report_feedback(ThumbsFeedback(
    request_id="req-456",
    is_positive=True
))

# 报告多候选选择（用于 A/B 测试）
await report_feedback(ChoiceSelectionFeedback(
    request_id="req-789",
    chosen_index=0,
    rejected_indices=[1, 2],
    latency_to_select_ms=1500.0
))

# 获取反馈记录
all_feedback = sink.get_events()
request_feedback = sink.get_events_by_request("req-123")
```

### 向量嵌入

```python
from ai_lib_python.embeddings import (
    EmbeddingClient, cosine_similarity, find_most_similar
)

# 创建嵌入客户端
client = await EmbeddingClient.create("openai/text-embedding-3-small")

# 生成嵌入向量
response = await client.embed("你好，世界！")
embedding = response.first.vector
print(f"维度: {len(embedding)}")

# 批量生成嵌入
texts = ["你好", "世界", "Python", "AI"]
response = await client.embed_batch(texts)

# 查找最相似的
query = response.embeddings[0].vector
candidates = [e.vector for e in response.embeddings[1:]]
results = find_most_similar(query, candidates, top_k=2)
for idx, score in results:
    print(f"文本 '{texts[idx+1]}' 相似度: {score:.4f}")

await client.close()
```

### 响应缓存

```python
from ai_lib_python.cache import CacheManager, CacheConfig, MemoryCache

# 创建缓存管理器
cache = CacheManager(
    config=CacheConfig(default_ttl_seconds=3600),
    backend=MemoryCache(max_size=1000)
)

# 缓存响应
key = cache.generate_key(model="gpt-4o", messages=messages)

# 先检查缓存
cached = await cache.get(key)
if cached:
    print("缓存命中！")
    response = cached
else:
    response = await client.chat().messages(messages).execute()
    await cache.set(key, response)

# 获取缓存统计
stats = cache.stats()
print(f"命中率: {stats.hit_ratio:.2%}")
```

### 插件系统

```python
from ai_lib_python.plugins import (
    Plugin, PluginContext, PluginRegistry, HookType, HookManager
)

# 创建自定义插件
class LoggingPlugin(Plugin):
    def name(self) -> str:
        return "logging"
    
    async def on_before_request(self, ctx: PluginContext) -> None:
        print(f"请求发往 {ctx.model}: {ctx.request}")
    
    async def on_after_response(self, ctx: PluginContext) -> None:
        print(f"收到响应: {ctx.response}")

# 注册插件
registry = PluginRegistry()
await registry.register(LoggingPlugin())

# 使用钩子进行细粒度控制
hooks = HookManager()
hooks.register(HookType.BEFORE_REQUEST, "log", lambda ctx: print(f"开始 {ctx.model}"))

# 触发钩子
ctx = PluginContext(model="gpt-4o", request={"messages": [...]})
await registry.trigger_before_request(ctx)
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
- **`PreflightChecker`**: 统一的请求预检
- **`SignalsSnapshot`**: 运行时状态聚合

### 路由类

- **`ModelManager`**: 集中式模型管理
- **`ModelInfo`**: 带能力信息的模型定义
- **`ModelArray`**: 端点间负载均衡
- **`ModelSelectionStrategy`**: 选择策略（成本、质量、性能等）

### 遥测类

- **`AiLibLogger`**: 带敏感数据脱敏的结构化日志
- **`MetricsCollector`**: 请求指标收集
- **`Tracer`**: 分布式追踪
- **`HealthChecker`**: 健康监控
- **`FeedbackSink`**: 用户反馈收集

### 嵌入类

- **`EmbeddingClient`**: 嵌入向量生成客户端
- **`Embedding`**: 单个嵌入结果
- **`EmbeddingResponse`**: 带使用统计的响应

### Token 类

- **`TokenCounter`**: Token 计数接口
- **`CostEstimate`**: 成本估算结果
- **`ModelPricing`**: 模型定价信息

### 缓存类

- **`CacheManager`**: 高级缓存管理
- **`CacheBackend`**: 缓存后端接口（内存、磁盘、空）
- **`CacheKeyGenerator`**: 确定性键生成

### 批处理类

- **`BatchCollector`**: 请求分组
- **`BatchExecutor`**: 并行执行

### 插件类

- **`Plugin`**: 插件基类
- **`PluginRegistry`**: 插件管理
- **`HookManager`**: 事件驱动钩子
- **`Middleware`**: 请求/响应链

### 传输类

- **`ConnectionPool`**: HTTP 连接池
- **`PoolConfig`**: 连接池配置

### 取消类

- **`CancelToken`**: 协作式取消令牌
- **`CancelHandle`**: 公共取消接口
- **`CancellableStream`**: 可取消的异步迭代器

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
│   │   └── validator.py    # Schema 验证（+ 版本/流式检查）
│   ├── transport/          # HTTP 传输
│   │   ├── http.py         # HttpTransport
│   │   ├── auth.py         # API 密钥解析
│   │   └── pool.py         # ConnectionPool
│   ├── pipeline/           # 流处理
│   │   ├── decode.py       # SSE/NDJSON 解码器
│   │   ├── select.py       # JSONPath 选择器
│   │   ├── accumulate.py   # 工具调用累积器
│   │   ├── event_map.py    # 事件映射器
│   │   └── fan_out.py      # FanOut, Replicate, Split 变换
│   ├── resilience/         # 弹性模式
│   │   ├── retry.py        # 重试策略
│   │   ├── rate_limiter.py # 限流器
│   │   ├── circuit_breaker.py  # 熔断器
│   │   ├── backpressure.py # 背压控制
│   │   ├── fallback.py     # 降级链
│   │   ├── executor.py     # 弹性执行器
│   │   ├── signals.py      # SignalsSnapshot
│   │   └── preflight.py    # PreflightChecker
│   ├── routing/            # 模型路由与负载均衡
│   │   ├── models.py       # ModelInfo, ModelCapabilities
│   │   ├── strategies.py   # 选择策略
│   │   ├── manager.py      # ModelManager
│   │   └── array.py        # ModelArray（负载均衡）
│   ├── client/             # 用户 API
│   │   ├── core.py         # AiClient
│   │   ├── builder.py      # 构建器
│   │   ├── response.py     # ChatResponse
│   │   └── cancel.py       # CancelToken, CancellableStream
│   ├── embeddings/         # 嵌入支持
│   │   ├── client.py       # EmbeddingClient
│   │   ├── types.py        # Embedding, EmbeddingRequest
│   │   └── vectors.py      # 向量运算
│   ├── cache/              # 响应缓存
│   │   ├── manager.py      # CacheManager
│   │   ├── backend.py      # MemoryCache, DiskCache
│   │   └── key.py          # CacheKeyGenerator
│   ├── tokens/             # Token 计数
│   │   ├── counter.py      # TokenCounter, TiktokenCounter
│   │   └── pricing.py      # ModelPricing, CostEstimate
│   ├── telemetry/          # 可观测性
│   │   ├── logging.py      # AiLibLogger
│   │   ├── metrics.py      # MetricsCollector
│   │   ├── tracing.py      # Tracer
│   │   ├── health.py       # HealthChecker
│   │   └── feedback.py     # 反馈类型和接收器
│   ├── batch/              # 请求批处理
│   │   ├── collector.py    # BatchCollector
│   │   └── executor.py     # BatchExecutor
│   ├── plugins/            # 插件系统
│   │   ├── base.py         # Plugin 基类
│   │   ├── registry.py     # PluginRegistry
│   │   ├── hooks.py        # HookManager
│   │   └── middleware.py   # Middleware 链
│   ├── structured/         # 结构化输出
│   │   ├── json_mode.py    # JsonModeConfig
│   │   ├── schema.py       # SchemaGenerator
│   │   └── validator.py    # OutputValidator
│   ├── utils/              # 工具类
│   │   └── tool_call_assembler.py  # ToolCallAssembler
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
