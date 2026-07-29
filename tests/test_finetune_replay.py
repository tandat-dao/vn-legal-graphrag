"""Test cho finetune/replay.py (TASK-FT-02).

Toàn bộ test dùng MockBackend → không cần weights, không cần GPU, không cần
Neo4j/Qdrant, không gọi API. Mô hình cục bộ chưa chốt (FT-03) nhưng đường đi
schema phải verify được ngay.

Đặt ở tests/ theo tiền lệ ui/ (module ngoài src/, test vẫn nằm ở tests/).
"""
from __future__ import annotations

import json
import math

import pytest

from finetune import replay
from src.evaluation.metrics import aggregate


# ---------------------------------------------------------------------------
# Fixtures — item nguồn tối giản, đúng schema của results_*.json
# ---------------------------------------------------------------------------

def _src_item(qid="V001", gap_type="gap2", gt=None, context="--- [Tier 1 | Hiệu lực: "
              "2024-01-01] Điều 3, Khoản 3. (luat-x-2024) ---\nNội dung.",
              top_k=20, answer="bất kỳ") -> dict:
    return {
        "id": qid,
        "question": "Câu hỏi thử?",
        "gap_type": gap_type,
        "theme": "dat-dai",
        "jurisdiction": "tp-hcm",
        "difficulty": "easy",
        "system": "graphrag",
        "answer": answer,
        "pred_citations": [],
        "ground_truth_citations": [{"dieu": "3", "khoan": "3", "van_ban": "luat-x-2024"}]
        if gt is None else gt,
        "citation_score": {}, "citation_score_dieu": {}, "norm_recall": 0.0,
        "negative_correct": None, "faithfulness": None, "elapsed_seconds": 0.0,
        "context_used": bool(context), "top_k_count": top_k, "context": context,
        "verifier": None,
    }


GP = replay.GenParams()


def _run(src, mode="general", spec="", n_shot=0, gp=None, n_ctx=16384):
    backend = replay.MockBackend(spec)
    return replay.replay_item(src, mode, backend, n_shot, gp or GP, n_ctx)


# ---------------------------------------------------------------------------
# INCLUDE_SCHEMA_B
# ---------------------------------------------------------------------------

def test_include_schema_b_bi_ep_false():
    """Đọc lúc import module → replay.py phải set env TRƯỚC khi import."""
    from src.retrieval import context_assembler
    assert context_assembler.INCLUDE_SCHEMA_B is False


def test_prompt_khong_chua_section_schema_b():
    src = _src_item()
    msgs = replay.build_chat_messages(src["question"], src["context"], "general", 0)
    assert "## TRẢ LỜI" not in msgs[0]["content"]
    assert "## CẢNH BÁO LEX" not in msgs[0]["content"]


# ---------------------------------------------------------------------------
# build_messages, mode, few-shot
# ---------------------------------------------------------------------------

def test_dung_build_messages_khong_phai_build_prompt():
    """system và user phải TÁCH RIÊNG (build_messages), không nối liền (build_prompt)."""
    src = _src_item()
    msgs = replay.build_chat_messages(src["question"], src["context"], "general", 0)
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[1]["content"].startswith("CONTEXT:")
    assert "CÂU HỎI: Câu hỏi thử?" in msgs[1]["content"]
    # system KHÔNG được chứa context (dấu hiệu đã nối nhầm kiểu build_prompt)
    assert "CONTEXT:" not in msgs[0]["content"]


def test_mode_irac_doi_system_prompt():
    src = _src_item()
    g = replay.build_chat_messages(src["question"], src["context"], "general", 0)[0]["content"]
    i = replay.build_chat_messages(src["question"], src["context"], "irac", 0)[0]["content"]
    assert g != i
    assert "### Vấn đề" in i and "### Vấn đề" not in g


@pytest.mark.parametrize("n_shot,n_msgs", [(0, 2), (1, 4), (2, 6)])
def test_n_shot_chen_dung_so_luot(n_shot, n_msgs):
    src = _src_item()
    msgs = replay.build_chat_messages(src["question"], src["context"], "general", n_shot)
    assert len(msgs) == n_msgs
    assert msgs[0]["role"] == "system" and msgs[-1]["role"] == "user"


