"""Smoke tests cho TASK-16 Naive RAG baseline (không cần Qdrant)."""
from pathlib import Path

import pytest

from src.baseline.naive_rag import _chunk_id, _parse_md_file, fixed_chunker


def test_fixed_chunker_basic():
    text = "abcdefghijklmnop" * 50  # 800 chars
    chunks = fixed_chunker(text, chunk_size=200, overlap=20)
    assert len(chunks) >= 4
    assert all(len(c) <= 200 for c in chunks)
    # Overlap: cuối chunk i phải xuất hiện ở đầu chunk i+1
    assert chunks[0][-20:] == chunks[1][:20]


def test_fixed_chunker_edge_cases():
    assert fixed_chunker("") == []
    assert fixed_chunker("   ") == []
    short = fixed_chunker("abc", chunk_size=100, overlap=10)
    assert short == ["abc"]


def test_fixed_chunker_invalid():
    with pytest.raises(ValueError):
        fixed_chunker("x", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        fixed_chunker("x", chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        fixed_chunker("x", chunk_size=10, overlap=-1)


def test_parse_md_file_real():
    p = Path("data") / "raw" / "luat-dat-dai-2024.md"
    norm_id, body = _parse_md_file(p)
    assert norm_id == "luat-dat-dai-2024"
    assert len(body) > 1000
    assert "## Điều" in body


def test_parse_md_file_missing_frontmatter(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("# No frontmatter\nbody only")
    with pytest.raises(ValueError, match="frontmatter"):
        _parse_md_file(f)


def test_chunk_id_deterministic():
    a = _chunk_id("luat-dat-dai-2024", 0)
    b = _chunk_id("luat-dat-dai-2024", 0)
    c = _chunk_id("luat-dat-dai-2024", 1)
    d = _chunk_id("nghi-dinh-102-2024-nd-cp", 0)
    assert a == b
    assert a != c
    assert a != d
    assert isinstance(a, int)


def test_chunker_on_real_file():
    p = Path("data") / "raw" / "nghi-dinh-101-2024-nd-cp.md"
    _, body = _parse_md_file(p)
    chunks = fixed_chunker(body, chunk_size=512, overlap=50)
    assert len(chunks) > 20  # ND 101 dài
    assert all(0 < len(c) <= 512 for c in chunks)
