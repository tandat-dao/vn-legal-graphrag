"""Unit test cho `LiveAdapter` + `ui/record.py` — Task 4 của `ui/docs/UI_DEMO_SPEC.md`.

**Chạy ở máy A: KHÔNG cần Neo4j/Qdrant/LLM.** Cách làm: tiêm client giả qua
`LiveAdapter(clients=...)` (nên `_build_clients` không bị gọi) và thay
`_chay_pipeline` bằng một hàm giả vừa phát log giống pipeline thật vừa trả
`PipelineResult` giả.

Phần này KHÔNG kiểm chứng được ở máy A (cần máy B, xem `ui/README.md`):
`_build_clients()` chạy thật, regex trong `parse_message` khớp log THẬT của
`src/`, và `run_pipeline` nhận đúng bộ keyword.
"""
import asyncio
import json
import logging
import threading

import pytest

from ui.adapters import (
    DEFAULT_LLM_CACHE_DIR,
    LiveAdapter,
    ReplayAdapter,
    doc_cau_hoi_goi_y,
)
from ui.trace import TraceCollector

CAU_HOI = "Hạn mức giao đất ở cho cá nhân tại TP.HCM tối đa là bao nhiêu?"

CONTEXT = (
    "--- [Tier 4 | Hiệu lực: 2024-09-30] Điều 3. Hạn mức, Khoản 1. "
    "(quyet-dinh-69-2024-qd-ubnd-tp-hcm) ---\n"
    "Điều 3. Hạn mức\nKhoản 1.\nKhông quá 160 m2/cá nhân."
)

KET_QUA_GIA = {
    "question": CAU_HOI,
    "query_plan": {"theme": "dat-dai", "jurisdiction": "tp-hcm",
                   "procedure": "chuyen-muc-dich-su-dung-dat", "temporal": None},
    "response_mode": "general",
    "lccids_count": 12,
    "top_k_count": 25,
    "context_tokens": 2180,
    "context": CONTEXT,
    "answer": "Không quá 160 m2 [Điều 3, Khoản 1, Văn bản quyet-dinh-69-2024-qd-ubnd-tp-hcm].",
    "citations": [{"loai": "dieu", "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm",
                   "dieu": "3", "khoan": "1", "diem": None}],
    "context_used": True,
    "elapsed_seconds": 18.7,
    "verifier": None,
}

# Ba dòng log thật của `src/` — đủ để chứng minh event log đi qua collector.
LOG_GIA = [
    ("src.pipeline", "run_pipeline: plan=dat-dai/tp-hcm"),
    ("src.retrieval.subgraph_extractor", "Stage 1: top-5 norm, scores=[0.62, 0.41]"),
    ("src.pipeline", "run_pipeline: hoàn thành trong 18.7s — 1 citations"),
]


def _clients_gia():
    """4 client giả — `_build_clients` KHÔNG được gọi khi truyền tham số này."""
    return (object(), object(), object(), object())


def _adapter(monkeypatch, ket_qua=None, loi: Exception | None = None,
             **kw) -> LiveAdapter:
    ad = LiveAdapter(clients=_clients_gia(), **kw)

    def _gia(question, params):
        for ten, msg in LOG_GIA:
            logging.getLogger(ten).info(msg)
        if loi is not None:
            raise loi
        return dict(ket_qua if ket_qua is not None else KET_QUA_GIA)

    monkeypatch.setattr(ad, "_chay_pipeline", _gia)
    return ad


def _thu_ask(adapter, question=CAU_HOI, **params) -> list[dict]:
    async def _go():
        return [ev async for ev in adapter.ask(question, **params)]
    return asyncio.run(_go())


# ---------------------------------------------------------------------------
# Khởi tạo client MỘT LẦN (spec mục 2.2)
# ---------------------------------------------------------------------------

def test_khong_goi_build_clients_khi_da_tiem_client(monkeypatch):
    """Truyền `clients=` thì `_build_clients` không được gọi (mục 2.2)."""
    import src.pipeline as pipeline

    def _no(*a, **k):
        raise AssertionError("_build_clients bị gọi — sai vòng đời client")

    monkeypatch.setattr(pipeline, "_build_clients", _no)
    ad = LiveAdapter(clients=_clients_gia())
    assert ad.mode == "live"


