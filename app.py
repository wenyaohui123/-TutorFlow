"""
TutorFlow — AI 编程导师
========================

基于 Streamlit 的本地 AI 编程教学平台。
双栏布局：代码编辑 | AI 对话
"""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import Database
from llm_service import LLMService
from ui_components import (
    render_code_editor,
    extract_and_render_mermaid,
    render_progress_overview,
)

# ── 文件名栏 ──────────────────────────────────────────────

FILENAME_BAR_CSS = """
<style>
    .filename-bar {
        display: flex; align-items: center;
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a; border-bottom: none;
        border-radius: 8px 8px 0 0;
        padding: 6px 14px; font-size: 13px;
        font-family: 'Consolas', 'Courier New', monospace; gap: 8px;
    }
    .filename-bar .file-icon { color: #f0c040; font-size: 16px; }
    .filename-bar .file-name { color: #d4d4d4; font-weight: 500; }
    .filename-bar .file-hint { color: #6a6a6a; margin-left: auto; font-size: 11px; }
</style>
"""

def render_filename_bar(filename: str = "main.py") -> None:
    st.markdown(FILENAME_BAR_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="filename-bar">'
        f'<span class="file-icon">📄</span>'
        f'<span class="file-name">{filename}</span>'
        f'<span class="file-hint">saved_code/</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── 页面配置 ──────────────────────────────────────────────

st.set_page_config(
    page_title="TutorFlow — AI 编程导师",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 初始化 ────────────────────────────────────────────────

config = Config()
db = Database(config)
llm = LLMService(config, db)

DEFAULT_CODE = """# TutorFlow - AI 编程导师
# 在侧边栏输入项目描述，AI 将为你生成学习模块。
# 选择一个模块开始学习，导师会一步步指导你。
#
# 工作流：
#   1. 输入项目提示词 -> 生成模块
#   2. 选择模块 -> 开始学习
#   3. 在本地 IDE 运行 -> 粘贴报错到下方
#   4. 向导师提问 -> 导师审查代码
"""

DEFAULT_FILENAME = "main.py"


def load_code_for_file(filename: str) -> str:
    filepath = os.path.join(config.saved_code_dir, filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                return content if content.strip() else DEFAULT_CODE
    except Exception:
        pass
    return DEFAULT_CODE


def save_code_to_file(code: str, filename: str) -> None:
    filepath = os.path.join(config.saved_code_dir, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        st.error(f"保存失败: {e}")


# ── Session State ─────────────────────────────────────────

def init_session_state():
    current_mod = db.get_current_module()
    auto_filename = f"{current_mod['name']}.py" if current_mod else DEFAULT_FILENAME

    defaults = {
        "messages": [],
        "code": load_code_for_file(auto_filename),
        "error_info": "",
        "current_filename": auto_filename,
        "selected_module_id": current_mod["id"] if current_mod else None,
        "project_prompt": "",
        "modules_generated": False,
        "api_configured": bool(config.api_key),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ── 全局 CSS ──────────────────────────────────────────────

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    }
    .main-header {
        font-size: 1.8rem; font-weight: 700;
        color: #0078d4; margin-bottom: 0.5rem;
    }
    .sidebar-section-title {
        font-size: 0.85rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px;
        color: #888; margin-top: 1rem; margin-bottom: 0.5rem;
    }
    .stChatInput textarea { font-size: 14px !important; }

    /* 模块选择卡片 */
    .module-select-card {
        border: 1px solid #3a3a3a; border-radius: 8px;
        padding: 10px 14px; margin: 4px 0;
        cursor: pointer; transition: all 0.15s;
    }
    .module-select-card:hover {
        border-color: #0078d4;
        background: rgba(0,120,212,0.05);
    }
    .module-select-card.selected {
        border-color: #0078d4;
        background: rgba(0,120,212,0.1);
    }
    .module-select-card .mod-name { font-weight: 600; font-size: 14px; }
    .module-select-card .mod-desc { font-size: 12px; color: #888; margin-top: 2px; }
    .module-select-card .mod-count { font-size: 11px; color: #666; margin-top: 2px; }

    /* 让主内容区铺满 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
    }
    .main > div:first-child {
        padding-top: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="main-header">🎓 TutorFlow</div>', unsafe_allow_html=True)
    st.caption("AI 编程导师 · 本地学习平台")
    st.divider()

    tab_project, tab_progress, tab_settings = st.tabs([
        "📝 项目设置", "📚 学习进度", "⚙️ API 设置"
    ])

    # ── Tab 1: 项目设置 ──
    with tab_project:
        st.markdown('<p class="sidebar-section-title">🚀 项目提示词</p>', unsafe_allow_html=True)
        st.caption("输入你要开发的项目描述，AI 将为你拆解学习模块。")

        project_prompt = st.text_area(
            "项目描述", value=st.session_state.project_prompt, height=150,
            placeholder="例如：\n开发一个简单的人事管理系统，包含：\n"
                        "- 员工信息管理（CRUD）\n"
                        "- 部门管理\n"
                        "- 考勤记录\n"
                        "- 使用 Python + Flask + SQLite",
            key="project_prompt_input", label_visibility="collapsed",
        )

        if project_prompt:
            st.session_state.project_prompt = project_prompt

        col_gen1, col_gen2 = st.columns([3, 1])
        with col_gen1:
            gen_clicked = st.button(
                "🤖 AI 生成学习模块", use_container_width=True,
                type="primary", key="btn_generate_modules",
            )
        with col_gen2:
            if st.button("🗑 清空", use_container_width=True, key="btn_clear_project"):
                st.session_state.project_prompt = ""
                st.session_state.modules_generated = False
                st.session_state.selected_module_id = None
                db.clear_all_modules()
                st.rerun()

        if gen_clicked:
            if not st.session_state.project_prompt.strip():
                st.error("请先输入项目描述。")
            elif not config.api_key:
                st.error("请先在「⚙️ API 设置」中配置 API Key。")
            else:
                with st.spinner("🤔 AI 正在分析项目结构..."):
                    try:
                        modules_data = llm.generate_project_modules(
                            st.session_state.project_prompt.strip()
                        )
                        if not modules_data:
                            st.error("AI 未能生成模块，请调整项目描述后重试。")
                        else:
                            count = db.import_project_modules(modules_data)
                            st.session_state.modules_generated = True
                            st.session_state.selected_module_id = None
                            st.success(f"✅ 已生成 {count} 个学习模块！")
                            st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except RuntimeError as e:
                        st.error(str(e))

        # ── 模块选择 ──
        modules = db.get_all_modules()
        if modules:
            st.divider()
            st.markdown('<p class="sidebar-section-title">📋 选择要学习的模块</p>', unsafe_allow_html=True)

            for mod in modules:
                subtasks = db.get_subtasks(mod["id"])
                is_selected = st.session_state.selected_module_id == mod["id"]
                is_current = mod["status"] == "in_progress"

                status_icon = {"pending": "⬜", "in_progress": "🔄", "completed": "✅"}.get(mod["status"], "❓")
                card_class = "module-select-card" + (" selected" if is_current else "")

                col_sel, col_info = st.columns([1, 9])
                with col_sel:
                    selected = st.radio(
                        "选择", options=[mod["id"]], format_func=lambda x: "",
                        key=f"select_mod_{mod['id']}", label_visibility="collapsed",
                        index=0 if is_selected else None if st.session_state.selected_module_id else None,
                    )
                    if selected and selected != st.session_state.selected_module_id:
                        st.session_state.selected_module_id = selected
                        st.rerun()
                with col_info:
                    st.markdown(
                        f'<div class="{card_class}">'
                        f'<div class="mod-name">{status_icon} {mod["name"]}</div>'
                        f'<div class="mod-desc">{mod.get("description", "")}</div>'
                        f'<div class="mod-count">{len(subtasks)} 个子任务</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.divider()

            selected_mod = db.get_module(st.session_state.selected_module_id) if st.session_state.selected_module_id else None
            if selected_mod:
                st.caption(f"已选择: **{selected_mod['name']}**")
                if st.button("🎯 开始学习此模块", use_container_width=True, type="primary"):
                    for m in modules:
                        db.update_module_status(m["id"], "pending")
                    db.update_module_status(st.session_state.selected_module_id, "in_progress")
                    new_filename = f"{selected_mod['name']}.py"
                    st.session_state.current_filename = new_filename
                    st.session_state.code = load_code_for_file(new_filename)
                    st.session_state.messages = []
                    db.clear_conversations()
                    st.success(f"🎯 开始学习「{selected_mod['name']}」！")
                    st.rerun()
            else:
                st.caption("👆 请先选择一个模块")

    # ── Tab 2: 学习进度 ──
    with tab_progress:
        render_progress_overview(db)

    # ── Tab 3: API 设置 ──
    with tab_settings:
        st.markdown('<p class="sidebar-section-title">🔑 大模型 API 配置</p>', unsafe_allow_html=True)

        api_preset = st.selectbox(
            "API 提供商",
            options=["自定义", "OpenAI", "DeepSeek", "Ollama (本地)", "Groq"],
            key="api_preset",
        )

        preset_urls = {
            "OpenAI": "https://api.openai.com/v1",
            "DeepSeek": "https://api.deepseek.com/v1",
            "Ollama (本地)": "http://localhost:11434/v1",
            "Groq": "https://api.groq.com/openai/v1",
        }
        preset_models = {
            "OpenAI": "gpt-4o",
            "DeepSeek": "deepseek-chat",
            "Ollama (本地)": "llama3",
            "Groq": "llama-3.1-70b-versatile",
        }

        with st.form("api_settings_form"):
            api_base = st.text_input(
                "API Base URL",
                value=preset_urls.get(api_preset, config.api_base) if not config.api_key else config.api_base,
                placeholder="https://api.openai.com/v1",
            )
            api_key = st.text_input(
                "API Key",
                value=config.api_key if config.api_key else "",
                type="password", placeholder="sk-...",
            )
            model = st.text_input(
                "模型名称",
                value=preset_models.get(api_preset, config.model) if not config.api_key else config.model,
                placeholder="gpt-4o / deepseek-chat / doubao-pro-32k",
            )

            col_save, col_test = st.columns(2)
            with col_save:
                save_clicked = st.form_submit_button("💾 保存配置", use_container_width=True)
            with col_test:
                test_clicked = st.form_submit_button("🔍 测试连接", use_container_width=True)

            if save_clicked:
                config.update_api(api_base, api_key, model)
                llm.config = config
                llm._client = None
                st.session_state.api_configured = bool(api_key)
                st.success("✅ API 配置已保存！")
                st.rerun()

            if test_clicked:
                if not api_key:
                    st.error("请先输入 API Key。")
                else:
                    config.update_api(api_base, api_key, model)
                    llm.config = config
                    llm._client = None
                    try:
                        test_response = llm.chat(
                            messages=[{"role": "user", "content": "请回复：连接成功！"}],
                            current_code="", error_info="",
                        )
                        if "连接成功" in test_response or ("错误" not in test_response and len(test_response) > 0):
                            st.success("✅ API 连接成功！")
                            st.session_state.api_configured = True
                        else:
                            st.warning(f"⚠️ 响应异常: {test_response[:200]}")
                    except Exception as e:
                        st.error(f"❌ 连接失败: {e}")

        if config.api_key:
            masked = config.api_key[:8] + "..." + config.api_key[-4:] if len(config.api_key) > 12 else "***"
            st.caption(f"✅ 当前: {config.model} @ {config.api_base}")
            st.caption(f"🔑 Key: {masked}")
        else:
            st.caption("⚠️ 尚未配置 API Key，聊天功能不可用。")

    st.divider()

    st.markdown('<p class="sidebar-section-title">🔧 快捷操作</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑 清空对话", use_container_width=True):
            st.session_state.messages = []
            db.clear_conversations()
            st.rerun()
    with col_b:
        if st.button("🔄 重置代码", use_container_width=True):
            st.session_state.code = DEFAULT_CODE
            save_code_to_file(DEFAULT_CODE, st.session_state.current_filename)
            st.rerun()

    if st.button("📥 导出对话记录", use_container_width=True):
        messages = st.session_state.messages
        if messages:
            export = "\n\n".join(f"## {m['role'].upper()}\n\n{m['content']}" for m in messages)
            st.download_button(
                "下载对话记录", data=export,
                file_name="tutorflow_conversation.md",
                mime="text/markdown", use_container_width=True,
            )
        else:
            st.caption("暂无对话记录。")

# ═══════════════════════════════════════════════════════════
# 主内容区：双栏布局
# ═══════════════════════════════════════════════════════════

col_code, col_chat = st.columns([5, 4], gap="medium")

# ── 左列：代码编辑区 ──

with col_code:
    render_filename_bar(st.session_state.current_filename)
    render_code_editor(code=st.session_state.code, height=520, key="code")

    btn_col1, btn_col2 = st.columns([1, 1], gap="small")
    with btn_col1:
        if st.button("💾 保存", use_container_width=True, key="btn_save"):
            save_code_to_file(st.session_state.code, st.session_state.current_filename)
            st.toast(f"✅ 已保存到 saved_code/{st.session_state.current_filename}", icon="💾")
    with btn_col2:
        new_filename = st.text_input(
            "文件名", value=st.session_state.current_filename,
            key="filename_editor", label_visibility="collapsed", placeholder="main.py",
        )
        if new_filename != st.session_state.current_filename:
            save_code_to_file(st.session_state.code, new_filename)
            st.session_state.current_filename = new_filename
            st.rerun()

    st.text_area(
        "🐛 报错信息（从本地 IDE 粘贴，AI 导师会帮你分析）",
        key="error_info", height=100,
        placeholder="将本地 IDE 的运行报错粘贴到这里...",
        label_visibility="visible",
    )

# ── 右列：AI 对话区（上下顶满）──

with col_chat:
    # 对话历史 — 用较大高度撑满
    chat_container = st.container(height=750)

    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#888;">
                <p style="font-size:3.5rem;margin-bottom:8px;">🎓</p>
                <p style="font-size:1.2rem;font-weight:600;color:#aaa;">TutorFlow</p>
                <p style="font-size:0.9rem;">
                    左侧编写代码，下方向导师提问<br>
                    导师会一步步引导你完成项目
                </p>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                cleaned = extract_and_render_mermaid(msg["content"])
                if cleaned.strip():
                    st.markdown(cleaned, unsafe_allow_html=False)

    if prompt := st.chat_input("向 AI 导师提问..."):
        if not st.session_state.api_configured and not config.api_key:
            st.error("⚠️ 请先在侧边栏 -> ⚙️ API 设置 中配置 API Key。")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        db.add_message("user", prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤔 导师思考中..."):
                response = llm.chat(
                    messages=st.session_state.messages,
                    current_code=st.session_state.code,
                    error_info=st.session_state.get("error_info", ""),
                )
            cleaned = extract_and_render_mermaid(response)
            if cleaned.strip():
                st.markdown(cleaned)

        st.session_state.messages.append({"role": "assistant", "content": response})
        db.add_message("assistant", response)

        if st.session_state.get("error_info", "").strip():
            st.session_state.error_info = ""
        st.rerun()
