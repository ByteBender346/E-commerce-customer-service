from pathlib import Path


def load_prompt(file_name: str) -> str:
    """读取 jinja2 提示词模板文件。"""
    path = Path(__file__).parent / "jinja2" / f"{file_name}.jinja2"
    return path.read_text(encoding="utf-8")