def test_fewshot_dung_dung_cu_phap_trich_dan_dich():
    """Ví dụ minh hoạ phải parse được bằng chính parser thật, nếu không là dạy sai."""
    from src.retrieval.answer_generator import parse_citations
    for _user, assistant in replay._FEWSHOT:
        cits = parse_citations(assistant)
        assert len(cits) == 1, f"ví dụ few-shot không parse ra đúng 1 citation: {assistant}"
        assert cits[0]["van_ban"] and cits[0]["dieu"]


def test_fewshot_khong_ro_ri_slug_cua_corpus():
    """Slug trong ví dụ phải là slug GIẢ — không được trùng văn bản thật."""
    for _user, assistant in replay._FEWSHOT:
        assert "vi-du" in assistant


# ---------------------------------------------------------------------------
# 10 câu hằng số (§9.1)
# ---------------------------------------------------------------------------

def test_cau_context_rong_sao_chep_hang_so_khong_goi_mo_hinh():
    class ExplodingBackend(replay.Backend):
        name = "explode"

        def generate(self, messages, gp):
            raise AssertionError("KHÔNG được gọi mô hình cho câu top_k_count=0")

    src = _src_item(qid="V106", gap_type="negative", gt=[], context="",
                    top_k=0, answer=replay.FROZEN_ANSWER)
    item = replay.replay_item(src, "general", ExplodingBackend(), 0, GP)
    assert item["answer"] == replay.FROZEN_ANSWER
    assert item["frozen_copy"] is True
    assert item["pred_citations"] == []
    assert item["negative_correct"] is True   # từ chối đúng
    assert item["elapsed_seconds"] == 0.0
    assert item["hit_token_cap"] is False


def test_hang_so_sai_thi_bao_loi_khong_am_tham_chay_tiep():
    src = _src_item(qid="V106", gap_type="negative", gt=[], context="",
                    top_k=0, answer="một chuỗi khác")
    with pytest.raises(AssertionError, match="hằng số"):
        _run(src)


def test_id_hang_so_khop_danh_sach_ke_hoach():
    assert replay.FROZEN_IDS == {"V106", "V107", "V108", "V109", "V110",
                                 "V111", "V112", "V113", "V115", "V116"}


def test_4_cau_negative_con_lai_van_qua_mo_hinh():
    """V005/V105/V114/V117 có context → phải phát lại bình thường."""
    src = _src_item(qid="V105", gap_type="negative", gt=[], top_k=12)
    item = _run(src)
    assert item["frozen_copy"] is False
    assert item["answer"] == replay.MockBackend.DEFAULT


# ---------------------------------------------------------------------------
# format_ok
# ---------------------------------------------------------------------------

def test_format_ok_true_khi_parse_duoc():
    item = _run(_src_item())
    assert item["format_ok"] is True
    assert len(item["pred_citations"]) == 1


def test_format_ok_false_khi_khong_parse_duoc():
    item = _run(_src_item(), spec="empty")
    assert item["format_ok"] is False
    assert item["pred_citations"] == []


def test_format_ok_mau_so_chi_tinh_cau_co_gt(tmp_path):
    """§3.1: mẫu số là 123 câu GT khác rỗng, không phải 137."""
    results = [
        _run(_src_item(qid="A")),                                   # GT khác rỗng, ok
        _run(_src_item(qid="B"), spec="empty"),                     # GT khác rỗng, hỏng
        _run(_src_item(qid="C", gap_type="negative", gt=[]), spec="empty"),  # GT rỗng
    ]
    s = replay.summarize(results)
    assert s["format_ok_mau_so"] == 2
    assert s["format_ok_rate"] == 0.5


# ---------------------------------------------------------------------------
# hit_token_cap
# ---------------------------------------------------------------------------

def test_hit_token_cap_duoc_ghi_cho_moi_item():
    for spec in ("", "empty", "cap"):
        item = _run(_src_item(), spec=spec)
        assert "hit_token_cap" in item
        assert isinstance(item["hit_token_cap"], bool)


def test_cham_tran_token_lam_mat_khoi_trich_dan():
    """Đúng chế độ hỏng mà kế hoạch cảnh báo: bị cắt → citation biến mất → F1=0."""
    item = _run(_src_item(), spec="cap")
    assert item["hit_token_cap"] is True
    assert item["pred_citations"] == []
    assert item["citation_score"]["f1"] == 0.0
    assert item["format_ok"] is False


def test_summarize_gom_dung_id_cham_tran():
    results = [_run(_src_item(qid="A")), _run(_src_item(qid="B"), spec="cap")]
    s = replay.summarize(results)
    assert s["n_hit_token_cap"] == 1
    assert s["ids_hit_token_cap"] == ["B"]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_item_du_field_aggregate_can():
    item = _run(_src_item())
    for k in ("gap_type", "theme", "citation_score", "citation_score_dieu",
              "norm_recall", "elapsed_seconds"):
        assert k in item


def test_assert_schema_bat_thieu_citation_score_dieu():
    """Thiếu field này thì aggregate trả 0.000 IM LẶNG — phải bắt bằng assert tay."""
    item = _run(_src_item())
    del item["citation_score_dieu"]
    with pytest.raises(AssertionError, match="IM LẶNG"):
        replay.assert_schema(item)


def test_assert_schema_bat_thieu_negative_correct():
    item = _run(_src_item(gap_type="negative", gt=[]))
    item["negative_correct"] = None
    with pytest.raises(AssertionError, match="negative_correct"):
        replay.assert_schema(item)


def test_faithfulness_luon_null():
    item = _run(_src_item())
    assert item["faithfulness"] is None


def test_assert_schema_bat_nan():
    item = _run(_src_item())
    item["citation_score"]["f1"] = math.nan
    with pytest.raises(AssertionError, match="NaN"):
        replay.assert_schema(item)


def test_khong_sinh_nan_o_bat_ky_dau():
    item = _run(_src_item())
    assert not replay._non_finite(item)
    json.dumps(item, allow_nan=False)  # raise nếu có NaN/Inf


# ---------------------------------------------------------------------------
# Truy hồi đóng băng
# ---------------------------------------------------------------------------

def test_context_va_top_k_copy_nguyen_tu_nguon():
    src = _src_item()
    item = _run(src)
    assert item["context"] == src["context"]
    assert item["top_k_count"] == src["top_k_count"]
    assert item["ground_truth_citations"] == src["ground_truth_citations"]


def test_giu_ten_he_nguon_de_so_duoc_voi_hang_gemini():
    item = _run(_src_item())
    assert item["system"] == "graphrag"


# ---------------------------------------------------------------------------
# Tham số sinh
# ---------------------------------------------------------------------------

def test_gen_params_mac_dinh_khop_nguon_qwen():
    """generation_config.json của Qwen3-4B-Instruct-2507 + README Best Practices."""
    d = replay.GenParams()
    assert d.temperature == 0.7
    assert d.top_p == 0.8
    assert d.top_k == 20
    assert d.min_p == 0.0
    assert 0.0 <= d.presence_penalty <= 2.0   # dải card cho phép
    assert d.max_new_tokens == 2048


def test_mac_dinh_khong_phai_greedy():
    """Greedy → lặp vô tận → chạm cap → mất khối trích dẫn ở cuối → F1=0 kỹ thuật."""
    d = replay.GenParams()
    assert d.temperature > 0.0
    assert d.as_dict()["greedy"] is False


def test_as_dict_ghi_du_toan_bo_tham_so():
    keys = set(replay.GenParams().as_dict())
    assert keys == {"temperature", "top_p", "top_k", "min_p",
                    "presence_penalty", "seed", "max_new_tokens", "greedy"}


# ---------------------------------------------------------------------------
# Chặn tràn n_ctx
# ---------------------------------------------------------------------------

def test_check_ctx_budget_bao_loi_khi_tran():
    with pytest.raises(replay.CtxOverflow, match="cắt bớt ngữ cảnh"):
        replay.check_ctx_budget("V001", n_prompt=15000, max_new_tokens=2048, n_ctx=16384)


