"""
Transitional — phát hiện thay đổi quy định và tìm điều khoản chuyển tiếp (việc 3).

Bài toán: người dân hỏi "hồi trước nghe 300 m2, sao giờ còn 250? đổi hồi nào?".
Trả lời được con số mới thì dễ; trả lời được ĐỔI TỪ VĂN BẢN NÀO SANG VĂN BẢN NÀO
và việc đang dở thì theo bản nào mới là chỗ khó.

Ba việc module này làm, TẤT ĐỊNH, không cần mô hình ngôn ngữ đoán:

1. `tim_cap_thay_the` — văn bản trong tập ứng viên đã hết hiệu lực, và văn bản
   nào đang thế chỗ nó. Quy tắc: cùng lĩnh vực + cùng phạm vi hiệu lực + cùng
   tầng, còn hiệu lực, ban hành sau. KHÔNG khớp theo ngày chính xác vì thực tế
   có chồng lấn (Luật Đất đai 2024 có hiệu lực 2024-08-01 trong khi bản 2013
   còn hiệu lực một phần tới 2025-01-01).

2. `tim_dieu_khoan_chuyen_tiep` — điều khoản chuyển tiếp của văn bản MỚI. Chính
   nó trả lời "việc đang dở xử theo bản nào". Nhận diện bằng nhãn Component
   chứa "chuyển tiếp" — heuristic, có thể sót điều khoản không đặt tên như vậy.

3. `mo_ta_thay_doi` — câu mô tả CHỈ nêu điều quan sát được (quy định đã thay
   đổi trong khoảng thời gian liên quan). KHÔNG khẳng định vụ việc của người
   dùng thuộc diện hồi tố hay chuyển tiếp — hệ thống không biết tình tiết vụ
   việc, khẳng định thêm là suy diễn không có căn cứ trong văn bản truy hồi.

Lưu ý thuật ngữ: phần lớn ca ở lĩnh vực hành chính là ĐIỀU KHOẢN CHUYỂN TIẾP,
không phải HIỆU LỰC HỒI TỐ. Hồi tố ("luật nhẹ hơn áp ngược về trước") là
nguyên tắc riêng của luật hình sự (Điều 7 Bộ luật Hình sự), không áp dụng cho
đất đai / hộ tịch / nuôi con nuôi.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# CTV.valid_to dùng sentinel này khi còn hiệu lực (xem CLAUDE.md VALID_TO_SENTINEL)
_SENTINEL = "9999-12-31"

# LƯU Ý: `theme` KHÔNG phải thuộc tính của Norm — nó là node riêng nối qua
# [:INCLUDES] (xem lược đồ). Thuộc tính Norm chỉ có: id, title, tier,
# valid_from, valid_to, summary.
_CYPHER_HET_HIEU_LUC = """
MATCH (cu:Norm)
WHERE cu.id IN $norm_ids
  AND cu.valid_to IS NOT NULL AND cu.valid_to <> $sentinel
MATCH (cu)-[:APPLIES_TO]->(j:Jurisdiction)
MATCH (th:Theme)-[:INCLUDES]->(cu)
OPTIONAL MATCH (th)-[:INCLUDES]->(moi:Norm)-[:APPLIES_TO]->(j)
WHERE moi.id <> cu.id
  AND moi.tier = cu.tier
  AND (moi.valid_to IS NULL OR moi.valid_to = $sentinel)
  AND moi.valid_from >= cu.valid_from
RETURN cu.id AS cu, cu.valid_from AS cu_tu, cu.valid_to AS cu_den,
       moi.id AS moi, moi.valid_from AS moi_tu
