"""
Reference Builder — ghi quan hệ [:REFERS_TO] (Component → Component) vào Neo4j.

Tách riêng khỏi reference_extractor.py: bên kia thuần xử lý văn bản (không cần
database), bên này chỉ lo ghi đồ thị.

Nguyên tắc (CLAUDE.md §3): dùng MERGE, chạy 2 lần cho kết quả giống nhau.
Cạnh CHỈ được tạo khi CẢ HAI đầu Component đã tồn tại — không tự tạo node mới,
vì một dẫn chiếu trỏ tới điều khoản chưa thu thập thì không có gì để nối.

Thuộc tính cạnh giữ lại để truy vết:
    loai  — noi_bo | lien_van_ban
    raw   — nguyên văn cụm dẫn chiếu, VD "khoản 2 Điều 143"

Chạy (mặc định trỏ vào BẢN SAO thử nghiệm, KHÔNG đụng CSDL demo):
    python -m src.ingestion.reference_builder --uri bolt://localhost:7688
    python -m src.ingestion.reference_builder --uri bolt://localhost:7688 --xoa
"""
from __future__ import annotations

import argparse
import glob
import logging
import os
import re
from collections import defaultdict

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

from src.ingestion.reference_extractor import (
    _SKIP_FILES,
    Reference,
    build_name_lexicon,
    build_norm_index,
    extract_from_file,
    nguon_component_id,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Cổng 7688 = bản sao thử nghiệm. CSDL demo ở 7687 — mặc định KHÔNG đụng tới.
_URI_MAC_DINH = "bolt://localhost:7688"

_MERGE_EDGE = """
MATCH (a:Component {id: $nguon})
MATCH (b:Component {id: $dich})
MERGE (a)-[r:REFERS_TO]->(b)
SET r.loai = $loai, r.raw = $raw, r.muc = $muc
RETURN 1 AS ok
"""


def thu_thap_dan_chieu(raw_dir: str) -> list[Reference]:
    """Trích toàn bộ dẫn chiếu đã giải chiếu được từ data/raw/."""
    indexes, so_hieu_map = build_norm_index(raw_dir)
    lexicon = build_name_lexicon(indexes)
    refs: list[Reference] = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "*.md"))):
        if os.path.basename(path) in _SKIP_FILES:
            continue
        refs.extend(extract_from_file(path, indexes, so_hieu_map, lexicon))
    return [r for r in refs if r.dich_path]


_DIEU = re.compile(r"^Điều\s+(\d+)\b")
_KHOAN = re.compile(r"^Khoản\s+(\d+)\b")
_DIEM = re.compile(r"^Điểm\s+([a-zđ]+)\b")


def nap_chi_muc_do_thi(driver: Driver) -> tuple[dict, dict, set]:
    """Đọc Component CÓ THẬT trong đồ thị → chỉ mục địa chỉ.

    Cần thiết vì parser chỉ sinh Component cho heading có nội dung chữ trực
    tiếp: một "Điều 5" chỉ chứa các Khoản con thì KHÔNG có node cấp Điều. Giải
    chiếu theo file .md sẽ trỏ vào ID không tồn tại.

    Trả về (chinh_xac, theo_dieu, tat_ca_id):
        chinh_xac[(norm, dieu, khoan, diem)] = component_id
        theo_dieu[(norm, dieu)]              = [component_id, ...]
    """
    chinh_xac: dict[tuple, str] = {}
    theo_dieu: dict[tuple, list[str]] = defaultdict(list)
    tat_ca: set[str] = set()

    with driver.session() as session:
        rows = session.run(
            "MATCH (n:Norm)-[:HAS_COMPONENT]->(c:Component) "
            "RETURN n.id AS norm, c.id AS cid, c.label AS label"
        )
        for row in rows:
            norm, cid, label = row["norm"], row["cid"], row["label"] or ""
            tat_ca.add(cid)
            dieu = khoan = diem = None
            for phan in label.split(" > "):
                phan = phan.strip()
                if (m := _DIEU.match(phan)):
                    dieu = m.group(1)
                elif (m := _KHOAN.match(phan)):
                    khoan = m.group(1)
                elif (m := _DIEM.match(phan)):
                    diem = m.group(1)
            if dieu is None:
                continue  # Phụ lục và các cấu trúc khác — chưa xử lý
            chinh_xac[(norm, dieu, khoan, diem)] = cid
            theo_dieu[(norm, dieu)].append(cid)

    return chinh_xac, dict(theo_dieu), tat_ca


def _tim_dich(r: Reference, chinh_xac: dict, theo_dieu: dict) -> list[str]:
    """Danh sách Component đích cho một dẫn chiếu.

    Dẫn chiếu tới cả một Điều ("Điều 143") nối tới MỌI Khoản của Điều đó —
    vì trong đồ thị, nội dung của Điều nằm ở các Khoản con.
    """
    norm, dieu = r.dich_norm, r.dich_dieu
    if not norm or not dieu:
        return []
    if r.dich_khoan:
        for key in (
            (norm, dieu, r.dich_khoan, r.dich_diem),
            (norm, dieu, r.dich_khoan, None),
        ):
            if key in chinh_xac:
                return [chinh_xac[key]]
        return []
    # Dẫn chiếu cấp Điều
    if (norm, dieu, None, None) in chinh_xac:
        return [chinh_xac[(norm, dieu, None, None)]]
    return theo_dieu.get((norm, dieu), [])