def test_check_ctx_budget_im_lang_khi_vua():
    replay.check_ctx_budget("V001", n_prompt=12011, max_new_tokens=2048, n_ctx=16384)


def test_check_ctx_budget_bien_vua_khit():
    replay.check_ctx_budget("V001", n_prompt=8192, max_new_tokens=8192, n_ctx=16384)
    with pytest.raises(replay.CtxOverflow):
        replay.check_ctx_budget("V001", n_prompt=8193, max_new_tokens=8192, n_ctx=16384)


def test_replay_item_dung_lai_khi_prompt_tran():
    """Backend đo được độ dài → tràn phải NỔ, không để llama.cpp cắt âm thầm."""
    backend = replay.MockBackend(token_counter=lambda s: 99_999)
    with pytest.raises(replay.CtxOverflow):
        replay.replay_item(_src_item(), "general", backend, 0, GP, n_ctx=16384)


def test_prompt_dai_duoc_ghi_tung_item():
    backend = replay.MockBackend(token_counter=lambda s: 1234)
    item = replay.replay_item(_src_item(), "general", backend, 0, GP, n_ctx=16384)
    assert item["n_tokens_prompt"] == 1234
    assert item["prompt_len_method"] == "mock-token-counter"


def test_backend_khong_do_duoc_thi_ghi_none_chu_khong_bia_so():
    item = _run(_src_item())
    assert item["n_tokens_prompt"] is None
    assert item["prompt_len_method"] == "khong-ho-tro"


def test_cau_hang_so_khong_kiem_tran():
    """Không gọi mô hình thì cũng không có prompt để tràn."""
    src = _src_item(qid="V106", gap_type="negative", gt=[], context="",
                    top_k=0, answer=replay.FROZEN_ANSWER)
    backend = replay.MockBackend(token_counter=lambda s: 99_999)
    item = replay.replay_item(src, "general", backend, 0, GP, n_ctx=16384)
    assert item["n_tokens_prompt"] is None


def test_summarize_gom_prompt_tokens_max():
    a = replay.replay_item(_src_item(qid="A"), "general",
                           replay.MockBackend(token_counter=lambda s: 100), 0, GP)
    b = replay.replay_item(_src_item(qid="B"), "general",
                           replay.MockBackend(token_counter=lambda s: 500), 0, GP)
    s = replay.summarize([a, b])
    assert s["prompt_tokens_max"] == 500
    assert s["prompt_tokens_do_duoc"] == 2


# ---------------------------------------------------------------------------
# render_prompt / --dump-prompt
# ---------------------------------------------------------------------------

def test_mock_render_prompt_co_du_vai_tro():
    msgs = replay.build_chat_messages("Câu hỏi?", "ngữ cảnh", "general", 0)
    rendered, how = replay.MockBackend().render_prompt(msgs)
    assert how == "mock-noi-tho"
    assert "<|system|>" in rendered and "<|user|>" in rendered
    assert "CÂU HỎI: Câu hỏi?" in rendered


# ---------------------------------------------------------------------------
# Backend llama-cpp — test bằng module giả (không có wheel Windows, chưa chốt model)
# ---------------------------------------------------------------------------

