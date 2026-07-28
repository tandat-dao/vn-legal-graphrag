"""
Answer Generator — TASK-13 (phần 2)
Gửi prompt vào Claude Sonnet 4.6, parse citations từ raw output.

Citation format trong câu trả lời: [Điều X, Khoản Y, Điểm Z, Tiết K, Văn bản W]
(và biến thể Phụ lục). parse_citations() là ORDER-INDEPENDENT, extract thành
list[dict] với keys: dieu, khoan, diem, tiet, van_ban, loai ("dieu" | "phu_luc").

Optional LLM cache: nếu `cache_dir` được truyền, kết quả được lưu/đọc theo
hash(prompt) — repeat call cùng prompt sẽ trả cache hit (tiết kiệm $ API).
Cache auto-invalidate khi prompt thay đổi (vì hash khác).
"""
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TypedDict

import anthropic

from src.retrieval.context_assembler import build_messages


# ---------------------------------------------------------------------------
# Output schema (loose sections — Schema B trong v2.2)
# ---------------------------------------------------------------------------

class AnswerSections(TypedDict):
    """3 section structured trong câu trả lời LLM (theo prompt template)."""
    tra_loi: str          # Nội dung chính
    canh_bao_lex: str     # "Không có" hoặc danh sách amendments
    pham_vi: str          # "Trong phạm vi corpus" / "Ngoài phạm vi corpus — ..."


# Regex bắt 3 section headers H2. KHÔNG yêu cầu thứ tự (LLM đôi khi đảo).
_SECTION_HEADERS = {
    "tra_loi": re.compile(r"^##\s+TRẢ\s*LỜI\s*$", re.MULTILINE | re.IGNORECASE),
    "canh_bao_lex": re.compile(r"^##\s+CẢNH\s*BÁO\s*LEX\s*$", re.MULTILINE | re.IGNORECASE),
    "pham_vi": re.compile(r"^##\s+PHẠM\s*VI\s*$", re.MULTILINE | re.IGNORECASE),
}


def parse_sections(raw_answer: str) -> AnswerSections:
    """Tách câu trả lời thành 3 section theo H2 markers.

    Nếu LLM không tuân thủ format (thiếu section, sai header), trường tương ứng
    sẽ là chuỗi rỗng. Vẫn return TypedDict đầy đủ keys để downstream xử lý.

    Args:
        raw_answer: Câu trả lời thô từ LLM.

    Returns:
        AnswerSections với 3 keys; mỗi value là nội dung sau header tới header
        kế tiếp (hoặc end-of-string). Trống nếu header không tìm thấy.
    """
    # Tìm vị trí từng header
    positions = []
    for key, pattern in _SECTION_HEADERS.items():
        m = pattern.search(raw_answer)
        if m:
            positions.append((m.start(), m.end(), key))
    positions.sort()

    sections = AnswerSections(tra_loi="", canh_bao_lex="", pham_vi="")
    for i, (_, end, key) in enumerate(positions):
        next_start = positions[i + 1][0] if i + 1 < len(positions) else len(raw_answer)
        sections[key] = raw_answer[end:next_start].strip()
    return sections

logger = logging.getLogger(__name__)

import os

MODEL = "claude-sonnet-4-6"
MAX_ANSWER_TOKENS = 3000
# TEMPERATURE: 0.0 = greedy deterministic; 1.0 = default Anthropic sampling.
# Toggle qua env var LLM_TEMPERATURE để A/B test reproducibility vs F1.
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))


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

# Citation parsing — ORDER-INDEPENDENT (commit 2-mode):
# Trước đây dùng 1 regex cố định thứ tự [Điều→Khoản→Điểm→Tiết→Văn bản]. IRAC mode
# khiến LLM đảo thứ tự (VD "[Điểm đ, Khoản 2, Phụ lục, Văn bản ...]") → regex fail
# → trả [] dù answer đúng (Q007: F1 0.50→0.00 giả). Fix: bắt mọi block [...] có
# "Văn bản", split theo dấu phẩy, phân loại từng phần theo prefix — KHÔNG phụ thuộc
# thứ tự. Tương đương parse_sections() đã robust với thứ tự section (Schema B).
#
# Các định dạng hỗ trợ (mọi hoán vị thứ tự thành phần đều hợp lệ):
#   [Điều X, Văn bản Z]                         [Phụ lục X, Văn bản Z]
#   [Điều X, Khoản Y, Văn bản Z]                [Phụ lục, Khoản Y, Văn bản Z]
#   [Điều X, Khoản Y, Điểm Z, Tiết K, Văn bản W]
#   [Điểm Z, Khoản Y, Điều X, Văn bản W]        ← đảo thứ tự vẫn parse được
_CITATION_BLOCK_RE = re.compile(r"\[([^\[\]]+)\]")
# Mỗi phần (sau split dấu phẩy): "Điều 121" / "Phụ lục II" / "Khoản 2" / "Văn bản ..."
_CITATION_PART_RE = re.compile(
    r"^(Điều|Phụ\s*lục|Khoản|Điểm|Tiết|Văn\s*bản)\s*(.*)$",
    re.IGNORECASE,
)


