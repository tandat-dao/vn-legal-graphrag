"""
Kiểm tra metadata và format của tất cả file data/raw/*.md trong Phase 1.

Cách dùng:
    python src/utils/validate_metadata.py data/raw/
    python src/utils/validate_metadata.py data/raw/ --check-duplicates
    python src/utils/validate_metadata.py data/raw/ --file luat-dat-dai-2024.md
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Các hằng số hợp lệ (theo CLAUDE.md — danh sách đóng)
# ---------------------------------------------------------------------------

VALID_THEMES = {"dat-dai", "ho-tich", "nuoi-con-nuoi"}
VALID_JURISDICTIONS = {"toan-quoc", "tp-hcm", "dong-nai"}
VALID_TIERS = {1, 2, 3, 4}

# Các file phụ trợ — không phải văn bản pháp luật, bỏ qua khi validate
NON_LEGAL_FILES = {
    "mapping_table.md",
    "specified_in_map.md",
    "crossref_decisions.md",
    "review_log.md",
    "formatted_temp.md",
}

REQUIRED_FIELDS = [
    "id",
    "title",
    "tier",
    "theme",
    "jurisdiction",
    "implements",
    "valid_from",
    "valid_to",
    "source_url",
    "source_vbhn",
    "amended_by_norms",
    "summary",
]

# Regex: heading hợp lệ bắt đầu bằng ##, ###, ####, #####
VALID_HEADING_PATTERN = re.compile(r"^#{2,5} ")
# Heading cấp 1 (# Điều) — bị cấm
FORBIDDEN_H1 = re.compile(r"^# [^\s]")
# Heading Chương/Mục — bị cấm
FORBIDDEN_CHUONG_MUC = re.compile(r"^#{1,6} (Chương|Mục) ")
# Khoản ở cấp ## — sai (phải là ###)
WRONG_KHOAN_LEVEL = re.compile(r"^## Khoản ")
# Separator --- bên trong body (không phải frontmatter)
SEPARATOR_IN_BODY = re.compile(r"^---\s*$")
# Watermark phổ biến từ vbpl.vn / congbao
WATERMARK_PATTERN = re.compile(r"CÔNG BÁO.*Số.*Ngày", re.IGNORECASE)
# Định dạng ngày hợp lệ
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# ID convention
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


# ---------------------------------------------------------------------------
# Phân tích file
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """Tách YAML frontmatter và phần body của file .md."""
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    yaml_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    return yaml_block, body


def parse_frontmatter(yaml_block: str) -> tuple[dict, str | None]:
    """Parse YAML, trả về (metadata_dict, lỗi_nếu_có)."""
    try:
        data = yaml.safe_load(yaml_block)
        if not isinstance(data, dict):
            return {}, "Frontmatter không phải YAML dictionary hợp lệ"
        return data, None
    except yaml.YAMLError as e:
        return {}, f"YAML parse error: {e}"


# ---------------------------------------------------------------------------
# Các hàm kiểm tra
# ---------------------------------------------------------------------------

def check_frontmatter(meta: dict, filename: str) -> list[str]:
    errors = []

    # 1. Trường bắt buộc
    for field in REQUIRED_FIELDS:
        if field not in meta:
            errors.append(f"[Frontmatter] Thiếu trường bắt buộc: `{field}`")

    # 2. id — convention và không trùng (uniqueness check ở cấp global)
    id_val = meta.get("id")
    if id_val is not None:
        if not isinstance(id_val, str):
            errors.append("[Frontmatter] `id` phải là string")
        elif not ID_PATTERN.match(id_val):
            errors.append(
                f"[Frontmatter] `id` sai convention: '{id_val}' "
                "(chỉ dùng chữ thường, chữ số, dấu gạch ngang)"
            )
        # Kiểm tra id khớp tên file
        expected_stem = Path(filename).stem
        if id_val != expected_stem:
            errors.append(
                f"[Frontmatter] `id` ('{id_val}') không khớp tên file ('{expected_stem}')"
            )

    # 3. title
    if "title" in meta and not isinstance(meta["title"], str):
        errors.append("[Frontmatter] `title` phải là string")

    # 4. tier
    tier = meta.get("tier")
    if tier is not None and tier not in VALID_TIERS:
        errors.append(f"[Frontmatter] `tier` không hợp lệ: {tier!r} — chỉ nhận 1, 2, 3, 4")

    # 5. theme
    theme = meta.get("theme")
    if theme is not None and theme not in VALID_THEMES:
        errors.append(
            f"[Frontmatter] `theme` không hợp lệ: '{theme}' "
            f"— chỉ nhận {sorted(VALID_THEMES)}"
        )

    # 6. jurisdiction
    jurisdiction = meta.get("jurisdiction")
    if jurisdiction is not None and jurisdiction not in VALID_JURISDICTIONS:
        errors.append(
            f"[Frontmatter] `jurisdiction` không hợp lệ: '{jurisdiction}' "
            f"— chỉ nhận {sorted(VALID_JURISDICTIONS)}"
        )

    # 6b. implements — null, string, hoặc list of string (đa cha — D-23)
    #     Một văn bản có thể hướng dẫn thi hành đồng thời nhiều văn bản cha
    #     (VD: TT 04/2020 implements cả NĐ 123/2015 lẫn Luật Hộ tịch 2014).
    implements = meta.get("implements")
    if implements is not None:
        if isinstance(implements, list):
            if len(implements) == 0:
                errors.append(
                    "[Frontmatter] `implements` là list rỗng — dùng null nếu không có văn bản cha"
                )
            for item in implements:
                if not isinstance(item, str):
                    errors.append(
                        f"[Frontmatter] `implements` chứa giá trị không phải string: {item!r}"
                    )
        elif not isinstance(implements, str):
            errors.append(
                "[Frontmatter] `implements` phải là string, list string, hoặc null "
                f"(hiện tại là {type(implements).__name__}: {implements!r})"
            )

    # 7. valid_from — bắt buộc phải có và đúng format
    valid_from = meta.get("valid_from")
    if valid_from is not None:
        if not isinstance(valid_from, str) or not DATE_PATTERN.match(valid_from):
            errors.append(
                f"[Frontmatter] `valid_from` sai format: '{valid_from}' — cần YYYY-MM-DD"
            )

    # 8. valid_to — null hoặc đúng format
    valid_to = meta.get("valid_to")
    if valid_to is not None:
        if not isinstance(valid_to, str) or not DATE_PATTERN.match(valid_to):
            errors.append(
                f"[Frontmatter] `valid_to` sai format: '{valid_to}' — cần YYYY-MM-DD hoặc null"
            )

    # 9. amended_by_norms — list hoặc null
    amended = meta.get("amended_by_norms")
    if amended is not None:
        if not isinstance(amended, list):
            errors.append(
                "[Frontmatter] `amended_by_norms` phải là list hoặc null "
                f"(hiện tại là {type(amended).__name__}: {amended!r})"
            )
        else:
            for item in amended:
                if not isinstance(item, str):
                    errors.append(
                        f"[Frontmatter] `amended_by_norms` chứa giá trị không phải string: {item!r}"
                    )

    # 10. source_url — phải có và là string
    source_url = meta.get("source_url")
    if source_url is not None and not isinstance(source_url, str):
        errors.append("[Frontmatter] `source_url` phải là string")

    # 11. summary — string hoặc null; cảnh báo nếu null (cần điền trước TASK-05)
    summary = meta.get("summary")
    if summary is not None and not isinstance(summary, str):
        errors.append("[Frontmatter] `summary` phải là string hoặc null")
    elif summary is None:
        errors.append("[Frontmatter] `summary` chưa được điền — cần viết 3-5 câu mô tả phạm vi văn bản trước TASK-05")

    return errors


def check_body(body: str, filename: str) -> list[str]:
    errors = []
    lines = body.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # Heading cấp 1 bị cấm
        if FORBIDDEN_H1.match(line):
            errors.append(f"[Heading] Dòng {lineno}: heading cấp # bị cấm — '{line.strip()}'")

        # Chương / Mục bị cấm
        if FORBIDDEN_CHUONG_MUC.match(line):
            errors.append(
                f"[Heading] Dòng {lineno}: tiêu đề Chương/Mục bị cấm — '{line.strip()}'"
            )

        # ## Khoản — sai cấp
        if WRONG_KHOAN_LEVEL.match(line):
            errors.append(
                f"[Heading] Dòng {lineno}: `## Khoản` sai cấp — phải là `### Khoản` — '{line.strip()}'"
            )

        # Separator --- trong body
        if SEPARATOR_IN_BODY.match(line):
            errors.append(
                f"[Body] Dòng {lineno}: dấu phân cách `---` không được phép trong body"
            )

        # Watermark
        if WATERMARK_PATTERN.search(line):
            errors.append(
                f"[Watermark] Dòng {lineno}: có thể còn watermark — '{line.strip()[:80]}'"
            )

    # Kiểm tra file phải có ít nhất 1 heading ## Điều hoặc ## Phụ lục
    has_content_heading = any(
        re.match(r"^## (Điều|Phụ lục)", line) for line in lines
    )
    if not has_content_heading:
        errors.append("[Body] Không tìm thấy heading `## Điều` hoặc `## Phụ lục` — file có thể trống")

    return errors


def check_spacing(body: str) -> list[str]:
    """Kiểm tra quy tắc 1 dòng trống giữa heading và nội dung."""
    errors = []
    lines = body.splitlines()

    for i, line in enumerate(lines):
        is_heading = re.match(r"^#{2,5} ", line)
        if not is_heading:
            continue

        # Sau heading phải là dòng trống (nếu không phải cuối file)
        if i + 1 < len(lines) and lines[i + 1].strip() != "":
            next_line = lines[i + 1]
            # Cho phép ngay sau heading là heading khác (cấp sâu hơn) — sẽ báo riêng
            if not re.match(r"^#{2,5} ", next_line):
                errors.append(
                    f"[Spacing] Dòng {i + 2}: thiếu dòng trống sau heading "
                    f"'{line.strip()[:60]}'"
                )

    return errors


# ---------------------------------------------------------------------------
# Kiểm tra toàn bộ 1 file
# ---------------------------------------------------------------------------

def validate_file(filepath: Path) -> tuple[dict | None, list[str]]:
    """
    Trả về (metadata, danh_sách_lỗi).
    metadata là None nếu không parse được frontmatter.
    """
    errors = []
    text = filepath.read_text(encoding="utf-8")

    yaml_block, body = split_frontmatter(text)
    if not yaml_block:
        errors.append("[Frontmatter] Không tìm thấy YAML frontmatter (thiếu dấu ---)")
        return None, errors

    meta, parse_err = parse_frontmatter(yaml_block)
    if parse_err:
        errors.append(f"[Frontmatter] {parse_err}")
        return None, errors

    errors.extend(check_frontmatter(meta, filepath.name))
    errors.extend(check_body(body, filepath.name))
    errors.extend(check_spacing(body))

    return meta, errors


# ---------------------------------------------------------------------------
# Kiểm tra global: id duy nhất + implements trỏ đúng
# ---------------------------------------------------------------------------

def check_global(all_meta: dict[str, dict]) -> list[tuple[str, str]]:
    """
    all_meta: {filename: metadata_dict}
    Trả về list (filename, lỗi).
    """
    errors = []

    # Thu thập tất cả id
    id_to_files: dict[str, list[str]] = defaultdict(list)
    for fname, meta in all_meta.items():
        id_val = meta.get("id")
        if id_val:
            id_to_files[id_val].append(fname)

    all_ids = set(id_to_files.keys())

    # Kiểm tra id duy nhất
    for id_val, files in id_to_files.items():
        if len(files) > 1:
            for fname in files:
                errors.append((fname, f"[Global] `id` trùng lặp: '{id_val}' xuất hiện trong {files}"))

    # Kiểm tra implements trỏ đúng id tồn tại (hỗ trợ đa cha — D-23)
    for fname, meta in all_meta.items():
        impl = meta.get("implements")
        if impl is None:
            continue
        impl_list = impl if isinstance(impl, list) else [impl]
        for parent in impl_list:
            if isinstance(parent, str) and parent not in all_ids:
                errors.append(
                    (fname, f"[Global] `implements: '{parent}'` không khớp id nào trong tập file")
                )

    # amended_by_norms: chỉ kiểm tra format (list of string), không yêu cầu
    # các id tham chiếu phải có trong tập file hiện tại vì các văn bản sửa đổi
    # có thể nằm ngoài scope thu thập.

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_files(data_dir: Path, single_file: str | None) -> list[Path]:
    if single_file:
        target = data_dir / single_file
        if not target.exists():
            print(f"❌ Không tìm thấy file: {target}")
            sys.exit(1)
        return [target]

    return sorted(
        f for f in data_dir.glob("*.md")
        if f.name not in NON_LEGAL_FILES
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kiểm tra metadata và format file data/raw/*.md Phase 1"
    )
    parser.add_argument("data_dir", help="Đường dẫn đến thư mục data/raw/")
    parser.add_argument(
        "--check-duplicates",
        action="store_true",
        help="Kiểm tra id trùng lặp toàn tập (mặc định đã bật khi chạy toàn bộ thư mục)",
    )
    parser.add_argument(
        "--file",
        metavar="FILENAME",
        help="Chỉ kiểm tra 1 file cụ thể (VD: luat-dat-dai-2024.md)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"❌ Không tìm thấy thư mục: {data_dir}")
        sys.exit(1)

    files = collect_files(data_dir, args.file)
    if not files:
        print("⚠️  Không tìm thấy file .md nào để kiểm tra.")
        sys.exit(0)

    print(f"🔍 Kiểm tra {len(files)} file trong {data_dir}/\n")

    all_meta: dict[str, dict] = {}
    file_errors: dict[str, list[str]] = {}
    total_errors = 0

    for filepath in files:
        meta, errors = validate_file(filepath)
        file_errors[filepath.name] = errors
        if meta:
            all_meta[filepath.name] = meta
        total_errors += len(errors)

    # Kiểm tra global (chỉ khi có ≥ 2 file hoặc --check-duplicates)
    global_errs: list[tuple[str, str]] = []
    if len(files) > 1 or args.check_duplicates:
        global_errs = check_global(all_meta)
        for fname, err in global_errs:
            file_errors.setdefault(fname, []).append(err)
            total_errors += 1

    # In kết quả
    has_any_error = False
    for filepath in files:
        fname = filepath.name
        errs = file_errors.get(fname, [])
        if errs:
            has_any_error = True
            print(f"❌ {fname} — {len(errs)} lỗi:")
            for err in errs:
                print(f"   • {err}")
            print()
        else:
            print(f"✅ {fname}")

    print()
    if has_any_error:
        print(f"{'=' * 60}")
        print(f"❌ FAIL — Tổng {total_errors} lỗi trong {len(file_errors)} file đã kiểm tra.")
        print(f"   Sửa tất cả lỗi trên trước khi chuyển sang TASK-05.")
        sys.exit(1)
    else:
        print(f"{'=' * 60}")
        print(f"✅ PASS — {len(files)} file hợp lệ, không có lỗi.")
        sys.exit(0)


if __name__ == "__main__":
    main()
