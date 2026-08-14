"""
Summary Ablation (việc 4) — phần tóm tắt do người viết đóng góp bao nhiêu?

Câu hỏi của giảng viên phản biện: các khâu có con người can thiệp như soạn
`summary` thì làm sao đảm bảo tính đúng đắn? Trả lời bằng ĐO ĐỘ NHẠY chứ không
bằng hứa hẹn quy trình rà soát: sinh lại toàn bộ summary bằng máy, chạy lại,
xem lệch bao nhiêu.

Hai kết cục đều có lợi:
  - Không tụt → summary người viết không phải cái nạng giấu mặt, hệ vững, VÀ
    khâu đó tự động hoá được (đáp luôn câu hỏi về tự động hoá).
  - Tụt → định lượng được chính xác con người đóng góp bao nhiêu, ghi vào phần
    hạn chế. Trung thực hơn là nói "chúng em viết cẩn thận".

PHÉP THỬ CÔNG BẰNG: máy được cho MỌI thứ tự động lấy được — tiêu đề, tầng,
phạm vi hiệu lực, ngày hiệu lực, và nhãn các Điều trong văn bản — nhưng KHÔNG
được xem summary người viết.

AN TOÀN CSDL: vector mới ghi với content_type="summary_auto", ID sinh từ
[norm_id, "summary_auto"] nên KHÁC ID của vector cũ. Thuần CỘNG THÊM, không ghi
đè gì. Vector "summary" của demo nguyên vẹn.

    python -m src.evaluation.summary_ablation --sinh      # gọi Gemini, ghi Qdrant
    python -m src.evaluation.summary_ablation --xem       # in đối chiếu
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONTENT_TYPE = "summary_auto"

_CYPHER_NORMS = """
MATCH (n:Norm)
OPTIONAL MATCH (n)-[:APPLIES_TO]->(j:Jurisdiction)
OPTIONAL MATCH (th:Theme)-[:INCLUDES]->(n)
RETURN n.id AS norm_id, n.title AS title, n.tier AS tier,
       n.valid_from AS valid_from, n.summary AS summary_nguoi,
       j.name AS jurisdiction, th.name AS theme
ORDER BY n.id
"""

# Nhãn Điều — đầu vào chính để máy hiểu văn bản nói về cái gì.
_CYPHER_LABELS = """
MATCH (n:Norm {id: $norm_id})-[:HAS_COMPONENT]->(c:Component)
RETURN DISTINCT split(c.label, ' > ')[0] AS dieu
"""

_PROMPT = """Bạn đang lập chỉ mục một văn bản quy phạm pháp luật Việt Nam để \
phục vụ định tuyến truy vấn.

Thông tin văn bản:
- Tên: {title}
- Tầng hiệu lực: {tier} (1=Luật/Nghị quyết QH, 2=Nghị định, 3=Thông tư, 4=cấp tỉnh)
- Phạm vi hiệu lực: {jurisdiction}
- Lĩnh vực: {theme}
- Ngày có hiệu lực: {valid_from}

Danh sách các Điều có trong văn bản:
{dieu_list}

Hãy viết một đoạn tóm tắt 3-5 câu để dùng làm chỉ mục tìm kiếm. Yêu cầu:
- Nêu văn bản quy định về việc gì, áp dụng cho đối tượng nào, ở phạm vi nào.
- Nêu ĐÍCH DANH số hiệu các Điều quan trọng nhất cho việc tra cứu thủ tục hành \
chính (ví dụ: điều kiện, trình tự, hồ sơ, thẩm quyền, hạn mức, nghĩa vụ tài chính).
- Chỉ dùng thông tin đã cho ở trên. TUYỆT ĐỐI không suy đoán nội dung không có \
trong danh sách Điều.
- Viết liền một đoạn văn xuôi tiếng Việt, không gạch đầu dòng, không tiêu đề.

