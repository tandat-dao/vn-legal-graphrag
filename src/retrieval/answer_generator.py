"""
Answer Generator — TASK-13 (phần 2)
Gửi prompt vào Claude Sonnet 4.6, parse citations từ raw output.

Citation format trong câu trả lời: [Điều X, Khoản Y, Văn bản Z]
parse_citations() extract thành list[dict] với keys: dieu, khoan, van_ban.

Optional LLM cache: nếu `cache_dir` được truyền, kết quả được lưu/đọc theo
hash(prompt) — repeat call cùng prompt sẽ trả cache hit (tiết kiệm $ API).
Cache auto-invalidate khi prompt thay đổi (vì hash khác).
"""
import hashlib
import json
import logging
import re
from pathlib import Path

import anthropic

from src.retrieval.context_assembler import build_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_ANSWER_TOKENS = 3000


# ---------------------------------------------------------------------------
# Local LLM cache (tiết kiệm $ API khi rerun eval với cùng prompt)
# ---------------------------------------------------------------------------

def _prompt_hash(prompt: str, model: str) -> str:
    return hashlib.sha256(f"{model}|{prompt}".encode()).hexdigest()[:16]


def _cache_get(cache_dir: Path | None, key: str) -> dict | None:
    if cache_dir is None:
        return None
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_put(cache_dir: Path | None, key: str, data: dict) -> None:
    if cache_dir is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )

# Regex bắt citation đa dạng định dạng:
#   [Điều X, Văn bản Z]
#   [Điều X, Khoản Y, Văn bản Z]
#   [Điều X, Khoản Y, Điểm Z, Văn bản W]
#   [Điều X, Khoản Y, Điểm Z, Tiết K, Văn bản W]
#   [Phụ lục X, Văn bản Z]
#   [Phụ lục X, Khoản Y, Văn bản Z]
#   [Phụ lục, Khoản Y, Văn bản Z]  (Phụ lục KHÔNG có số — văn bản chỉ 1 Phụ lục duy nhất)
# Group 1: loại đầu (Điều | Phụ lục), Group 2: số/ký hiệu (optional cho Phụ lục)
# Group 3: Khoản (optional), Group 4: Điểm (optional), Group 5: Tiết (optional)
# Group 6: Văn bản id
_CITATION_RE = re.compile(
    r"\[(Điều|Phụ lục)"
    r"(?:\s+([^,\]]+))?"  # số/ký hiệu optional (cần thiết cho Phụ lục duy nhất, VD NQ 02/2023)
    r"(?:,\s*Khoản\s+([^,\]]+))?"
    r"(?:,\s*Điểm\s+([^,\]]+))?"
    r"(?:,\s*Tiết\s+([^,\]]+))?"
    r",\s*Văn bản\s+([^\]]+)\]",
    re.IGNORECASE,
)


def parse_citations(raw_answer: str) -> list[dict]:
    """Extract citations từ câu trả lời LLM.

    Hỗ trợ các định dạng:
        [Điều X, Văn bản Z]
        [Điều X, Khoản Y, Văn bản Z]
        [Điều X, Khoản Y, Điểm Z, Văn bản W]
        [Điều X, Khoản Y, Điểm Z, Tiết K, Văn bản W]
        [Phụ lục X, Văn bản Z]
        [Phụ lục X, Khoản Y, Văn bản Z]

    Returns:
        List dict với keys: dieu, khoan, diem (optional), tiet (optional),
        van_ban, loai. `loai` = "dieu" | "phu_luc"; `dieu` chứa số/ký hiệu
        của Điều hoặc Phụ lục để backward compat.
    """
    citations = []
    for match in _CITATION_RE.finditer(raw_answer):
        loai_raw = match.group(1).strip().lower()
        loai = "phu_luc" if loai_raw.startswith("phụ") else "dieu"
        # Group 2 (số/ký hiệu) optional cho Phụ lục duy nhất; Điều bắt buộc có
        raw_number = match.group(2)
        if raw_number is None:
            if loai == "dieu":
                continue  # "Điều" không có số là format không hợp lệ
            number = "_default"  # Phụ lục duy nhất → sentinel
        else:
            number = raw_number.strip()
        khoan = match.group(3).strip() if match.group(3) else None
        diem = match.group(4).strip() if match.group(4) else None
        tiet = match.group(5).strip() if match.group(5) else None
        van_ban = match.group(6).strip()
        c = {
            "dieu": number,
            "khoan": khoan,
            "diem": diem,
            "tiet": tiet,
            "van_ban": van_ban,
            "loai": loai,
        }
        citations.append(c)
    return citations


def generate_answer(
    question: str,
    context: str,
    llm_client: anthropic.Anthropic,
    cache_dir: Path | None = None,
) -> dict:
    """Gửi prompt vào Claude Sonnet 4.6, trả về answer + citations.

    Args:
        question: Câu hỏi tiếng Việt của người dùng.
        context: Context string từ assemble_context().
        llm_client: Anthropic client đã khởi tạo.
        cache_dir: Nếu set, lưu/đọc answer theo hash(prompt). Repeat call cùng
                   prompt → cache hit, không gọi API ($0 cost). Dùng cho eval/dev.

    Returns:
        Dict với keys:
          - answer (str): Câu trả lời tiếng Việt với citations inline.
          - citations (list[dict]): Danh sách citations đã parse.
          - context_used (bool): True nếu context không rỗng.
          - cache_hit (bool): True nếu kết quả từ cache (tiết kiệm API).
    """
    if not context.strip():
        logger.warning("generate_answer: context rỗng — LLM sẽ trả lời không có nguồn")

    prompt = build_prompt(question, context)
    cache_key = _prompt_hash(prompt, MODEL)
    cached = _cache_get(cache_dir, cache_key)
    if cached is not None:
        logger.info(f"generate_answer: cache HIT ({cache_key}) — $0 API")
        # Re-parse citations với parser hiện tại (parser có thể đã sửa từ lúc cache)
        citations = parse_citations(cached["answer"])
        return {
            "answer": cached["answer"],
            "citations": citations,
            "context_used": bool(context.strip()),
            "cache_hit": True,
        }

    message = llm_client.messages.create(
        model=MODEL,
        max_tokens=MAX_ANSWER_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_answer = message.content[0].text.strip()
    citations = parse_citations(raw_answer)

    logger.info(
        f"generate_answer: {len(raw_answer)} chars, {len(citations)} citations"
    )

    _cache_put(cache_dir, cache_key, {"answer": raw_answer})

    return {
        "answer": raw_answer,
        "citations": citations,
        "context_used": bool(context.strip()),
        "cache_hit": False,
    }
