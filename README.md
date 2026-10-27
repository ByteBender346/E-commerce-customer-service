# 电商客服智能对话系统

基于 **FastAPI + LangChain** 的电商智能客服后端：通过 **YAML 流程编排引擎** 驱动多轮业务对话（查订单、查物流、退款申请），配合 **LLM 三轨道意图分发**（任务流 / 知识检索 / 闲聊）与 **槽位收集机制**，实现可配置、可扩展的自动化客服对话。

> 解决什么问题：电商客服需要在多轮对话中收集订单号、理解业务意图、调用后端 API 完成查询或售后；硬编码对话逻辑难以维护。本系统将业务流程抽象为 YAML 配置，新增业务只需加配置和 Action，无需改动引擎代码。

**适用场景**：电商售后客服、订单/物流自助查询、退款退货流程引导、商品知识问答。

---

## 效果预览

| 对话流程 | 说明 |
| --- | --- |
| 查订单状态 | 用户说"帮我查下订单"→ 系统收集订单号 → 调用订单 API → 返回状态与金额 |
| 查物流 | 用户说"物流到哪了"→ 收集订单号 → 并发查订单+物流 → 返回快递公司与运单号 |
| 退款申请 | 用户说"我要退款"→ 收集订单号 + 退款原因 → 提交确认 |
| 知识咨询 | 用户点击商品卡片问"这个商品参数"→ 调商品 API → LLM 组织自然语言回复 |
| 闲聊 | 用户打招呼 → 纯 LLM 友好回复，不切业务 |

---

## 功能清单

- **YAML 流程编排**：业务流程（start / collect / action / end）全部声明在 YAML 中，支持条件分支、槽位收集、校验失败回退
- **三轨道意图分发**：TurnPlanner 让 LLM 输出结构化 TurnPlan JSON，Validator 校验后只执行一条轨道，多意图自动澄清
- **槽位自动收集**：collect 步骤缺失槽位时自动激活系统追问流程；用户点击订单/商品卡片时自动填充对应槽位
- **任务打断与恢复**：正在退款时用户突然问物流 → 当前任务挂起 → 处理物流后可恢复退款
- **Action 插件化**：内置 `action_response`（static / rephrase / generate 三种回复模式）+ `action_listen`；自定义 Action 通过包扫描自动注册
- **知识检索多源融合**：商品 API、订单 API、FAQ、RAG 四类 Provider 按意图路由，并发检索后 LLM 组织回复
- **对话状态持久化**：完整对话状态（当前任务、挂起任务、槽位、会话历史、焦点对象）序列化为 JSON 存入 MySQL
- **会话超时管理**：1 小时无活动自动结束会话并重置运行时状态

---

## 技术栈

- **后端框架**：FastAPI + Uvicorn（异步 ASGI）
- **LLM 调用**：LangChain（`init_chat_model`、PromptTemplate | llm | OutputParser 管道）
- **流程引擎**：自研 YAML Flow（类似 Rasa 的 slot + action 机制，支持条件跳转 eval）
- **数据存储**：MySQL（SQLAlchemy 2.0 异步 ORM，aiomysql 驱动）
- **HTTP 调用**：HTTPX AsyncClient（异步请求电商业务后端 API）
- **模板渲染**：Jinja2（Prompt 模板 + 回复文本变量插值）
- **配置管理**：Pydantic Settings（.env 环境变量加载）

---

## 项目亮点

