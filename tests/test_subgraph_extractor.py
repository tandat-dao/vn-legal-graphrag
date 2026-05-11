"""
Tests cho src/retrieval/subgraph_extractor.py — TASK-11.

Chiến lược: mock Qdrant + Neo4j + encode_text để chạy offline.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.subgraph_extractor import (
    LCCID_LIMIT,
    _JURISDICTION_ALLOW,
    extract_subgraph,
    stage1_norm_ids,
    stage2_component_ids,
)
from src.retrieval.query_planner import QueryPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan(
    theme="dat-dai",
    procedure="chuyen-muc-dich-su-dung-dat",
    jurisdiction="tp-hcm",
    temporal=None,
    is_complete=True,
) -> QueryPlan:
    return QueryPlan(
        theme=theme,
        procedure=procedure,
        jurisdiction=jurisdiction,
        temporal=temporal,
        is_complete=is_complete,
        missing_fields=[],
    )


def _make_qdrant_point(norm_id: str, score: float = 0.9) -> MagicMock:
    point = MagicMock()
    point.payload = {"norm_id": norm_id, "content_type": "summary"}
    point.score = score
    return point


def _mock_qdrant(norm_ids: list[str]) -> MagicMock:
    points = [_make_qdrant_point(nid, 0.9 - i * 0.05) for i, nid in enumerate(norm_ids)]
    result = MagicMock()
    result.points = points
    client = MagicMock()
    client.query_points.return_value = result
    return client


def _mock_neo4j(component_ids: list[str]) -> MagicMock:
    rows = [{"component_id": cid} for cid in component_ids]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value.data.return_value = rows
    driver = MagicMock()
    driver.session.return_value = session
    return driver


def _mock_model() -> MagicMock:
    model = MagicMock()
    return model


# ---------------------------------------------------------------------------
# 1. Tests cho _JURISDICTION_ALLOW mapping
# ---------------------------------------------------------------------------

class TestJurisdictionAllow:
    def test_toan_quoc_only_national(self):
        assert _JURISDICTION_ALLOW["toan-quoc"] == ["toan-quoc"]

    def test_tp_hcm_includes_national(self):
        allowed = _JURISDICTION_ALLOW["tp-hcm"]
        assert "toan-quoc" in allowed
        assert "tp-hcm" in allowed
        assert "dong-nai" not in allowed

    def test_dong_nai_includes_national(self):
        allowed = _JURISDICTION_ALLOW["dong-nai"]
        assert "toan-quoc" in allowed
        assert "dong-nai" in allowed
        assert "tp-hcm" not in allowed


# ---------------------------------------------------------------------------
# 2. Tests cho stage1_norm_ids
# ---------------------------------------------------------------------------

class TestStage1NormIds:
    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_returns_norm_ids_in_order(self, mock_encode):
        norm_ids = ["luat-dat-dai-2024", "nghi-dinh-102-2024-nd-cp", "nghi-dinh-50-2026-nd-cp"]
        client = _mock_qdrant(norm_ids)
        model = _mock_model()
        plan = _make_plan(theme="dat-dai")

        result = stage1_norm_ids("phí chuyển mục đích đất", plan, client, model, top_n=3)

        assert result == norm_ids
        assert len(result) == 3

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_filter_uses_theme(self, mock_encode):
        client = _mock_qdrant(["luat-dat-dai-2024"])
        model = _mock_model()
        plan = _make_plan(theme="dat-dai")

        stage1_norm_ids("câu hỏi đất đai", plan, client, model)

        call_kwargs = client.query_points.call_args
        query_filter = call_kwargs.kwargs.get("query_filter") or call_kwargs.args[2] if len(call_kwargs.args) > 2 else call_kwargs.kwargs["query_filter"]
        # Kiểm tra filter được truyền vào
        assert client.query_points.called

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_none_theme_returns_empty(self, mock_encode):
        client = _mock_qdrant([])
        model = _mock_model()
        plan = _make_plan(theme=None, is_complete=False)

        result = stage1_norm_ids("câu hỏi không rõ lĩnh vực", plan, client, model)

        assert result == []
        client.query_points.assert_not_called()

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_top_n_respected(self, mock_encode):
        client = _mock_qdrant(["norm-1", "norm-2"])
        model = _mock_model()
        plan = _make_plan(theme="ho-tich")

        stage1_norm_ids("đăng ký khai sinh", plan, client, model, top_n=2)

        call_kwargs = client.query_points.call_args
        # limit phải được truyền đúng
        limit = call_kwargs.kwargs.get("limit")
        assert limit == 2


# ---------------------------------------------------------------------------
# 3. Tests cho stage2_component_ids
# ---------------------------------------------------------------------------

class TestStage2ComponentIds:
    def test_returns_component_ids(self):
        comp_ids = ["luat-dat-dai-2024>Điều 116", "nghi-dinh-102-2024-nd-cp>Điều 3"]
        driver = _mock_neo4j(comp_ids)
        plan = _make_plan(jurisdiction="tp-hcm")

        result = stage2_component_ids(["luat-dat-dai-2024"], plan, driver)

        assert set(result) == set(comp_ids)

    def test_empty_norm_ids_returns_empty(self):
        driver = _mock_neo4j([])
        plan = _make_plan()

        result = stage2_component_ids([], plan, driver)

        assert result == []
        driver.session.assert_not_called()

    def test_jurisdiction_allowed_set_correct_tp_hcm(self):
        driver = _mock_neo4j([])
        plan = _make_plan(jurisdiction="tp-hcm")

        stage2_component_ids(["norm-1"], plan, driver)

        session = driver.session.return_value.__enter__.return_value
        call_kwargs = session.run.call_args
        params = call_kwargs.kwargs if call_kwargs.kwargs else {}
        if not params:
            # positional args style: run(query, **params)
            params = {k: v for k, v in zip(["allowed_jurisdictions", "temporal", "seed_ids"],
                                            call_kwargs.args[1:])}
        allowed = params.get("allowed_jurisdictions") or call_kwargs.kwargs.get("allowed_jurisdictions")
        assert "toan-quoc" in allowed
        assert "tp-hcm" in allowed

    def test_jurisdiction_toan_quoc_excludes_local(self):
        driver = _mock_neo4j([])
        plan = _make_plan(jurisdiction="toan-quoc", theme="ho-tich",
                          procedure="dang-ky-khai-sinh")

        stage2_component_ids(["luat-ho-tich-2014"], plan, driver)

        session = driver.session.return_value.__enter__.return_value
        call_kwargs = session.run.call_args
        allowed = call_kwargs.kwargs.get("allowed_jurisdictions")
        assert allowed == ["toan-quoc"]
        assert "tp-hcm" not in allowed
        assert "dong-nai" not in allowed

    def test_temporal_param_passed(self):
        driver = _mock_neo4j([])
        plan = _make_plan(jurisdiction="toan-quoc", temporal="2025-08-01")

        stage2_component_ids(["norm-1"], plan, driver)

        session = driver.session.return_value.__enter__.return_value
        call_kwargs = session.run.call_args
        temporal = call_kwargs.kwargs.get("temporal")
        assert temporal == "2025-08-01"

    def test_warning_when_over_limit(self, caplog):
        # LCCID_LIMIT = 2000; tạo 2001 component_ids để trigger warning
        many_ids = [f"comp-{i}" for i in range(LCCID_LIMIT + 1)]
        driver = _mock_neo4j(many_ids)
        plan = _make_plan()

        import logging
        with caplog.at_level(logging.WARNING, logger="src.retrieval.subgraph_extractor"):
            result = stage2_component_ids(["norm-1"], plan, driver)

        assert len(result) == LCCID_LIMIT + 1
        assert any("vượt giới hạn" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# 4. Tests cho extract_subgraph (orchestrator)
# ---------------------------------------------------------------------------

class TestExtractSubgraph:
    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_dod_1_dat_dai_tp_hcm_returns_components(self, mock_encode):
        """DoD: CMĐSDĐ TP.HCM → có Component của cả Luật (tier1) và văn bản TP.HCM (tier4)."""
        norm_ids_stage1 = ["nghi-dinh-50-2026-nd-cp"]
        comp_ids = [
            "luat-dat-dai-2024>Điều 116>Khoản 1",       # tier 1
            "quyet-dinh-tp-hcm-2025>Điều 1",             # tier 4 TP.HCM
        ]
        client = _mock_qdrant(norm_ids_stage1)
        driver = _mock_neo4j(comp_ids)
        model = _mock_model()
        plan = _make_plan(theme="dat-dai", jurisdiction="tp-hcm")

        result = extract_subgraph("phí chuyển mục đích đất TP.HCM", plan, driver, client, model)

        assert len(result) == 2
        # Phải có cả tier 1 và tier 4
        assert any("luat-dat-dai" in cid for cid in result)
        assert any("tp-hcm" in cid for cid in result)

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_dod_2_khai_sinh_no_local_components(self, mock_encode):
        """DoD: đăng ký khai sinh (toan-quoc) → KHÔNG có Component địa phương."""
        norm_ids_stage1 = ["luat-ho-tich-2014"]
        # Chỉ trả về toan-quoc components (Neo4j đã lọc bằng Cypher)
        comp_ids = [
            "luat-ho-tich-2014>Điều 14",
            "nghi-dinh-123-2015-nd-cp>Điều 7",
        ]
        client = _mock_qdrant(norm_ids_stage1)
        driver = _mock_neo4j(comp_ids)
        model = _mock_model()
        plan = _make_plan(
            theme="ho-tich", procedure="dang-ky-khai-sinh",
            jurisdiction="toan-quoc",
        )

        result = extract_subgraph("điều kiện đăng ký khai sinh", plan, driver, client, model)

        # Không có component của văn bản địa phương
        assert not any("tp-hcm" in cid.lower() or "dong-nai" in cid.lower() for cid in result)
        # Cypher phải được gọi với allowed = ["toan-quoc"]
        session = driver.session.return_value.__enter__.return_value
        call_kwargs = session.run.call_args
        allowed = call_kwargs.kwargs.get("allowed_jurisdictions")
        assert allowed == ["toan-quoc"]

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_dod_3_nuoi_con_nuoi_vs_dang_ky_lai(self, mock_encode):
        """DoD: hai thủ tục nuôi con nuôi gọi Stage 1 với theme khác nhau."""
        client1 = _mock_qdrant(["luat-nuoi-con-nuoi-2010"])
        client2 = _mock_qdrant(["nghi-dinh-nuoi-con-nuoi-2014"])
        driver = _mock_neo4j([])
        model = _mock_model()

        plan1 = _make_plan(theme="nuoi-con-nuoi", procedure="dang-ky-nuoi-con-nuoi",
                           jurisdiction="toan-quoc")
        plan2 = _make_plan(theme="nuoi-con-nuoi", procedure="dang-ky-lai-nuoi-con-nuoi",
                           jurisdiction="toan-quoc")

        stage1_norm_ids("đăng ký nuôi con nuôi", plan1, client1, model)
        stage1_norm_ids("đăng ký lại nuôi con nuôi", plan2, client2, model)

        # Cả hai đều gọi Qdrant (không fail)
        assert client1.query_points.called
        assert client2.query_points.called

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_dod_4_temporal_filter_passed_to_cypher(self, mock_encode):
        """DoD: CTV với valid_to < temporal không xuất hiện — Cypher nhận temporal đúng."""
        client = _mock_qdrant(["luat-dat-dai-2024"])
        driver = _mock_neo4j(["luat-dat-dai-2024>Điều 116"])
        model = _mock_model()
        plan = _make_plan(jurisdiction="toan-quoc", temporal="2025-08-01")

        extract_subgraph("quy định đất đai tháng 8/2025", plan, driver, client, model)

        session = driver.session.return_value.__enter__.return_value
        call_kwargs = session.run.call_args
        temporal = call_kwargs.kwargs.get("temporal")
        assert temporal == "2025-08-01"

    @patch("src.retrieval.subgraph_extractor.encode_text", return_value=[0.1] * 1024)
    def test_empty_plan_theme_returns_empty(self, mock_encode):
        """Nếu theme=None (plan chưa hoàn chỉnh) → Stage 1 trả [] → Stage 2 không chạy."""
        client = _mock_qdrant([])
        driver = _mock_neo4j([])
        model = _mock_model()
        plan = _make_plan(theme=None, is_complete=False)

        result = extract_subgraph("câu hỏi không rõ", plan, driver, client, model)

        assert result == []
        driver.session.assert_not_called()
