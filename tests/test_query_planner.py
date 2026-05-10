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
    _compute_completeness,
    _validate_and_clean,
    build_confirmation_prompt,
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
        assert result == {"theme": "dat-dai", "procedure": "cap-so-do-lan-dau",
                          "jurisdiction": "tp-hcm", "temporal": "2025-01-01"}

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
        assert result == {"theme": None, "procedure": None,
                          "jurisdiction": None, "temporal": None}


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
# 3. Unit tests cho _compute_completeness
# ---------------------------------------------------------------------------

class TestComputeCompleteness:
    def test_complete_dat_dai(self):
        fields = {"theme": "dat-dai", "procedure": "chuyen-muc-dich-su-dung-dat",
                  "jurisdiction": "tp-hcm", "temporal": None}
        is_complete, missing = _compute_completeness(fields)
        assert is_complete is True
        assert missing == []

    def test_dat_dai_missing_jurisdiction(self):
        fields = {"theme": "dat-dai", "procedure": "chuyen-muc-dich-su-dung-dat",
                  "jurisdiction": None, "temporal": None}
        is_complete, missing = _compute_completeness(fields)
        assert is_complete is False
        assert "jurisdiction" in missing

    def test_missing_theme(self):
        fields = {"theme": None, "procedure": "dang-ky-khai-sinh",
                  "jurisdiction": "toan-quoc", "temporal": None}
        is_complete, missing = _compute_completeness(fields)
        assert is_complete is False
        assert "theme" in missing

    def test_ho_tich_toan_quoc_complete(self):
        fields = {"theme": "ho-tich", "procedure": "dang-ky-khai-sinh",
                  "jurisdiction": "toan-quoc", "temporal": None}
        is_complete, missing = _compute_completeness(fields)
        assert is_complete is True


# ---------------------------------------------------------------------------
# 4. Unit tests cho build_confirmation_prompt
# ---------------------------------------------------------------------------

class TestBuildConfirmationPrompt:
    def test_missing_jurisdiction(self):
        prompt = build_confirmation_prompt(["jurisdiction"])
        assert "tỉnh" in prompt or "thành phố" in prompt or "địa phương" in prompt.lower()

    def test_missing_theme(self):
        prompt = build_confirmation_prompt(["theme"])
        assert "lĩnh vực" in prompt

    def test_missing_procedure(self):
        prompt = build_confirmation_prompt(["procedure"])
        assert "thủ tục" in prompt

    def test_empty_missing(self):
        prompt = build_confirmation_prompt([])
        assert len(prompt) > 0

    def test_multiple_missing(self):
        prompt = build_confirmation_prompt(["theme", "jurisdiction"])
        assert len(prompt) > 0


# ---------------------------------------------------------------------------
# 5. Integration-style tests cho plan_query (mock LLM)
# ---------------------------------------------------------------------------

class TestPlanQuery:
    def test_dod_1_dat_dai_tp_hcm_complete(self):
        """DoD: 'Phí CMĐSDĐ tại TP.HCM' → theme=dat-dai, procedure=chuyen-..., jurisdiction=tp-hcm, is_complete=True"""
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
        assert plan["is_complete"] is True

    def test_dod_2_dat_dai_no_jurisdiction_incomplete(self):
        """DoD: 'Phí chuyển mục đích' (không địa phương) → is_complete=False, missing=[jurisdiction]"""
        client = _mock_client({
            "theme": "dat-dai",
            "procedure": "chuyen-muc-dich-su-dung-dat",
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Phí chuyển mục đích là bao nhiêu?", client)
        assert plan["is_complete"] is False
        assert "jurisdiction" in plan["missing_fields"]

    def test_dod_3_khai_sinh_auto_toan_quoc(self):
        """DoD: 'Đăng ký khai sinh' → theme=ho-tich, jurisdiction tự động toan-quoc, is_complete=True"""
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
        assert plan["is_complete"] is True

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
        assert plan["is_complete"] is True

    def test_cap_so_do_dong_nai(self):
        """Cấp sổ đỏ Đồng Nai: dat-dai + dong-nai + is_complete."""
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
        assert plan["is_complete"] is True

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
        assert plan["is_complete"] is True

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
        assert plan["is_complete"] is True

    def test_unknown_theme_incomplete(self):
        """LLM trả về theme không hợp lệ → bị xóa → is_complete=False."""
        client = _mock_client({
            "theme": "luat-lao-dong",
            "procedure": None,
            "jurisdiction": None,
            "temporal": None,
        })
        plan = plan_query("Quy định về hợp đồng lao động?", client)
        assert plan["theme"] is None
        assert plan["is_complete"] is False
        assert "theme" in plan["missing_fields"]

    def test_llm_invalid_json_graceful(self):
        """LLM trả về JSON rỗng/lỗi → plan với tất cả None, is_complete=False."""
        content = MagicMock()
        content.text = "xin lỗi tôi không hiểu câu hỏi"
        message = MagicMock()
        message.content = [content]
        client = MagicMock()
        client.messages.create.return_value = message

        plan = plan_query("???", client)
        assert plan["theme"] is None
        assert plan["is_complete"] is False
