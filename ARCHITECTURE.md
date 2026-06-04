# 🎓 TutorFlow — 架构与技术文档

> AI 编程导师 — 基于 Streamlit 的本地 AI 编程教学平台

---

## 一、项目概述

TutorFlow 是一个本地运行的 Web 应用，通过大语言模型（LLM）扮演编程导师角色，指导用户**一步步从零完成复杂的开发项目**。核心设计理念是：**AI 不会直接给答案，而是引导用户自己思考和实践**。

### 核心能力

```
用户输入项目描述 → AI 拆解学习模块 → 逐步教学 → 用户写代码 → AI 审查引导
```

---

## 二、技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端框架** | Streamlit 1.58 | Web UI（宽屏三栏布局、聊天组件、文件上传） |
| **代码编辑器** | Monaco Editor (streamlit-monaco) / text_area fallback | Python 语法高亮编辑 |
| **数据库** | SQLite 3 (WAL mode, thread-safe) | 模块/子任务/对话/笔记持久化 |
| **LLM SDK** | openai >= 1.0 | OpenAI 兼容 API 调用（支持 豆包/GPT/DeepSeek 等） |
| **代码执行** | subprocess (Python) | 隔离子进程执行代码，超时控制 |
| **图表渲染** | Mermaid.js (CDN) | 聊天消息中渲染流程图 |
| **配置持久化** | JSON 文件 (`data/config.json`) | API Key 本地加密存储 |
| **代码持久化** | 本地文件 (`saved_code/*.py`) | 每个模块独立 .py 文件 |

---

## 三、项目结构

```
study_pp/
├── app.py              # 主入口 — Streamlit UI、布局、事件处理
├── config.py           # 配置管理 — API 配置 + JSON 持久化
├── database.py         # 数据库层 — SQLite CRUD 封装
├── llm_service.py      # LLM 服务 — 上下文拼装 + System Prompt + API 调用
├── code_runner.py      # 代码执行 — subprocess 隔离执行
├── ui_components.py    # UI 组件 — 编辑器/Mermaid/进度展示
├── requirements.txt    # 依赖清单
├── README.md           # 用户文档
├── ARCHITECTURE.md     # 本文档
├── data/
│   ├── progress.db     # SQLite 数据库（自动创建）
│   └── config.json     # API 配置（自动创建）
└── saved_code/
    └── *.py            # 用户代码存档（按模块命名）
```

---

## 四、核心架构详解

### 4.1 数据流

```
┌─────────────────────────────────────────────────────────┐
│                      用户操作                            │
│  输入项目描述 │ 选择模块 │ 编写代码 │ 粘贴报错 │ 发送消息  │
└──────┬───────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
       │           │          │          │          │
       ▼           ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────┐
│                   app.py (调度中心)                      │
│  session_state: code | messages | filename | module_id  │
└──┬──────────┬──────────┬───────────┬───────────────────┘
   │          │          │           │
   ▼          ▼          ▼           ▼
┌──────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
│config│ │  db  │ │llm_service│ │code_runner│
│.py   │ │ .py  │ │   .py     │ │   .py     │
└──────┘ └──┬───┘ └────┬─────┘ └──────────┘
            │          │
            ▼          ▼
      ┌─────────┐  ┌─────────────┐
      │ SQLite  │  │ LLM API     │
      │ (本地)   │  │ (云端/本地)  │
      └─────────┘  └─────────────┘
```

### 4.2 模块职责

#### `app.py` — 应用入口与 UI 调度

- **双栏布局**：左 5/9 代码编辑区 + 右 4/9 AI 对话区
- **侧边栏**：项目设置（生成模块）+ 学习进度 + API 配置 + 快捷操作
- **Session State 管理**：`messages`（对话历史）、`code`（代码内容）、`current_filename`、`selected_module_id` 等
- **事件处理**：保存代码、AI 对话、模块选择、进度更新

#### `config.py` — 配置管理

- 使用 Python `dataclass` 管理所有配置项
- **API 配置持久化**：保存到 `data/config.json`，启动时自动加载
- **环境变量优先**：`TUTORFLOW_API_KEY` 等环境变量覆盖文件配置
- 自动创建 `data/` 和 `saved_code/` 目录

```python
# 核心持久化逻辑
def update_api(self, api_base, api_key, model):
    self.api_base = api_base
    self.api_key = api_key
    self.model = model
    self._save_to_file()  # 自动写入 data/config.json
```

#### `database.py` — 数据库层

- **SQLite + WAL 模式**：支持并发读写
- **线程安全**：所有写操作通过 `threading.Lock` 保护
- **外键级联**：删除模块自动删除子任务

**数据模型**：

```sql
modules (id, name, description, status, order_index, created_at, updated_at)
subtasks (id, module_id FK, name, description, status, order_index, ...)
conversations (id, role, content, created_at)
learning_notes (id, subtask_id FK, content, created_at)
```

**核心方法**：
- `import_project_modules(data)` — 批量导入 LLM 生成的项目结构
- `get_progress_summary()` — 生成学习进度文本摘要，注入 LLM 上下文
- `get_current_module()` — 获取 `in_progress` 模块（自动降级到第一个 pending）

#### `llm_service.py` — LLM 服务层

