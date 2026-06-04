"""
TutorFlow UI 组件

提供可复用的 Streamlit UI 组件：
- 代码编辑器（支持 Monaco 增强模式 + 文件名栏）
- Mermaid 流程图渲染
- 学习进度展示
- 对话消息渲染
"""

import re
import json
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional


# ── 代码编辑器 ─────────────────────────────────────────────

# 文件名栏 CSS
FILENAME_BAR_CSS = """
<style>
    .filename-bar {
        display: flex;
        align-items: center;
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
        border-bottom: none;
        border-radius: 8px 8px 0 0;
        padding: 6px 14px;
        font-size: 13px;
        font-family: 'Consolas', 'Courier New', monospace;
        gap: 8px;
    }
    .filename-bar .file-icon {
        color: #f0c040;
        font-size: 16px;
    }
    .filename-bar .file-name {
        color: #d4d4d4;
        font-weight: 500;
    }
    .filename-bar .file-hint {
        color: #6a6a6a;
        margin-left: auto;
        font-size: 11px;
    }
    /* 当文件名栏存在时，编辑器去掉上圆角 */
    .filename-bar + div > .code-editor-container,
    .filename-bar + .stMarkdown + div > .code-editor-container {
        border-radius: 0 0 8px 8px !important;
    }
</style>
"""

# 自定义 CSS：让 text_area 看起来像代码编辑器
CODE_EDITOR_CSS = """
<style>
    /* 代码编辑器容器样式 */
    .code-editor-container {
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    .code-editor-container .stTextArea {
        margin: 0;
    }
    .code-editor-container .stTextArea textarea {
        font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas',
                     'Monaco', 'Courier New', monospace !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        background-color: #1e1e1e !important;
        color: #d4d4d4 !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 16px !important;
        tab-size: 4;
    }
    .code-editor-container .stTextArea textarea:focus {
        box-shadow: inset 0 0 0 2px #0078d4 !important;
        outline: none !important;
    }
    .code-editor-container .stTextArea textarea::placeholder {
        color: #6a6a6a !important;
    }
</style>
"""


def render_filename_bar(filename: str = "main.py") -> None:
    """渲染编辑器顶部的文件名标签栏"""
    st.markdown(FILENAME_BAR_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="filename-bar">'
        f'<span class="file-icon">📄</span>'
        f'<span class="file-name">{filename}</span>'
        f'<span class="file-hint">saved_code/</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_code_editor(
    code: str = "",
    height: int = 500,
    key: str = "code_editor",
) -> str:
    """
    渲染代码编辑器。

    优先尝试 streamlit-monaco；如果未安装则回退到
    增强版 text_area（暗色主题 + 等宽字体）。

    Returns:
        编辑器中的当前代码
    """
    st.markdown(CODE_EDITOR_CSS, unsafe_allow_html=True)

    # ── 尝试使用 Monaco ──
    try:
        from streamlit_monaco import st_monaco

        edited_code = st_monaco(
            value=code or "# 在这里编写你的 Python 代码\n",
            language="python",
            theme="vs-dark",
            height=height,
            key=f"{key}_monaco",
            options={
                "minimap": {"enabled": False},
                "fontSize": 14,
                "lineNumbers": "on",
                "scrollBeyondLastLine": False,
                "automaticLayout": True,
                "tabSize": 4,
                "renderWhitespace": "selection",
            },
        )
        if isinstance(edited_code, dict):
            return edited_code.get("value", code)
        return edited_code if edited_code else code

    except ImportError:
        pass

    # ── 备用：暗色主题 text_area ──
    st.markdown('<div class="code-editor-container">', unsafe_allow_html=True)
    placeholder = "# 在这里编写你的 Python 代码\n"
    edited_code = st.text_area(
        label="代码编辑器",
        value=code if code else placeholder,
        height=height,
        key=key,
        label_visibility="collapsed",
        placeholder=placeholder,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    return edited_code


# ── Mermaid 渲染 ──────────────────────────────────────────

MERMAID_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: '{theme}',
            securityLevel: 'loose',
        }});
    </script>
    <style>
        body {{
            margin: 0;
            padding: 16px;
            background-color: {bg};
            display: flex;
            justify-content: center;
        }}
        .mermaid {{
            font-family: 'Segoe UI', sans-serif;
        }}
    </style>
</head>
<body>
    <div class="mermaid">
{diagram}
    </div>
