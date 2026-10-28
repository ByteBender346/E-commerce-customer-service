# 电商客服智能对话系统

基于 **FastAPI + LangChain + 自研 YAML 流程引擎** 的电商智能客服后端。用户可以在一个会话里连续办理查订单、查物流、申请退款、咨询商品知识，过程中随时插话、切换业务、取消或恢复任务——系统通过 **任务栈状态机 + LLM 三轨道意图分发 + 槽位收集机制** 管理这些复杂对话状态，让"理解"和"执行"解耦，业务可配置、幻觉可拦截、状态可恢复。

> 解决什么问题：电商客服对话不是简单的一问一答。用户可能在退款流程填到一半突然问物流、点击订单卡片代替手动输入、填错订单号需要重新引导、同时表达多个意图需要澄清；硬编码对话逻辑无法维护，纯 LLM 自由发挥又会幻觉出不存在流程。本系统用 YAML 声明业务流程、代码状态机管理状态、LLM 只做意图路由，把业务复杂度和工程可靠性分开治理。

**适用场景**：电商售后客服、订单/物流自助查询、退款退货流程引导、商品知识问答。

---

## 系统架构

![消息处理流程图](docs/images/78.png)

> 完整消息流转：用户消息 → FastAPI → 加载历史状态 → 对话引擎 → 按消息类型分流（文本走三轨道意图计划，对象消息自动补槽）→ 命令执行 → 流程推进 → Action 调用业务 API → 生成回复 → 状态持久化。

---

## 核心业务场景

| 场景 | 系统行为 |
| --- | --- |
| 查订单状态 | 用户说"帮我查下订单" → 收集订单号 → 调订单 API → 返回状态、金额、商品摘要 |
| 查物流 | 收集订单号 → 并发查订单+物流 → 返回快递公司、运单号、当前进度 |
| 退款申请 | 收集订单号 + 退款原因 → 提交确认 |
| **退款中突然问物流** | 退款任务压入暂停栈 → 处理物流 → 用户说"继续" → 按 flow_id 恢复退款（step/slots 不丢） |
| **点击订单卡片** | 自动识别当前需要收集的槽位（order_number），卡片 ID 直接注入，不用手输订单号 |
| **填错订单号** | 槽位校验失败（eval 条件）→ 清空槽位 → 提示重新提供，不带着脏数据往下走 |
| **同时问两件事** | Validator 检测到多轨道 → 澄清"先办业务还是先咨询？"，不猜测执行 |
| 商品知识咨询 | 点击商品卡片 → 商品 API 取参数 → LLM 基于数据生成回复，不编造 |
| 闲聊 | 纯 LLM 友好回复，不触发任何业务动作 |

---

## 功能清单

- **YAML 流程编排引擎**：业务流程（start / collect / action / end 四种节点）全部声明在 YAML，支持条件分支（Python 表达式）、槽位收集、校验失败回退；新增业务只加配置 + Action，引擎零改动
- **LLM 三轨道意图分发**：TurnPlanner 让 LLM 输出结构化 TurnPlan JSON（任务流 / 知识检索 / 闲聊三选一），TurnPlanValidator 校验轨道冲突、命令合法性、焦点对象匹配，不合法触发澄清追问而非乱执行
- **任务栈打断与恢复**：active_task + paused_tasks 双栈设计，退款中途切物流、新任务打断旧任务，均可通过 resume_flow 恢复，step_id/slots 完整保留
- **系统流程隔离**：SystemContext 封装任务启动/中断/取消/恢复/收集槽位 7 类中间态（"好的，我们先把退款放一放"这类系统提示），与业务任务隔离，不污染业务 YAML
- **槽位多通道收集**：文本由 LLM 解析 set_slots 命令、对象消息（订单/商品卡片点击）自动补槽、焦点对象自动填充，三通道互补
- **槽位校验与清空重问**：collect 步骤支持 validation 条件（eval），校验失败自动清槽并提示用户重新提供，拦截脏数据进入后续动作
- **Action 插件化**：内置 action_response（static / rephrase / generate 三种回复模式）+ action_listen；自定义 Action 通过 pkgutil 包扫描自动注册，新增业务动作仅需新增一个类文件
- **知识多源路由**：商品 API、订单 API、FAQ、RAG 四类 Provider 按意图路由，订单+物流用 asyncio.gather 并发拉取
- **对话状态持久化**：完整对话状态（活跃任务、暂停栈、系统流程、焦点对象、会话历史、槽位）序列化为 JSON 整份 upsert 至 MySQL
- **两阶段提交**：本轮回复先存 pending_turn，整轮执行成功才 commit 进历史，Action 失败不产生"半截回复已入库"的不一致
- **会话超时管理**：60 分钟无活动自动结束会话、重置运行时状态，避免长会话状态膨胀

