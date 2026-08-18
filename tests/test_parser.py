import hashlib
import textwrap
from pathlib import Path

import pytest

from src.ingestion.parser import TextUnit, generate_id, parse_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_md(tmp_path: Path, content: str, name: str = "test.md") -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def _frontmatter(extra: str = "") -> str:
    return textwrap.dedent(f"""\
        ---
        id: "test-norm-2024"
        title: "Văn bản test"
        tier: 1
        theme: "dat-dai"
        jurisdiction: "toan-quoc"
        implements: null
        valid_from: "2024-01-01"
        valid_to: null
        source_url: "https://example.com"
        source_vbhn: null
        amended_by_norms: null
        summary: null
        {extra}---
    """)


VALID_MD = _frontmatter() + textwrap.dedent("""\

    ## Điều 1. Phạm vi

    Nội dung điều một.

    ## Điều 2. Đối tượng

    ### Khoản 1.

    Nội dung khoản một điều hai.

    ### Khoản 2.

    Nội dung khoản hai điều hai.

    #### Điểm a.

    Nội dung điểm a khoản hai.
""")


# ---------------------------------------------------------------------------
# generate_id
# ---------------------------------------------------------------------------

def test_generate_id_deterministic():
    path = ["luat-dat-dai-2024", "Điều 1. Phạm vi điều chỉnh"]
    assert generate_id(path) == generate_id(path)


def test_generate_id_length():
    assert len(generate_id(["a", "b"])) == 16


def test_generate_id_unique_paths():
    assert generate_id(["norm", "Điều 1."]) != generate_id(["norm", "Điều 2."])


def test_generate_id_formula():
    path = ["luat-dat-dai-2024", "Điều 5.", "Khoản 2."]
    expected = hashlib.sha256(">".join(path).encode()).hexdigest()[:16]
    assert generate_id(path) == expected


# ---------------------------------------------------------------------------
# parse_file — happy path
# ---------------------------------------------------------------------------

