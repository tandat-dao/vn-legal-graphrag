"""Xóa cờ `ontology_mapped` của các Component bị đánh dấu OAN ở Pass 4.

    python scripts/reset_ontology_flags.py --dry-run   # chỉ đếm, không ghi
    python scripts/reset_ontology_flags.py             # thực thi

Bối cảnh: `ontology_mapper.map_component_to_concepts` từng nuốt mọi exception và
trả `[]`. Khi Gemini trả 429 (free tier 5 request/phút), Pass 4 vẫn chạy tiếp và
`SET c.ontology_mapped = true` cho từng Component dù KHÔNG map được concept nào.
Vì `graph_builder` Pass 4 dùng chính cờ đó để bỏ qua Component đã xử lý
(idempotency), những Component này sẽ bị bỏ qua VĨNH VIỄN ở các lần chạy sau —
lỗ hổng câm trong đồ thị.

⚠️ CÔNG CỤ KHẮC PHỤC MỘT LẦN, KHÔNG PHẢI DỌN DẸP ĐỊNH KỲ. Sau khi
`ontology_mapper` đã raise thay vì nuốt lỗi, "có cờ + 0 cạnh" KHÔNG còn nghĩa là
bị đánh dấu oan — nó là kết quả HỢP LỆ khi LLM trả `[]` (quy tắc 4 của prompt:
nội dung không thuộc khái niệm nào). Chạy script trong trạng thái lành mạnh sẽ
map lại vô ích, tốn tiền, và những Component vốn không có concept nào sẽ bị map
lặp lại mãi. Chỉ dùng khi BIẾT CHẮC một mẻ Pass 4 đã chạy với phiên bản nuốt lỗi.

Script này chỉ nhắm vào Component thỏa CẢ HAI điều kiện:
  • `ontology_mapped = true`
  • KHÔNG có cạnh `[:MAPS_TO_CONCEPT]` nào

Component đã map thành công (có cạnh) được GIỮ NGUYÊN — chúng đến từ response
Gemini thật, không cần map lại. Lệnh xóa cạnh bên dưới do đó là chốt an toàn
(no-op với dữ liệu hiện tại), phòng trường hợp state khác dự kiến.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

for _luong in (sys.stdout, sys.stderr):
    if getattr(_luong, "encoding", "").lower() != "utf-8":
        try:
            _luong.reconfigure(encoding="utf-8")
        except Exception:                           # noqa: BLE001 — không chặn script
            pass

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from dotenv import load_dotenv                      # noqa: E402
from neo4j import GraphDatabase                     # noqa: E402

load_dotenv(GOC / ".env")

# Component bị đánh dấu oan: có cờ nhưng không có cạnh concept nào.
_DIEU_KIEN_OAN = """
    MATCH (c:Component)
    WHERE c.ontology_mapped = true
      AND NOT EXISTS { MATCH (c)-[:MAPS_TO_CONCEPT]->() }
"""

_DEM_OAN = _DIEU_KIEN_OAN + " RETURN count(c) AS so"

# REMOVE (không SET null) để lần chạy sau `c.ontology_mapped = true` là false,
# đồng thời truy vấn `EXISTS(c.ontology_mapped)` cũng phản ánh đúng.
_XOA_CO = _DIEU_KIEN_OAN + """
    WITH c
    OPTIONAL MATCH (c)-[r:MAPS_TO_CONCEPT]->()
    DELETE r
    REMOVE c.ontology_mapped
    RETURN count(DISTINCT c) AS so_component, count(r) AS so_canh
"""

_THONG_KE = {
    "Component": "MATCH (c:Component) RETURN count(c) AS so",
    "Component có cờ ontology_mapped": "MATCH (c:Component) WHERE c.ontology_mapped = true RETURN count(c) AS so",
    "Cạnh MAPS_TO_CONCEPT": "MATCH ()-[r:MAPS_TO_CONCEPT]->() RETURN count(r) AS so",
    "Component bị đánh dấu OAN": _DEM_OAN,
}


def _in_thong_ke(session, tieu_de: str) -> None:
    print(f"\n── {tieu_de} ──")
    for nhan, cypher in _THONG_KE.items():
        print(f"  {nhan:34} = {session.run(cypher).single()['so']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="chỉ in số lượng, không ghi vào Neo4j")
    args = parser.parse_args()

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not all((uri, user, password)):
        print("LỖI: thiếu NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD trong .env")
        return 1

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
    except Exception as err:                        # noqa: BLE001 — báo rõ rồi thoát
        print(f"LỖI: không kết nối được Neo4j ({uri}): {err}")
        driver.close()
        return 1

    try:
        with driver.session() as session:
            _in_thong_ke(session, "TRƯỚC khi xóa")

            so_oan = session.run(_DEM_OAN).single()["so"]
            if so_oan == 0:
                print("\nKhông có Component nào bị đánh dấu oan — không cần làm gì.")
                return 0

            if args.dry_run:
                print(f"\n[dry-run] Sẽ xóa cờ của {so_oan} Component. Không ghi gì.")
                return 0

            ket_qua = session.execute_write(
                lambda tx: tx.run(_XOA_CO).single()
            )
            print(f"\nĐã xóa cờ `ontology_mapped` của {ket_qua['so_component']} Component"
                  f" và {ket_qua['so_canh']} cạnh [:MAPS_TO_CONCEPT] kèm theo.")

            _in_thong_ke(session, "SAU khi xóa")
            print("\nLần chạy `graph_builder` tiếp theo sẽ map lại các Component này.")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
