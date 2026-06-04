"""
TutorFlow (AI 编程导师) 配置管理

管理 LLM API 配置、应用路径、代码执行参数等。
支持通过环境变量覆盖默认配置。
配置自动持久化到 data/config.json，重启不丢失。
"""

import os
import json
from dataclasses import dataclass, field


@dataclass
class Config:
    """TutorFlow 应用全局配置"""

    # ── LLM API 配置 ──
    api_base: str = field(
        default_factory=lambda: os.getenv(
            "TUTORFLOW_API_BASE", "https://api.openai.com/v1"
        )
    )
    api_key: str = field(
        default_factory=lambda: os.getenv("TUTORFLOW_API_KEY", "")
    )
    model: str = field(
        default_factory=lambda: os.getenv("TUTORFLOW_MODEL", "gpt-4o")
    )
    max_tokens: int = 4096
    temperature: float = 0.7

    # ── 本地路径 ──
    _base_dir: str = field(
        default_factory=lambda: os.path.dirname(os.path.abspath(__file__))
    )

    @property
    def data_dir(self) -> str:
        return os.path.join(self._base_dir, "data")

    @property
    def saved_code_dir(self) -> str:
        return os.path.join(self._base_dir, "saved_code")

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "progress.db")

    @property
    def config_file(self) -> str:
        """API 配置持久化文件路径"""
        return os.path.join(self.data_dir, "config.json")

    @property
    def current_code_file(self) -> str:
        return os.path.join(self.saved_code_dir, "current.py")

    # ── 代码执行配置 ──
    code_timeout: int = 30  # 子进程执行超时（秒）

    def __post_init__(self):
        """确保必要的目录存在，并从本地文件恢复配置"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.saved_code_dir, exist_ok=True)
        self._load_from_file()

    def _load_from_file(self) -> None:
        """从本地 JSON 文件加载 API 配置（环境变量优先）"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 环境变量优先，文件配置作为 fallback
                if not os.getenv("TUTORFLOW_API_BASE"):
                    self.api_base = data.get("api_base", self.api_base)
                if not os.getenv("TUTORFLOW_API_KEY"):
                    self.api_key = data.get("api_key", self.api_key)
                if not os.getenv("TUTORFLOW_MODEL"):
                    self.model = data.get("model", self.model)
        except Exception:
            pass  # 文件损坏或不存在时使用默认值

    def _save_to_file(self) -> None:
        """持久化 API 配置到本地 JSON 文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "api_base": self.api_base,
                        "api_key": self.api_key,
                        "model": self.model,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass  # 写入失败不影响使用

    def update_api(
        self, api_base: str, api_key: str, model: str
    ) -> None:
        """运行时更新 API 配置，并自动持久化"""
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self._save_to_file()

    @property
    def is_configured(self) -> bool:
        """检查 API 是否已配置"""
        return bool(self.api_base and self.api_key and self.model)
