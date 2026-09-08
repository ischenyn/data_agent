from functools import lru_cache
from pathlib import Path

prompt_path = Path(__file__).parents[2] / "prompts"


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """读取 prompt 模板文件并缓存(避免在线问答阶段每次调用都读盘)"""
    file_path = prompt_path / f"{name}.prompt"
    return file_path.read_text(encoding="utf-8")