---

## 核心设计

### 1. "LLM 计划 + 代码执行"混合架构

LLM 不直接操纵系统状态，只输出受控命令，工程代码负责校验和执行：

```
用户文本
  → TurnPlanner（LLM 生成 TurnPlan JSON：task/knowledge/chitchat 三选一）
  → TurnPlanValidator（校验轨道数量、命令非空、焦点对象匹配）
  → 通过 → CommandProcessor（start_flow/set_slots/resume_flow/cancel_flow 应用到状态）
  → 失败 → ClarifyResponder（生成自然语言追问）
  → FlowExecutor（双层循环推进 YAML 流程，直到 action_listen 等待用户输入）
```

这条链解决的核心问题：**LLM 幻觉拦截**。LLM 生成了不存在的 flow、重复轨道、缺焦点对象时，Validator 直接拒绝并澄清，不让幻觉状态进入执行层。

### 2. 任务栈状态机

```
DialogueState
├── active_task        # 当前业务任务（flow_id / step_id / slots）
├── paused_tasks[]     # 被打断挂起的任务栈（可多个，支持恢复）
├── active_system_flow # 系统过渡流程（收集槽位/打断提示/恢复提示）
├── focused_object     # 用户点击的订单/商品卡片
├── sessions[]         # 会话历史（Turn 列表，60 分钟超时重置）
└── pending_turn       # 本轮暂存，两阶段提交
```

用户插话时：当前任务压入 `paused_tasks` → 新任务成为 `active_task` → 系统流程提示"先把 xx 放一放" → 用户说"继续" → `resume_flow` 按 flow_id 找回原任务，`step_id` 和 `slots` 原样恢复。

### 3. 对象消息自动补槽

用户点击订单卡片时，引擎先判断当前 collect 步骤需要哪个槽位（从系统收集流程 `CollectSystemContext` 或用户任务 `CollectSlotStep` 取），再按对象类型匹配：

| 对象类型 | 收集槽位 | 注入值 |
| --- | --- | --- |
| order | order_number | 卡片 ID |
| product | product_id | 卡片 ID |

匹配不上则进入澄清（"我已经收到这个订单了，你想查状态、查物流还是退款？"），不猜用户意图。

### 4. 双层循环流程推进器

- **外层**（run_task）：不断取出 ActionCall 执行，直到遇到 `action_listen`（等待用户输入）退出
- **内层**（advance_until_action）：在流程节点间导航——start 直接跳下一步、end 结束任务、collect 处理槽位收集与校验、action 返回 ActionCall

条件分支通过 `eval(condition, {"slots": ..., "context": ...})` 执行 YAML 中声明的 Python 表达式（配置可信，非用户输入）。

### 5. Action 插件化

- `Action` 抽象基类：子类定义 `name` + `run(state, action_kwargs) -> ActionResult(messages, slot_updates)`
- `ActionRegistry`：name → Action 实例的注册字典
- 自动扫描：`pkgutil.iter_modules` 遍历 custom 包 → `inspect.getmembers` 找出 Action 子类 → 自动注册，新增 Action 文件即被发现
- Action 不直接改状态，只声明 `slot_updates`，由 FlowExecutor 统一回写，保持 Action 无状态、可测试

---

## 技术栈

- **后端框架**：FastAPI + Uvicorn（异步 ASGI），lifespan 生命周期管理资源
- **LLM 调用**：LangChain（`init_chat_model` + `PromptTemplate | llm | JsonOutputParser / StrOutputParser` 管道）
- **流程引擎**：自研 YAML Flow（Flow → Step → Link 三层模型，4 种节点类型，条件分支 eval）
- **数据存储**：MySQL（SQLAlchemy 2.0 异步 ORM，aiomysql 驱动），状态 JSON 整存整取
- **HTTP 调用**：HTTPX AsyncClient（异步请求电商业务后端 API，订单+物流并发拉取）
- **模板渲染**：Jinja2（Prompt 模板 + 回复文本变量插值，如 `订单{{ slots.order_number }}`）
- **配置管理**：Pydantic Settings（.env 环境变量加载）

---

## 目录结构

