"""Kiểm tra máy trình diễn trước buổi bảo vệ — CHẠY Ở MÁY B.

    python scripts/preflight.py            # kiểm đầy đủ
    python scripts/preflight.py --nhanh    # bỏ qua mục chậm (nạp thử BGE-M3)

In báo cáo từng mục kèm CÁCH SỬA khi hỏng. Thoát code 1 nếu có mục **BẮT BUỘC**
hỏng (không chạy `live` được), 0 nếu chỉ có cảnh báo.

Không sửa gì, không ghi gì vào database — chỉ đọc. Chi tiết quy trình dựng máy B:
`ui/docs/LIVE_GUIDE.md`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Emoji + tiếng Việt trên console Windows (cp1252 sẽ ném UnicodeEncodeError).
for _luong in (sys.stdout, sys.stderr):
    if getattr(_luong, "encoding", "").lower() != "utf-8":
        try:
            _luong.reconfigure(encoding="utf-8")
        except Exception:                           # noqa: BLE001 — không chặn preflight
            pass

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from dotenv import load_dotenv                      # noqa: E402

load_dotenv(GOC / ".env")

# Số liệu tham chiếu của corpus hiện tại (docs/PROJECT_STATUS.md): 32 Norm đa-domain.
SO_NORM_MONG_DOI = 32

DAT = "✅"
CANH_BAO = "⚠️ "
HONG = "❌"


class KetQua:
    """Gom kết quả từng mục để in bảng tổng kết và quyết định exit code."""

    def __init__(self) -> None:
        self.muc: list[tuple[str, str, str, str]] = []   # (trạng thái, tên, chi tiết, cách sửa)

    def them(self, trang_thai: str, ten: str, chi_tiet: str, cach_sua: str = "") -> None:
        self.muc.append((trang_thai, ten, chi_tiet, cach_sua))
        print(f"{trang_thai} {ten}: {chi_tiet}")
        if cach_sua:
            print(f"     → {cach_sua}")

    def dat(self, ten, chi_tiet):            self.them(DAT, ten, chi_tiet)
    def canh_bao(self, ten, ct, sua=""):     self.them(CANH_BAO, ten, ct, sua)
    def hong(self, ten, ct, sua=""):         self.them(HONG, ten, ct, sua)

    @property
    def so_hong(self) -> int:
        return sum(1 for m in self.muc if m[0] == HONG)

    @property
    def so_canh_bao(self) -> int:
        return sum(1 for m in self.muc if m[0] == CANH_BAO)


def tieu_de(text: str) -> None:
    print(f"\n{'─' * 68}\n{text}\n{'─' * 68}")


# ---------------------------------------------------------------------------
# 1. Docker
# ---------------------------------------------------------------------------

def kiem_docker(kq: KetQua) -> None:
    tieu_de("1. Docker và container")

    if shutil.which("docker") is None:
        kq.hong("Docker CLI", "không tìm thấy lệnh `docker` trong PATH",
                "Cài Docker Desktop rồi mở nó lên; hoặc chạy Neo4j/Qdrant "
                "bằng cách khác và bỏ qua mục này.")
        return

    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                           capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        kq.hong("Docker daemon", "`docker ps` treo quá 25s",
                "Docker Desktop đang khởi động hoặc bị treo — mở lại rồi đợi "
                "icon chuyển sang trạng thái chạy.")
        return
    except OSError as e:
        kq.hong("Docker daemon", f"không chạy được `docker ps`: {e}",
                "Mở Docker Desktop.")
        return

    if r.returncode != 0:
        loi = (r.stderr or "").strip().splitlines()
        kq.hong("Docker daemon", f"`docker ps` lỗi: {loi[0][:110] if loi else r.returncode}",
                "Mở Docker Desktop và đợi nó khởi động xong (icon phải hết quay).")
        return

    dang_chay = {}
    for dong in r.stdout.strip().splitlines():
        if "\t" in dong:
            ten, trang_thai = dong.split("\t", 1)
            dang_chay[ten.strip()] = trang_thai.strip()
    kq.dat("Docker daemon", f"đang chạy, {len(dang_chay)} container")

    # Tên container lấy từ docker-compose.yml của repo.
    for ten in ("graphrag-neo4j", "graphrag-qdrant"):
        if ten in dang_chay:
            kq.dat(f"Container {ten}", dang_chay[ten])
        else:
            kq.canh_bao(
                f"Container {ten}", "không thấy trong `docker ps`",
                "Chạy `docker compose up -d` ở thư mục gốc repo. "
                "(Nếu bạn chạy DB ngoài Docker thì bỏ qua — mục kết nối bên dưới "
                "mới là mục quyết định.)")


# ---------------------------------------------------------------------------
# 2. .env
# ---------------------------------------------------------------------------

# (tên khóa, bắt buộc?, mô tả) — đối chiếu `os.getenv` thật trong src/ và ui/.
KHOA_ENV = [
    ("NEO4J_URI",       True,  "địa chỉ bolt của Neo4j"),
    ("NEO4J_USER",      True,  "user Neo4j"),
    ("NEO4J_PASSWORD",  True,  "mật khẩu Neo4j"),
    ("QDRANT_HOST",     False, "mặc định localhost nếu thiếu"),
    ("QDRANT_PORT",     False, "mặc định 6333 nếu thiếu"),
    ("DEMO_MODE",       False, "mode lúc khởi động UI: live | replay"),
]


def kiem_env(kq: KetQua) -> str:
    """Kiểm .env; trả về `llm_mode` sẽ dùng để kiểm phần LLM cho khớp."""
    tieu_de("2. Tệp .env")

    if not (GOC / ".env").is_file():
        kq.hong(".env", f"không có tệp {GOC / '.env'}",
                "Chép `.env.example` thành `.env` rồi điền mật khẩu Neo4j và "
                "khóa LLM.")
    else:
        kq.dat(".env", "có tệp")

    for ten, bat_buoc, mo_ta in KHOA_ENV:
        gia_tri = os.getenv(ten)
        if gia_tri:
            hien = "***" if "PASSWORD" in ten or "KEY" in ten else gia_tri
            kq.dat(f"  {ten}", hien)
        elif bat_buoc:
            kq.hong(f"  {ten}", f"THIẾU — {mo_ta}",
                    f"Thêm dòng `{ten}=...` vào .env (xem .env.example).")
        else:
            kq.canh_bao(f"  {ten}", f"chưa đặt — {mo_ta}", "")

    # LLM: chỉ bắt buộc đúng bộ khóa mà mode đang chọn cần tới.
    llm_mode = (os.getenv("LLM_MODE") or "claude").strip().lower()
    kq.dat("  LLM_MODE", f"{llm_mode} (cờ --llm-mode lúc chạy sẽ đè giá trị này)")

    can_claude = llm_mode in {"claude", "claude-fallback", "gemini-fallback"}
    can_gemini = llm_mode in {"gemini", "gemini-fallback", "claude-fallback"}

    co_claude = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY"))
    if co_claude:
        kq.dat("  ANTHROPIC_API_KEY", "***")
    elif can_claude:
        kq.hong("  ANTHROPIC_API_KEY", f"THIẾU mà mode {llm_mode} cần Claude",
                "Thêm ANTHROPIC_API_KEY=... vào .env. Lưu ý faithfulness judge "
                "LUÔN dùng Claude Haiku, không phụ thuộc LLM_MODE.")

    vertex = (os.getenv("GEMINI_USE_VERTEX") or "false").lower() == "true"
    co_gemini = bool(os.getenv("GEMINI_API_KEY")) or vertex
    if co_gemini:
        kq.dat("  Gemini", "Vertex ADC" if vertex else "GEMINI_API_KEY")
        if vertex and not os.getenv("GEMINI_VERTEX_PROJECT"):
            kq.canh_bao("  GEMINI_VERTEX_PROJECT", "chưa đặt mà GEMINI_USE_VERTEX=true",
                        "Thêm GEMINI_VERTEX_PROJECT=<id project GCP> vào .env.")
    elif can_gemini:
        kq.canh_bao("  Gemini", f"chưa cấu hình; mode {llm_mode} sẽ tự lùi về Claude thuần",
                    "Muốn dùng Gemini: đặt GEMINI_API_KEY, hoặc "
                    "GEMINI_USE_VERTEX=true + `gcloud auth application-default login`.")

    return llm_mode


# ---------------------------------------------------------------------------
# 3. Neo4j
# ---------------------------------------------------------------------------

def kiem_neo4j(kq: KetQua) -> None:
    tieu_de("3. Neo4j — kết nối và dữ liệu")

    uri, user, mk = (os.getenv("NEO4J_URI"), os.getenv("NEO4J_USER"),
                     os.getenv("NEO4J_PASSWORD"))
    if not all([uri, user, mk]):
        kq.hong("Neo4j", "thiếu biến môi trường nên không thử kết nối được",
                "Điền NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD vào .env (mục 2).")
        return

    try:
        from neo4j import GraphDatabase
    except ImportError:
        kq.hong("Neo4j", "chưa cài package `neo4j`",
                "pip install -r requirements.txt")
        return

    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(user, mk))
        driver.verify_connectivity()
        kq.dat("Kết nối Neo4j", uri)
    except Exception as e:                           # noqa: BLE001
        ten_loi = type(e).__name__
        goi_y = ("Sai mật khẩu. docker-compose.yml nội suy NEO4J_AUTH TỪ .env nên "
                 "không thể gõ lệch; nguyên nhân thật là đổi mật khẩu SAU khi volume "
                 "Neo4j đã tạo. Trả .env về mật khẩu cũ, hoặc `docker compose down -v` "
                 "rồi ingest lại (xóa sạch đồ thị)." if "Auth" in ten_loi else
                 "Chạy `docker compose up -d` rồi đợi ~20s cho Neo4j lên "
                 "(`docker compose logs neo4j | tail -20`).")
        kq.hong("Kết nối Neo4j", f"{ten_loi}: {str(e).splitlines()[0][:120]}", goi_y)
        if driver:
            driver.close()
        return

    try:
        with driver.session() as s:
            dem = {}
            for nhan in ("Norm", "Component", "CTV", "TextUnit",
                         "Theme", "Jurisdiction", "Concept"):
                dem[nhan] = s.run(f"MATCH (n:{nhan}) RETURN count(n) AS c").single()["c"]
            canh = s.run(
                "MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY c DESC"
            ).data()

        if dem["Norm"] == 0:
            kq.hong("Dữ liệu Neo4j", "0 Norm — đồ thị RỖNG",
                    "Chạy `python -m src.ingestion.graph_builder` (~vài phút, "
                    "có gọi LLM ở Pass 4 nên cần khóa API).")
        elif dem["Norm"] < SO_NORM_MONG_DOI:
            kq.canh_bao("Dữ liệu Neo4j",
                        f"{dem['Norm']} Norm (mong đợi {SO_NORM_MONG_DOI}) — "
                        f"{dem['Component']} Component",
                        "Ingest có thể chưa chạy hết. Chạy lại "
                        "`python -m src.ingestion.graph_builder` — script dùng MERGE "
                        "nên chạy lại an toàn.")
        else:
            kq.dat("Dữ liệu Neo4j",
                   f"{dem['Norm']} Norm · {dem['Component']} Component · "
                   f"{dem['CTV']} CTV · {dem['TextUnit']} TextUnit")

        if dem["Component"] == 0 and dem["Norm"] > 0:
            kq.hong("Component", "có Norm nhưng 0 Component — ingest dở dang",
                    "Chạy lại `python -m src.ingestion.graph_builder`.")

        if canh:
            kq.dat("Cạnh đồ thị", " · ".join(f"{c['t']} {c['c']}" for c in canh[:6]))
        else:
            kq.hong("Cạnh đồ thị", "0 cạnh — có node nhưng không có quan hệ nào",
                    "Ingest dở dang: Stage 2 duyệt IMPLEMENTS|AMENDS sẽ không ra gì. "
                    "Chạy lại `python -m src.ingestion.graph_builder` (MERGE nên "
                    "chạy lại an toàn).")
    except Exception as e:                           # noqa: BLE001
        kq.hong("Đếm dữ liệu Neo4j", f"{type(e).__name__}: {e}",
                "Neo4j kết nối được nhưng truy vấn hỏng — xem "
                "`docker compose logs neo4j | tail -30`.")
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# 4. Qdrant
# ---------------------------------------------------------------------------

def kiem_qdrant(kq: KetQua) -> None:
    tieu_de("4. Qdrant — kết nối và collection")

    try:
        from qdrant_client import QdrantClient
    except ImportError:
        kq.hong("Qdrant", "chưa cài package `qdrant-client`",
                "pip install -r requirements.txt")
        return

    # Tên collection + số chiều lấy thẳng từ src/ingestion/vectorizer.py.
    try:
        from src.ingestion.vectorizer import COLLECTION_NAME, VECTOR_DIM
    except Exception:                                # noqa: BLE001
        COLLECTION_NAME, VECTOR_DIM = "legal_texts", 1024

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    try:
        # check_compatibility=False: bản client/server lệch nhau chỉ in cảnh báo
        # nhiễu, không liên quan tới thứ preflight đang kiểm.
        client = QdrantClient(host=host, port=port, timeout=10,
                              check_compatibility=False)
        ten_cac_col = [c.name for c in client.get_collections().collections]
        kq.dat("Kết nối Qdrant", f"{host}:{port} — {len(ten_cac_col)} collection")
    except Exception as e:                           # noqa: BLE001
        kq.hong("Kết nối Qdrant", f"{type(e).__name__}: {str(e).splitlines()[0][:120]}",
                "Chạy `docker compose up -d`; kiểm tra cổng 6333 có bị chiếm không "
                "(`docker compose ps`).")
        return

    if COLLECTION_NAME not in ten_cac_col:
        kq.hong(f"Collection {COLLECTION_NAME}",
                f"KHÔNG tồn tại (đang có: {', '.join(ten_cac_col) or 'không có gì'})",
                "Chạy `python -m src.ingestion.vectorizer` — script tự tạo "
                "collection nếu chưa có (chạy SAU graph_builder).")
        return

    try:
        so_diem = client.count(COLLECTION_NAME, exact=True).count
        info = client.get_collection(COLLECTION_NAME)
        so_chieu = getattr(getattr(info.config.params, "vectors", None), "size", None)
        mo_ta = f"{so_diem} điểm" + (f" · {so_chieu} chiều" if so_chieu else "")
        if so_diem == 0:
            kq.hong(f"Collection {COLLECTION_NAME}", "tồn tại nhưng RỖNG (0 điểm)",
                    "Chạy `python -m src.ingestion.vectorizer` (~vài phút, encode "
                    "bằng BGE-M3; dùng upsert nên chạy lại an toàn).")
        else:
            kq.dat(f"Collection {COLLECTION_NAME}", mo_ta)
        if so_chieu and so_chieu != VECTOR_DIM:
            kq.hong("Số chiều vector", f"{so_chieu} ≠ {VECTOR_DIM} (BGE-M3)",
                    f"Collection dựng bằng model khác. Xóa rồi vectorize lại: "
                    f"`python -c \"from qdrant_client import QdrantClient; "
                    f"QdrantClient(host='{host}',port={port})"
                    f".delete_collection('{COLLECTION_NAME}')\"`.")
    except Exception as e:                           # noqa: BLE001
        kq.canh_bao(f"Collection {COLLECTION_NAME}", f"không đếm được: {e}", "")


# ---------------------------------------------------------------------------
# 5. Python package + BGE-M3
# ---------------------------------------------------------------------------

def kiem_package(kq: KetQua, nhanh: bool) -> None:
    tieu_de("5. Python package và model BGE-M3")

    print(f"   Python {sys.version.split()[0]} — {sys.executable}")

    for ten, bat_buoc, sua in [
        ("sentence_transformers", True,
         "pip install -r requirements.txt — thiếu cái này thì `_build_clients()` "
         "ném ImportError và LiveAdapter không dựng được."),
        ("neo4j", True, "pip install -r requirements.txt"),
        ("qdrant_client", True, "pip install -r requirements.txt"),
        ("anthropic", True, "pip install -r requirements.txt"),
        ("fastapi", True, "pip install -r requirements.txt"),
        ("uvicorn", True, "pip install -r requirements.txt"),
        ("google.genai", False, "pip install google-genai — chỉ cần nếu chạy --llm-mode gemini*"),
    ]:
        try:
            __import__(ten)
            kq.dat(f"  import {ten}", "OK")
        except ImportError as e:
            (kq.hong if bat_buoc else kq.canh_bao)(f"  import {ten}", str(e)[:80], sua)

    # BGE-M3 đã nằm trong cache HuggingFace chưa (lần đầu tải ~2.2 GB).
    hf = Path(os.getenv("HF_HOME") or (Path.home() / ".cache" / "huggingface"))
    thu_muc = hf / "hub" / "models--BAAI--bge-m3"
    if thu_muc.is_dir():
        try:
            dung_luong = sum(f.stat().st_size for f in thu_muc.rglob("*") if f.is_file())
            if dung_luong < 1e9:
                kq.canh_bao(
                    "Cache BGE-M3", f"chỉ {dung_luong / 1e9:.1f} GB — có vẻ tải DỞ "
                    "(bản đủ khoảng 2,2 GB)",
                    "Cắm mạng chạy `python scripts/preflight.py` (bỏ --nhanh) để "
                    "tải nốt, hoặc xóa thư mục cache rồi tải lại.")
            else:
                kq.dat("Cache BGE-M3", f"{thu_muc} ({dung_luong / 1e9:.1f} GB)")
        except OSError:
            kq.dat("Cache BGE-M3", str(thu_muc))
    else:
        kq.canh_bao("Cache BGE-M3", f"chưa thấy trong {hf / 'hub'}",
                    "Lần chạy đầu sẽ tải ~2.2 GB từ HuggingFace — CẦN MẠNG. "
                    "Làm việc này TRƯỚC buổi bảo vệ, đừng để đến lúc lên trình bày.")

    if nhanh:
        print("   (bỏ qua nạp thử BGE-M3 vì --nhanh)")
        return

    try:
        from src.ingestion.vectorizer import load_model
    except Exception as e:                           # noqa: BLE001
        kq.hong("Nạp BGE-M3", f"không import được load_model: {e}",
                "Kiểm tra lại các package bắt buộc ở trên.")
        return
    try:
        import time
        t0 = time.perf_counter()
        model = load_model()
        giay = time.perf_counter() - t0
        chieu = getattr(model, "get_sentence_embedding_dimension", lambda: "?")()
        kq.dat("Nạp BGE-M3", f"{giay:.1f}s · {chieu} chiều")
        if giay > 60:
            kq.canh_bao("Thời gian nạp BGE-M3", f"{giay:.0f}s là chậm",
                        "UI nạp model MỘT LẦN lúc khởi động, nên hãy bật server "
                        "trước khi vào phòng bảo vệ.")
    except Exception as e:                           # noqa: BLE001
        kq.hong("Nạp BGE-M3", f"{type(e).__name__}: {str(e)[:120]}",
                "Thường là chưa tải model và máy đang offline. Cắm mạng chạy một "
                "lần cho model vào cache, hoặc đặt HF_HUB_OFFLINE=1 nếu đã có cache.")


# ---------------------------------------------------------------------------
# 6. Fixture cho lưới an toàn
# ---------------------------------------------------------------------------

def kiem_fixture(kq: KetQua) -> None:
    tieu_de("6. Fixture (lưới an toàn khi live hỏng giữa buổi)")

    thu_muc = GOC / "ui" / "fixtures"
    if not thu_muc.is_dir():
        kq.hong("ui/fixtures/", "không có thư mục",
                "Chạy `python -m ui.record data/evaluation/demo_questions.txt`.")
        return

    try:
        from ui.adapters import ReplayAdapter
    except Exception as e:                           # noqa: BLE001
        kq.hong("ui/fixtures/", f"không import được ReplayAdapter: {e}", "")
        return

    adapter = ReplayAdapter(fixtures_dir=thu_muc)
    ds = adapter.thong_tin_fixtures()
    if not ds:
        kq.hong("ui/fixtures/", "0 fixture hợp lệ",
                "Chạy `python -m ui.record data/evaluation/demo_questions.txt` "
                "với ĐÚNG bộ cờ sẽ dùng lúc demo.")
        return

    tam = [f for f in ds if f.get("tam")]
    kq.dat("ui/fixtures/", f"{len(ds)} fixture")
    for f in ds:
        danh_dau = "  (VIẾT TAY TẠM)" if f.get("tam") else ""
        print(f"     · {f['question'][:66]}{danh_dau}")
    if tam:
        kq.canh_bao(
            "Fixture viết tay tạm", f"{len(tam)}/{len(ds)} chưa phải lượt chạy thật",
            "Ghi đè bằng lượt chạy thật: "
            "`python -m ui.record \"<câu hỏi>\" --overwrite`.")

    # Câu trong demo_questions.txt mà chưa có fixture → lúc fallback sẽ trắng tay.
    tep_cau = GOC / "data" / "evaluation" / "demo_questions.txt"
    if tep_cau.is_file():
        from ui.adapters import doc_cau_hoi_goi_y
        thieu = [q for q in doc_cau_hoi_goi_y(tep_cau) if adapter.tim_fixture(q) is None]
        if thieu:
            kq.canh_bao(
                "Câu chưa có fixture", f"{len(thieu)} câu trong demo_questions.txt",
                "Nếu live hỏng giữa buổi thì những câu này KHÔNG fallback được. "
                f"Chạy `python -m ui.record {tep_cau.as_posix()}`.")
            for q in thieu:
                print(f"     · {q[:66]}")
        else:
            kq.dat("Phủ demo_questions.txt", "mọi câu đều có fixture")


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/preflight.py",
        description="Kiểm tra máy trình diễn trước buổi bảo vệ (chạy ở máy B).")
    parser.add_argument("--nhanh", action="store_true",
                        help="Bỏ qua bước nạp thử BGE-M3 (mục chậm nhất).")
    args = parser.parse_args(argv)

    print("=" * 68)
    print("PREFLIGHT — kiểm tra máy trình diễn (GraphRAG Pháp luật VN)")
    print(f"Thư mục repo: {GOC}")
    print("=" * 68)

    kq = KetQua()
    kiem_docker(kq)
    kiem_env(kq)
    kiem_neo4j(kq)
    kiem_qdrant(kq)
    kiem_package(kq, args.nhanh)
    kiem_fixture(kq)

    tieu_de("TỔNG KẾT")
    if kq.so_hong:
        print(f"{HONG} {kq.so_hong} mục BẮT BUỘC hỏng — chưa chạy `live` được.")
        print("\nCần sửa:")
        for trang_thai, ten, chi_tiet, sua in kq.muc:
            if trang_thai == HONG:
                print(f"  · {ten.strip()}: {chi_tiet}")
                if sua:
                    print(f"      → {sua}")
    else:
        print(f"{DAT} Không có mục bắt buộc nào hỏng — chạy `live` được.")
        print("\nBước tiếp theo:")
        print("  1. python -m ui.record data/evaluation/demo_questions.txt "
              "[--jurisdiction ...]   (ghi lưới an toàn)")
        print("  2. DEMO_MODE=live uvicorn ui.server:app --port 8000")

    if kq.so_canh_bao:
        print(f"\n{CANH_BAO}{kq.so_canh_bao} cảnh báo (không chặn, nhưng nên xử lý "
              "trước buổi bảo vệ).")
    print(f"\nChi tiết quy trình: ui/docs/LIVE_GUIDE.md")
    return 1 if kq.so_hong else 0


if __name__ == "__main__":
    sys.exit(main())
