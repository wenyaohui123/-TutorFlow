"""
TutorFlow LLM 服务层

负责：
1. 拼装上下文（对话 + 代码 + 进度）
2. 注入系统提示词
3. 调用 OpenAI 兼容 API
4. 流式 / 非流式响应处理
"""

import json
from typing import Optional
from openai import OpenAI

from config import Config
from database import Database


# ── 核心系统提示词 ──────────────────────────────────────────

SYSTEM_PROMPT = """你是一位极其严谨、极具耐心的算法与开发导师。你的任务是指导用户一步步从零完成复杂的开发项目。

【核心教学纪律】
1. **绝对禁止急躁与过度解答**：你不能一次性输出几百行代码。每次互动，只能聚焦一个极小的逻辑节点（例如：只写一个数据结构的初始化，或者一个特定的状态转移表达式）。
2. **原理解释优先**：在要求用户写代码前，必须先用清晰、通俗的语言解释底层算法逻辑。遇到复杂的模块交互时，请务必使用简单的 Mermaid 流程图绘制简易的示意图，无需复杂的配图，只要能说明逻辑流向即可。
3. **严格的教学状态机**：你的教学必须遵循以下循环，严禁跳步：
   - 步骤 A (抛出任务)：解释当前小节的理论，画简易图，告诉用户需要实现什么目标。停住，等待用户。
   - 步骤 B (审查代码)：读取用户在左侧写出的代码，如果错误，直接指出逻辑漏洞并引导修改；如果正确，给予肯定。
   - 步骤 C (推进进度)：只有当用户写出了正确的表达式或代码块，且明确表示理解后，才能推进到下一个极小的知识点。
4. **授人以渔**：如果用户遇到 Bug，不要直接丢出修复后的代码。请引导用户分析报错信息，指出可能出问题的数据结构或内存逻辑，让用户自己动手改。

【当前学生状态】
{progress_summary}

【学生当前代码】
```python
{current_code}
```

【重要提醒】
- 查看学生当前的代码和进度，据此调整你的教学内容。
- 如果学生代码中有错误，优先引导他们自己发现，不要直接给出答案。
- 请用中文回复。
- 适当使用 Mermaid 流程图辅助说明，格式为 ```mermaid ... ```。
- 每次回复聚焦一个知识点，不要贪多。"""