```
├── main.py                          # 项目入口（uvicorn 启动）
├── .env                             # 环境变量配置
├── pyproject.toml                   # 项目元数据
├── flow_config/                     # YAML 业务流程配置
│   ├── user_flows.yml               # 用户业务流程（欢迎/查订单/查物流/退款/相似推荐/人工客服）
│   └── system_flows.yml             # 系统流程（任务开始/恢复/中断/取消/收集信息/无法处理）
└── dianshang/                       # 项目主体包
    ├── api/                         # FastAPI 接口层（app / dependencies / schemas / routers）
    ├── conf/config.py               # Pydantic Settings 配置加载
    ├── infrastructure/              # LLM 客户端 / HTTPX 客户端 / 数据库引擎
    ├── domain/                      # 领域模型（messages / contexts / state）
    ├── engine/                      # 对话引擎（builder 组装 / dialogue_engine 总调度）
    ├── service/dialogue_service.py  # 加载状态→引擎处理→保存状态
    ├── repository/                  # DialogueState MySQL 读写（upsert）
    ├── models/                      # SQLAlchemy ORM（dialogue_states 表）
    ├── plan/                        # TurnPlanner / TurnPlanValidator / TurnPlan 模型
    ├── task/                        # 任务流处理（command / flow / action 三层）
    │   └── action/
    │       ├── builtin/             # action_response（static/rephrase/generate）+ action_listen
    │       └── custom/              # 查订单 / 查物流 / 相似推荐 / 自定义扩展点（自动扫描注册）
    ├── knowledge/                   # 知识层（intents / providers / registry / responder / handler）
    ├── chitchat/                    # 闲聊层
    ├── clarify/                     # 澄清追问层
    └── prompts/                     # Jinja2 Prompt 模板（turn_plan / knowledge / clarify / chitchat）
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

服务启动后监听 `http://127.0.0.1:8000`，接口文档见 `http://127.0.0.1:8000/docs`。

---

## 接口文档

### POST /api/chat

发送消息并获取客服回复。

**文本消息**

```json
{
  "sender_id": "user_1001",
  "text": "帮我查一下订单状态",
  "message_id": "msg_001"
}
```

**对象消息（用户点击订单卡片）**

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
    { "text": "请告诉我你的订单号。" }
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

---

## 扩展指南

### 新增一个业务流程（如"换货申请"）

在 `flow_config/user_flows.yml` 中添加流程定义，引擎启动时自动加载，无需改动任何 Python 代码：

```yaml
flows:
  exchange_request:
    name: 换货申请
    description: 帮用户提交换货申请
    steps:
      - id: start
        type: start
        next: ask_order_number
      - id: ask_order_number
        type: collect
        slot_name: order_number
        response:
          text: "请告诉我要换货的订单号。"
        next: ask_reason
      - id: ask_reason
        type: collect
        slot_name: exchange_reason
        response:
          text: "请说明换货原因。"
        next: submitted
      - id: submitted
        type: action
        action: action_response
        args:
          text: "好的，订单{{ slots.order_number }}的换货申请已提交，原因：{{ slots.exchange_reason }}。"
        next: end
      - id: end
        type: end
        next: []
```

### 新增一个自定义 Action

在 `dianshang/task/action/custom/` 下新建文件，保存后自动被扫描注册：

```python
from dianshang.task.action.base import Action, ActionResult
from dianshang.domain.state import DialogueState

class CheckInventoryAction(Action):
    name = "action_check_inventory"

    async def run(self, state: DialogueState, action_kwargs: dict) -> ActionResult:
        product_id = state.active_task.slots.get("product_id")
        # 调用库存 API ...
        return ActionResult(slot_updates={"stock": "有货"})
```

---

## 典型对话演示

**场景：退款流程中插入物流查询，再恢复退款**

```
用户：我要申请退款
客服：请告诉我你的订单号。
用户：A20260410001
客服：请简单说一下退款原因。
用户：不想要了。对了，这个订单现在到哪了？
客服：好的，我们先把退款申请放一放。
      订单A20260410001由顺丰速运配送，物流单号是SF1234567890。当前进度：已签收。
用户：继续退款吧
客服：好的，我们继续刚才的退款申请。
      订单A20260410001的退款申请已提交，原因是：不想要了。后续会尽快为你处理。
```

**场景：点击订单卡片自动补槽**

```
用户：（点击订单卡片，type=order, id=A20260410001）帮我查下这个
客服：订单A20260410001当前状态是：已发货。订单金额 ¥299.00。商品：无线蓝牙耳机。
```
