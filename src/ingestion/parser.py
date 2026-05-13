import hashlib
import re
from typing import TypedDict

import yaml


class TextUnit(TypedDict):
    id: str
    context_path: list[str]
    text: str
    metadata: dict


_LEVEL2_PREFIXES = ("Điều ", "Phụ lục")
_LEVEL3_PREFIXES = ("Khoản ",)
_LEVEL4_PREFIXES = ("Điểm ",)
_LEVEL5_PREFIXES = ("Tiết ",)

_HEADING_RE = re.compile(r"^(#{1,6}) (.+)$")


def generate_id(context_path: list[str]) -> str:
    raw = ">".join(context_path)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _parse_heading(line: str) -> tuple[int, str] | None:
    """Trả về (level, text) nếu là heading, ngược lại None."""
    m = _HEADING_RE.match(line)
    return (len(m.group(1)), m.group(2).strip()) if m else None


def _validate_heading(level: int, text: str, lineno: int, raw_line: str) -> None:
    if level == 1:
        raise ValueError(
            f"Dòng {lineno}: heading cấp 1 không hợp lệ: '{raw_line}'. "
            "Dùng '## Điều N.' thay vì '# Điều N.'."
        )
    if level == 2 and not any(text.startswith(p) for p in _LEVEL2_PREFIXES):
        raise ValueError(
            f"Dòng {lineno}: heading '##' không hợp lệ: '{raw_line}'. "
            "Cấp ## chỉ dùng cho 'Điều N.' hoặc 'Phụ lục ...'."
        )
    if level == 3 and not any(text.startswith(p) for p in _LEVEL3_PREFIXES):
        raise ValueError(
            f"Dòng {lineno}: heading '###' không hợp lệ: '{raw_line}'. "
            "Cấp ### chỉ dùng cho 'Khoản N.'."
        )
    if level == 4 and not any(text.startswith(p) for p in _LEVEL4_PREFIXES):
        raise ValueError(
            f"Dòng {lineno}: heading '####' không hợp lệ: '{raw_line}'. "
            "Cấp #### chỉ dùng cho 'Điểm a.'."
        )
    if level == 5 and not any(text.startswith(p) for p in _LEVEL5_PREFIXES):
        raise ValueError(
            f"Dòng {lineno}: heading '#####' không hợp lệ: '{raw_line}'. "
            "Cấp ##### chỉ dùng cho 'Tiết N.'."
        )
    if level > 5:
        raise ValueError(
            f"Dòng {lineno}: heading cấp {level} không hợp lệ: '{raw_line}'."
        )


def parse_file(filepath: str) -> dict:
    """Đọc một file .md chuẩn hóa Phase 1, trả về dict với keys 'metadata' và 'nodes'.

    Raises:
        ValueError: khi frontmatter thiếu hoặc có heading sai format.
        FileNotFoundError: khi file không tồn tại.
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError(
            f"{filepath}: không tìm thấy YAML frontmatter hợp lệ "
            "(file phải bắt đầu bằng '---')."
        )

    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        raise ValueError(f"{filepath}: YAML frontmatter không hợp lệ.")

    norm_id = metadata.get("id")
    if not norm_id:
        raise ValueError(f"{filepath}: frontmatter thiếu field 'id'.")

    body = parts[2]
    nodes: list[TextUnit] = []
    stack: list[tuple[int, str]] = []  # (level, heading_text)
    text_buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal text_buffer
        if not text_buffer:
            return
        context_path = [norm_id] + [h[1] for h in stack]
        body = "\n".join(text_buffer).strip()
        if body:
            # Prepend heading vào text để BGE-M3 thấy ngữ cảnh Điều/Khoản.
            # Bỏ qua norm_id (gốc), chỉ giữ heading từ cấp Điều xuống.
            # Đây là điều kiện để embedding của Điều 122 chứa "Điều kiện..." từ tiêu đề.
            heading_lines = [h[1] for h in stack]
            text = "\n".join(heading_lines + [body])
            nodes.append(
                TextUnit(
                    id=generate_id(context_path),
                    context_path=context_path,
                    text=text,
                    metadata=metadata,
                )
            )
        text_buffer = []

    for lineno, raw in enumerate(body.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        parsed = _parse_heading(line)
        if parsed is not None:
            level, text = parsed
            _validate_heading(level, text, lineno, line)
            flush_buffer()

            # Stack LIFO: pop mọi heading cùng cấp hoặc thấp hơn trong phân cấp
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, text))
        else:
            if not stack:
                raise ValueError(
                    f"{filepath} dòng {lineno}: nội dung không có heading cha: "
                    f"'{line[:60]}'"
                )
            text_buffer.append(line)

    flush_buffer()

    return {"metadata": metadata, "nodes": nodes}
