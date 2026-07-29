"""Unit test cho `ui/adapters.py` — Task 3 của `docs/UI_DEMO_SPEC.md`.

Chạy ở máy A: không cần Neo4j/Qdrant/LLM.
"""
import asyncio
import json

import pytest

from ui.adapters import (
    ReplayAdapter,
    chuan_hoa_cau_hoi,
    slug_cau_hoi,
    su_kien_ket_qua,
)

CAU_HOI = "Hạn mức giao đất ở tại TP.HCM là bao nhiêu?"

CONTEXT = (
    "--- [Tier 4 | Hiệu lực: 2024-09-30] Điều 3. Hạn mức, Khoản 1. "
    "(quyet-dinh-69-2024-qd-ubnd-tp-hcm) ---\n"
    "Điều 3. Hạn mức\nKhoản 1.\nKhông quá 160 m2/cá nhân."
)

FIXTURE = {
    "question": CAU_HOI,
    "recorded_at": "2026-07-26T10:00:00",
    "mode": "live",
    "params": {"force_jurisdiction": "tp-hcm", "llm_mode": "claude"},
    "events": [
        {"seq": 0, "t": 0.0, "step": "question", "kind": "result", "raw": "",
         "data": {"question": CAU_HOI, "force_jurisdiction": "tp-hcm"}},
        {"seq": 1, "t": 0.2, "step": "plan", "kind": "log",
         "raw": "run_pipeline: plan=dat-dai/tp-hcm",
         "data": {"theme": "dat-dai", "jurisdiction": "tp-hcm"}},
        {"seq": 2, "t": 0.4, "step": "done", "kind": "log",
         "raw": "run_pipeline: hoàn thành trong 0.4s — 1 citations",
         "data": {"elapsed_seconds": 0.4, "n_citations": 1}},
    ],
    "result": {
        "context": CONTEXT,
        "answer": "Không quá 160 m2 [Điều 3, Khoản 1, Văn bản quyet-dinh-69-2024-qd-ubnd-tp-hcm].",
        "citations": [{"dieu": "3", "khoan": "1", "diem": None, "tiet": None,
                       "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "loai": "dieu"}],
        "context_tokens": 120, "top_k_count": 1, "context_used": True,
        "elapsed_seconds": 0.4, "lccids_count": 2, "verifier": None,
        "response_mode": "general", "query_plan": {"theme": "dat-dai"},
    },
}


@pytest.fixture()
def adapter(tmp_path):
    (tmp_path / "cau-1.json").write_text(
        json.dumps(FIXTURE, ensure_ascii=False), encoding="utf-8")
    return ReplayAdapter(fixtures_dir=tmp_path, speed=1000)


def _chay(adapter, question, **params):
    async def _go():
        return [e async for e in adapter.ask(question, **params)]
    return asyncio.run(_go())


# ---------------------------------------------------------------------------
# Chuẩn hóa câu hỏi
# ---------------------------------------------------------------------------

def test_chuan_hoa_bo_dau_cau_va_khoang_trang():
    assert chuan_hoa_cau_hoi("  Hạn mức  giao đất ở TP.HCM?? ") == "hạn mức giao đất ở tp hcm"


def test_chuan_hoa_giu_dau_tieng_viet():
    # Bỏ dấu sẽ làm "hạn mức" và "han muc" trùng khóa — không được
    assert chuan_hoa_cau_hoi("hạn mức") != chuan_hoa_cau_hoi("han muc")


def test_slug_bo_dau_cho_ten_file():
    assert slug_cau_hoi("Hạn mức giao đất ở TP.HCM?") == "han-muc-giao-dat-o-tp-hcm"


# ---------------------------------------------------------------------------
# ReplayAdapter
# ---------------------------------------------------------------------------

def test_nap_fixture_va_liet_ke_cau_hoi(adapter):
    assert adapter.cau_hoi_co_san() == [CAU_HOI]
    assert adapter.thong_tin_fixtures()[0]["file"] == "cau-1.json"


def test_khop_cau_hoi_long_hoa_thuong_va_dau_cau(adapter):
    events = _chay(adapter, "hạn mức giao đất ở tại tp hcm là bao nhiêu")
    assert events[0]["step"] == "question"
    assert not any(e["kind"] == "error" for e in events)


def test_phat_lai_dung_thu_tu_va_seq_lien_tuc(adapter):
    events = _chay(adapter, CAU_HOI)
    assert [e["seq"] for e in events] == list(range(len(events)))
    assert [e["t"] for e in events] == sorted(e["t"] for e in events)
    assert events[-1]["kind"] == "done"


def test_phat_lai_sinh_event_ket_qua(adapter):
    events = _chay(adapter, CAU_HOI)
    ctx = [e for e in events if e["step"] == "context" and e["kind"] == "result"][0]
    gen = [e for e in events if e["step"] == "generate" and e["kind"] == "result"][0]
    assert len(ctx["data"]["blocks"]) == 1
    assert ctx["data"]["blocks"][0]["norm_id"] == "quyet-dinh-69-2024-qd-ubnd-tp-hcm"
    assert gen["data"]["citation_links"][0]["khop"] == "chinh-xac"
    assert gen["data"]["citation_links"][0]["block_index"] == 0


def test_khong_co_fixture_thi_bao_loi_kem_danh_sach(adapter):
    events = _chay(adapter, "một câu chưa ghi bao giờ")
    assert len(events) == 1
    assert events[0]["kind"] == "error"
    assert CAU_HOI in events[0]["data"]["cau_hoi_co_san"]
    assert "ui.record" in events[0]["data"]["thong_bao"]


def test_thu_muc_fixture_rong_van_bao_loi_ro_rang(tmp_path):
    adapter = ReplayAdapter(fixtures_dir=tmp_path / "trong", speed=1000)
    events = _chay(adapter, "bất kỳ")
    assert events[0]["kind"] == "error"
    assert events[0]["data"]["cau_hoi_co_san"] == []


def test_fixture_hong_khong_lam_sap_adapter(tmp_path):
    (tmp_path / "hong.json").write_text("{ không phải json", encoding="utf-8")
    (tmp_path / "cau-1.json").write_text(
        json.dumps(FIXTURE, ensure_ascii=False), encoding="utf-8")
    adapter = ReplayAdapter(fixtures_dir=tmp_path, speed=1000)
    assert adapter.cau_hoi_co_san() == [CAU_HOI]


def test_speed_theo_request_de_len_env(adapter):
    # speed lớn → phát lại gần như tức thì (chỉ kiểm tham số được nhận, không đo giờ)
    events = _chay(adapter, CAU_HOI, speed=500)
    assert len(events) > 3
    events = _chay(adapter, CAU_HOI, speed="hỏng")   # giá trị rác → lùi về mặc định
    assert len(events) > 3


def test_fixture_tam_duoc_gan_co_canh_bao(tmp_path):
    tam = dict(FIXTURE, tam=True, ghi_chu="số minh họa")
    (tmp_path / "tam.json").write_text(json.dumps(tam, ensure_ascii=False), encoding="utf-8")
    adapter = ReplayAdapter(fixtures_dir=tmp_path, speed=1000)
    events = _chay(adapter, CAU_HOI)
    assert events[0]["data"]["fixture_tam"] is True
    assert events[0]["data"]["fixture_ghi_chu"] == "số minh họa"


# ---------------------------------------------------------------------------
# su_kien_ket_qua — dùng chung live + replay
# ---------------------------------------------------------------------------

def test_su_kien_ket_qua_du_4_event_va_seq_tiep_noi():
    events = su_kien_ket_qua(FIXTURE["result"], seq_bat_dau=10, t=1.5)
    assert [e["step"] for e in events] == ["context", "generate", "verify", "done"]
    assert [e["seq"] for e in events] == [10, 11, 12, 13]
    assert all(e["t"] == 1.5 for e in events)
    assert events[-1]["kind"] == "done"


def test_su_kien_ket_qua_chiu_duoc_result_rong():
    events = su_kien_ket_qua({}, 0, 0.0)
    assert events[0]["data"]["blocks"] == []
    assert events[1]["data"]["answer"] == ""
    assert events[-1]["data"]["n_citations"] == 0
