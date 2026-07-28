"""
Ablation config (E1) — cấu hình tắt từng cơ chế KG để chạy double dissociation.

Triết lý (docs/EVALUATION_ARCHITECTURE.md §E1): mỗi ablation = Full GraphRAG
TẮT ĐÚNG MỘT thành phần, cắt ở CẤP CẠNH graph để tránh confound. Mỗi ablation
phải sụp ĐÚNG gap tương ứng và ổn định ở gap khác.

Bản đồ ablation → gap → điểm cắt:
  no-theme        Gap 1  Stage 1: bỏ FieldCondition(theme) trong Qdrant
  no-jurisdiction Gap 2  Stage 2: allowed = mọi tỉnh (bỏ hard-filter APPLIES_TO)
  no-implements   Gap 3  Stage 2: traversal chỉ còn [:AMENDS] (bỏ IMPLEMENTS)
  no-amends       Gap 4a Stage 2: traversal chỉ còn [:IMPLEMENTS] (bỏ AMENDS)
  no-temporal     Gap 4b Stage 2: temporal=None → tắt lọc CTV valid_from/to
  no-traversal    (sàn)  Stage 2: chỉ seed norm, không mở rộng *1..4
  dense-only      (sàn)  Bỏ toàn bộ mở rộng graph + graph-boost (chỉ Stage 1 dense)

Mặc định = FULL (không tắt gì) → hành vi pipeline KHÔNG đổi.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AblationConfig:
    name: str = "full"
    no_theme: bool = False          # Gap 1
    no_jurisdiction: bool = False   # Gap 2
    no_implements: bool = False     # Gap 3
    no_amends: bool = False         # Gap 4a
    no_temporal: bool = False       # Gap 4b
    no_traversal: bool = False      # sàn: không mở rộng graph
    dense_only: bool = False        # sàn: bỏ toàn bộ KG

    @property
    def traversal_rels(self) -> list[str]:
        """Danh sách quan hệ dùng cho traversal Stage 2 (rỗng = chỉ seed)."""
        if self.no_traversal or self.dense_only:
            return []
        rels = []
        if not self.no_implements:
            rels.append("IMPLEMENTS")
        if not self.no_amends:
            rels.append("AMENDS")
        return rels

    @property
    def gap_target(self) -> str | None:
        """Gap mà ablation này KỲ VỌNG làm sụp (để chấm double dissociation)."""
        return {
            "no-theme": "gap1", "no-jurisdiction": "gap2",
            "no-implements": "gap3", "no-amends": "gap4", "no-temporal": "gap4",
        }.get(self.name)


FULL = AblationConfig(name="full")

# 5 ablation cốt lõi cho double-dissociation E1 + 2 sàn tham chiếu
ABLATIONS: dict[str, AblationConfig] = {
    "full": FULL,
    "no-theme": AblationConfig(name="no-theme", no_theme=True),
    "no-jurisdiction": AblationConfig(name="no-jurisdiction", no_jurisdiction=True),
    "no-implements": AblationConfig(name="no-implements", no_implements=True),
    "no-amends": AblationConfig(name="no-amends", no_amends=True),
    "no-temporal": AblationConfig(name="no-temporal", no_temporal=True),
    "no-traversal": AblationConfig(name="no-traversal", no_traversal=True),
    "dense-only": AblationConfig(name="dense-only", dense_only=True),
}


def get_ablation(name: str | None) -> AblationConfig:
    """Trả về AblationConfig theo tên (None/'full' → FULL). Raise nếu tên lạ."""
    if name is None:
        return FULL
    if name not in ABLATIONS:
        raise ValueError(
            f"Ablation '{name}' không hợp lệ. Chọn: {', '.join(ABLATIONS)}"
        )
    return ABLATIONS[name]
