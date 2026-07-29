"""Unit test cho `ui/server.py` — Task 3 của `docs/UI_DEMO_SPEC.md`.

Trọng tâm: quy tắc đồng thời ở mục 2.3 — `/api/ask` phải serialize, request thứ
hai bị TỪ CHỐI ngay (không xếp hàng), và lock phải được nhả sau đó.
Chạy ở máy A: mode `replay`, không cần Neo4j/Qdrant/LLM.
"""
import json
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