- **YAML 声明式流程引擎**：将对话业务抽象为 `Flow → Step → Link` 三层模型，start / collect / action / end 四种节点类型，条件分支用 Python 表达式在 YAML 中声明。新增"换货申请"业务只需在 YAML 中加一段配置 + 一个 Action 类，引擎零改动。
- **LLM 三轨道调度与校验闭环**：TurnPlanner 让 LLM 在单轮内判断走任务流、知识检索还是闲聊，并输出结构化 JSON；TurnPlanValidator 校验轨道数量、命令非空、焦点对象匹配，不合法时由 ClarifyResponder 生成自然语言追问，避免 LLM 幻觉导致的状态机异常。
- **双层循环流程推进器**：外层循环不断取出 ActionCall 并执行，直到遇到 `action_listen`（等待用户输入）退出；内层循环在流程节点间导航，跳过 start/end，处理 collect 槽位收集与条件跳转，实现了声明式流程到命令执行的完整闭环。
- **焦点对象自动补槽**：用户点击前端订单卡片时，系统自动识别当前 collect 步骤需要哪个槽位（order_number / product_id），将卡片 ID 注入槽位，无需用户手动输入。
- **任务栈打断恢复**：active_task + paused_tasks 双栈设计，用户中途切换业务时自动挂起当前流程并触发系统提示，新流程结束后可通过 `resume_flow` 命令恢复挂起任务。
- **Action 自动注册**：通过 `pkgutil` + `inspect` 扫描 custom 包下所有 `Action` 子类自动注册，新增 Action 文件即被发现，无需手动登记。

---

## 目录结构

```
├── main.py                          # 项目入口（uvicorn 启动）
├── .env                             # 环境变量配置
├── pyproject.toml                   # 项目元数据
├── flow_config/                     # YAML 业务流程配置
│   ├── user_flows.yml               # 用户业务流程（查订单/查物流/退款/相似推荐/人工客服）
│   └── system_flows.yml             # 系统流程（任务开始/中断/取消/恢复/收集信息/无法处理）
└── dianshang/                       # 项目主体包
    ├── api/                         # FastAPI 接口层
    │   ├── app.py                   # FastAPI 实例 + lifespan 生命周期
    │   ├── dependencies.py          # 依赖注入（引擎/数据库/服务）
    │   ├── schemas.py                # Pydantic 请求/响应模型
    │   └── routers/
    │       └── chat_router.py       # /api/chat 对话接口、/api/chat/history 历史接口
    ├── conf/
    │   └── config.py                 # Pydantic Settings 配置加载
    ├── infrastructure/              # 基础设施层
    │   ├── llm.py                    # LangChain LLM 客户端初始化
    │   ├── http_client.py            # HTTPX 异步客户端
    │   └── database.py               # SQLAlchemy 异步引擎与会话工厂
    ├── domain/                      # 领域模型层
    │   ├── messages.py               # UserMessage / BotMessage / MessageObject
    │   ├── contexts.py                # TaskContext / SystemContext（任务执行快照）
    │   └── state.py                   # DialogueState / Session / Turn / FocusedObject
    ├── engine/                      # 对话引擎层
    │   ├── builder.py                # 组装所有 Handler/Provider/Runner
    │   └── dialogue_engine.py         # 总调度：会话准备→轮次开始→分发Handler→提交
    ├── service/
    │   └── dialogue_service.py       # 业务服务：加载状态→引擎处理→保存状态
    ├── repository/
    │   └── dialogue_state_repository.py  # 对话状态 MySQL 读写（upsert）
    ├── models/
    │   ├── base.py                   # SQLAlchemy DeclarativeBase
    │   └── dialogue_state.py         # dialogue_states 表 ORM 映射
    ├── plan/                        # 意图计划层
    │   ├── models.py                 # TurnPlan / TaskTurnPlan / KnowledgeTurnPlan / ClarifyReason
    │   ├── turn_planner.py           # LLM 生成 TurnPlan
    │   └── validator.py              # TurnPlan 校验（轨道数/命令/焦点对象）
    ├── task/                        # 任务流处理层
    │   ├── handler.py                # TaskHandler 入口
    │   ├── command/
    │   │   ├── models.py             # Command（start_flow/set_slots/cancel_flow/resume_flow）
    │   │   └── processor.py          # 命令应用到对话状态（启动/挂起/恢复/取消）
    │   ├── flow/
    │   │   ├── loader.py             # YAML → FlowsList 解析
    │   │   ├── models.py             # Flow / FlowSlot / FlowsList
    │   │   ├── steps.py              # Start/Action/Collect/End 四种步骤
    │   │   ├── links.py              # Static/Conditional/Fallback 跳转
    │   │   └── executor.py           # 双层循环推进流程
    │   └── action/
    │       ├── base.py               # Action 抽象基类 + ActionResult
    │       ├── registry.py           # Action 注册中心
    │       ├── runner.py              # Action 执行器
    │       ├── builder.py             # 内置+自定义 Action 自动注册
    │       ├── builtin/
    │       │   ├── action_response.py    # 回复动作（static/rephrase/generate）
    │       │   └── action_listen.py      # 停止信号，等待用户输入
    │       └── custom/
    │           ├── shared.py             # 订单/物流/商品 API 请求封装
    │           ├── lookup_order_status.py # 查询订单状态
    │           ├── lookup_logistics.py    # 查询物流
    │           ├── recommend_similar_products.py  # 相似推荐（占位）
    │           └── action_custom.py       # 自定义 Action 示例
    ├── knowledge/                   # 知识处理层
    │   ├── intents.py                # 知识意图定义（7 种意图）
    │   ├── providers.py              # 四类 Provider（Product/Order/FAQ/RAG）
    │   ├── registry.py               # Provider 注册中心
    │   ├── resposnder.py              # LLM 基于知识片段生成回复
    │   └── handler.py                 # KnowledgeHandler 入口
    ├── chitchat/                    # 闲聊处理层
    │   ├── responder.py              # 纯 LLM 闲聊回复
    │   └── handler.py                 # ChitChatHandler 入口
    ├── clarify/
    │   └── responder.py               # 校验失败时生成自然语言追问
    └── prompts/                     # Prompt 模板层
        ├── history_builder.py         # 对话历史渲染为 USER:/BOT: 文本
        ├── prompt_load.py             # Jinja2 模板加载
        └── jinja2/
            ├── turn_plan.jinja2       # 三轨道意图分类 Prompt
            ├── knowledge_respond.jinja2  # 知识回复 Prompt
            ├── clarify_respond.jinja2   # 澄清追问改写 Prompt
            └── chitchat_respond.jinja2  # 闲聊回复 Prompt
```