def test_build_clients_chi_goi_dung_mot_lan(monkeypatch):
    """Không tiêm client → gọi `_build_clients` ĐÚNG một lần lúc __init__."""
    import src.pipeline as pipeline

    dem = {"n": 0}

    def _dem(llm_mode="claude"):
        dem["n"] += 1
        return _clients_gia()

    monkeypatch.setattr(pipeline, "_build_clients", _dem)
    ad = LiveAdapter(llm_mode="claude")
    assert dem["n"] == 1
    # Nhiều lượt hỏi KHÔNG dựng lại client
    monkeypatch.setattr(ad, "_chay_pipeline", lambda q, p: dict(KET_QUA_GIA))
    _thu_ask(ad)
    _thu_ask(ad)
    assert dem["n"] == 1


def test_client_duoc_truyen_vao_run_pipeline(monkeypatch):
    """4 client của adapter phải đi vào `run_pipeline` qua keyword (mục 2.2)."""
    ad = LiveAdapter(clients=_clients_gia())
    thay = {}

    import src.pipeline as pipeline
    monkeypatch.setattr(pipeline, "run_pipeline",
                        lambda q, **kw: thay.update(kw) or dict(KET_QUA_GIA))
    ad._chay_pipeline(CAU_HOI, {"jurisdiction": "tp-hcm", "response_mode": "irac"})

    assert thay["neo4j_driver"] is ad.neo4j_driver
    assert thay["qdrant_client"] is ad.qdrant_client
    assert thay["anthropic_client"] is ad.anthropic_client
    assert thay["model"] is ad.model
    assert thay["force_jurisdiction"] == "tp-hcm"
    assert thay["response_mode"] == "irac"
    assert thay["llm_cache_dir"] == DEFAULT_LLM_CACHE_DIR


def test_no_llm_cache_tat_cache(monkeypatch):
    ad = LiveAdapter(clients=_clients_gia(), no_llm_cache=True)
    assert ad.llm_cache_dir is None
    assert ad._tham_so({})["llm_cache_dir"] is None


def test_tham_so_bo_qua_top_k_khi_khong_dat():
    """Không đặt top_k/max_tokens thì KHÔNG truyền → giữ mặc định của `src/`."""
    ad = LiveAdapter(clients=_clients_gia())
    kw = ad._tham_so({})
    assert "top_k" not in kw and "max_tokens" not in kw
    ad2 = LiveAdapter(clients=_clients_gia(), top_k=10, max_tokens=3000)
    kw2 = ad2._tham_so({})
    assert kw2["top_k"] == 10 and kw2["max_tokens"] == 3000


# ---------------------------------------------------------------------------
# Chuỗi event của ask() (spec mục 4.1)
# ---------------------------------------------------------------------------

def test_ask_phat_du_chuoi_event(monkeypatch):
    ad = _adapter(monkeypatch)
    events = _thu_ask(ad, jurisdiction="tp-hcm")

    assert events[0]["step"] == "question" and events[0]["kind"] == "result"
    assert events[0]["data"]["question"] == CAU_HOI
    assert events[0]["data"]["force_jurisdiction"] == "tp-hcm"

    # Log thật của pipeline đi qua collector
    raws = [e["raw"] for e in events]
    assert any("Stage 1:" in r for r in raws)
    assert any("hoàn thành" in r for r in raws)

    # Đuôi do su_kien_ket_qua dựng
    duoi = [(e["step"], e["kind"]) for e in events[-4:]]
    assert duoi == [("context", "result"), ("generate", "result"),
                    ("verify", "result"), ("done", "done")]

    ctx = events[-4]["data"]
    assert ctx["n_blocks"] == 1 and ctx["blocks"][0]["tier"] == 4
    gen = events[-3]["data"]
    assert gen["answer"].startswith("Không quá 160")
    assert gen["citation_links"][0]["khop"] == "chinh-xac"


def test_seq_va_t_khong_lui(monkeypatch):
    """`seq` tăng đều 1 và `t` không giảm — mục 2.3 nói đây là lỗi vỡ trước hội đồng."""
    ad = _adapter(monkeypatch)
    events = _thu_ask(ad)
    assert [e["seq"] for e in events] == list(range(len(events)))
    ts = [e["t"] for e in events]
    assert all(b >= a for a, b in zip(ts, ts[1:])), ts


def test_step_hop_le(monkeypatch):
    from ui.trace import KINDS, STEPS
    ad = _adapter(monkeypatch)
    for e in _thu_ask(ad):
        assert e["step"] in STEPS, e
        assert e["kind"] in KINDS, e