"""


def _khoang_cach_ngay(a: str | None, b: str | None) -> int:
    """|a − b| tính theo ngày. Trả số rất lớn nếu thiếu/hỏng ngày."""
    from datetime import date
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except (TypeError, ValueError):
        return 10**9

_CYPHER_CHUYEN_TIEP = """
MATCH (n:Norm {id: $norm_id})-[:HAS_COMPONENT]->(c:Component)
WHERE toLower(c.label) CONTAINS 'chuyển tiếp'
RETURN c.id AS id, c.label AS label
ORDER BY c.label
"""


def tim_cap_thay_the(norm_ids: list[str], neo4j_driver) -> list[dict]:
    """Cặp (văn bản cũ đã hết hiệu lực → văn bản đang thế chỗ) trong tập ứng viên.

    Trả về [] khi không có văn bản nào hết hiệu lực — đây là tín hiệu để KHÔNG
    gắn cảnh báo. Quan trọng: cảnh báo chỉ được nổ khi thật sự có thay đổi, nếu
    nổ ở mọi câu thì nó thành lời rào đón vô nghĩa.
    """
    if not norm_ids or neo4j_driver is None:
        return []
    gom: dict[str, dict] = {}
    with neo4j_driver.session() as s:
        for r in s.run(_CYPHER_HET_HIEU_LUC, norm_ids=norm_ids, sentinel=_SENTINEL):
            cu = r["cu"]
            muc = gom.setdefault(cu, {
                "cu": cu, "cu_tu": r["cu_tu"], "cu_den": r["cu_den"],
                "moi": None, "moi_tu": None,
            })
            if not r["moi"]:
                continue
            # Bản kế nhiệm = ứng viên có ngày hiệu lực GẦN NHẤT với ngày văn bản
            # cũ hết hiệu lực. Chỉ "cùng lĩnh vực/tầng/phạm vi" là chưa đủ: TP.HCM
            # có nhiều quyết định tầng 4 cùng lĩnh vực đất đai nhưng khác chủ đề
            # (QĐ 52/2016 về nội dung khác hẳn QĐ 18/2016).
            #
            # HẠN CHẾ: đây là suy đoán theo thời gian, đồ thị KHÔNG có cạnh
            # "thay thế" tường minh. Cách chắc chắn hơn là khai báo trong
            # frontmatter — ghi vào phần hạn chế.
            mm = _khoang_cach_ngay(r["moi_tu"], r["cu_den"])
            if muc["moi"] is None or mm < _khoang_cach_ngay(muc["moi_tu"], r["cu_den"]):
                muc["moi"], muc["moi_tu"] = r["moi"], r["moi_tu"]
    return list(gom.values())


def tim_dieu_khoan_chuyen_tiep(norm_id: str, neo4j_driver) -> list[dict]:
    """Điều khoản chuyển tiếp của một văn bản ([{id, label}])."""
    if not norm_id or neo4j_driver is None:
        return []
    with neo4j_driver.session() as s:
        return [dict(r) for r in s.run(_CYPHER_CHUYEN_TIEP, norm_id=norm_id)]


def thu_thap_chuyen_tiep(norm_ids: list[str], neo4j_driver) -> tuple[list[dict], list[str]]:
    """Cặp văn bản bị thay thế + điều khoản chuyển tiếp liên quan.

    Điều khoản chuyển tiếp được tra trên TOÀN BỘ văn bản ứng viên, không chỉ
    bản kế nhiệm: chương chuyển tiếp của văn bản gốc thường không nằm trong kho
    (D-01 thu thập theo Chương/Mục), trong khi các nghị định hướng dẫn mới ban
    hành lại có sẵn — và chính chúng quy định việc đang dở xử ra sao.

    Ưu tiên bản kế nhiệm lên đầu vì nó sát vấn đề nhất.
    """
    cap = tim_cap_thay_the(norm_ids, neo4j_driver)
    uu_tien = [c["moi"] for c in cap if c.get("moi")]
    thu_tu = uu_tien + [n for n in norm_ids if n not in uu_tien]

    comp_ids: list[str] = []
    for norm_id in thu_tu:
        comp_ids.extend(x["id"] for x in tim_dieu_khoan_chuyen_tiep(norm_id, neo4j_driver))
    return cap, comp_ids


def mo_ta_thay_doi(cap: list[dict], co_dieu_khoan_chuyen_tiep: bool) -> str:
    """Câu mô tả thay đổi — chỉ nêu điều QUAN SÁT ĐƯỢC, không phán vụ việc.

    Cố ý KHÔNG dùng chữ "hồi tố" và KHÔNG khẳng định trường hợp người dùng
    thuộc diện nào: hệ thống chỉ biết văn bản đã đổi, không biết tình tiết.
    """
    if not cap:
        return ""
    c = cap[0]
    s = (
        f"Quy định về nội dung này đã thay đổi: {c['cu']} hết hiệu lực từ "
        f"{c['cu_den']}"
    )
    if c.get("moi"):
        s += f", được thay thế bởi {c['moi']} (hiệu lực từ {c['moi_tu']})"
    s += ". Nội dung ở từng thời điểm được nêu bên dưới."
    if co_dieu_khoan_chuyen_tiep:
        s += (
            " Việc xác định quy định nào áp dụng cho một trường hợp cụ thể phụ "
            "thuộc điều khoản chuyển tiếp (đã trích dẫn) và tình tiết vụ việc; "
            "nên tham khảo ý kiến chuyên gia pháp lý."
        )
    else:
        s += (
            " Việc xác định quy định nào áp dụng cho một trường hợp cụ thể phụ "
            "thuộc tình tiết vụ việc; nên tham khảo ý kiến chuyên gia pháp lý."
        )
    return s
