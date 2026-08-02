"""Unit test cho `ui/corpus.py` — Task 1 của `ui/docs/UI_DEMO_SPEC.md`.

Chạy được ở máy A: chỉ đọc `data/raw/*.md`, không cần Neo4j/Qdrant/LLM.
"""
import pytest

from ui.corpus import (
    get_component_text,
    load_corpus,
    norm_graph,
    parse_body,
    parse_norm_file,
    render_node,
)

MD_MAU = """---
id: "van-ban-thu-2024"
title: "Văn bản thử"
so_hieu: "99/2024/NĐ-CP"
tier: 2
theme: "dat-dai"
jurisdiction: "toan-quoc"
implements:
  - "luat-dat-dai-2024"
  - "nghi-quyet-254-2025-qh15"
valid_from: "2024-08-01"
valid_to: null
source_url: "https://vbpl.vn/..."
source_vbhn: null
amended_by_norms: "nghi-dinh-226-2025-nd-cp"
summary: "Một câu tóm tắt: có cả dấu hai chấm."
---

## Điều 1. Phạm vi điều chỉnh

Nội dung Điều 1.

## Điều 2. Hạn mức

### Khoản 1.

Nội dung khoản 1.

#### Điểm a.

Nội dung điểm a.

### Khoản 2.

Nội dung khoản 2.

## Phụ lục I. Biểu mức thu

### Khoản 1.

Nội dung phụ lục.
"""


@pytest.fixture()
def norm(tmp_path):
    path = tmp_path / "van-ban-thu-2024.md"
    path.write_text(MD_MAU, encoding="utf-8")
    return parse_norm_file(path)


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def test_frontmatter_chuan_hoa(norm):
    assert norm["id"] == "van-ban-thu-2024"
    assert norm["tier"] == 2
    assert norm["theme"] == "dat-dai"
    assert norm["valid_to"] is None
    assert norm["summary"].endswith("dấu hai chấm.")


def test_implements_list_va_amended_string_deu_thanh_list(norm):
    # D-23: implements chấp nhận string | list | null
    assert norm["implements"] == ["luat-dat-dai-2024", "nghi-quyet-254-2025-qh15"]
    assert norm["amended_by_norms"] == ["nghi-dinh-226-2025-nd-cp"]


def test_amended_by_norms_dang_string_co_canh_bao(tmp_path, caplog):
    # graph_builder Pass 3 chỉ xử lý list → scalar sẽ khiến UI vẽ cạnh AMENDS
    # không tồn tại trong Neo4j. Phải cảnh báo.
    path = tmp_path / "b.md"
    path.write_text(MD_MAU, encoding="utf-8")
    with caplog.at_level("WARNING", logger="ui.corpus"):
        norm = parse_norm_file(path)
    assert norm["amended_by_norms"] == ["nghi-dinh-226-2025-nd-cp"]
    assert any("amended_by_norms" in r.message for r in caplog.records)


def test_amended_by_norms_dang_list_khong_canh_bao(tmp_path, caplog):
    path = tmp_path / "c.md"
    path.write_text(
        MD_MAU.replace(
            'amended_by_norms: "nghi-dinh-226-2025-nd-cp"',
            'amended_by_norms:\n  - "nghi-dinh-226-2025-nd-cp"',
        ),
        encoding="utf-8",
    )
    with caplog.at_level("WARNING", logger="ui.corpus"):
        parse_norm_file(path)
    assert not [r for r in caplog.records if "amended_by_norms" in r.message]


def test_implements_null_thanh_list_rong(tmp_path):
    path = tmp_path / "a.md"
    path.write_text(
        MD_MAU.replace(
            'implements:\n  - "luat-dat-dai-2024"\n  - "nghi-quyet-254-2025-qh15"',
            "implements: null",
        ),
        encoding="utf-8",
    )
    assert parse_norm_file(path)["implements"] == []


# ---------------------------------------------------------------------------
# Thân bài
# ---------------------------------------------------------------------------

