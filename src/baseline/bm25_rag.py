"""
BM25 baseline (E2a) — retrieval LEXICAL (từ khóa) thay cho dense (BGE-M3).

Trả lời câu hỏi khoa học: "chọn DENSE (ngữ nghĩa) có đáng không, hay IR từ khóa
kinh điển cũng ngang?". Retrieve trên CÙNG đơn vị (leaf TextUnit cấp Điều/Khoản)
mà dense dùng → so sánh có kiểm soát: chỉ khác HÀM XẾP HẠNG.

Kỳ vọng (docs/EVALUATION_ARCHITECTURE.md §E2a): BM25 tốt trên câu trùng từ chính
xác (trích dẫn cấu trúc), YẾU trên câu diễn đạt khác/khẩu ngữ (register) — nơi
dense thắng. Nếu Full/dense KHÔNG vượt BM25 → nền embedding là chi phí thừa.

BM25 tự cài (Okapi, k1=1.5, b=0.75) — không thêm dependency; corpus ~4.5k unit,
inverted index đủ nhanh. Tokenize theo âm tiết (whitespace + regex) — đủ cho baseline.
"""
from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

from src.ingestion.parser import parse_file
from src.retrieval.answer_generator import generate_answer

logger = logging.getLogger(__name__)

_NON_NORM = {"mapping_table.md", "crossref_decisions.md", "review_log.md"}
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_K1, _B = 1.5, 0.75


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _unit_label(context_path: list[str]) -> str:
    """Nhãn citation từ context_path: 'Điều X, Khoản Y (van_ban)'."""
    norm_id = context_path[0]
    parts = context_path[1:]
    if not parts:
        return norm_id
    # Rút gọn heading 'Điều 3. Hạn mức...' → 'Điều 3'
    short = []
    for seg in parts:
        m = re.match(r"^(Điều|Khoản|Điểm|Tiết|Phụ lục)\s+(\S+?)[.\s]", seg + " ")
        short.append(f"{m.group(1)} {m.group(2)}" if m else seg)
    return f"{', '.join(short)} ({norm_id})"


class _BM25Corpus:
    """Index BM25 trên leaf TextUnit của corpus (lazy, build 1 lần)."""

    def __init__(self, raw_dir: Path):
        self.labels: list[str] = []
        self.texts: list[str] = []
        docs_tokens: list[list[str]] = []
        for f in sorted(raw_dir.glob("*.md")):
            if f.name in _NON_NORM:
                continue
            parsed = parse_file(str(f))
            for node in parsed["nodes"]:
                self.labels.append(_unit_label(node["context_path"]))
                self.texts.append(node["text"])
                docs_tokens.append(_tokenize(node["text"]))

        self.N = len(docs_tokens)
        self.doc_len = [len(d) for d in docs_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        # Inverted index: term -> list[(doc_idx, tf)]
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        df: Counter = Counter()
        for i, toks in enumerate(docs_tokens):
            tf = Counter(toks)
            for term, freq in tf.items():
                self.postings[term].append((i, freq))
                df[term] += 1
        self.idf = {
            t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()
        }
        logger.info(f"BM25: index {self.N} leaf units, {len(self.idf)} terms")

    def top_k(self, query: str, k: int) -> list[int]:
        scores = [0.0] * self.N
        for term in _tokenize(query):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, f in self.postings[term]:
                denom = f + _K1 * (1 - _B + _B * self.doc_len[i] / self.avgdl)
                scores[i] += idf * f * (_K1 + 1) / denom
        ranked = sorted(range(self.N), key=lambda i: scores[i], reverse=True)
        return [i for i in ranked if scores[i] > 0][:k]


_CORPUS: _BM25Corpus | None = None


def get_bm25_corpus(raw_dir: str = "data/raw") -> _BM25Corpus:
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = _BM25Corpus(Path(raw_dir))
    return _CORPUS


def run_bm25_query(
    question: str,
    llm_client: anthropic.Anthropic,
    corpus: _BM25Corpus | None = None,
    top_k: int = 20,
    cache_dir: Path | None = None,
    mode: str = "general",
) -> dict:
    """Retrieve top-k lexical → context → generate. Dict khớp shape baseline."""
    t0 = time.perf_counter()
    corpus = corpus or get_bm25_corpus()
    idxs = corpus.top_k(question, top_k)
    context = "\n\n".join(
        f"--- {corpus.labels[i]} ---\n{corpus.texts[i].strip()}" for i in idxs
    )
    gen = generate_answer(question, context, llm_client, cache_dir=cache_dir, mode=mode)
    return {
        "answer": gen["answer"],
        "citations": gen["citations"],
        "context_used": gen["context_used"],
        "top_k_count": len(idxs),
        "context": context,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }
