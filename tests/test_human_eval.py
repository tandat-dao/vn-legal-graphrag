"""Tests cho E2c human_eval — trọng tâm: toán kappa (cổng validation)."""
import math

from src.evaluation.human_eval import (
    build_instances,
    cohen_kappa,
    interpret_kappa,
    kappa_report,
    pairwise_kappa,
    quadratic_weighted_kappa,
    select_sample,
)


class TestCohenKappa:
    def test_perfect_agreement(self):
        assert cohen_kappa([0, 1, 1, 0], [0, 1, 1, 0]) == 1.0

    def test_total_disagreement_binary(self):
        # đảo hoàn toàn → kappa âm mạnh
        assert cohen_kappa([0, 0, 1, 1], [1, 1, 0, 0]) < 0

    def test_empty(self):
        assert math.isnan(cohen_kappa([], []))


class TestQWK:
    def test_perfect(self):
        assert quadratic_weighted_kappa([1, 3, 5, 2], [1, 3, 5, 2]) == 1.0

    def test_reversed_is_negative(self):
        assert quadratic_weighted_kappa([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) < -0.5

    def test_close_beats_far(self):
        # lệch nhẹ (±1) cho kappa cao hơn lệch xa (±4) — đặc trưng QWK
        near = quadratic_weighted_kappa([1, 2, 3, 4, 5], [2, 3, 4, 5, 4])
        far = quadratic_weighted_kappa([1, 2, 3, 4, 5], [5, 1, 5, 1, 1])
        assert near > far


class TestPairwiseAndReport:
    def test_three_raters_mean(self):
        ratings = {
            "r1": {"i1": 5, "i2": 1, "i3": 3},
            "r2": {"i1": 5, "i2": 1, "i3": 3},
            "r3": {"i1": 4, "i2": 2, "i3": 3},
        }
        res = pairwise_kappa(ratings, ordinal=True)
        assert res["n_raters"] == 3
        assert len(res["pairs"]) == 3  # C(3,2)
        assert res["pairs"]["r1↔r2"] == 1.0

    def test_only_common_instances(self):
        ratings = {"a": {"i1": 5, "i2": 1}, "b": {"i1": 5}}  # chỉ i1 chung
        res = pairwise_kappa(ratings, ordinal=True)
        assert "a↔b" in res["pairs"]

    def test_kappa_report_per_dim(self):
        scores = {
            "r1": {"V1#1": {"B1_clarity": 5, "B2_useful": 4}},
            "r2": {"V1#1": {"B1_clarity": 5, "B2_useful": 4}},
        }
        rep = kappa_report(scores, ["B1_clarity", "B2_useful"])
        assert rep["B1_clarity"]["mean_kappa"] == 1.0
        assert "interpret" in rep["B1_clarity"]


class TestInterpret:
    def test_bands(self):
        assert interpret_kappa(float("nan")) == "N/A"
        assert "thấp" in interpret_kappa(0.3)
        assert "cao" in interpret_kappa(0.7)
        assert "rất cao" in interpret_kappa(0.9)


class TestSampleAndInstances:
    def _fake(self, n=12):
        gaps = ["gap1", "gap2", "gap3", "gap4"]
        items = [{"id": f"V{i:03d}", "question": f"q{i}", "gap_type": gaps[i % 4],
                  "answer": f"ans{i}"} for i in range(n)]
        return {"graphrag": items, "baseline": [dict(x, answer=f"b{x['id']}") for x in items]}

    def test_sample_deterministic(self):
        by = self._fake()
        s1 = select_sample(by, 8, seed=42)
        s2 = select_sample(by, 8, seed=42)
        assert s1 == s2  # seed cố định → tái lập

    def test_sample_stratified(self):
        by = self._fake()
        sample = select_sample(by, 8, seed=42)
        gaps = {next(it["gap_type"] for it in by["graphrag"] if it["id"] == qid)
                for qid in sample}
        assert len(gaps) == 4  # phủ đủ 4 gap

    def test_instances_blind_and_keyed(self):
        by = self._fake(4)
        sample = select_sample(by, 4, seed=1)
        instances, key = build_instances(sample, by, seed=1)
        # mỗi câu × 2 hệ = 2 instance; key ánh xạ về system thật
        assert len(instances) == len(sample) * 2
        for ins in instances:
            assert ins["iid"] in key
            assert key[ins["iid"]]["system"] in ("graphrag", "baseline")
        # instance KHÔNG lộ system (chấm mù)
        assert all("system" not in ins for ins in instances)
