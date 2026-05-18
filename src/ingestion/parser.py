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

# Regex bắt annotation amendment trong HTML comment:
#   <!-- amended_by: 49/2026/NĐ-CP, khoản 1 Điều 13, hiệu lực: 31/01/2026, nội dung: sửa đổi, bổ sung khoản này -->
# Group 1: số hiệu VB sửa (amending_norm — VD "49/2026/NĐ-CP")
# Group 2: vị trí trong VB sửa (amending_loc — VD "khoản 1 Điều 13")
# Group 3: ngày hiệu lực (DD/MM/YYYY — VD "31/01/2026")
# Group 4: nội dung mô tả (raw content — VD "sửa đổi, bổ sung khoản này")
_AMENDMENT_RE = re.compile(
    r"<!--\s*amended_by:\s*"
    r"([^,]+),\s*"
    r"([^,]+),\s*"
    r"hiệu lực:\s*([\d/]+),\s*"
    r"nội dung:\s*(.+?)\s*-->",
    re.DOTALL,
)

# Map keyword đầu nội dung → change_type chuẩn (longest-match-first)
_CHANGE_TYPE_KEYWORDS = (
    ("sửa đổi, bổ sung", "sua-doi-bo-sung"),
    ("thay cụm từ", "thay-cum-tu"),
    ("bổ sung", "bo-sung"),
    ("thay thế", "thay-the"),
    ("bãi bỏ", "bai-bo"),
    ("sửa đổi", "sua-doi"),
    ("thay", "thay-the"),  # fallback cho "thay \"...\" bằng \"...\""
)


def _normalize_effective_date(raw: str) -> str | None:
    """Convert DD/MM/YYYY → YYYY-MM-DD. Trả None nếu format không khớp."""
    parts = raw.strip().split("/")
    if len(parts) != 3:
        return None
    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{y:04d}-{m:02d}-{d:02d}"
    except ValueError:
        return None


def _detect_change_type(content: str) -> str:
    """Detect change_type từ đầu nội dung amendment."""
    content_lower = content.strip().lower()
    for keyword, slug in _CHANGE_TYPE_KEYWORDS:
        if content_lower.startswith(keyword):
            return slug
    return "khac"


def extract_amendments(text: str) -> list[dict]:
    """Extract toàn bộ amendment annotations từ text.

    Returns:
        List dict với keys: amending_norm, amending_loc, effective_date,
        change_type, content_summary, raw_match.
    """
    results = []
    for m in _AMENDMENT_RE.finditer(text):
        amending_norm = m.group(1).strip()
        amending_loc = m.group(2).strip()
        effective_raw = m.group(3).strip()
        content = m.group(4).strip()
        results.append({
            "amending_norm": amending_norm,
            "amending_loc": amending_loc,
            "effective_date": _normalize_effective_date(effective_raw) or effective_raw,
            "change_type": _detect_change_type(content),
            "content_summary": content,
            "raw_match": m.group(0),
        })
    return results


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
            # Extract amendments TỪ raw body trước khi process text.
            # Mỗi Component có thể có 0+ amendments (HTML comments inline).
            amendments = extract_amendments(body)
            # Prepend heading vào text để BGE-M3 thấy ngữ cảnh Điều/Khoản.
            # Bỏ qua norm_id (gốc), chỉ giữ heading từ cấp Điều xuống.
            # Đây là điều kiện để embedding của Điều 122 chứa "Điều kiện..." từ tiêu đề.
            heading_lines = [h[1] for h in stack]
            text = "\n".join(heading_lines + [body])
            node = TextUnit(
                id=generate_id(context_path),
                context_path=context_path,
                text=text,
                metadata=metadata,
            )
            # Gắn amendments vào node (TypedDict tolerate extra key tại runtime)
            if amendments:
                node["amendments"] = amendments  # type: ignore
            nodes.append(node)
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