# ---------------------------------------------------------------------------
# Mỗi request một collector, gỡ sạch handler (spec mục 2.3)
# ---------------------------------------------------------------------------

def _dem_collector() -> int:
    return sum(isinstance(h, TraceCollector)
               for h in logging.getLogger("src").handlers)


def test_collector_duoc_go_sau_moi_request(monkeypatch):
    ad = _adapter(monkeypatch)
    truoc = _dem_collector()
    for _ in range(5):
        _thu_ask(ad)
    assert _dem_collector() == truoc, "handler tích lũy — quên removeHandler"


def test_collector_duoc_go_ca_khi_pipeline_loi(monkeypatch):
    ad = _adapter(monkeypatch, loi=RuntimeError("Neo4j chết"))
    truoc = _dem_collector()
    _thu_ask(ad)
    assert _dem_collector() == truoc


def test_collector_duoc_go_khi_client_ngat_giua_chung(monkeypatch):
    """Đóng generator sớm (client bấm Stop) vẫn phải gỡ handler."""
    ad = _adapter(monkeypatch)
    truoc = _dem_collector()

    async def _go():
        gen = ad.ask(CAU_HOI)
        await gen.__anext__()          # lấy đúng event `question` rồi bỏ
        await gen.aclose()

    asyncio.run(_go())
    assert _dem_collector() == truoc


def test_hai_request_khong_tron_event(monkeypatch):
    """Chạy tuần tự hai câu: event câu sau không dính event câu trước."""
    ad = _adapter(monkeypatch)
    a = _thu_ask(ad, question="câu A")
    b = _thu_ask(ad, question="câu B")
    assert a[0]["data"]["question"] == "câu A"
    assert b[0]["data"]["question"] == "câu B"
    assert len(a) == len(b)
    assert b[0]["seq"] == 0 and b[0]["t"] == 0.0


# ---------------------------------------------------------------------------
# Khóa không chờ (spec mục 2.3)
# ---------------------------------------------------------------------------

def _adapter_cham(monkeypatch, cho: threading.Event) -> LiveAdapter:
    """Adapter mà `_chay_pipeline` KẸT tới khi `cho` được set — để dựng cảnh chồng lượt."""
    ad = LiveAdapter(clients=_clients_gia())

    def _cham(question, params):
        logging.getLogger("src.pipeline").info("run_pipeline: plan=dat-dai/tp-hcm")
        assert cho.wait(timeout=10), "test treo: pipeline giả không được thả"
        return dict(KET_QUA_GIA)

    monkeypatch.setattr(ad, "_chay_pipeline", _cham)
    return ad


def test_hai_luot_chong_nhau_bi_tu_choi(monkeypatch):
    """Lượt thứ hai khi lượt đầu CHƯA xong → event lỗi, KHÔNG xếp hàng."""
    cho = threading.Event()
    ad = _adapter_cham(monkeypatch, cho)

    async def _go():
        gen1 = ad.ask(CAU_HOI)
        await gen1.__anext__()          # lượt 1 đã giao thread và đang kẹt
        ev2 = [e async for e in ad.ask(CAU_HOI)]
        cho.set()
        async for _ in gen1:            # xả nốt lượt 1 cho sạch
            pass
        return ev2

    ev2 = asyncio.run(_go())
    assert len(ev2) == 1, [e["step"] for e in ev2]
    assert ev2[0]["kind"] == "error"
    assert ev2[0]["data"]["loai"] == "dang-ban"
    assert "PHÁT LẠI" in ev2[0]["data"]["thong_bao"]


def test_khoa_duoc_nha_du_client_ngat_giua_chung(monkeypatch):
    """Client ngắt giữa chừng: thread vẫn chạy nốt rồi NHẢ khóa.

    Đây là ca mà lock cấp module của `server.py` không đỡ được — nó nhả ngay khi
    generator SSE đóng, trong khi `run_pipeline` còn chạy (spec mục 2.3).
    """
    cho = threading.Event()
    ad = _adapter_cham(monkeypatch, cho)

    async def _go():
        gen = ad.ask(CAU_HOI)
        await gen.__anext__()
        await gen.aclose()              # client bấm Stop / đóng tab
        # Quan sát NGAY: `asyncio.run()` chờ executor lúc tắt loop nên đo sau
        # khi nó trả về thì bao giờ cũng thấy đã nhả.
        con_khoa = ad._khoa_pipeline.locked()
        cho.set()                       # thả cho pipeline chạy nốt
        for _ in range(100):
            if not ad._khoa_pipeline.locked():
                break
            await asyncio.sleep(0.05)
        return con_khoa, ad._khoa_pipeline.locked()

    con_khoa, con_khoa_sau = asyncio.run(_go())
    assert con_khoa, "pipeline còn chạy mà đã nhả khóa"
    assert not con_khoa_sau, "thread xong mà không nhả khóa"