---

## 运行步骤

### 环境要求

| 依赖 | 要求 |
| --- | --- |
| Python | >= 3.12 |
| MySQL | >= 8.0（创建 `customer_service` 数据库） |
| LLM API | 通义千问 / DeepSeek 等 OpenAI 兼容接口 |
| 业务后端 | 电商模拟后端（订单/商品 API，默认 `http://127.0.0.1:18081`） |

### 2. 虚拟环境并安装依赖

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux
source .venv/bin/activate

pip install fastapi uvicorn langchain langchain-openai sqlalchemy aiomysql pymysql httpx pydantic pydantic-settings jinja2 pyyaml
```

### 3. 准备数据库

```sql
CREATE DATABASE customer_service DEFAULT CHARACTER SET utf8mb4;

CREATE TABLE dialogue_states (
    sender_id VARCHAR(255) PRIMARY KEY,
    state_json TEXT NOT NULL
);
```

### 4. 配置环境变量
```ini
# ====== LLM 配置 ======
LLM_MODEL=qwen-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-xxx

# ====== 电商业务后端地址 ======
COMMERCE_API_BASE_URL=http://127.0.0.1:18081

# ====== 数据库 ======
DATABASE_URL=mysql+aiomysql://root:password@127.0.0.1:3306/customer_service

# ====== 服务监听 ======
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 5. 启动服务

```bash
python main.py
```

服务启动后监听 `http://127.0.0.1:8000`。

---

## 接口文档

### POST /api/chat

发送消息并获取客服回复。

**请求体**

```json
{
  "sender_id": "user_1001",
  "text": "帮我查一下订单状态",
  "message_id": "msg_001"
}
```

用户点击订单卡片时（对象消息）：

```json
{
  "sender_id": "user_1001",
  "object": {
    "type": "order",
    "id": "A20260410001",
    "title": "订单 #A20260410001"
  }
}
```

**响应体**

```json
{
  "sender_id": "user_1001",
  "message_id": "msg_001",
  "messages": [
    {
      "text": "请告诉我你的订单号。"
    }
  ]
}
```

### GET /api/chat/history?sender_id=user_1001

获取对话历史（当前为演示数据）。

```json
{
  "sender_id": "user_1001",
  "messages": [
    { "role": "user", "text": "你好" },
    { "role": "bot", "text": "你好，我是电商客服助手，有什么可以帮您？" }
  ]
}
```