class LLMService:
    """大模型服务封装"""

    def __init__(self, config: Optional[Config] = None,
                 database: Optional[Database] = None):
        self.config = config or Config()
        self.db = database or Database()
        self._client: Optional[OpenAI] = None
        self._last_api_base: str = ""
        self._last_api_key: str = ""

    @property
    def client(self) -> OpenAI:
        """懒初始化 OpenAI 客户端（配置变更时重建）"""
        if (self._client is None
                or self._last_api_base != self.config.api_base
                or self._last_api_key != self.config.api_key):
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
            )
            self._last_api_base = self.config.api_base
            self._last_api_key = self.config.api_key
        return self._client

    def _build_context(self, current_code: str = "",
                       error_info: str = "") -> dict:
        """
        拼装给 LLM 的完整上下文：
        - 进度摘要
        - 当前代码
        - 报错信息（如有）
        """
        progress = self.db.get_progress_summary()

        # 注入当前代码和报错
        extra = ""
        if current_code.strip():
            extra += f"\n\n【学生当前代码】\n```python\n{current_code}\n```"
        if error_info.strip():
            extra += f"\n\n【学生遇到的报错】\n{error_info}"

        system = SYSTEM_PROMPT.format(
            progress_summary=progress,
            current_code=current_code or "# 学生尚未编写代码",
        )

        if error_info.strip():
            system += f"\n\n⚠️ 学生当前遇到了以下报错，请引导他们分析并解决：\n{error_info}"

        return system

    def chat(self, messages: list[dict], current_code: str = "",
             error_info: str = "") -> str:
        """
        发送对话请求，返回助手回复。

        Args:
            messages: 对话历史 [{"role":"user"|"assistant", "content":"..."}, ...]
            current_code: 左侧编辑器当前代码
            error_info: 用户输入的报错信息

        Returns:
            助手回复文本
        """
        system = self._build_context(current_code, error_info)

        api_messages = [{"role": "system", "content": system}]
        # 限制上下文长度（最近 40 轮）
        api_messages.extend(messages[-80:])

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=api_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            error_msg = str(e)
            # 常见错误友好提示
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                return (
                    "❌ **API 认证失败**\n\n"
                    "请检查 API Key 是否正确配置。\n"
                    "在左侧边栏 → API 设置中更新你的 API Key。"
                )
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                return (
                    "❌ **网络连接失败**\n\n"
                    f"无法连接到 `{self.config.api_base}`。\n"
                    "请检查 API Base URL 和网络连接。"
                )
            elif "model" in error_msg.lower():
                return (
                    f"❌ **模型错误**: {error_msg}\n\n"
                    "请检查模型名称是否正确，或该 API 是否支持所选模型。"
                )
            else:
                return f"❌ **API 调用失败**: {error_msg}"

    # ── 项目模块生成 ─────────────────────────────────────

    MODULE_GEN_SYSTEM = """你是一个项目架构分解专家。用户会给你一个项目的需求描述，你需要将其拆解为合理的学习模块和子任务。

请严格按照以下 JSON 格式输出（不要输出任何其他内容）：

```json
{
  "modules": [
    {
      "name": "模块名称（简洁、具体）",
      "description": "模块描述（1-2句话说明要学什么）",
      "subtasks": [
        {"name": "子任务名称", "description": "简要说明"},
        {"name": "子任务名称", "description": "简要说明"}
      ]
    }
  ]
}
```

拆解原则：
1. 模块数量控制在 4-8 个，按开发顺序排列
2. 每个模块 3-6 个子任务，每个子任务是一个极小的可执行单元
3. 从简单到复杂，循序渐进
4. 每个模块聚焦一个独立的技术点或功能区域
5. 子任务要具体到"实现什么功能"或"学习什么概念"，不要笼统
6. 使用中文命名"""

    def generate_project_modules(self, project_prompt: str) -> list[dict]:
        """
        根据项目描述生成学习模块结构。

        Args:
            project_prompt: 用户的项目需求描述

        Returns:
            modules_data 列表，格式与 import_project_modules 兼容
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.MODULE_GEN_SYSTEM},
                    {"role": "user", "content": f"请为以下项目拆解学习模块：\n\n{project_prompt}"},
                ],
                max_tokens=4096,
                temperature=0.7,
            )

            content = response.choices[0].message.content or ""

            # 尝试从回复中提取 JSON
            # 先找 ```json ... ``` 代码块
            import re
            json_match = re.search(r'```json\s*\n(.*?)```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

            # 尝试找 { ... } 最外层
            brace_match = re.search(r'\{.*\}', content, re.DOTALL)
            if brace_match:
                content = brace_match.group(0)

            data = json.loads(content)
            modules = data.get("modules", [])

            return modules

        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(
                f"AI 返回的内容无法解析为模块结构。\n"
                f"请重试或调整项目描述。\n"
                f"原始输出:\n{content[:500]}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"模块生成失败: {e}") from e

    def chat_stream(self, messages: list[dict], current_code: str = "",
                    error_info: str = ""):
        """
        流式对话（生成器）。

        用法：
            for chunk in llm.chat_stream(messages, code, error):
                yield chunk
        """
        system = self._build_context(current_code, error_info)

        api_messages = [{"role": "system", "content": system}]
        api_messages.extend(messages[-80:])

        try:
            stream = self.client.chat.completions.create(
                model=self.config.model,
                messages=api_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n\n❌ **错误**: {e}"
