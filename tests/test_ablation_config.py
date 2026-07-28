"""Tests cho ablation config (E1) — cắt cạnh graph, double dissociation."""
import pytest

from src.retrieval.ablation_config import ABLATIONS, FULL, get_ablation
from src.retrieval.subgraph_extractor import _build_stage2_cypher


class TestAblationRegistry:
    def test_full_default(self):
        assert get_ablation(None) is FULL
        assert get_ablation("full").name == "full"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            get_ablation("no-such-ablation")

    def test_all_registered(self):
        for name in ("no-theme", "no-jurisdiction", "no-implements",
                     "no-amends", "no-temporal", "no-traversal", "dense-only"):
            assert name in ABLATIONS
            assert get_ablation(name).name == name


class TestTraversalRels:
    def test_full_both_edges(self):
        assert get_ablation("full").traversal_rels == ["IMPLEMENTS", "AMENDS"]

    def test_no_implements_keeps_amends(self):
        assert get_ablation("no-implements").traversal_rels == ["AMENDS"]

    def test_no_amends_keeps_implements(self):
        assert get_ablation("no-amends").traversal_rels == ["IMPLEMENTS"]

    def test_no_traversal_empty(self):
        assert get_ablation("no-traversal").traversal_rels == []

    def test_dense_only_empty(self):
        assert get_ablation("dense-only").traversal_rels == []


class TestGapTarget:
    def test_gap_mapping(self):
        assert get_ablation("no-theme").gap_target == "gap1"
        assert get_ablation("no-jurisdiction").gap_target == "gap2"
        assert get_ablation("no-implements").gap_target == "gap3"
        assert get_ablation("no-amends").gap_target == "gap4"
        assert get_ablation("no-temporal").gap_target == "gap4"
        assert get_ablation("full").gap_target is None


class TestCypherBuilder:
    def test_full_has_both(self):
        c = _build_stage2_cypher(["IMPLEMENTS", "AMENDS"])
        assert "IMPLEMENTS|AMENDS*1..4" in c

    def test_no_implements_only_amends(self):
        c = _build_stage2_cypher(["AMENDS"])
        assert "[:AMENDS*1..4]" in c
        assert "IMPLEMENTS" not in c

    def test_empty_no_expansion(self):
        c = _build_stage2_cypher([])
        # Không có mệnh đề mở rộng traversal → chỉ seed
        assert "*1..4" not in c
        assert "related.id = seed_id" in c

    def test_all_variants_return_norm_and_component(self):
        for rels in ([], ["AMENDS"], ["IMPLEMENTS"], ["IMPLEMENTS", "AMENDS"]):
            c = _build_stage2_cypher(rels)
            assert "RETURN DISTINCT related.id AS norm_id, c.id AS component_id" in c