def parse_citations(raw_answer: str) -> list[dict]:
    """Extract citations từ câu trả lời LLM (order-independent).

    Bắt mọi block `[...]` chứa "Văn bản", tách theo dấu phẩy, phân loại từng phần
    theo prefix (Điều/Phụ lục/Khoản/Điểm/Tiết/Văn bản) bất kể thứ tự xuất hiện.

    Hỗ trợ mọi hoán vị, VD:
        [Điều X, Khoản Y, Điểm Z, Văn bản W]
        [Điểm Z, Khoản Y, Phụ lục, Văn bản W]   ← thứ tự đảo vẫn hợp lệ

    Returns:
        List dict với keys: dieu, khoan, diem (optional), tiet (optional),
        van_ban, loai. `loai` = "dieu" | "phu_luc"; `dieu` chứa số/ký hiệu
        của Điều hoặc Phụ lục để backward compat.
    """
    citations = []
    # Dedupe: LLM đôi khi cite cùng 1 vị trí 2+ lần trong cùng answer (đã quan sát ở
    # Q025 canonical run 20260519: cite "Điều 116, Khoản 5, Văn bản luat-dat-dai-2024"
    # 2 lần liên tiếp). Trùng lặp hạ precision oan trong metric F1. Giữ duy nhất bản
    # đầu tiên — đây là idempotent fix, không thay đổi semantics câu trả lời.
    seen: set[tuple] = set()
    for block in _CITATION_BLOCK_RE.finditer(raw_answer):
        content = block.group(1)
        loai: str | None = None
        number: str | None = None
        khoan = diem = tiet = van_ban = None

        for part in content.split(","):
            pm = _CITATION_PART_RE.match(part.strip())
            if not pm:
                continue
            kind = pm.group(1).lower().replace(" ", "")  # "phụ lục"→"phụlục", "văn bản"→"vănbản"
            val = pm.group(2).strip()
            if kind == "điều":
                loai = "dieu"
                number = val or None
            elif kind == "phụlục":
                loai = "phu_luc"
                number = val if val else "_default"
            elif kind == "khoản":
                khoan = val or None
            elif kind == "điểm":
                diem = val or None
            elif kind == "tiết":
                tiet = val or None
            elif kind == "vănbản":
                van_ban = val or None

        # Validation: phải có Văn bản + loại (Điều/Phụ lục); Điều bắt buộc có số.
        if van_ban is None or loai is None:
            continue
        if loai == "dieu" and not number:
            continue

        key = (loai, number, khoan, diem, tiet, van_ban)
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "dieu": number,
            "khoan": khoan,
            "diem": diem,
            "tiet": tiet,
            "van_ban": van_ban,
            "loai": loai,
        })
    return citations


def generate_answer(
    question: str,
    context: str,
    llm_client: anthropic.Anthropic,
    cache_dir: Path | None = None,
    mode: str = "general",
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

    system_prompt, user_prompt = build_messages(question, context, mode)
    # Cache key hash trên cả system + user; system đã khác nhau theo mode → cache
    # tự phân biệt general vs irac, không cần thêm mode vào key.
    cache_key = _prompt_hash(system_prompt + "\n\n" + user_prompt, MODEL)
    cached = _cache_get(cache_dir, cache_key)
    if cached is not None:
        logger.info(f"generate_answer: cache HIT ({cache_key}) — $0 API")
        # Re-parse citations + sections với parser hiện tại (parser có thể đã sửa từ lúc cache)
        citations = parse_citations(cached["answer"])
        sections = parse_sections(cached["answer"])
        return {
            "answer": cached["answer"],
            "citations": citations,
            "sections": sections,
            "context_used": bool(context.strip()),
            "cache_hit": True,
        }

    # Anthropic prompt caching: đánh dấu system_prompt ephemeral → cache hit giảm 90%
    # input cost. TTL ~5 phút, đủ cho 1 batch eval. User message KHÔNG cache (thay đổi
    # mỗi câu hỏi). Yêu cầu: system_prompt phải có >=1024 tokens để cache có hiệu lực.
    message = llm_client.messages.create(
        model=MODEL,
        max_tokens=MAX_ANSWER_TOKENS,
        temperature=TEMPERATURE,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_answer = message.content[0].text.strip()
    citations = parse_citations(raw_answer)
    sections = parse_sections(raw_answer)

    logger.info(
        f"generate_answer: {len(raw_answer)} chars, {len(citations)} citations, "
        f"sections={ {k: bool(v) for k, v in sections.items()} }"
    )

    _cache_put(cache_dir, cache_key, {"answer": raw_answer})

    return {
        "answer": raw_answer,
        "citations": citations,
        "sections": sections,
        "context_used": bool(context.strip()),
        "cache_hit": False,
    }
