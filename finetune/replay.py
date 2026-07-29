"""TASK-FT-02 — Bộ phát lại: đổi mô hình sinh, GIỮ NGUYÊN truy hồi.

Nguyên tắc nền (kế hoạch §4): `results_*.json` đã lưu chuỗi `context` byte-identical
với cái mô hình sinh thực sự nhận. Nên không cần Neo4j, không cần Qdrant, không
chạy lại truy hồi, không gọi API nào. Truy hồi bị khoá tuyệt đối giữa các hàng của
ma trận → chênh lệch đo được thuần tuý thuộc về mô hình sinh.

    Đọc results JSON nguồn (CHỈ ĐỌC)
      → mỗi item: (id, question, context)
      → tra mode từ finetune/data/mode_map.json
      → dựng prompt bằng src.retrieval.context_assembler.build_messages
      → gọi backend (mock | llama-cpp GGUF)
      → parse bằng src.retrieval.answer_generator.parse_citations
      → chấm bằng src.evaluation.metrics (KHÔNG tự viết hàm chấm)
      → ghi results JSON mới vào finetune/results/, ĐÚNG SCHEMA HIỆN TẠI

Mô hình cục bộ CHƯA chốt (việc của FT-03) → backend cắm được. Toàn bộ đường đi
schema verify được bằng `--model mock`, không phụ thuộc đã tải weights hay chưa.

Ví dụ:
    python -m finetune.replay --input data/evaluation/results_graphrag_20260710-085236.json \\
        --model mock --limit 5
    python -m finetune.replay --input ... --model models/qwen3-4b-q4.gguf --n-shot 2
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    # Thiếu dòng này thì thông báo lỗi tiếng Việt vỡ trên console Windows (cp1252).
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# PHẢI đặt TRƯỚC khi import context_assembler.
# INCLUDE_SCHEMA_B đọc bằng os.getenv NGAY LÚC IMPORT MODULE
# (src/retrieval/context_assembler.py:23) — đổi sau khi import KHÔNG có tác dụng.
# Mẻ 10/07 chạy với false; để true thì system prompt đổi hình dạng và prompt
# không còn trùng khít với mẻ gốc.
# ---------------------------------------------------------------------------
os.environ["INCLUDE_SCHEMA_B"] = "false"

from src.evaluation.metrics import (  # noqa: E402
    aggregate,
    citation_score,
    negative_correct,
    norm_recall,
)
from src.retrieval import context_assembler  # noqa: E402
from src.retrieval.answer_generator import parse_citations  # noqa: E402
from src.retrieval.context_assembler import build_messages  # noqa: E402

# Chốt kế hoạch §9.1(3): dùng build_messages (system, user), KHÔNG dùng build_prompt.
# Chỉ lùi về build_prompt nếu model chốt ở FT-03 không có system role — và khi đó
# CẢ BỐN Ô phải dùng chung một lựa chọn, trộn hai cách là tự tạo confound.

assert context_assembler.INCLUDE_SCHEMA_B is False, (
    "INCLUDE_SCHEMA_B=True — system prompt sẽ khác mẻ gốc. "
    "context_assembler đã bị import ở đâu đó TRƯỚC khi replay.py set env."
)

REPO = Path(__file__).resolve().parents[1]
MODE_MAP_PATH = REPO / "finetune/data/mode_map.json"
DEFAULT_OUT_DIR = REPO / "finetune/results"

# Hằng số của nhánh truy hồi rỗng — src/pipeline.py:233.
# 10 câu này Gemini CHƯA TỪNG được gọi: pipeline.py:223 `if not norm_ids:` return
# TRƯỚC assemble_context (dòng 256) và generate_answer (dòng 261). Nhánh này thuộc
# truy hồi, mà truy hồi đã đóng băng → đầu ra của nó cũng phải đóng băng (§9.1).
FROZEN_ANSWER = "Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này."
FROZEN_IDS = {"V106", "V107", "V108", "V109", "V110", "V111", "V112", "V113", "V115", "V116"}

MAX_NEW_TOKENS = 2048  # §9.4(3). Gemini p50=257 max=1313 nhưng khối trích dẫn nằm
# CUỐI câu trả lời — mô hình nhỏ dài dòng hơn, bị cắt là mất citation → F1=0 vì lý
# do thuần kỹ thuật. Mọi item ghi `hit_token_cap`.
DEFAULT_N_CTX = 16384  # token_budget.md §2.7(1)


# ---------------------------------------------------------------------------
# Few-shot: ví dụ minh hoạ ĐỊNH DẠNG, không phải kiến thức pháp luật
# ---------------------------------------------------------------------------
# Cú pháp lấy từ api_contract.md §3.2 (xác minh trên 401/401 khối thực tế).
# Header ngữ cảnh theo đúng khuôn assemble_context (api_contract.md §6.1).
# Dùng slug GIẢ, không có trong corpus 32 văn bản → không rò rỉ đáp án; mục đích
# duy nhất là dạy "chép slug từ ngoặc đơn cuối header ra khối trích dẫn".
# PHẢI giống hệt nhau ở cả bốn ô của ma trận, nếu không là confound.
_FEWSHOT: list[tuple[str, str]] = [
    (
        "CONTEXT:\n"
        "--- [Tier 1 | Hiệu lực: 2020-01-01] Điều 7. Thời hạn giải quyết, Khoản 2. "
        "(luat-vi-du-2019) ---\n"
        "Điều 7. Thời hạn giải quyết\nKhoản 2.\n"
        "Cơ quan tiếp nhận phải giải quyết trong thời hạn 05 ngày làm việc kể từ ngày "
        "nhận đủ hồ sơ hợp lệ.\n\n"
        "CÂU HỎI: Thời hạn giải quyết là bao lâu?\n\nTRẢ LỜI:",
        "Thời hạn giải quyết là 05 ngày làm việc kể từ ngày cơ quan tiếp nhận nhận đủ "
        "hồ sơ hợp lệ [Điều 7, Khoản 2, Văn bản luat-vi-du-2019].",
    ),
    (
        "CONTEXT:\n"
        "--- [Tier 2 | Hiệu lực: 2021-06-15] Điều 12. Mức thu, Khoản 1, Điểm b. "
        "(nghi-dinh-vi-du-2021-nd-cp) ---\n"
        "Điều 12. Mức thu\nKhoản 1.\nĐiểm b.\n"
        "Đối với cá nhân cư trú tại khu vực nông thôn: 20.000 đồng một lần.\n\n"
        "CÂU HỎI: Cá nhân ở nông thôn nộp bao nhiêu tiền?\n\nTRẢ LỜI:",
        "Cá nhân cư trú tại khu vực nông thôn nộp 20.000 đồng một lần "
        "[Điều 12, Khoản 1, Điểm b, Văn bản nghi-dinh-vi-du-2021-nd-cp].",
    ),
]


# ---------------------------------------------------------------------------
# Tham số sinh
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenParams:
    """Tham số sinh. Mặc định = khuyến nghị của Qwen cho Qwen3-4B-Instruct-2507.

    Nguồn (đã đối chiếu trực tiếp, không nhớ):
      - `generation_config.json` của repo: `do_sample: true`, `temperature: 0.7`,
        `top_k: 20`, `top_p: 0.8`.
      - README mục *Best Practices*: "We suggest using Temperature=0.7, TopP=0.8,
        TopK=20, and MinP=0" và "you can adjust the `presence_penalty` parameter
        between 0 and 2 to reduce endless repetitions. However, using a higher value
        may occasionally result in language mixing and a slight decrease in model
        performance."

    **KHÔNG greedy decoding.** Lặp vô tận sẽ ăn hết `max_new_tokens`; khối trích dẫn
    nằm CUỐI câu trả lời nên bị cắt mất → `parse_citations` trả `[]` → F1 = 0 vì lý
    do thuần kỹ thuật, không phải vì mô hình không biết luật.

    > Đính chính về xuất xứ: câu "**DO NOT use greedy decoding**, as it can lead to
    > performance degradation and endless repetitions" nằm trên model card
    > **Qwen3-8B** (hybrid-thinking) và chỉ áp cho *thinking mode*. Card của
    > `Qwen3-4B-Instruct-2507` KHÔNG có câu đó. Việc bỏ greedy vẫn đúng, nhưng căn cứ
    > là `do_sample: true` + bộ tham số khuyến nghị + cảnh báo "endless repetitions"
    > ở mục presence_penalty của chính card 2507 — không phải câu trích trên.

    ⚠️ **Đánh đổi tính tất định.** Kế hoạch §TASK-FT-02 ghi "temperature 0, seed cố
    định". Với `temperature > 0` thì tái lập chỉ còn ở mức *cùng seed + cùng build
    llama.cpp + cùng phần cứng → cùng đầu ra*, không còn là greedy tất định. Sinh
    vẫn có phương sai giữa các seed → ảnh hưởng cách đọc N=1 ở FT-06.

    ⚠️ **Chốt ở FT-03 rồi thì phải GIỐNG HỆT NHAU ở cả bốn ô của ma trận.** Khác
    tham số sinh giữa các ô là tự tạo confound, đúng loại làm hỏng mục 4.7.
    """

    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    min_p: float = 0.0
    # Card chỉ nêu dải hợp lệ 0–2, KHÔNG nêu giá trị mặc định → 1.0 là lựa chọn giữa
    # dải: đủ để dập lặp vô tận mà chưa tới vùng card cảnh báo trộn ngôn ngữ (đầu ra
    # bắt buộc là tiếng Việt nên trộn ngôn ngữ là rủi ro thật).
    presence_penalty: float = 1.0
    seed: int = 42
    max_new_tokens: int = MAX_NEW_TOKENS

    def as_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "min_p": self.min_p,
            "presence_penalty": self.presence_penalty,
            "seed": self.seed,
            "max_new_tokens": self.max_new_tokens,
            "greedy": self.temperature == 0.0,
        }


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

@dataclass
class Generation:
    text: str
    hit_token_cap: bool
    n_tokens_out: int | None = None
    # Số token prompt do CHÍNH backend báo (usage.prompt_tokens). Dùng đối chiếu với
    # số ta tự đếm — kiểm tra hạ tầng thứ ba mà §TASK-FT-03 quy trình (3) yêu cầu.
    n_tokens_prompt_backend: int | None = None


class Backend:
    """Giao diện tối thiểu mà replay cần. Model chốt ở FT-03, không phải ở đây."""

    name: str = "abstract"

    def generate(self, messages: list[dict], gp: GenParams) -> Generation:
        raise NotImplementedError

    def render_prompt(self, messages: list[dict]) -> tuple[str | None, str]:
        """Prompt ĐÃ RENDER qua chat template. Trả (chuỗi | None, tên_phương_pháp)."""
        return None, "khong-ho-tro"

    def count_prompt_tokens(self, messages: list[dict]) -> tuple[int | None, str]:
        """Số token của prompt đã render. Trả (số | None, tên_phương_pháp).

        None = backend không đo được → bỏ qua kiểm tràn n_ctx (có cảnh báo).
        """
        return None, "khong-ho-tro"


class MockBackend(Backend):
    """Trả chuỗi cố định. Dùng để verify toàn bộ đường đi schema mà không cần weights.

    `--model mock`            → chuỗi mặc định có 1 citation hợp lệ
    `--model mock:empty`      → chuỗi KHÔNG parse ra citation nào (test format_ok=False)
    `--model mock:cap`        → mô phỏng chạm trần token (test hit_token_cap)
    `--model mock:@path.txt`  → đọc chuỗi từ file
    """

    DEFAULT = ("Theo quy định, mức áp dụng là 250 m2 "
               "[Điều 3, Khoản 3, Văn bản quyet-dinh-69-2024-qd-ubnd-tp-hcm].")
    EMPTY = "Tôi không đủ thông tin để cung cấp câu trả lời chính xác cho bạn."

    def __init__(self, spec: str = "", token_counter=None) -> None:
        self.name = f"mock:{spec}" if spec else "mock"
        self._hit_cap = False
        # Mock KHÔNG tự bịa số token. Test bơm hàm đếm vào để kiểm logic chặn tràn;
        # mặc định None → replay bỏ qua kiểm tràn và nói rõ là đã bỏ qua.
        self._token_counter = token_counter
        if spec == "empty":
            self._text = self.EMPTY
        elif spec == "cap":
            self._text = self.DEFAULT[:40]
            self._hit_cap = True
        elif spec.startswith("@"):
            self._text = Path(spec[1:]).read_text(encoding="utf-8")
        else:
            self._text = self.DEFAULT

    def generate(self, messages: list[dict], gp: GenParams) -> Generation:
        assert messages and messages[0]["role"] == "system", "messages sai cấu trúc"
        assert messages[-1]["role"] == "user", "lượt cuối phải là user"
        return Generation(self._text, self._hit_cap, n_tokens_out=None)

    def render_prompt(self, messages: list[dict]) -> tuple[str | None, str]:
        # Không có chat template thật → nối thô, chỉ để soi bằng mắt.
        joined = "\n\n".join(f"<|{m['role']}|>\n{m['content']}" for m in messages)
        return joined, "mock-noi-tho"

    def count_prompt_tokens(self, messages: list[dict]) -> tuple[int | None, str]:
        if self._token_counter is None:
            return None, "khong-ho-tro"
        rendered, _ = self.render_prompt(messages)
        return self._token_counter(rendered), "mock-token-counter"


class LlamaCppBackend(Backend):
    """llama-cpp-python + GGUF. Import lazy — không cài cũng chạy được backend mock."""

    def __init__(self, model_path: str, n_ctx: int, n_gpu_layers: int,
                 gp: GenParams) -> None:
        from llama_cpp import Llama  # lazy

        self.name = f"llama-cpp:{Path(model_path).name}"
        self._n_ctx = n_ctx
        self._llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            seed=gp.seed,
            n_gpu_layers=n_gpu_layers,
            logits_all=False,
            verbose=False,
        )

    def generate(self, messages: list[dict], gp: GenParams) -> Generation:
        out = self._llm.create_chat_completion(
            messages=messages,
            temperature=gp.temperature,
            top_p=gp.top_p,
            top_k=gp.top_k,
            min_p=gp.min_p,
            presence_penalty=gp.presence_penalty,
            seed=gp.seed,
            max_tokens=gp.max_new_tokens,
        )
        choice = out["choices"][0]
        text = (choice["message"].get("content") or "").strip()
        hit_cap = choice.get("finish_reason") == "length"
        usage = out.get("usage") or {}
        return Generation(text, hit_cap, usage.get("completion_tokens"),
                          usage.get("prompt_tokens"))

    def render_prompt(self, messages: list[dict]) -> tuple[str | None, str]:
        """Render bằng ĐÚNG chat template nhúng trong file GGUF, qua jinja2.

        Cố ý KHÔNG gọi `llama_cpp.llama_chat_format` (API nội bộ, chữ ký đổi giữa các
        bản). Ta đọc thẳng `tokenizer.chat_template` trong metadata GGUF — chính
        chuỗi mà llama.cpp dùng — rồi render bằng jinja2.

        ⚠️ Đây là **tái dựng trung thực từ cùng một template**, không phải chuỗi
        llama.cpp thực sự nạp: bản dựng của llama.cpp có thể render bằng engine C++
        riêng và lệch ở chi tiết khoảng trắng. Đủ dùng cho mục đích của
        `--dump-prompt` (soi bằng mắt trước khi tiêu 548 lượt sinh) và cho việc ước
        lượng độ dài, nhưng đừng coi là byte-identical.

        Đường này CHƯA từng chạy với weights thật (Windows không có wheel dựng sẵn cho
        llama-cpp-python) → bọc try/except, hỏng thì lùi về đếm xấp xỉ, không làm
        chết cả mẻ chạy.
        """
        try:
            import jinja2

            meta = self._llm.metadata or {}
            tmpl = meta.get("tokenizer.chat_template")
            if not tmpl:
                return None, "gguf-khong-co-chat-template"

            def _tok(key: str) -> str:
                tid = meta.get(key)
                if tid is None:
                    return ""
                return self._llm.detokenize([int(tid)]).decode("utf-8", errors="ignore")

            env = jinja2.Environment(undefined=jinja2.StrictUndefined,
                                     trim_blocks=True, lstrip_blocks=True)
            rendered = env.from_string(tmpl).render(
                messages=messages,
                add_generation_prompt=True,
                bos_token=_tok("tokenizer.ggml.bos_token_id"),
                eos_token=_tok("tokenizer.ggml.eos_token_id"),
            )
            return rendered, "gguf-chat-template-jinja2"
        except Exception as e:  # noqa: BLE001 — hỏng thì lùi, không chết mẻ chạy
            return None, f"render-loi:{type(e).__name__}"

    def count_prompt_tokens(self, messages: list[dict]) -> tuple[int | None, str]:
        rendered, how = self.render_prompt(messages)
        try:
            if rendered is not None:
                return len(self._llm.tokenize(rendered.encode("utf-8"))), how
            # Lùi: cộng token từng message + phụ trội đánh dấu vai trò. XẤP XỈ, và
            # nói rõ là xấp xỉ — thà báo "gần đúng" còn hơn im lặng bỏ kiểm tràn.
            total = sum(len(self._llm.tokenize(m["content"].encode("utf-8")))
                        for m in messages)
            return total + 8 * len(messages) + 8, f"xap-xi({how})"
        except Exception as e:  # noqa: BLE001
            return None, f"dem-loi:{type(e).__name__}"


def make_backend(model: str, n_ctx: int, n_gpu_layers: int, gp: GenParams) -> Backend:
    if model == "mock" or model.startswith("mock:"):
        return MockBackend(model[5:] if model.startswith("mock:") else "")
    path = Path(model)
    if not path.exists():
        raise SystemExit(f"❌ Không tìm thấy model: {model} "
                         f"(dùng `--model mock` để verify schema không cần weights)")
    return LlamaCppBackend(str(path), n_ctx, n_gpu_layers, gp)


# ---------------------------------------------------------------------------
# Chặn tràn cửa sổ ngữ cảnh
# ---------------------------------------------------------------------------

class CtxOverflow(RuntimeError):
    """Prompt + phần sinh ra vượt n_ctx. Dừng hẳn, KHÔNG để llama.cpp cắt âm thầm."""


def check_ctx_budget(qid: str, n_prompt: int, max_new_tokens: int, n_ctx: int) -> None:
    """Prompt bị cắt âm thầm là lỗi không thể phát hiện về sau: câu trả lời vẫn có,
    vẫn parse được, chỉ là mô hình chưa từng nhìn thấy phần đầu ngữ cảnh. Chặn ngay.
    """
    need = n_prompt + max_new_tokens
    if need > n_ctx:
        raise CtxOverflow(
            f"{qid}: prompt {n_prompt} token + max_new_tokens {max_new_tokens} "
            f"= {need} > n_ctx {n_ctx}. llama.cpp sẽ cắt bớt ngữ cảnh mà KHÔNG báo. "
            f"Tăng --n-ctx (token_budget.md §2.7: 16384 đủ cho cả 127 câu GraphRAG) "
            f"hoặc giảm --max-new-tokens."
        )


# ---------------------------------------------------------------------------
# Chỉ báo chẩn đoán: soft_article_hit (bộ trích LỎNG)
# ---------------------------------------------------------------------------
# Kế hoạch §TASK-FT-03 "Hai chỉ báo chẩn đoán". `format_ok` là sàn rất thấp (chỉ cần
# 1 khối parse được) nên một mình nó không phân biệt hai kiểu hỏng rất khác nhau:
#
#   soft cao + format thấp → biết điều luật nào, không biết viết cú pháp
#                            → ĐÚNG thứ tinh chỉnh sửa được
#   soft thấp + format thấp → không định vị nổi điều luật trong ngữ cảnh 12k
#                            → ngoại lệ duy nhất được leo thang lên 8B (§9.5)
#
# ⚠️ BẮT BUỘC độc lập hoàn toàn với `parse_citations`: khi format_ok=0 thì
# `pred_citations` rỗng → nếu dựa vào nó, chỉ báo undefined ĐÚNG LÚC CẦN NHẤT.
# Vì vậy quét văn bản THÔ, không quan tâm ngoặc vuông, không quan tâm cú pháp.

_SOFT_DIEU_RE = re.compile(r"Điều\s+(\d+[a-zA-Z]?)", re.IGNORECASE)
_SOFT_KHOAN_RE = re.compile(r"Khoản\s+(\d+)", re.IGNORECASE)
# Slug: chuỗi thường/số/gạch ngang dài ≥15, không dính vào token dài hơn.
# KHÔNG dùng IGNORECASE — slug theo convention luôn là chữ thường.
_SOFT_SLUG_RE = re.compile(r"(?<![a-z0-9-])[a-z0-9-]{15,}(?![a-z0-9-])")


def soft_article_mentions(text: str) -> dict[str, set[str]]:
    """Trích LỎNG mọi cụm định vị điều luật từ văn bản thô, bất kể cú pháp."""
    return {
        "dieu": {m.group(1).lower() for m in _SOFT_DIEU_RE.finditer(text)},
        "khoan": {m.group(1) for m in _SOFT_KHOAN_RE.finditer(text)},
        "slug": set(_SOFT_SLUG_RE.findall(text)),
    }


def _mention_in_context(kind: str, value: str, context: str) -> bool:
    if kind == "slug":
        return value in context
    word = "Điều" if kind == "dieu" else "Khoản"
    # Chặn "Điều 116" khớp nhầm vào "Điều 1160".
    return re.search(rf"{word}\s+{re.escape(value)}(?![0-9])", context,
                     re.IGNORECASE) is not None


def soft_article_report(answer: str, context: str) -> dict:
    """Đối chiếu cụm trích lỏng trong câu trả lời với ngữ cảnh của CHÍNH item đó.

    `hit_rate` = tỉ lệ cụm được nhắc mà thực sự có mặt trong ngữ cảnh.
    None khi câu trả lời không nhắc cụm nào (từ chối trả lời, câu hằng số) —
    None chứ KHÔNG phải 0.0, vì "không nhắc gì" khác "nhắc toàn thứ bịa".
    """
    found = soft_article_mentions(answer)
    detail, n_total, n_hit = {}, 0, 0
    for kind, values in found.items():
        hits = {v for v in values if _mention_in_context(kind, v, context)}
        detail[kind] = {"n": len(values), "n_hit": len(hits),
                        "miss": sorted(values - hits)[:10]}
        n_total += len(values)
        n_hit += len(hits)
    return {
        "n_mentions": n_total,
        "n_hit": n_hit,
        "hit_rate": (n_hit / n_total) if n_total else None,
        "theo_loai": detail,
    }


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# aggregate() truy cập trực tiếp bằng [...] → thiếu là KeyError.
_REQUIRED = ("gap_type", "theme", "citation_score", "norm_recall", "elapsed_seconds")
# aggregate() dùng .get() cho citation_score_dieu → THIẾU KHÔNG RAISE mà làm cột
# "F1 cấp Điều" ra 0.000 IM LẶNG (metrics.py:213-215). Một trong bốn cột báo cáo
# sai mà không có dấu hiệu gì → phải assert tay.
_REQUIRED_SILENT = ("citation_score_dieu",)
_SCORE_KEYS = ("precision", "recall", "f1")


def _non_finite(obj) -> bool:
    """True nếu có NaN/Inf ở bất cứ đâu. File gốc có 118 literal NaN → JSON không chuẩn."""
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(_non_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_non_finite(v) for v in obj)
    return False


def assert_schema(item: dict) -> None:
    """Chặn TRƯỚC khi ghi. Kế hoạch: sai schema thì sửa replay.py, KHÔNG sửa src/."""
    qid = item.get("id", "?")
    for k in _REQUIRED:
        assert k in item, f"{qid}: thiếu '{k}' → metrics.aggregate sẽ KeyError"
    for k in _REQUIRED_SILENT:
        assert k in item, f"{qid}: thiếu '{k}' → cột F1 cấp Điều ra 0.000 IM LẶNG"
    for k in ("citation_score", "citation_score_dieu"):
        for s in _SCORE_KEYS:
            assert s in item[k], f"{qid}: {k} thiếu '{s}'"
    if item["gap_type"] == "negative":
        assert item.get("negative_correct") is not None, (
            f"{qid}: gap_type='negative' mà negative_correct=None → aggregate KeyError"
        )
    assert item["faithfulness"] is None, f"{qid}: faithfulness phải null (không đo tỉ lệ hậu thuẫn)"
    assert not _non_finite(item), f"{qid}: có NaN/Inf → JSON không chuẩn"


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def summarize(results: list[dict]) -> dict:
    """Thống kê dẫn xuất TỪ results, không tích luỹ theo lượt chạy.

    Quan trọng với `--resume`: nếu đếm trong vòng lặp thì item lấy lại từ file
    .partial.jsonl không được tính, metadata sẽ báo thiếu.
    """
    den = [r for r in results if r["gt_nonempty"]]  # 123/137 — kế hoạch §3.1
    cap = [r["id"] for r in results if r["hit_token_cap"]]
    plens = [r["n_tokens_prompt"] for r in results if r.get("n_tokens_prompt") is not None]
    # soft_article_hit: bỏ qua item không nhắc cụm nào (None), không coi là 0.
    soft = [r["soft_article_hit"] for r in results if r.get("soft_article_hit") is not None]
    return {
        "soft_article_hit_mean": (sum(soft) / len(soft)) if soft else None,
        "soft_article_hit_do_duoc": len(soft),
        "soft_article_mentions_tong": sum(r["soft_article"]["n_mentions"]
                                          for r in results if "soft_article" in r),
        "n_qua_mo_hinh": sum(1 for r in results if not r["frozen_copy"]),
        "n_sao_chep_hang_so": sum(1 for r in results if r["frozen_copy"]),
        "n_hit_token_cap": len(cap),
        "ids_hit_token_cap": cap,
        "format_ok_rate": (sum(1 for r in den if r["format_ok"]) / len(den)) if den else None,
        "format_ok_mau_so": len(den),
        "prompt_tokens_max": max(plens) if plens else None,
        "prompt_tokens_do_duoc": len(plens),
        # Kiểm hạ tầng §TASK-FT-03(3): ta tự đếm vs backend tự báo. Lệch lớn = chat
        # template ta tái dựng khác cái backend thực nạp → prompt không như ta tưởng.
        "prompt_len_lech_max": max(
            (abs(r["prompt_len_lech"]) for r in results
             if r.get("prompt_len_lech") is not None), default=None),
    }


def build_chat_messages(question: str, context: str, mode: str, n_shot: int) -> list[dict]:
    """(system, user) từ build_messages + n_shot cặp minh hoạ định dạng chèn giữa."""
    system_prompt, user_prompt = build_messages(question, context, mode)
    msgs: list[dict] = [{"role": "system", "content": system_prompt}]
    for shot_user, shot_assistant in _FEWSHOT[:n_shot]:
        msgs.append({"role": "user", "content": shot_user})
        msgs.append({"role": "assistant", "content": shot_assistant})
    msgs.append({"role": "user", "content": user_prompt})
    return msgs


def replay_item(src: dict, mode: str, backend: Backend, n_shot: int,
                gp: GenParams, n_ctx: int = DEFAULT_N_CTX) -> dict:
    """Phát lại một câu. Truy hồi (context/top_k_count) copy nguyên từ nguồn."""
    qid = src["id"]
    gt = src.get("ground_truth_citations", [])
    frozen = src["top_k_count"] == 0
    n_prompt: int | None = None
    how_prompt = "khong-do"

    if frozen:
        # Sao chép hằng số. KHÔNG đưa qua mô hình (§9.1).
        assert src["answer"] == FROZEN_ANSWER, (
            f"{qid}: top_k_count=0 nhưng answer không phải hằng số pipeline.py:233 — "
            f"file nguồn không đúng như giả định của FT-00"
        )
        answer, hit_cap, elapsed, n_out = FROZEN_ANSWER, False, 0.0, None
        n_prompt_backend = None
    else:
        msgs = build_chat_messages(src["question"], src["context"], mode, n_shot)
        # Đo TRƯỚC khi gọi: tràn thì dừng hẳn, không để llama.cpp cắt âm thầm.
        n_prompt, how_prompt = backend.count_prompt_tokens(msgs)
        if n_prompt is not None:
            check_ctx_budget(qid, n_prompt, gp.max_new_tokens, n_ctx)
        t0 = time.perf_counter()
        gen = backend.generate(msgs, gp)
        elapsed = round(time.perf_counter() - t0, 3)
        answer, hit_cap, n_out = gen.text, gen.hit_token_cap, gen.n_tokens_out
        n_prompt_backend = gen.n_tokens_prompt_backend

    citations = parse_citations(answer)

    # format_ok: chỉ có nghĩa trên tập câu ĐƯỢC KỲ VỌNG có trích dẫn (§3.1).
    gt_nonempty = bool(gt)
    format_ok = len(citations) >= 1
    # Độc lập với parse_citations — xem chú thích ở soft_article_report().
    soft = soft_article_report(answer, src["context"])

    cs_khoan = citation_score(citations, gt, level="khoan")
    cs_dieu = citation_score(citations, gt, level="dieu")

    return {
        # --- 20 key của schema hiện tại (run_evaluation.py:258-279) ---
        "id": qid,
        "question": src["question"],
        "gap_type": src["gap_type"],
        "theme": src["theme"],
        "jurisdiction": src["jurisdiction"],
        "difficulty": src["difficulty"],
        "system": src["system"],          # giữ tên hệ NGUỒN → so được với hàng Gemini
        "answer": answer,
        "pred_citations": citations,
        "ground_truth_citations": gt,
        "citation_score": cs_khoan,
        "citation_score_dieu": cs_dieu,
        "norm_recall": norm_recall(citations, gt),
        "negative_correct": (negative_correct(citations, src["gap_type"])
                             if src["gap_type"] == "negative" else None),
        "faithfulness": None,             # không đo tỉ lệ hậu thuẫn → null, KHÔNG NaN
        "elapsed_seconds": elapsed,
        "context_used": bool(src["context"].strip()),
        "top_k_count": src["top_k_count"],
        "context": src["context"],        # truy hồi đóng băng: copy nguyên
        "verifier": None,
        # --- field phụ của replay (aggregate bỏ qua) ---
        "response_mode": mode,
        "format_ok": format_ok,
        "soft_article_hit": soft["hit_rate"],   # chỉ báo chẩn đoán, §TASK-FT-03
        "soft_article": soft,
        "gt_nonempty": gt_nonempty,
        "hit_token_cap": hit_cap,
        "n_tokens_out": n_out,
        "n_tokens_prompt": n_prompt,       # log độ dài prompt TỪNG item (ta tự đếm)
        "prompt_len_method": how_prompt,
        "n_tokens_prompt_backend": n_prompt_backend,   # backend tự báo — để đối chiếu
        "prompt_len_lech": (None if (n_prompt is None or n_prompt_backend is None)
                            else n_prompt - n_prompt_backend),
        "frozen_copy": frozen,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="TASK-FT-02 — phát lại với mô hình sinh khác")
    ap.add_argument("--input", required=True, type=Path,
                    help="results JSON nguồn trong data/evaluation/ (CHỈ ĐỌC)")
    ap.add_argument("--model", required=True,
                    help="đường dẫn GGUF, hoặc 'mock' / 'mock:empty' / 'mock:cap' / 'mock:@file'")
    ap.add_argument("--out", type=Path, default=None, help="file JSON đầu ra")
    ap.add_argument("--limit", type=int, default=0, help="chỉ chạy N câu đầu (0 = full)")
    ap.add_argument("--ids", default="",
                    help="chỉ chạy các id này, cách bởi dấu phẩy (vd cho gate FT-03: "
                         "lấy từ finetune/data/gate_ids.json). Loại trừ với --limit.")
    ap.add_argument("--n-shot", type=int, default=0, choices=[0, 1, 2],
                    help="số ví dụ minh hoạ định dạng; PHẢI giống nhau ở cả bốn ô")
    ap.add_argument("--resume", action="store_true", help="bỏ qua item đã có trong file .partial.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    ap.add_argument("--n-ctx", type=int, default=DEFAULT_N_CTX)
    ap.add_argument("--n-gpu-layers", type=int, default=-1, help="-1 = đẩy hết lên GPU")
    ap.add_argument("--tag", default="", help="nhãn thêm vào tên file đầu ra")
    ap.add_argument("--dump-prompt", type=Path, default=None,
                    help="ghi prompt ĐÃ RENDER của item đầu tiên ra file rồi soi bằng mắt")

    _d = GenParams()
    g = ap.add_argument_group(
        "tham số sinh",
        "Mặc định = khuyến nghị Qwen cho Qwen3-4B-Instruct-2507. Đổi được để FT-03 "
        "thử nhiều ứng viên — nhưng CHỐT XONG thì phải GIỐNG HỆT ở cả bốn ô.",
    )
    g.add_argument("--temperature", type=float, default=_d.temperature)
    g.add_argument("--top-p", type=float, default=_d.top_p)
    g.add_argument("--top-k", type=int, default=_d.top_k)
    g.add_argument("--min-p", type=float, default=_d.min_p)
    g.add_argument("--presence-penalty", type=float, default=_d.presence_penalty)
    args = ap.parse_args()

    gp = GenParams(
        temperature=args.temperature, top_p=args.top_p, top_k=args.top_k,
        min_p=args.min_p, presence_penalty=args.presence_penalty,
        seed=args.seed, max_new_tokens=args.max_new_tokens,
    )
    if gp.temperature == 0.0:
        print("⚠️  temperature=0 (greedy). Qwen khuyến nghị do_sample=true; greedy dễ "
              "sinh lặp vô tận → chạm max_new_tokens → mất khối trích dẫn ở cuối → F1=0 "
              "vì lý do kỹ thuật.")

    if not args.input.exists():
        print(f"❌ Không có file nguồn: {args.input}", file=sys.stderr)
        return 2
    if args.ids and args.limit > 0:
        print("❌ --ids và --limit loại trừ nhau: --limit cắt N câu ĐẦU (không phân "
              "tầng), --ids chọn đúng danh sách. Dùng cả hai thì không rõ ý định.",
              file=sys.stderr)
        return 2

    src_data = json.loads(args.input.read_text(encoding="utf-8"))
    system = src_data["system"]
    items = src_data["results"]
    if args.ids:
        want = [s.strip() for s in args.ids.split(",") if s.strip()]
        have = {it["id"] for it in items}
        missing = [q for q in want if q not in have]
        if missing:
            print(f"❌ --ids có id không tồn tại trong {args.input.name}: {missing}",
                  file=sys.stderr)
            return 2
        want_set = set(want)
        # Giữ THỨ TỰ NGUỒN, không theo thứ tự gõ trên CLI → hai lần chạy cùng bộ id
        # cho cùng thứ tự item trong file kết quả.
        items = [it for it in items if it["id"] in want_set]
        print(f"--ids: chọn {len(items)}/{len(src_data['results'])} câu")
    elif args.limit > 0:
        items = items[: args.limit]

    mode_data = json.loads(MODE_MAP_PATH.read_text(encoding="utf-8"))
    mode_map = mode_data["he_thong"][system]["mode_map"]
    # Cột baseline luôn general — TẤT ĐỊNH theo run_evaluation.py:93, không phải suy luận.
    if system == "baseline":
        assert set(mode_map.values()) == {"general"}, "mode_map baseline phải toàn general"

    # Kiểm chéo file nguồn với phát hiện của FT-00: đúng 10 câu hằng số, đúng id đó.
    # (Chỉ kiểm khi chạy FULL — có --limit thì tập con đương nhiên không khớp.)
    if system == "graphrag" and args.limit == 0 and not args.ids:
        found = {it["id"] for it in items if it["top_k_count"] == 0}
        assert found == FROZEN_IDS, (
            f"File nguồn có tập câu hằng số khác FT-00 đã ghi: "
            f"thừa {sorted(found - FROZEN_IDS)}, thiếu {sorted(FROZEN_IDS - found)}"
        )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_tag = Path(args.model).stem.replace(".", "-") if "mock" not in args.model else "mock"
    suffix = f"_{args.tag}" if args.tag else ""
    out_path = args.out or (DEFAULT_OUT_DIR /
                            f"results_{system}_{model_tag}{suffix}_{timestamp}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = out_path.with_suffix(".partial.jsonl")

    done: dict[str, dict] = {}
    if args.resume and partial_path.exists():
        for line in partial_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["id"]] = rec
        print(f"RESUME: đã có {len(done)} item trong {partial_path.name}")
    elif partial_path.exists():
        partial_path.unlink()

    backend = make_backend(args.model, args.n_ctx, args.n_gpu_layers, gp)
    print(f"backend={backend.name} n_shot={args.n_shot} n_ctx={args.n_ctx} "
          f"INCLUDE_SCHEMA_B=False")
    print(f"  tham số sinh: {json.dumps(gp.as_dict(), ensure_ascii=False)}")

    # --dump-prompt: đường llama-cpp chưa từng chạy với weights thật → nhìn tận mắt
    # prompt đã render TRƯỚC khi tiêu 548 lượt sinh.
    if args.dump_prompt:
        first = next((s for s in items if s["top_k_count"] > 0), None)
        if first is None:
            print("  --dump-prompt: không có item nào qua mô hình để dump")
        else:
            msgs = build_chat_messages(first["question"], first["context"],
                                       mode_map[first["id"]], args.n_shot)
            rendered, how = backend.render_prompt(msgs)
            n_tok, how_tok = backend.count_prompt_tokens(msgs)
            args.dump_prompt.parent.mkdir(parents=True, exist_ok=True)
            header = (f"# item={first['id']}  mode={mode_map[first['id']]}  "
                      f"n_shot={args.n_shot}\n"
                      f"# backend={backend.name}  render={how}  "
                      f"do_dai={n_tok} token ({how_tok})  n_ctx={args.n_ctx}\n"
                      f"# tham so sinh={json.dumps(gp.as_dict(), ensure_ascii=False)}\n"
                      + "#" * 70 + "\n")
            body = rendered if rendered is not None else json.dumps(
                msgs, ensure_ascii=False, indent=2)
            args.dump_prompt.write_text(header + body, encoding="utf-8")
            print(f"  --dump-prompt → {args.dump_prompt} "
                  f"(render={how}, {n_tok} token)")

    # Thăm dò một lần: backend có đo được độ dài prompt không? Nếu không thì việc
    # bỏ qua kiểm tràn phải được NÓI RA, không im lặng.
    _probe = next((s for s in items if s["top_k_count"] > 0), None)
    if _probe is not None:
        _n, _how = backend.count_prompt_tokens(
            build_chat_messages(_probe["question"], _probe["context"],
                                mode_map[_probe["id"]], args.n_shot))
        if _n is None:
            print(f"  ⚠️  backend không đo được độ dài prompt ({_how}) → BỎ QUA kiểm "
                  f"tràn n_ctx. Chấp nhận được với mock; với weights thật thì không.")
        else:
            print(f"  kiểm tràn n_ctx: BẬT (phương pháp {_how}, "
                  f"ngưỡng {args.n_ctx} - {gp.max_new_tokens} = "
                  f"{args.n_ctx - gp.max_new_tokens} token cho prompt)")

    results: list[dict] = []
    with partial_path.open("a", encoding="utf-8") as fh:
        for i, src in enumerate(items, 1):
            qid = src["id"]
            if qid in done:
                results.append(done[qid])
                continue
            item = replay_item(src, mode_map[qid], backend, args.n_shot, gp, args.n_ctx)
            assert_schema(item)
            # Ghi NGAY khi xong → --resume dùng lại được nếu đứt giữa chừng.
            fh.write(json.dumps(item, ensure_ascii=False, allow_nan=False) + "\n")
            fh.flush()
            results.append(item)
            flag = " CAP!" if item["hit_token_cap"] else ""
            plen = ("" if item["n_tokens_prompt"] is None
                    else f" prompt={item['n_tokens_prompt']}tok")
            print(f"  [{i}/{len(items)}] {qid} mode={item['response_mode']:7s}"
                  f"{plen} cit={len(item['pred_citations'])} "
                  f"F1={item['citation_score']['f1']:.2f}{flag}")

    agg = aggregate(results)
    summary = summarize(results)
    fmt_rate = summary["format_ok_rate"]

    payload = {
        "system": system,
        "test_set": src_data.get("test_set"),
        "timestamp": timestamp,
        "total_elapsed_s": round(sum(r["elapsed_seconds"] for r in results), 2),
        "replay": {
            "nguon": str(args.input).replace("\\", "/"),
            "ids_loc": args.ids or None,
            "backend": backend.name,
            "model": args.model,
            "gen_params": gp.as_dict(),   # TOÀN BỘ tham số sinh
            "n_shot": args.n_shot,
            "n_ctx": args.n_ctx,
            "include_schema_b": False,
            "prompt_builder": "build_messages",
            **summary,
        },
        "results": results,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
                        encoding="utf-8")

    print(f"\nĐã ghi {out_path}")
    print(f"  qua mô hình={summary['n_qua_mo_hinh']}  "
          f"sao chép hằng số={summary['n_sao_chep_hang_so']}")
    print(f"  format_ok_rate={fmt_rate if fmt_rate is None else f'{fmt_rate:.3f}'} "
          f"(mẫu số {summary['format_ok_mau_so']} câu GT khác rỗng)")
    sm = summary["soft_article_hit_mean"]
    print(f"  soft_article_hit={sm if sm is None else f'{sm:.3f}'} "
          f"({summary['soft_article_hit_do_duoc']} câu có nhắc điều luật, "
          f"{summary['soft_article_mentions_tong']} cụm)")
    if summary["n_hit_token_cap"]:
        print(f"  ⚠️  CHẠM TRẦN TOKEN {summary['n_hit_token_cap']} câu: "
              f"{summary['ids_hit_token_cap']}\n"
              f"      Khối trích dẫn nằm CUỐI câu trả lời → mọi con số của ô này "
              f"phải đọc lại trước khi đưa vào bảng.")
    else:
        print("  hit_token_cap: 0 câu")
    line = (f"  aggregate: F1_khoan={agg['f1_mean']:.3f} "
            f"F1_dieu={agg['f1_dieu_mean']:.3f} NormR={agg['norm_recall_mean']:.3f}")
    if "negative_correct_rate" in agg:
        line += (f" tu_choi_dung={agg['negative_correct_rate']:.3f}"
                 f" ({agg['negative_count']} câu)")
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
