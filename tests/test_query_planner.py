"""
Tests cho src/retrieval/query_planner.py — TASK-10.

Chiến lược: mock _call_llm để test logic nội bộ mà không cần Anthropic API.
Mỗi test case cung cấp raw LLM output và verify kết quả sau validate + rules.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.query_planner import (
    QueryPlan,
    _apply_jurisdiction_rules,
    _validate_and_clean,
    _validate_temporal_intent,
    plan_query,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mock_client(llm_response: dict) -> MagicMock:
    """Trả về Anthropic client mock với response JSON cố định."""
    content = MagicMock()
    content.text = json.dumps(llm_response, ensure_ascii=False)
    message = MagicMock()
    message.content = [content]
    client = MagicMock()
    client.messages.create.return_value = message
    return client


# ---------------------------------------------------------------------------
# 1. Unit tests cho _validate_and_clean
# ---------------------------------------------------------------------------

class TestValidateAndClean:
    def test_valid_all_fields(self):
        raw = {"theme": "dat-dai", "procedure": "cap-so-do-lan-dau",
               "jurisdiction": "tp-hcm", "temporal": "2025-01-01"}
        result = _validate_and_clean(raw)
        assert result["theme"] == "dat-dai"
        assert result["procedure"] == "cap-so-do-lan-dau"
        assert result["jurisdiction"] == "tp-hcm"
        assert result["temporal"] == "2025-01-01"
        assert result["temporal_intent"]["has_temporal_context"] is False

    def test_invalid_theme_cleared(self):
        raw = {"theme": "luat-hinh-su", "procedure": None,
               "jurisdiction": None, "temporal": None}
        result = _validate_and_clean(raw)
        assert result["theme"] is None

    def test_invalid_jurisdiction_cleared(self):
        raw = {"theme": "dat-dai", "procedure": None,
               "jurisdiction": "ha-noi", "temporal": None}
        result = _validate_and_clean(raw)
        assert result["jurisdiction"] is None

    def test_temporal_non_string_cleared(self):
        raw = {"theme": "ho-tich", "procedure": "dang-ky-khai-sinh",
               "jurisdiction": "toan-quoc", "temporal": 2025}
        result = _validate_and_clean(raw)
        assert result["temporal"] is None

    def test_empty_raw(self):
        result = _validate_and_clean({})
        assert result["theme"] is None
        assert result["procedure"] is None
        assert result["jurisdiction"] is None
        assert result["temporal"] is None
        # temporal_intent default rỗng
        assert result["temporal_intent"] == {
            "has_temporal_context": False,
            "temporal_anchor": None,
            "case_status": None,
            "reasoning": "",
        }


# ---------------------------------------------------------------------------
# 2. Unit tests cho _apply_jurisdiction_rules
# ---------------------------------------------------------------------------

class TestApplyJurisdictionRules:
    def test_ho_tich_auto_toan_quoc(self):
        fields = {"theme": "ho-tich", "procedure": "dang-ky-khai-sinh",
                  "jurisdiction": None, "temporal": None}
        result = _apply_jurisdiction_rules(fields)
        assert result["jurisdiction"] == "toan-quoc"

    def test_nuoi_con_nuoi_auto_toan_quoc(self):
        fields = {"theme": "nuoi-con-nuoi", "procedure": "dang-ky-nuoi-con-nuoi",
                  "jurisdiction": None, "temporal": None}
        result = _apply_jurisdiction_rules(fields)
        assert result["jurisdiction"] == "toan-quoc"

    def test_dat_dai_no_auto_jurisdiction(self):
        fields = {"theme": "dat-dai", "procedure": "cap-so-do-lan-dau",
                  "jurisdiction": None, "temporal": None}
        result = _apply_jurisdiction_rules(fields)
        assert result["jurisdiction"] is None

    def test_existing_jurisdiction_not_overwritten(self):
        fields = {"theme": "ho-tich", "procedure": "dang-ky-khai-sinh",
                  "jurisdiction": "tp-hcm", "temporal": None}
        result = _apply_jurisdiction_rules(fields)
        assert result["jurisdiction"] == "tp-hcm"


# ---------------------------------------------------------------------------
# 3. Integration-style tests cho plan_query (mock LLM)
# ---------------------------------------------------------------------------

class TestPlanQuery:
    def test_dod_1_dat_dai_tp_hcm(self):
        """DoD: 'Phí CMĐSDĐ tại TP.HCM' → theme=dat-dai, procedure=chuyen-..., jurisdiction=tp-hcm"""
        client = _mock_client({
            "theme": "dat-dai",
            "procedure": "chuyen-muc-dich-su-dung-dat",
            "jurisdiction": "tp-hcm",
            "temporal": None,
        })
        plan = plan_query("Phí chuyển mục đích sử dụng đất tại TP.HCM là bao nhiêu?", client)
        assert plan["theme"] == "dat-dai"
        assert plan["procedure"] == "chuyen-muc-dich-su-dung-dat"
        assert plan["jurisdiction"] == "tp-hcm"

    def test_dod_2_dat_dai_no_jurisdiction_stays_none(self):
        """DoD: 'Phí chuyển mục đích' (không địa phương) → đất đai giữ jurisdiction=None."""
        client = _mock_client({
            "theme": "dat-dai",
            "procedure": "chuyen-muc-dich-su-dung-dat",
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Phí chuyển mục đích là bao nhiêu?", client)
        assert plan["theme"] == "dat-dai"
        assert plan["jurisdiction"] is None

    def test_dod_3_khai_sinh_auto_toan_quoc(self):
        """DoD: 'Đăng ký khai sinh' → theme=ho-tich, jurisdiction tự động toan-quoc"""
        client = _mock_client({
            "theme": "ho-tich",
            "procedure": "dang-ky-khai-sinh",
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Điều kiện đăng ký khai sinh là gì?", client)
        assert plan["theme"] == "ho-tich"
        assert plan["procedure"] == "dang-ky-khai-sinh"
        assert plan["jurisdiction"] == "toan-quoc"

    def test_dod_4_nuoi_con_nuoi_auto_toan_quoc(self):
        """Hộ tịch Nuôi con nuôi: tự động toan-quoc."""
        client = _mock_client({
            "theme": "nuoi-con-nuoi",
            "procedure": "dang-ky-nuoi-con-nuoi",
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Hồ sơ đăng ký nuôi con nuôi trong nước gồm gì?", client)
        assert plan["jurisdiction"] == "toan-quoc"

    def test_cap_so_do_dong_nai(self):
        """Cấp sổ đỏ Đồng Nai: dat-dai + dong-nai."""
        client = _mock_client({
            "theme": "dat-dai",
            "procedure": "cap-so-do-lan-dau",
            "jurisdiction": "dong-nai",
            "temporal": None,
        })
        plan = plan_query("Thủ tục cấp sổ đỏ lần đầu ở Đồng Nai?", client)
        assert plan["theme"] == "dat-dai"
        assert plan["procedure"] == "cap-so-do-lan-dau"
        assert plan["jurisdiction"] == "dong-nai"

    def test_dang_ky_lai_nuoi_con_nuoi(self):
        """Đăng ký LẠI nuôi con nuôi: phân biệt với đăng ký mới."""
        client = _mock_client({
            "theme": "nuoi-con-nuoi",
            "procedure": "dang-ky-lai-nuoi-con-nuoi",
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Đăng ký lại nuôi con nuôi cần giấy tờ gì?", client)
        assert plan["procedure"] == "dang-ky-lai-nuoi-con-nuoi"
        assert plan["jurisdiction"] == "toan-quoc"

    def test_cap_ban_sao_ho_tich(self):
        """Cấp bản sao trích lục hộ tịch: ho-tich + toan-quoc."""
        client = _mock_client({
            "theme": "ho-tich",
            "procedure": "cap-ban-sao-trich-luc-ho-tich",
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Xin cấp bản sao trích lục khai sinh mất phí không?", client)
        assert plan["theme"] == "ho-tich"
        assert plan["procedure"] == "cap-ban-sao-trich-luc-ho-tich"
        assert plan["jurisdiction"] == "toan-quoc"

    def test_temporal_field_preserved(self):
        """Trường temporal được giữ nguyên khi LLM trả về."""
        client = _mock_client({
            "theme": "dat-dai",
            "procedure": "chuyen-muc-dich-su-dung-dat",
            "jurisdiction": "tp-hcm",
            "temporal": "2025-08-01",
        })
        plan = plan_query("Phí CMĐSDĐ tại TP.HCM theo quy định tháng 8/2025?", client)
        assert plan["temporal"] == "2025-08-01"

    def test_unknown_theme_cleared(self):
        """LLM trả về theme không hợp lệ → bị xóa về None."""
        client = _mock_client({
            "theme": "luat-lao-dong",
            "procedure": None,
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Quy định về hợp đồng lao động?", client)
        assert plan["theme"] is None

    def test_llm_invalid_json_graceful(self):
        """LLM trả về JSON rỗng/lỗi → plan với tất cả None (graceful)."""
        content = MagicMock()
        content.text = "xin lỗi tôi không hiểu câu hỏi"
        message = MagicMock()
        message.content = [content]
        client = MagicMock()
        client.messages.create.return_value = message

        plan = plan_query("???", client)
        assert plan["theme"] is None


# ---------------------------------------------------------------------------
# 5. Unit tests cho _validate_temporal_intent (B2 — Temporal Layer)
# ---------------------------------------------------------------------------

class TestValidateTemporalIntent:
    def test_default_when_input_none(self):
        result = _validate_temporal_intent(None)
        assert result["has_temporal_context"] is False
        assert result["temporal_anchor"] is None
        assert result["case_status"] is None

    def test_default_when_input_not_dict(self):
        assert _validate_temporal_intent("not a dict")["has_temporal_context"] is False
        assert _validate_temporal_intent([1, 2, 3])["has_temporal_context"] is False

    def test_full_temporal_context(self):
        raw = {
            "has_temporal_context": True,
            "temporal_anchor": "2020-06",
            "case_status": "do-dang",
            "reasoning": "Hồ sơ nộp 2020 chưa có quyết định",
        }
        result = _validate_temporal_intent(raw)
        assert result["has_temporal_context"] is True
        assert result["temporal_anchor"] == "2020-06"
        assert result["case_status"] == "do-dang"

    def test_invalid_case_status_cleared(self):
        raw = {
            "has_temporal_context": True,
            "temporal_anchor": "2020-06",
            "case_status": "linh-tinh",  # không hợp lệ
            "reasoning": "...",
        }
        result = _validate_temporal_intent(raw)
        assert result["case_status"] is None

    def test_empty_anchor_normalized_to_none(self):
        raw = {
            "has_temporal_context": True,
            "temporal_anchor": "   ",  # whitespace
            "case_status": None,
            "reasoning": "test",
        }
        result = _validate_temporal_intent(raw)
        assert result["temporal_anchor"] is None

    def test_has_ctx_false_clears_fields(self):
        """Khi LLM bảo has_temporal_context=False, anchor/case_status forced None."""
        raw = {
            "has_temporal_context": False,
            "temporal_anchor": "2020",  # nên bị xoá
            "case_status": "do-dang",   # nên bị xoá
            "reasoning": "Câu hỏi hiện hành",
        }
        result = _validate_temporal_intent(raw)
        assert result["temporal_anchor"] is None
        assert result["case_status"] is None
        assert result["reasoning"] == "Câu hỏi hiện hành"

    def test_validate_and_clean_includes_temporal_intent(self):
        """_validate_and_clean trả về dict có temporal_intent key."""
        raw = {
            "theme": "dat-dai", "procedure": None, "jurisdiction": "tp-hcm",
            "temporal": None,
            "temporal_intent": {
                "has_temporal_context": True,
                "temporal_anchor": "luat-cu",
                "case_status": "moi",
                "reasoning": "Mua đất luật cũ giờ mới làm thủ tục",
            },
        }
        result = _validate_and_clean(raw)
        assert result["temporal_intent"]["has_temporal_context"] is True
        assert result["temporal_intent"]["temporal_anchor"] == "luat-cu"
        assert result["temporal_intent"]["case_status"] == "moi"
