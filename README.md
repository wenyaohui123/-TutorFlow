# 🎓 TutorFlow — AI 编程导师

基于 **Python + Streamlit** 的本地 AI 编程教学平台。左侧代码编辑器 + 右侧 AI 导师对话窗口，帮助你一步步从零完成复杂的开发项目。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 💻 **代码编辑器** | Monaco 编辑器（可选）/ 暗色主题文本编辑器，Python 语法高亮 |
| ▶️ **代码执行** | 隔离的子进程环境，支持超时控制，捕获 stdout/stderr |
| 🤖 **AI 导师** | 基于大模型的编程导师，严格遵循教学纪律，逐步引导 |
| 📊 **进度追踪** | SQLite 本地数据库，管理学习模块、子任务、知识笔记 |
| 🎨 **Mermaid 图表** | 聊天消息中自动渲染流程图，辅助理解复杂逻辑 |
| 💾 **代码持久化** | 一键保存代码到本地文件，启动时自动恢复 |
| 📥 **对话导出** | 支持导出完整对话记录为 Markdown 文件 |
| 🔌 **多 API 支持** | 兼容 OpenAI / DeepSeek / Ollama / Groq 等 API |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

可选：安装 Monaco 编辑器增强

```bash
pip install streamlit-monaco
```

### 2. 启动应用

```bash
streamlit run app.py
```

应用将在浏览器中自动打开（默认 `http://localhost:8501`）。

### 3. 配置 API

1. 点击左侧边栏 → **⚙️ API 设置**
2. 选择你的 API 提供商（OpenAI / DeepSeek / Ollama / Groq / 自定义）
3. 填写 API Key 和模型名称
4. 点击 **💾 保存配置**，然后点击 **🔍 测试连接**

---

## 📁 项目结构

```
study_pp/
├── app.py              # 🏠 主应用入口（Streamlit UI）
├── config.py           # ⚙️ 配置管理（API Key、路径、超时等）
├── database.py         # 🗄️ SQLite 数据库层（模块/子任务/对话/笔记）
├── llm_service.py      # 🧠 LLM 服务层（上下文拼装 + API 调用）
├── code_runner.py      # ▶️ 代码执行器（subprocess 隔离执行）
├── ui_components.py    # 🎨 UI 组件（编辑器、Mermaid、进度展示）
├── requirements.txt    # 📦 Python 依赖
├── README.md           # 📖 项目说明
├── data/               # 💾 数据库文件（自动创建）
│   └── progress.db
└── saved_code/         # 📝 代码存档（自动创建）
    └── current.py
```

---

## 🎯 使用流程

### 学习工作流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 1. 创建模块  │ ──▶ │ 2. 编写代码  │ ──▶ │ 3. 运行测试  │
│   & 子任务   │     │   左侧编辑器  │     │   查看输出   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 6. 推进进度  │ ◀── │ 5. 导师审查  │ ◀── │ 4. 求助导师  │
│  更新任务状态 │     │   引导修改   │     │   发送消息   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### AI 导师教学纪律

导师严格遵循以下原则：

1. **禁止急躁** — 每次只聚焦一个极小的逻辑节点（如一个数据结构初始化）
2. **原理优先** — 先解释底层逻辑，必要时画 Mermaid 流程图
3. **教学状态机** — 抛出任务 → 审查代码 → 推进进度，严禁跳步
4. **授人以渔** — 引导分析报错，不直接丢出修复后的代码

---

## 🔌 支持的 API 提供商

| 提供商 | API Base URL | 推荐模型 |
|--------|-------------|---------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Ollama (本地) | `http://localhost:11434/v1` | `llama3` |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-70b-versatile` |
| 自定义 | 任意 OpenAI 兼容 API | 按需填写 |

---

## 🛠️ 技术栈

- **前端**: Streamlit 1.28+ (wide layout, chat components)
- **编辑器**: Monaco Editor (optional) / Streamlit text_area
- **数据库**: SQLite (thread-safe, WAL mode)
- **LLM**: OpenAI-compatible API
- **代码执行**: subprocess (isolated, timeout-controlled)
- **图表**: Mermaid.js (CDN)

---

## 📝 License

MIT — 自由使用、修改和分发。