def ghi_canh(driver: Driver, refs: list[Reference]) -> dict:
    """Ghi cạnh REFERS_TO. Trả về thống kê tạo được / bỏ qua."""
    chinh_xac, theo_dieu, tat_ca = nap_chi_muc_do_thi(driver)
    logger.info(
        f"Chỉ mục đồ thị: {len(tat_ca)} Component, "
        f"{len(chinh_xac)} địa chỉ Điều/Khoản/Điểm"
    )

    cap: dict[tuple[str, str], Reference] = {}
    tu_tro = khong_co_dich = nguon_thieu = 0
    for r in refs:
        nguon = nguon_component_id(r)
        if nguon not in tat_ca:
            nguon_thieu += 1
            continue
        dichs = _tim_dich(r, chinh_xac, theo_dieu)
        if not dichs:
            khong_co_dich += 1
            continue
        # muc="khoan": dẫn chiếu chỉ đích danh một khoản/điểm → 1 đích, chính xác.
        # muc="dieu" : dẫn chiếu cả một Điều → nở ra mọi Khoản của Điều đó, kém
        #              chính xác hơn. Đánh dấu để khâu truy hồi lọc/ưu tiên được.
        muc = "khoan" if r.dich_khoan else "dieu"
        for dich in dichs:
            if nguon == dich:
                tu_tro += 1
                continue
            cap.setdefault((nguon, dich), (r, muc))

    tao = 0
    with driver.session() as session:
        for (nguon, dich), (r, muc) in cap.items():
            if session.run(
                _MERGE_EDGE, nguon=nguon, dich=dich, loai=r.loai, raw=r.raw, muc=muc
            ).single():
                tao += 1

    return {
        "cap_duy_nhat": len(cap),
        "tao": tao,
        "nguon_khong_co_node": nguon_thieu,
        "khong_tim_thay_dich": khong_co_dich,
        "tu_tro_bo_qua": tu_tro,
    }


def xoa_canh(driver: Driver) -> int:
    """Gỡ toàn bộ cạnh REFERS_TO (để chạy lại sạch hoặc hoàn tác)."""
    with driver.session() as session:
        rec = session.run(
            "MATCH ()-[r:REFERS_TO]->() DELETE r RETURN count(r) AS n"
        ).single()
        return rec["n"] if rec else 0


def thong_ke(driver: Driver) -> dict:
    """Đếm cạnh REFERS_TO hiện có + độ phủ Component."""
    with driver.session() as session:
        rec = session.run(
            """
            MATCH ()-[r:REFERS_TO]->() WITH count(r) AS canh
            MATCH (c:Component) WITH canh, count(c) AS tong_comp
            MATCH (a:Component)-[:REFERS_TO]->() WITH canh, tong_comp, count(DISTINCT a) AS co_di
            MATCH ()-[:REFERS_TO]->(b:Component)
            RETURN canh, tong_comp, co_di, count(DISTINCT b) AS co_den
            """
        ).single()
        return dict(rec) if rec else {}


def main() -> None:
    ap = argparse.ArgumentParser(description="Ghi quan hệ REFERS_TO vào Neo4j")
    ap.add_argument("--uri", default=_URI_MAC_DINH,
                    help=f"Bolt URI (mặc định {_URI_MAC_DINH} = bản sao thử nghiệm)")
    ap.add_argument("--xoa", action="store_true", help="Gỡ hết cạnh REFERS_TO rồi thoát")
    args = ap.parse_args()

    load_dotenv()
    auth = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))

    if args.uri == "bolt://localhost:7687":
        logger.warning("⚠️  Đang trỏ vào CSDL DEMO (7687), không phải bản sao thử nghiệm!")

    driver = GraphDatabase.driver(args.uri, auth=auth)
    try:
        if args.xoa:
            n = xoa_canh(driver)
            logger.info(f"Đã gỡ {n} cạnh REFERS_TO khỏi {args.uri}")
            return

        raw_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
        )
        refs = thu_thap_dan_chieu(raw_dir)
        logger.info(f"Trích được {len(refs)} dẫn chiếu đã giải chiếu")

        kq = ghi_canh(driver, refs)
        logger.info(
            f"Cặp duy nhất: {kq['cap_duy_nhat']} | tạo cạnh: {kq['tao']}"
        )
        logger.info(
            f"Bỏ qua — nguồn không có node: {kq['nguon_khong_co_node']} | "
            f"không tìm thấy đích: {kq['khong_tim_thay_dich']} | "
            f"tự trỏ: {kq['tu_tro_bo_qua']}"
        )

        st = thong_ke(driver)
        if st:
            logger.info(
                f"Đồ thị {args.uri}: {st['canh']} cạnh REFERS_TO | "
                f"{st['co_di']} Component có dẫn chiếu đi, "
                f"{st['co_den']} được dẫn tới / {st['tong_comp']} tổng"
            )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
