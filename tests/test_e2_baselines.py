"""Tests cho E2a baselines: closed-book + oracle (không gọi API thật)."""
from unittest.mock import MagicMock

from src.baseline.closed_book import run_closedbook_query
from src.evaluation.oracle import _cit_label, build_oracle_context


def _mock_client(text: str) -> MagicMock:
    content = MagicMock(); content.text = text
    msg = MagicMock(); msg.content = [content]
    client = MagicMock(); client.messages.create.return_value = msg
    return client


class TestClosedBook:
    def test_shape_and_no_context(self):
        client = _mock_client("Hạn mức là 250 m² [Điều 3, Khoản 3, Văn bản qd-69].")
        out = run_closedbook_query("Hạn mức đất ở?", client, cache_dir=None)
        assert out["context_used"] is False
        assert out["context"] == ""
        assert out["top_k_count"] == 0
        assert "answer" in out and "citations" in out
        assert "elapsed_seconds" in out

    def test_no_retrieval_call(self):
        """Closed-book KHÔNG được đụng Neo4j/Qdrant — chỉ 1 call LLM."""
        client = _mock_client("Tôi không chắc chắn.")
        run_closedbook_query("câu hỏi", client, cache_dir=None)
        assert client.messages.create.call_count == 1
        # System prompt phải là closed-book (không có context tra cứu)
        kwargs = client.messages.create.call_args.kwargs
        sys_text = kwargs["system"][0]["text"]
        assert "KHÔNG được cung cấp tài liệu" in sys_text


class TestOracleContext:
    def test_cit_label_dieu(self):
        assert _cit_label({"dieu": "3", "khoan": "3", "van_ban": "qd-69"}) \
            == "Điều 3, Khoản 3 (qd-69)"

    def test_cit_label_phu_luc(self):
        assert _cit_label({"dieu": "1B", "khoan": "1", "van_ban": "nq",
                           "loai": "phu_luc"}) == "Phụ lục 1B, Khoản 1 (nq)"

    def test_cit_label_phu_luc_default(self):
        assert _cit_label({"dieu": "_default", "van_ban": "nq", "loai": "phu_luc"}) \
            == "Phụ lục (nq)"

    def test_build_context_empty_for_no_citations(self):
        assert build_oracle_context([], {}) == ""

    def test_build_context_labels_and_text(self):
        idx = {"vb": [{"dieu": "3", "khoan": "1", "diem": None, "pl": None,
                       "text": "Nội dung khoản 1."}]}
        ctx = build_oracle_context([{"dieu": "3", "khoan": "1", "van_ban": "vb"}], idx)
        assert "--- Điều 3, Khoản 1 (vb) ---" in ctx
        assert "Nội dung khoản 1." in ctx