Chỉ trả về đoạn tóm tắt, không thêm lời dẫn."""


def _lay_norms(driver) -> list[dict]:
    with driver.session() as s:
        return [dict(r) for r in s.run(_CYPHER_NORMS)]


def _lay_dieu(driver, norm_id: str, gioi_han: int = 80) -> list[str]:
    with driver.session() as s:
        rows = [r["dieu"] for r in s.run(_CYPHER_LABELS, norm_id=norm_id)]
    return [d for d in rows if d][:gioi_han]


def sinh_summary(norm: dict, dieu_list: list[str], llm) -> str:
    """Gọi LLM sinh summary. Chỉ dùng thông tin tự động lấy được."""
    prompt = _PROMPT.format(
        title=norm.get("title") or norm["norm_id"],
        tier=norm.get("tier"),
        jurisdiction=norm.get("jurisdiction") or "không rõ",
        theme=norm.get("theme") or "không rõ",
        valid_from=norm.get("valid_from") or "không rõ",
        dieu_list="\n".join(f"- {d}" for d in dieu_list) or "(không có)",
    )
    resp = llm.messages.create(
        model=os.getenv("GEMINI_MODEL_GENERATOR", "gemini-2.5-pro"),
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        b.text for b in resp.content if getattr(b, "type", "text") == "text"
    ).strip()


def ghi_qdrant(qdrant, model, norm: dict, summary: str) -> None:
    """Upsert vector summary_auto — CỘNG THÊM, không đụng vector 'summary' cũ."""
    from qdrant_client.models import PointStruct

    from src.ingestion.parser import generate_id
    from src.ingestion.vectorizer import _hex_to_qdrant_id, encode_text

    vec = encode_text(model, summary)
    pid = _hex_to_qdrant_id(generate_id([norm["norm_id"], CONTENT_TYPE]))
    qdrant.upsert(
        "legal_texts",
        points=[PointStruct(id=pid, vector=vec, payload={
            "content_type": CONTENT_TYPE,
            "norm_id": norm["norm_id"],
            "tier": norm.get("tier"),
            "theme": norm.get("theme"),
            "jurisdiction": norm.get("jurisdiction"),
            "valid_from": norm.get("valid_from"),
            "summary_auto": summary,
        })],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh summary bằng máy để đo độ nhạy")
    ap.add_argument("--sinh", action="store_true", help="Gọi LLM và ghi Qdrant")
    ap.add_argument("--xem", action="store_true", help="In đối chiếu người vs máy")
    ap.add_argument("--llm-mode", default="gemini")
    ap.add_argument("--gioi-han", type=int, default=0, help="Chỉ làm N văn bản đầu")
    args = ap.parse_args()

    load_dotenv()
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
        warn_notification_severity="OFF",
    )
    qdrant = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"),
                          port=int(os.getenv("QDRANT_PORT", "6333")))
    try:
        norms = _lay_norms(driver)
        if args.gioi_han:
            norms = norms[: args.gioi_han]

        if args.xem:
            from qdrant_client.models import (FieldCondition, Filter,
                                              MatchValue)
            pts, _ = qdrant.scroll("legal_texts", scroll_filter=Filter(must=[
                FieldCondition(key="content_type",
                               match=MatchValue(value=CONTENT_TYPE))]),
                limit=200, with_payload=True)
            may = {p.payload["norm_id"]: p.payload.get("summary_auto", "")
                   for p in pts}
            print(f"Đã sinh {len(may)}/{len(norms)} summary bằng máy\n")
            for n in norms[:4]:
                print("=" * 72)
                print(n["norm_id"])
                print("  [NGƯỜI]", (n.get("summary_nguoi") or "")[:260], "...")
                print("  [MÁY]  ", (may.get(n["norm_id"]) or "(chưa có)")[:260], "...")
            return 0

        if not args.sinh:
            print("Cần --sinh hoặc --xem", file=sys.stderr)
            return 2

        from src.ingestion.vectorizer import load_model
        from src.utils.llm_config import make_llm_client
        llm = make_llm_client(mode=args.llm_mode)
        model = load_model()

        for i, n in enumerate(norms, 1):
            dieu = _lay_dieu(driver, n["norm_id"])
            try:
                s = sinh_summary(n, dieu, llm)
            except Exception as e:
                logger.error(f"[{i}/{len(norms)}] {n['norm_id']}: LỖI {e}")
                continue
            if not s:
                logger.warning(f"[{i}/{len(norms)}] {n['norm_id']}: rỗng, bỏ qua")
                continue
            ghi_qdrant(qdrant, model, n, s)
            logger.info(f"[{i}/{len(norms)}] {n['norm_id']}: {len(dieu)} Điều "
                        f"→ {len(s)} ký tự")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