def test_parse_body_cay_phan_cap(norm):
    muc = norm["muc"]
    assert [(m["cap"], m["so"]) for m in muc] == [
        ("dieu", "1"), ("dieu", "2"), ("phu_luc", "I"),
    ]
    khoan = muc[1]["con"]
    assert [(k["cap"], k["so"]) for k in khoan] == [("khoan", "1"), ("khoan", "2")]
    assert [(d["cap"], d["so"]) for d in khoan[0]["con"]] == [("diem", "a")]


def test_parse_body_heading_la_khong_lam_sap():
    cay = parse_body("## Chương I\n\nNội dung lạ.\n\n## Điều 1.\n\nNội dung.")
    assert cay[0]["cap"] == "khac"
    assert cay[1]["cap"] == "dieu"


def test_render_node_gom_heading_va_cap_con(norm):
    text = render_node(norm["muc"][1])
    assert text.startswith("Điều 2. Hạn mức")
    assert "Khoản 1." in text and "Điểm a." in text and "Khoản 2." in text


# ---------------------------------------------------------------------------
# get_component_text
# ---------------------------------------------------------------------------

def test_get_component_text_cac_cap(tmp_path):
    (tmp_path / "van-ban-thu-2024.md").write_text(MD_MAU, encoding="utf-8")
    load_corpus(tmp_path, refresh=True)

    ca_dieu = get_component_text("van-ban-thu-2024", "2", raw_dir=tmp_path)
    assert "Khoản 1." in ca_dieu and "Khoản 2." in ca_dieu

    khoan = get_component_text("van-ban-thu-2024", "2", "1", raw_dir=tmp_path)
    assert khoan.startswith("Khoản 1.") and "Khoản 2." not in khoan

    diem = get_component_text("van-ban-thu-2024", "2", "1", "a", raw_dir=tmp_path)
    assert diem.startswith("Điểm a.")

    # Phụ lục + tiền tố dạng đầy đủ vẫn tra được
    assert get_component_text("van-ban-thu-2024", "I", raw_dir=tmp_path).startswith(
        "Phụ lục I."
    )
    assert get_component_text("van-ban-thu-2024", "Điều 1.", raw_dir=tmp_path)

    # Không tìm thấy → None (không raise)
    assert get_component_text("van-ban-thu-2024", "99", raw_dir=tmp_path) is None
    assert get_component_text("van-ban-thu-2024", "2", "9", raw_dir=tmp_path) is None
    assert get_component_text("khong-ton-tai", "1", raw_dir=tmp_path) is None

    load_corpus(refresh=True)   # trả cache về corpus thật


# ---------------------------------------------------------------------------
# Đồ thị + corpus thật
# ---------------------------------------------------------------------------

def test_corpus_that_du_32_van_ban():
    corpus = load_corpus(refresh=True)
    assert len(corpus) >= 32
    assert "luat-dat-dai-2024" in corpus
    assert corpus["luat-dat-dai-2024"]["tier"] == 1


def test_norm_graph_canh_implements_va_amends():
    graph = norm_graph()
    canh = {(e["source"], e["target"], e["type"]) for e in graph["edges"]}
    # IMPLEMENTS: NĐ 102 hướng dẫn thi hành Luật ĐĐ 2024
    assert ("nghi-dinh-102-2024-nd-cp", "luat-dat-dai-2024", "IMPLEMENTS") in canh
    # D-23: đa-cha
    assert ("thong-tu-04-2020-tt-btp", "luat-ho-tich-2014", "IMPLEMENTS") in canh
    assert ("thong-tu-04-2020-tt-btp", "nghi-dinh-123-2015-nd-cp", "IMPLEMENTS") in canh
    # D-09: AMENDS đi từ văn bản sửa đổi → văn bản bị sửa
    assert ("nghi-quyet-254-2025-qh15", "luat-dat-dai-2024", "AMENDS") in canh


def test_norm_graph_bo_canh_treo():
    graph = norm_graph()
    ids = {n["id"] for n in graph["nodes"]}
    for e in graph["edges"]:
        assert e["source"] in ids and e["target"] in ids
    # amended_by_norms của Luật ĐĐ 2024 trỏ tới nhiều luật ngoài corpus
    assert graph["bo_qua"]