</body>
</html>
"""


def render_mermaid(diagram: str, height: int = 300,
                   theme: str = "default") -> None:
    """
    在 Streamlit 中渲染 Mermaid 流程图。

    Args:
        diagram: Mermaid 语法内容（不含 ```mermaid 标记）
        height: iframe 高度
        theme: 'default' | 'dark' | 'forest' | 'neutral'
    """
    bg = "#ffffff" if theme == "default" else "#1e1e1e"

    html = MERMAID_HTML_TEMPLATE.format(
        diagram=diagram.strip(),
        theme=theme,
        bg=bg,
    )
    components.html(html, height=height, scrolling=True)


def extract_and_render_mermaid(content: str) -> str:
    """
    从 Markdown 内容中提取 Mermaid 代码块并渲染。

    将 ```mermaid ... ``` 替换为占位符，渲染图表后拼接。

    Returns:
        移除 Mermaid 块后的纯 Markdown（图表已单独渲染）
    """
    pattern = r"```mermaid\s*\n(.*?)```"
    matches = list(re.finditer(pattern, content, re.DOTALL))

    for i, match in enumerate(matches):
        diagram = match.group(1).strip()
        if diagram:
            # 估算高度：每行约20px
            lines = diagram.count("\n") + 1
            height = max(200, min(600, lines * 22))
            render_mermaid(diagram, height=height)

    # 返回移除 Mermaid 块后的内容
    cleaned = re.sub(pattern, "", content, flags=re.DOTALL)
    return cleaned


def render_chat_message(role: str, content: str) -> None:
    """
    渲染一条聊天消息。

    - 支持 Markdown
    - 自动检测并渲染 Mermaid 图表
    - user/assistant 分别使用不同样式
    """
    with st.chat_message(role):
        # 先渲染 Mermaid 图表
        cleaned = extract_and_render_mermaid(content)
        # 再渲染剩余 Markdown
        if cleaned.strip():
            st.markdown(cleaned)


# ── 进度管理 UI ───────────────────────────────────────────

def render_module_card(module: dict, subtasks: list[dict], db) -> None:
    """渲染单个模块卡片及其子任务"""
    status_map = {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
    }
    icon = status_map.get(module["status"], "❓")

    with st.expander(
        f"{icon} {module['name']}",
        expanded=(module["status"] == "in_progress"),
    ):
        if module.get("description"):
            st.caption(module["description"])

        for st_item in subtasks:
            st_icon = status_map.get(st_item["status"], "❓")
            col1, col2 = st.columns([8, 2])

            with col1:
                st.markdown(f"{st_icon} {st_item['name']}")
                if st_item.get("description"):
                    st.caption(f"　{st_item['description']}")

            with col2:
                new_status = st.selectbox(
                    "状态",
                    options=["pending", "in_progress", "completed"],
                    index=["pending", "in_progress", "completed"].index(
                        st_item["status"]
                    ),
                    key=f"status_subtask_{st_item['id']}",
                    label_visibility="collapsed",
                )
                if new_status != st_item["status"]:
                    db.update_subtask_status(st_item["id"], new_status)
                    st.rerun()


def render_progress_overview(db) -> None:
    """渲染学习进度概览（用于侧边栏），含总进度条和各模块进度"""
    modules = db.get_all_modules()

    if not modules:
        st.info("还没有学习模块，点击下方按钮创建。")
        return

    # ── 总体统计 ──
    total_subtasks = 0
    completed_subtasks = 0
    for mod in modules:
        subtasks = db.get_subtasks(mod["id"])
        total_subtasks += len(subtasks)
        completed_subtasks += sum(1 for s in subtasks if s["status"] == "completed")

    if total_subtasks > 0:
        pct = int(completed_subtasks / total_subtasks * 100)
        st.progress(
            completed_subtasks / total_subtasks,
            text=f"📊 总进度: {completed_subtasks}/{total_subtasks} ({pct}%)",
        )
    else:
        st.caption("📊 暂无子任务，先生成模块吧")

    # ── 当前焦点 ──
    current_module = db.get_current_module()
    if current_module:
        st.markdown(
            f"**🎯 当前:** {current_module['name']} `[{current_module['status']}]`"
        )
        current_subtask = db.get_current_subtask(current_module["id"])
        if current_subtask:
            st.markdown(f"**📌 子任务:** {current_subtask['name']} `[{current_subtask['status']}]`")

    st.divider()

    # ── 各模块进度 ──
    for mod in modules:
        subtasks = db.get_subtasks(mod["id"])
        done = sum(1 for s in subtasks if s["status"] == "completed")
        total = len(subtasks)

        status_icon = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(mod["status"], "❓")

        with st.expander(
            f"{status_icon} {mod['name']}",
            expanded=(mod["status"] == "in_progress"),
        ):
            if mod.get("description"):
                st.caption(mod["description"])

            # 模块内进度条
            if total > 0:
                st.progress(done / total, text=f"模块进度: {done}/{total}")
            else:
                st.caption("暂无子任务")

            for st_item in subtasks:
                st_icon = {"pending": "⬜", "in_progress": "🔷", "completed": "✅"}.get(st_item["status"], "❓")
                col1, col2 = st.columns([8, 2])
                with col1:
                    st.markdown(
                        f'<span style="font-size:13px;">{st_icon} '
                        f'{st_item["name"]}</span>',
                        unsafe_allow_html=True,
                    )
                    if st_item.get("description"):
                        st.caption(f"　{st_item['description']}")
                with col2:
                    new_status = st.selectbox(
                        "状态",
                        options=["pending", "in_progress", "completed"],
                        index=["pending", "in_progress", "completed"].index(
                            st_item["status"]
                        ),
                        key=f"status_subtask_{st_item['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != st_item["status"]:
                        db.update_subtask_status(st_item["id"], new_status)
                        st.rerun()