**上下文拼装**：每次对话自动将以下信息打包发给大模型：

```
System Prompt
  + 教学纪律（禁止急躁、原理优先、教学状态机、授人以渔）
  + 学习进度摘要（来自 database.get_progress_summary()）
  + 学生当前代码（来自左侧编辑器）
  + 报错信息（如有）
  + 对话历史（最近 40 轮）
```

**System Prompt 设计** — 这是整个应用的核心：

```
1. 绝对禁止急躁 — 每次只聚焦一个极小逻辑节点
2. 原理解释优先 — 先讲原理，画 Mermaid 图，再让用户写代码
3. 教学状态机 — A(抛出任务) → B(审查代码) → C(推进进度) 严禁跳步
4. 授人以渔 — 引导分析报错，不直接丢修复代码
```

**API 兼容性**：使用 OpenAI SDK，兼容所有 OpenAI 格式 API：
- OpenAI (GPT-4o)
- DeepSeek (deepseek-chat)
- 火山引擎豆包 (doubao-pro-32k)
- Ollama 本地模型
- Groq

**项目模块生成**：`generate_project_modules()` 方法使用独立 System Prompt 将用户的自然语言项目描述拆解为结构化的模块→子任务 JSON，自动写入数据库。

#### `code_runner.py` — 代码执行器

- **subprocess 隔离**：代码在独立子进程中运行
- **超时控制**：默认 30 秒，超时自动 kill
- **输出捕获**：分别捕获 stdout 和 stderr
- **临时文件**：代码写入 tempfile，执行后自动清理

#### `ui_components.py` — 可复用 UI 组件

- `render_code_editor()` — Monaco Editor（可选）/ 暗色主题 text_area 回退
- `render_filename_bar()` — 编辑器顶部文件名标签
- `extract_and_render_mermaid()` — 自动识别 Markdown 中的 Mermaid 代码块并渲染
- `render_progress_overview()` — 侧边栏进度面板（总进度条 + 各模块进度 + 子任务管理）

### 4.3 记忆与持久化机制

| 记忆类型 | 存储位置 | 持久化方式 |
|----------|----------|-----------|
| **API 配置** | `data/config.json` | JSON 文件，保存时写入，启动时加载 |
| **学习进度** | `data/progress.db` | SQLite，每次状态变更即时写入 |
| **对话历史** | `data/progress.db` → `conversations` 表 | 每轮对话追加 |
| **用户代码** | `saved_code/{模块名}.py` | 点击保存时写入文件 |
| **学习笔记** | `data/progress.db` → `learning_notes` 表 | 手动添加 |
| **运行时状态** | `st.session_state` | 仅当前会话，刷新保留（Streamlit 机制） |

**重启恢复流程**：
```
1. config.py → 加载 data/config.json → 恢复 API 配置
2. database.py → 连接 data/progress.db → 恢复学习进度
3. app.py → 查询 in_progress 模块 → 恢复当前文件名和代码
4. saved_code/{模块名}.py → 加载上次保存的代码
```

---

## 五、用户工作流

```
① 配置 API
   侧边栏 → ⚙️ API 设置 → 选择提供商 → 填写 Key → 保存（自动持久化）

② 创建项目
   侧边栏 → 📝 项目设置 → 输入项目描述
   → 点击「🤖 AI 生成学习模块」
   → LLM 返回结构化模块列表 → 写入 SQLite

③ 开始学习
   选择一个模块 → 点击「🎯 开始学习此模块」
   → 创建 {模块名}.py 代码文件 → 清空对话 → 模块状态设为 in_progress

④ 教学循环
   导师: 解释原理 → 画 Mermaid 图 → 告诉你实现什么 → 等待
   你:   在左侧写代码 → 在本地 IDE 运行 → 粘贴报错（如有）→ 发送消息
   导师: 审查代码 → 指出问题 / 给予肯定 → 推进或停留

⑤ 手动推进
   侧边栏 → 📚 学习进度 → 修改子任务状态
   → 即时写入 SQLite → 下次对话 LLM 看到更新后的进度
```

---

## 六、设计决策与权衡

| 决策 | 理由 |
|------|------|
| **Streamlit 而非 React** | 快速开发、Python 全栈、学习场景无需复杂前端 |
| **SQLite 而非 PostgreSQL** | 本地单用户、零配置、零运维 |
| **文件名栏本地定义** | 避免 Streamlit 的跨文件 import 缓存问题 |
| **不内置代码运行** | 用户用本地 IDE 运行，更贴近真实开发环境 |
| **进度手动更新** | 给用户完全控制权，AI 无法越权修改学习状态 |
| **System Prompt 严格教学纪律** | 防止 LLM "过度帮助"，确保学习效果 |

---

## 七、启动方式

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 可选：安装 Monaco 编辑器增强
pip install streamlit-monaco

# 3. 启动
streamlit run app.py

# 4. 浏览器打开 http://localhost:8501
```

---

## 八、扩展方向

- [ ] 支持多项目切换
- [ ] 代码 diff 对比（导师修改 vs 用户代码）
- [ ] 语音交互
- [ ] 学习报告导出（PDF）
- [ ] WebSocket 流式对话
- [ ] Docker 一键部署