def test_parse_valid_file_metadata(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    result = parse_file(filepath)
    assert result["metadata"]["id"] == "test-norm-2024"
    assert result["metadata"]["tier"] == 1


def test_parse_valid_file_node_count(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    nodes = parse_file(filepath)["nodes"]
    # Điều 1, Điều 2/Khoản 1, Điều 2/Khoản 2, Điều 2/Khoản 2/Điểm a
    assert len(nodes) == 4


def test_parse_valid_file_context_paths(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    paths = [n["context_path"] for n in parse_file(filepath)["nodes"]]
    assert ["test-norm-2024", "Điều 1. Phạm vi"] in paths
    assert ["test-norm-2024", "Điều 2. Đối tượng", "Khoản 1."] in paths
    assert ["test-norm-2024", "Điều 2. Đối tượng", "Khoản 2."] in paths
    assert ["test-norm-2024", "Điều 2. Đối tượng", "Khoản 2.", "Điểm a."] in paths


def test_parse_valid_file_text_content(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    nodes = parse_file(filepath)["nodes"]
    texts = {tuple(n["context_path"]): n["text"] for n in nodes}
    assert "Nội dung điều một." in texts[("test-norm-2024", "Điều 1. Phạm vi")]


def test_parse_dieu_without_khoan(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        ## Điều 5. Điều không có khoản

        Nội dung trực tiếp dưới điều.
    """)
    filepath = _write_md(tmp_path, md)
    nodes = parse_file(filepath)["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["context_path"] == ["test-norm-2024", "Điều 5. Điều không có khoản"]
    assert "Nội dung trực tiếp" in nodes[0]["text"]


def test_parse_phu_luc_heading(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        ## Phụ lục I - Phần A - Mục 1. Danh sách

        ### Khoản 1.

        Nội dung phụ lục.
    """)
    filepath = _write_md(tmp_path, md)
    nodes = parse_file(filepath)["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["context_path"][1].startswith("Phụ lục")


def test_parse_ids_are_deterministic(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    ids1 = [n["id"] for n in parse_file(filepath)["nodes"]]
    ids2 = [n["id"] for n in parse_file(filepath)["nodes"]]
    assert ids1 == ids2


def test_parse_node_ids_match_generate_id(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    for node in parse_file(filepath)["nodes"]:
        assert node["id"] == generate_id(node["context_path"])


def test_parse_metadata_propagated_to_all_nodes(tmp_path):
    filepath = _write_md(tmp_path, VALID_MD)
    nodes = parse_file(filepath)["nodes"]
    for node in nodes:
        assert node["metadata"]["id"] == "test-norm-2024"


def test_parse_amended_by_comment_included_in_text(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        ## Điều 1. Phạm vi

        Nội dung gốc.
        <!-- amended_by: 47/2024/QH15, khoản 1 Điều 1, hiệu lực: 2025-07-01, nội dung: sửa đổi nội dung -->
    """)
    filepath = _write_md(tmp_path, md)
    nodes = parse_file(filepath)["nodes"]
    assert len(nodes) == 1
    assert "amended_by" in nodes[0]["text"]


# ---------------------------------------------------------------------------
# parse_file — lỗi heading format
# ---------------------------------------------------------------------------

def test_parse_raises_on_level1_heading(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        # Điều 1. Sai cấp
        Nội dung.
    """)
    with pytest.raises(ValueError, match="cấp 1"):
        parse_file(_write_md(tmp_path, md))


def test_parse_raises_on_khoan_at_level2(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        ## Khoản 1.
        Nội dung.
    """)
    with pytest.raises(ValueError, match="##"):
        parse_file(_write_md(tmp_path, md))


def test_parse_raises_on_chuong_heading(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        ## Chương I. Tiêu đề chương
        ## Điều 1. Nội dung
        Nội dung điều.
    """)
    with pytest.raises(ValueError, match="##"):
        parse_file(_write_md(tmp_path, md))


def test_parse_raises_on_dieu_at_level3(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        ## Điều 1. Điều đúng

        ### Điều 2. Điều sai cấp
        Nội dung.
    """)
    with pytest.raises(ValueError, match="###"):
        parse_file(_write_md(tmp_path, md))


def test_parse_raises_on_text_without_heading(tmp_path):
    md = _frontmatter() + textwrap.dedent("""\

        Nội dung không có heading cha.
    """)
    with pytest.raises(ValueError, match="heading cha"):
        parse_file(_write_md(tmp_path, md))


# ---------------------------------------------------------------------------
# parse_file — lỗi frontmatter
# ---------------------------------------------------------------------------

def test_parse_raises_on_missing_id(tmp_path):
    md = textwrap.dedent("""\
        ---
        title: "Thiếu id"
        tier: 1
        theme: "dat-dai"
        jurisdiction: "toan-quoc"
        implements: null
        valid_from: "2024-01-01"
        valid_to: null
        source_url: "https://example.com"
        source_vbhn: null
        amended_by_norms: null
        summary: null
        ---

        ## Điều 1. Test
        Nội dung.
    """)
    with pytest.raises(ValueError, match="id"):
        parse_file(_write_md(tmp_path, md))


def test_parse_raises_on_missing_frontmatter(tmp_path):
    md = "## Điều 1. Không có frontmatter\nNội dung.\n"
    with pytest.raises(ValueError, match="frontmatter"):
        parse_file(_write_md(tmp_path, md))


# ---------------------------------------------------------------------------
# parse_file — tất cả file thực tế trong data/raw/
# ---------------------------------------------------------------------------

DATA_RAW = Path(__file__).parents[1] / "data" / "raw"
# Chỉ parse các file văn bản pháp luật (có YAML frontmatter với field 'id').
# crossref_decisions.md và mapping_table.md là file dự án, không phải norm file.
# Dùng CHUNG danh sách với graph_builder thay vì chép lại — bản chép ở đây từng
# lệch khi thêm TODO_review.md, làm test đỏ dù ingestion đã bỏ qua file đó.
from src.ingestion.graph_builder import _NON_NORM_FILES  # noqa: E402
REAL_MD_FILES = sorted(p for p in DATA_RAW.glob("*.md") if p.name not in _NON_NORM_FILES)


@pytest.mark.parametrize("filepath", REAL_MD_FILES, ids=lambda p: p.name)
def test_parse_real_file_no_exception(filepath):
    """Mỗi file trong data/raw/ phải parse được mà không có exception."""
    result = parse_file(str(filepath))
    assert "metadata" in result
    assert "nodes" in result
    # Mọi node phải có id đúng format (16 ký tự hex)
    for node in result["nodes"]:
        assert len(node["id"]) == 16
        assert node["id"] == generate_id(node["context_path"])