def test_chay_ghi_bi_tu_choi_khi_dang_chay(monkeypatch):
    """`record.py` cũng không được chen ngang một lượt đang chạy."""
    cho = threading.Event()
    ad = _adapter_cham(monkeypatch, cho)

    async def _go():
        gen = ad.ask(CAU_HOI)
        await gen.__anext__()
        with pytest.raises(RuntimeError, match="đang chạy"):
            ad.chay_ghi(CAU_HOI)
        cho.set()
        async for _ in gen:
            pass

    asyncio.run(_go())


def test_khoa_duoc_nha_sau_khi_xong(monkeypatch):
    ad = _adapter(monkeypatch)
    _thu_ask(ad)
    assert not ad._khoa_pipeline.locked()
    _thu_ask(ad)
    assert not ad._khoa_pipeline.locked()


def test_khoa_duoc_nha_khi_pipeline_loi(monkeypatch):
    ad = _adapter(monkeypatch, loi=RuntimeError("bùm"))
    _thu_ask(ad)
    assert not ad._khoa_pipeline.locked()


# ---------------------------------------------------------------------------
# Lỗi → event tiếng Việt (spec Task 4)
# ---------------------------------------------------------------------------

class _LoiLLM(Exception):
    """Giả `anthropic.APIStatusError`: nhận dạng qua thuộc tính `status_code`."""
    status_code = 529


def test_loi_llm_goi_y_replay(monkeypatch):
    ad = _adapter(monkeypatch, loi=_LoiLLM("Overloaded"))
    events = _thu_ask(ad)
    loi = events[-1]
    assert loi["kind"] == "error"
    assert loi["data"]["loai"] == "loi-llm"
    assert "529" in loi["data"]["thong_bao"]
    assert "PHÁT LẠI" in loi["data"]["thong_bao"]
    # Lỗi thay cho đuôi kết quả — không được phát `generate` rỗng
    assert not any(e["step"] == "generate" and e["kind"] == "result" for e in events)


def test_loi_ha_tang_goi_y_kiem_docker(monkeypatch):
    ad = _adapter(monkeypatch, loi=RuntimeError("Neo4j unreachable"))
    loi = _thu_ask(ad)[-1]
    assert loi["data"]["loai"] == "loi-pipeline"
    assert "docker compose ps" in loi["data"]["thong_bao"]


def test_loi_van_giu_event_log_da_phat(monkeypatch):
    """Lỗi giữa chừng vẫn giữ event log đã phát — không im lặng nuốt."""
    ad = _adapter(monkeypatch, loi=RuntimeError("bùm"))
    events = _thu_ask(ad)
    assert any("Stage 1:" in e["raw"] for e in events)


# ---------------------------------------------------------------------------
# chay_ghi() — đường dùng cho record.py
# ---------------------------------------------------------------------------

def test_chay_ghi_tra_event_log_va_result(monkeypatch):
    ad = _adapter(monkeypatch)
    events, result = ad.chay_ghi(CAU_HOI, jurisdiction="tp-hcm")
    assert result["answer"] == KET_QUA_GIA["answer"]
    assert events[0]["step"] == "question"
    # KHÔNG được chứa đuôi — ReplayAdapter dựng lại từ `result`
    assert not any(e["step"] in {"context", "generate", "verify"} and e["kind"] == "result"
                   for e in events)
    assert not any(e["kind"] == "done" for e in events)


def test_chay_ghi_va_ask_cho_cung_chuoi_log(monkeypatch):
    """Fixture phải giống hệt lúc chạy live (yêu cầu của Task 4)."""
    ad = _adapter(monkeypatch)
    events_ghi, _ = ad.chay_ghi(CAU_HOI)
    events_ask = _thu_ask(ad)
    assert [(e["step"], e["kind"], e["raw"]) for e in events_ghi] == \
           [(e["step"], e["kind"], e["raw"]) for e in events_ask[:len(events_ghi)]]