class _FakeLlama:
    """Giả llama_cpp.Llama, ghi lại tham số để kiểm truyền đúng."""

    last_kwargs: dict = {}

    def __init__(self, **kwargs):
        _FakeLlama.last_kwargs = kwargs
        self.calls = []
        self.metadata = {
            "tokenizer.chat_template":
                "{% for m in messages %}<|{{m.role}}|>{{m.content}}{% endfor %}",
            "tokenizer.ggml.eos_token_id": 1,
            "tokenizer.ggml.bos_token_id": 2,
        }

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        _FakeLlama.last_call = kwargs
        finish = "length" if "CAT" in kwargs["messages"][-1]["content"] else "stop"
        return {
            "choices": [{"message":
                         {"content": " Trả lời [Điều 3, Khoản 3, Văn bản luat-x-2024]. "},
                         "finish_reason": finish}],
            "usage": {"completion_tokens": 17},
        }

    def tokenize(self, b, **kw):
        return list(range(len(b) // 4))   # 1 token ~ 4 byte, đủ để test logic

    def detokenize(self, ids):
        return b"<eos>"


@pytest.fixture
def fake_llama_cpp(monkeypatch, tmp_path):
    import sys
    import types
    mod = types.ModuleType("llama_cpp")
    mod.Llama = _FakeLlama
    monkeypatch.setitem(sys.modules, "llama_cpp", mod)
    gguf = tmp_path / "model-q4.gguf"
    gguf.write_bytes(b"stub")
    return gguf


def test_llamacpp_nhan_du_tham_so_sinh(fake_llama_cpp):
    gp = replay.GenParams(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0,
                          presence_penalty=1.0, seed=1234, max_new_tokens=2048)
    b = replay.make_backend(str(fake_llama_cpp), n_ctx=16384, n_gpu_layers=-1, gp=gp)
    b.generate([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], gp)
    assert _FakeLlama.last_kwargs["seed"] == 1234
    assert _FakeLlama.last_kwargs["n_ctx"] == 16384
    c = _FakeLlama.last_call
    assert c["temperature"] == 0.7 and c["top_p"] == 0.8 and c["top_k"] == 20
    assert c["min_p"] == 0.0 and c["presence_penalty"] == 1.0
    assert c["seed"] == 1234 and c["max_tokens"] == 2048


def test_llamacpp_anh_xa_finish_reason_length_thanh_hit_cap(fake_llama_cpp):
    gp = replay.GenParams(max_new_tokens=64)
    b = replay.make_backend(str(fake_llama_cpp), n_ctx=8192, n_gpu_layers=0, gp=gp)
    ok = b.generate([{"role": "system", "content": "s"},
                     {"role": "user", "content": "u"}], gp)
    cut = b.generate([{"role": "system", "content": "s"},
                      {"role": "user", "content": "CAT"}], gp)
    assert ok.hit_token_cap is False
    assert cut.hit_token_cap is True
    assert ok.n_tokens_out == 17
    assert ok.text == "Trả lời [Điều 3, Khoản 3, Văn bản luat-x-2024]."  # đã strip


def test_llamacpp_render_prompt_dung_chat_template_cua_gguf(fake_llama_cpp):
    gp = replay.GenParams()
    b = replay.make_backend(str(fake_llama_cpp), n_ctx=16384, n_gpu_layers=0, gp=gp)
    msgs = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USR"}]
    rendered, how = b.render_prompt(msgs)
    assert how == "gguf-chat-template-jinja2"
    assert "<|system|>SYS" in rendered and "<|user|>USR" in rendered
    n, how_n = b.count_prompt_tokens(msgs)
    assert n == len(rendered.encode("utf-8")) // 4
    assert how_n == "gguf-chat-template-jinja2"


def test_llamacpp_lui_ve_xap_xi_khi_gguf_khong_co_chat_template(fake_llama_cpp):
    gp = replay.GenParams()
    b = replay.make_backend(str(fake_llama_cpp), n_ctx=16384, n_gpu_layers=0, gp=gp)
    b._llm.metadata = {}          # GGUF không nhúng template
    rendered, how = b.render_prompt([{"role": "user", "content": "x"}])
    assert rendered is None and how == "gguf-khong-co-chat-template"
    n, how_n = b.count_prompt_tokens([{"role": "user", "content": "x" * 40}])
    assert n is not None and how_n.startswith("xap-xi")   # nói rõ là xấp xỉ


def test_make_backend_bao_loi_ro_khi_thieu_file_model():
    with pytest.raises(SystemExit, match="mock"):
        replay.make_backend("khong/ton/tai.gguf", 16384, -1, replay.GenParams())


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def test_chuoi_mock_sach_utf8_khong_ky_tu_hong():
    for s in (replay.MockBackend.DEFAULT, replay.MockBackend.EMPTY,
              replay.FROZEN_ANSWER):
        assert "�" not in s                       # không có ký tự thay thế
        assert s == s.encode("utf-8").decode("utf-8")  # round-trip sạch
        assert "Ã" not in s and "Ð" not in s           # dấu hiệu mojibake


def test_file_replay_py_sach_utf8():
    from pathlib import Path as _P
    raw = _P(replay.__file__).read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "không được có BOM"
    assert "�" not in raw.decode("utf-8")


# ---------------------------------------------------------------------------
# soft_article_hit — bộ trích LỎNG (§TASK-FT-03)
# ---------------------------------------------------------------------------

_CTX = ("--- [Tier 1 | Hiệu lực: 2024-01-01] Điều 116. Tên điều, Khoản 5. "
        "(luat-dat-dai-2024) ---\nNội dung điều 116 khoản 5.")


def test_soft_bat_duoc_cum_ngoai_ngoac_vuong():
    """Phải LỎNG: không phụ thuộc cú pháp trích dẫn, không phụ thuộc ngoặc vuông."""
    r = replay.soft_article_report(
        "Theo Điều 116 Khoản 5 của luat-dat-dai-2024 thì ...", _CTX)
    assert r["n_mentions"] == 3
    assert r["hit_rate"] == 1.0


def test_soft_doc_lap_hoan_toan_voi_parse_citations():
    """Khi format_ok=0 (không parse ra citation nào) soft vẫn phải có giá trị."""
    from src.retrieval.answer_generator import parse_citations
    answer = "Căn cứ Điều 116 Khoản 5 văn bản luat-dat-dai-2024."
    assert parse_citations(answer) == []          # đúng lúc chỉ báo kia vô dụng
    r = replay.soft_article_report(answer, _CTX)
    assert r["hit_rate"] == 1.0


def test_soft_phat_hien_cum_bia_khong_co_trong_ngu_canh():
    r = replay.soft_article_report(
        "Theo Điều 999 Khoản 7 của nghi-dinh-bia-2099-nd-cp thì ...", _CTX)
    assert r["n_mentions"] == 3
    assert r["n_hit"] == 0
    assert r["hit_rate"] == 0.0


def test_soft_khong_khop_nham_tien_to_so():
    """'Điều 116' không được khớp vào 'Điều 1160'."""
    r = replay.soft_article_report("Điều 1160.", _CTX)
    assert r["theo_loai"]["dieu"]["n_hit"] == 0


def test_soft_none_khi_khong_nhac_gi():
    """Câu từ chối: không nhắc cụm nào → None, KHÔNG phải 0.0."""
    r = replay.soft_article_report(replay.MockBackend.EMPTY, _CTX)
    assert r["n_mentions"] == 0
    assert r["hit_rate"] is None


def test_soft_slug_phai_du_dai_va_khong_dinh_token_dai_hon():
    short = replay.soft_article_mentions("abc-def")            # <15 ký tự
    assert short["slug"] == set()
    ok = replay.soft_article_mentions("luat-dat-dai-2024")
    assert ok["slug"] == {"luat-dat-dai-2024"}


def test_soft_dem_cum_duy_nhat_khong_dem_lap():
    """Nhắc cùng một điều 3 lần vẫn là 1 cụm — nếu không thì câu IRAC bị thổi số."""
    r = replay.soft_article_report("Điều 116. Điều 116. Điều 116.", _CTX)
    assert r["theo_loai"]["dieu"]["n"] == 1


def test_soft_ghi_vao_item_va_summarize():
    item = _run(_src_item())
    assert "soft_article_hit" in item and "soft_article" in item
    s = replay.summarize([item])
    assert "soft_article_hit_mean" in s
    assert s["soft_article_hit_do_duoc"] == 1


def test_summarize_bo_qua_item_none_khong_coi_la_0():
    a = _run(_src_item(qid="A"))                      # có nhắc cụm
    b = _run(_src_item(qid="B"), spec="empty")        # không nhắc gì → None
    s = replay.summarize([a, b])
    assert b["soft_article_hit"] is None
    assert s["soft_article_hit_do_duoc"] == 1
    assert s["soft_article_hit_mean"] == a["soft_article_hit"]


def test_soft_tren_cau_tra_loi_that_cua_gemini():
    """Trần tham chiếu: Gemini không nhắc điều luật nào ngoài ngữ cảnh."""
    import json as _json
    from pathlib import Path as _P
    src = _P("data/evaluation/results_graphrag_20260710-085236.json")
    if not src.exists():
        pytest.skip("không có file results nguồn")
    rows = _json.loads(src.read_text(encoding="utf-8"))["results"]
    rates = [replay.soft_article_report(x["answer"], x["context"])["hit_rate"]
             for x in rows]
    got = [r for r in rates if r is not None]
    assert len(got) == 118
    assert min(got) == 1.0


# ---------------------------------------------------------------------------
# gate_ids.json
# ---------------------------------------------------------------------------

@pytest.fixture
def gate():
    import json as _json
    from pathlib import Path as _P
    p = _P("finetune/data/gate_ids.json")
    if not p.exists():
        pytest.skip("chưa sinh gate_ids.json")
    return _json.loads(p.read_text(encoding="utf-8"))


def test_gate_du_15_cau_phan_tang(gate):
    import collections
    c = collections.Counter(x["gap_type"] for x in gate["chi_tiet"])
    assert len(gate["ids"]) == 15
    assert c == {"gap1": 3, "gap2": 3, "gap3": 3, "gap4": 3, "negative": 3}


def test_gate_negative_chi_lay_tu_4_cau_qua_mo_hinh(gate):
    negs = {x["id"] for x in gate["chi_tiet"] if x["gap_type"] == "negative"}
    assert negs <= {"V005", "V105", "V114", "V117"}
    assert not (negs & replay.FROZEN_IDS)


def test_gate_khong_co_cau_hang_so(gate):
    assert all(x["top_k_count"] > 0 for x in gate["chi_tiet"])


def test_gate_mau_so_format_ok_la_12(gate):
    """3 câu negative có GT rỗng → mẫu số 12, không phải 15."""
    assert sum(1 for x in gate["chi_tiet"] if x["gt_nonempty"]) == 12


def test_gate_chon_tat_dinh():
    """Chạy lại bộ chọn phải ra đúng danh sách cũ."""
    import json as _json
    from pathlib import Path as _P
    from finetune import select_gate_ids as sel
    p = _P("finetune/data/gate_ids.json")
    if not p.exists():
        pytest.skip("chưa sinh gate_ids.json")
    before = _json.loads(p.read_text(encoding="utf-8"))["ids"]
    items = _json.loads(sel.SOURCE.read_text(encoding="utf-8"))["results"]
    again = []
    for g in sel.GROUPS:
        sent = [x for x in items if x["gap_type"] == g and x["top_k_count"] > 0]
        again += [x["id"] for x in sel.pick(sent, sel.PER_GROUP)]
    assert again == before


def test_gate_phu_nhieu_theme_moi_nhom(gate):
    import collections
    by = collections.defaultdict(set)
    for x in gate["chi_tiet"]:
        by[x["gap_type"]].add(x["theme"])
    for g in ("gap1", "gap2", "gap3", "gap4"):
        assert len(by[g]) >= 2, f"{g} chỉ phủ {by[g]}"


# ---------------------------------------------------------------------------
# End-to-end: aggregate đọc được, KHÔNG cần sửa src/
# ---------------------------------------------------------------------------

def test_aggregate_doc_duoc_ket_qua_replay():
    results = [
        _run(_src_item(qid="A", gap_type="gap1")),
        _run(_src_item(qid="B", gap_type="gap2"), spec="empty"),
        _run(_src_item(qid="C", gap_type="negative", gt=[]), spec="empty"),
    ]
    for r in results:
        replay.assert_schema(r)
    agg = aggregate(results)
    assert agg["count"] == 3
    assert agg["negative_count"] == 1
    assert agg["negative_correct_rate"] == 1.0
    # Cột F1 cấp Điều phải THẬT SỰ được tính, không phải 0.000 im lặng
    assert agg["f1_dieu_mean"] > 0.0


def test_round_trip_qua_json_strict():
    """JSON phải chuẩn: parser strict (không chấp nhận NaN) đọc được."""
    results = [_run(_src_item(qid="A"))]
    blob = json.dumps({"results": results}, ensure_ascii=False, allow_nan=False)

    def _reject(x):
        raise ValueError(f"JSON không chuẩn: {x}")

    back = json.loads(blob, parse_constant=_reject)
    assert aggregate(back["results"])["count"] == 1
