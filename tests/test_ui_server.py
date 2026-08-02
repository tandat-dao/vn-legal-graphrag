"""Unit test cho `ui/server.py` — Task 3 của `ui/docs/UI_DEMO_SPEC.md`.

Trọng tâm: quy tắc đồng thời ở mục 2.3 — `/api/ask` phải serialize, request thứ
hai bị TỪ CHỐI ngay (không xếp hàng), và lock phải được nhả sau đó.
Chạy ở máy A: mode `replay`, không cần Neo4j/Qdrant/LLM.
"""
import json
import logging
import threading
import time

import pytest
from fastapi.testclient import TestClient

from ui import server as srv
from ui.adapters import ReplayAdapter

CAU_HOI = "Câu hỏi thử cho server?"

FIXTURE = {
    "question": CAU_HOI,
    "mode": "live",
    "events": [
        {"seq": 0, "t": 0.0, "step": "question", "kind": "result", "raw": "",
         "data": {"question": CAU_HOI}},
        {"seq": 1, "t": 0.9, "step": "plan", "kind": "log",
         "raw": "run_pipeline: plan=dat-dai/tp-hcm",
         "data": {"theme": "dat-dai", "jurisdiction": "tp-hcm"}},
    ],
    "result": {
        "context": "--- luat-dat-dai-2024 ---\nNội dung.",
        "answer": "Trả lời thử.", "citations": [], "elapsed_seconds": 0.9,
        "context_tokens": 10, "top_k_count": 1, "verifier": None,
    },
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    (tmp_path / "cau.json").write_text(json.dumps(FIXTURE, ensure_ascii=False),
                                       encoding="utf-8")
    # speed=1 → fixture dài 0.9s, đủ để test chồng request.
    monkeypatch.setattr(srv, "_adapter", ReplayAdapter(fixtures_dir=tmp_path, speed=1))
    with TestClient(srv.app) as c:
        monkeypatch.setattr(srv, "_adapter", ReplayAdapter(fixtures_dir=tmp_path, speed=1))
        yield c


def _events(text: str) -> list[dict]:
    return [json.loads(d[6:]) for d in text.splitlines() if d.startswith("data: ")]


# ---------------------------------------------------------------------------
# Endpoint cơ bản
# ---------------------------------------------------------------------------

def test_api_mode(client):
    d = client.get("/api/mode").json()
    assert d["mode"] == "replay"
    assert d["questions"] == [CAU_HOI]
    assert d["dang_ban"] is False


def test_trang_chu_tra_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # Mục 2.3: frontend KHÔNG được dùng EventSource
    assert "EventSource" not in r.text or "KHÔNG dùng EventSource" in r.text


def test_api_norm_graph(client):
    d = client.get("/api/norm-graph").json()
    assert len(d["nodes"]) >= 32
    assert any(e["type"] == "AMENDS" for e in d["edges"])


def test_api_text_tim_thay_va_khong_tim_thay(client):
    d = client.get("/api/text", params={
        "norm_id": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "dieu": "3", "khoan": "1"}).json()
    assert d["tim_thay"] is True and "m2" in d["text"]

    d = client.get("/api/text", params={
        "norm_id": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "dieu": "999"}).json()
    assert d["tim_thay"] is False and d["text"] is None


def test_api_ask_tra_dung_dong_su_kien(client):
    r = client.post("/api/ask", json={"question": CAU_HOI})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    events = _events(r.text)
    assert [e["seq"] for e in events] == list(range(len(events)))
    assert events[-1]["kind"] == "done"


def test_api_ask_cau_hoi_rong(client):
    events = _events(client.post("/api/ask", json={"question": "   "}).text)
    assert events[0]["kind"] == "error"


# ---------------------------------------------------------------------------
# Mục 2.3 — đồng thời
# ---------------------------------------------------------------------------

def test_hai_request_chong_nhau_thi_request_sau_bi_tu_choi(client):
    ket_qua: dict[str, list[dict]] = {}

    def chay(ten: str):
        ket_qua[ten] = _events(client.post("/api/ask", json={"question": CAU_HOI}).text)

    t1 = threading.Thread(target=chay, args=("a",))
    t1.start()
    time.sleep(0.35)          # để request A kịp giữ lock (fixture dài 0.9s)
    chay("b")
    t1.join()

    assert ket_qua["a"][-1]["kind"] == "done"          # A chạy trọn vẹn
    assert len(ket_qua["b"]) == 1                       # B KHÔNG xếp hàng
    assert ket_qua["b"][0]["kind"] == "error"
    assert ket_qua["b"][0]["data"]["loai"] == "dang-ban"


def test_lock_duoc_nha_sau_khi_xong(client):
    for _ in range(2):
        events = _events(client.post("/api/ask", json={"question": CAU_HOI}).text)
        assert events[-1]["kind"] == "done"
    assert srv._KHOA_ASK.locked() is False


def test_lock_duoc_nha_ca_khi_adapter_nem_loi(client, monkeypatch):
    class AdapterHong(ReplayAdapter):
        async def ask(self, question, **params):
            raise RuntimeError("hỏng giữa chừng")
            yield  # pragma: no cover — giữ hàm là async generator

    monkeypatch.setattr(srv, "_adapter", AdapterHong(fixtures_dir=None, speed=1))
    events = _events(client.post("/api/ask", json={"question": CAU_HOI}).text)
    assert events[0]["kind"] == "error"
    assert "hỏng giữa chừng" in events[0]["data"]["thong_bao"]
    assert srv._KHOA_ASK.locked() is False


# ---------------------------------------------------------------------------
# Task 5 — đổi live ⇄ replay không cần restart (POST /api/mode)
# ---------------------------------------------------------------------------

def test_doi_mode_tu_choi_gia_tri_la(client):
    r = client.post("/api/mode", json={"mode": "xyz"})
    assert r.status_code == 400
    assert "live" in r.json()["detail"]


def test_doi_mode_ve_chinh_no_la_no_op(client):
    r = client.post("/api/mode", json={"mode": "replay"})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "replay"
    # Trạng thái dựng SAU khi nhả khóa — nếu không UI hiện "đang đổi…" mãi.
    assert d["dang_doi_mode"] is False


def test_doi_mode_sang_live_that_bai_van_giu_adapter_cu(client, monkeypatch):
    """Dựng LiveAdapter hỏng → 503, nhưng adapter đang chạy KHÔNG được mất."""
    import ui.adapters as adapters

    def _hong(*a, **k):
        raise RuntimeError("Neo4j chưa chạy")

    monkeypatch.setattr(adapters, "LiveAdapter", _hong)
    truoc = srv._adapter

    r = client.post("/api/mode", json={"mode": "live"})
    assert r.status_code == 503
    assert "PHÁT LẠI" in r.json()["detail"]
    assert srv._adapter is truoc, "mất adapter cũ khi đổi hụt"
    assert client.get("/api/mode").json()["mode"] == "replay"
    # Lý do hỏng được giữ lại để UI hiện ra
    assert srv._LOI_DOI_MODE and "docker compose ps" in srv._LOI_DOI_MODE


def test_doi_mode_sang_live_thanh_cong(client, monkeypatch):
    """Dựng được LiveAdapter → adapter cũ bị `dong()`, mode đổi sang live."""
    import ui.adapters as adapters

    class _LiveGia(adapters.BaseAdapter):
        mode = "live"

        def cau_hoi_co_san(self):
            return ["câu live"]

    monkeypatch.setattr(adapters, "LiveAdapter", _LiveGia)
    cu = srv._adapter
    da_dong = {"n": 0}
    monkeypatch.setattr(cu, "dong", lambda: da_dong.__setitem__("n", da_dong["n"] + 1))

    d = client.post("/api/mode", json={"mode": "live"}).json()
    assert d["mode"] == "live"
    assert d["questions"] == ["câu live"]
    assert d["replay_speed"] is None
    assert da_dong["n"] == 1, "adapter cũ không được đóng → rò Neo4j driver"

    # và quay lại replay được
    assert client.post("/api/mode", json={"mode": "replay"}).json()["mode"] == "replay"


def test_doi_mode_bi_chan_khi_dang_chay(client):
    """Đang phát một câu thì KHÔNG được thay adapter (cắt luồng SSE đang chạy)."""
    ket = {}

    def _hoi():
        ket["r"] = client.post("/api/ask", json={"question": CAU_HOI})

    t = threading.Thread(target=_hoi)
    t.start()
    try:
        for _ in range(200):            # đợi lock được giữ
            if srv._KHOA_ASK.locked():
                break
            time.sleep(0.01)
        assert srv._KHOA_ASK.locked()
        r = client.post("/api/mode", json={"mode": "live"})
        assert r.status_code == 409
        assert "đợi câu đó chạy xong" in r.json()["detail"]
    finally:
        t.join(timeout=15)


def test_tham_so_speed_di_vao_adapter(client, monkeypatch):
    """Nút chỉnh tốc độ: `speed` trong body /api/ask phải tới được adapter."""
    nhan = {}
    goc = srv._adapter.ask

    async def _bat(question, **params):
        nhan.update(params)
        async for ev in goc(question, **params):
            yield ev

    monkeypatch.setattr(srv._adapter, "ask", _bat)
    client.post("/api/ask", json={"question": CAU_HOI, "speed": 8})
    assert nhan["speed"] == 8


# ---------------------------------------------------------------------------
# Lọc log truy cập tài nguyên tĩnh (Task 5)
# ---------------------------------------------------------------------------

def _ban_ghi(duong_dan: str, ma: int) -> logging.LogRecord:
    """Giả đúng dạng record của `uvicorn.access`: args = (host, method, path, http, code)."""
    return logging.LogRecord(
        name="uvicorn.access", level=logging.INFO, pathname="", lineno=0,
        msg='%s - "%s %s HTTP/%s" %d', args=("127.0.0.1:1", "GET", duong_dan, "1.1", ma),
        exc_info=None,
    )


def test_loc_bo_log_vendor_thanh_cong():
    loc = srv._LocTaiNguyenTinh()
    for p in ("/static/vendor/fonts/be-vietnam-pro-400-vietnamese.woff2",
              "/static/vendor/fonts/be-vietnam-pro.css",
              "/static/vendor/tailwind.min.js"):
        assert loc.filter(_ban_ghi(p, 200)) is False, p
    assert loc.filter(_ban_ghi("/static/vendor/tailwind.min.js", 304)) is False


def test_loc_GIU_log_vendor_loi():
    """404 vendor = quên copy thư mục vendor → phải nhìn thấy."""
    loc = srv._LocTaiNguyenTinh()
    assert loc.filter(_ban_ghi("/static/vendor/tailwind.min.js", 404)) is True
    assert loc.filter(_ban_ghi("/static/vendor/fonts/x.woff2", 500)) is True


def test_loc_khong_dung_toi_log_khac():
    loc = srv._LocTaiNguyenTinh()
    for p in ("/", "/api/mode", "/api/ask", "/api/norm-graph", "/static/index.html"):
        assert loc.filter(_ban_ghi(p, 200)) is True, p


def test_loc_khong_vo_khi_record_khac_dang():
    """Đổi format log của uvicorn thì filter phải cho qua, không được ném."""
    loc = srv._LocTaiNguyenTinh()
    r = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, "chuỗi thường", None, None)
    assert loc.filter(r) is True
    r2 = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, "%s", ("a",), None)
    assert loc.filter(r2) is True