def test_chay_ghi_nha_khoa(monkeypatch):
    ad = _adapter(monkeypatch)
    ad.chay_ghi(CAU_HOI)
    assert not ad._khoa_pipeline.locked()


# ---------------------------------------------------------------------------
# ui/record.py
# ---------------------------------------------------------------------------

def test_doc_cau_hoi_goi_y_bo_dong_trong_va_thang(tmp_path):
    p = tmp_path / "q.txt"
    p.write_text("# ghi chú\n\nCâu một?\n   \nCâu hai?\n# cuối\n", encoding="utf-8")
    assert doc_cau_hoi_goi_y(p) == ["Câu một?", "Câu hai?"]


def test_doc_cau_hoi_goi_y_file_khong_ton_tai(tmp_path):
    assert doc_cau_hoi_goi_y(tmp_path / "khong-co.txt") == []


def test_doc_danh_sach_cau_hoi_phan_biet_file_va_cau(tmp_path):
    from ui.record import doc_danh_sach_cau_hoi
    p = tmp_path / "q.txt"
    p.write_text("Câu A?\nCâu B?\n", encoding="utf-8")
    assert doc_danh_sach_cau_hoi(str(p)) == ["Câu A?", "Câu B?"]
    assert doc_danh_sach_cau_hoi("Một câu hỏi bình thường?") == ["Một câu hỏi bình thường?"]


def test_ghi_fixture_dung_dinh_dang(monkeypatch, tmp_path):
    from ui.record import ghi_fixture
    ad = _adapter(monkeypatch)
    dich = ghi_fixture(ad, CAU_HOI, tmp_path,
                       {"jurisdiction": "tp-hcm", "response_mode": None,
                        "verify": False, "verify_tier": 1, "llm_mode": "claude"})
    assert dich is not None and dich.exists()
    d = json.loads(dich.read_text(encoding="utf-8"))
    assert d["question"] == CAU_HOI
    assert d["mode"] == "live"
    assert d["params"]["force_jurisdiction"] == "tp-hcm"
    assert d["params"]["llm_mode"] == "claude"
    assert d["events"] and d["result"]["answer"]
    assert "recorded_at" in d
    assert not d.get("tam"), "fixture ghi thật KHÔNG được mang cờ tạm"


def test_ghi_fixture_khong_ghi_de_neu_chua_bao(monkeypatch, tmp_path):
    from ui.record import ghi_fixture
    ad = _adapter(monkeypatch)
    params = {"jurisdiction": None, "response_mode": None, "verify": False,
              "verify_tier": 1, "llm_mode": "claude"}
    d1 = ghi_fixture(ad, CAU_HOI, tmp_path, params)
    assert d1 is not None
    assert ghi_fixture(ad, CAU_HOI, tmp_path, params) is None      # bỏ qua
    assert ghi_fixture(ad, CAU_HOI, tmp_path, params, ghi_de=True) is not None


def test_fixture_ghi_ra_replay_lai_duoc(monkeypatch, tmp_path):
    """Hợp đồng record → replay: fixture vừa ghi phải phát lại ra đủ 7 bước.

    Đây là test giá trị nhất chạy được ở máy A: nó nối `LiveAdapter.chay_ghi`
    với `ReplayAdapter.ask` mà không cần DB.
    """
    from ui.record import ghi_fixture
    ad = _adapter(monkeypatch)
    ghi_fixture(ad, CAU_HOI, tmp_path,
                {"jurisdiction": "tp-hcm", "response_mode": None,
                 "verify": False, "verify_tier": 1, "llm_mode": "claude"})

    replay = ReplayAdapter(fixtures_dir=tmp_path, speed=1000.0)
    ev_replay = asyncio.run(_gom(replay.ask(CAU_HOI)))
    ev_live = _thu_ask(ad, jurisdiction="tp-hcm")

    assert [e["step"] for e in ev_replay] == [e["step"] for e in ev_live]
    assert [e["kind"] for e in ev_replay] == [e["kind"] for e in ev_live]
    assert [e["seq"] for e in ev_replay] == list(range(len(ev_replay)))
    assert ev_replay[-3]["data"]["answer"] == ev_live[-3]["data"]["answer"]
    # Không phát trùng đuôi
    assert sum(e["kind"] == "done" for e in ev_replay) == 1


async def _gom(gen) -> list[dict]:
    return [e async for e in gen]
