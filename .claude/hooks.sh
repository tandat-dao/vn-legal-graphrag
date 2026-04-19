#!/usr/bin/env bash
# =============================================================================
# .claude/hooks.sh
# Claude Code lifecycle hooks — Ontology-Driven GraphRAG cho Pháp luật VN
#
# Cách hoạt động:
#   - Claude Code gọi script này với 1 argument là tên event
#   - Dữ liệu event được truyền qua stdin dưới dạng JSON
#   - Exit code 0  → cho phép tiếp tục
#   - Exit code 2  → CHẶN tool, Claude đọc stderr như một cảnh báo/giải thích
#   - Exit code 1  → lỗi script (không chặn, nhưng log lại)
# =============================================================================

set -euo pipefail

EVENT="${1:-unknown}"

# Đọc toàn bộ stdin vào biến (có thể là JSON từ Claude Code)
INPUT_JSON=""
if [ -t 0 ]; then
  INPUT_JSON="{}"
else
  INPUT_JSON=$(cat)
fi

# Helper: lấy giá trị từ JSON bằng grep/sed (không cần jq)
# Dùng jq nếu có, fallback về grep
json_get() {
  local key="$1"
  local json="$2"
  if command -v jq &>/dev/null; then
    echo "$json" | jq -r ".$key // empty" 2>/dev/null || echo ""
  else
    # Fallback đơn giản — chỉ hoạt động với JSON một lớp
    echo "$json" | grep -o "\"$key\": *\"[^\"]*\"" | sed 's/.*": *"\(.*\)"/\1/' | head -1
  fi
}

# =============================================================================
# EVENT: pre_bash — chạy trước khi Claude Code thực thi lệnh Bash
# =============================================================================
handle_pre_bash() {
  local tool_name
  local command
  tool_name=$(json_get "tool_name" "$INPUT_JSON")
  command=$(json_get "command" "$(echo "$INPUT_JSON" | grep -o '"tool_input":{[^}]*}' | head -1)" 2>/dev/null || echo "")
  
  # Nếu không parse được command, thử cách khác
  if [ -z "$command" ] && command -v jq &>/dev/null; then
    command=$(echo "$INPUT_JSON" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")
  fi

  # -------------------------------------------------------------------------
  # CHẶN: Truy cập database trực tiếp qua curl
  # -------------------------------------------------------------------------
  if echo "$command" | grep -qE "curl.*(localhost:(7474|7687|6333|6334))"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⛔  CHẶN: Không được truy cập database trực tiếp qua curl      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  RULE: Mọi thao tác với Neo4j và Qdrant phải đi qua Python.     ║
║                                                                  ║
║  ✅ ĐÚNG:  python src/ingestion/graph_builder.py                 ║
║  ✅ ĐÚNG:  python src/ingestion/vectorizer.py                    ║
║  ✅ ĐÚNG:  python src/utils/connection_check.py                  ║
║                                                                  ║
║  ❌ SAI:   curl -X POST http://localhost:7474/...                ║
║  ❌ SAI:   curl http://localhost:6333/collections/...            ║
║                                                                  ║
║  Lý do: Mọi thay đổi database phải traceable qua code.          ║
║  Xem CLAUDE.md phần "QUY TẮC TUYỆT ĐỐI" mục 1.                ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    exit 2
  fi

  # -------------------------------------------------------------------------
  # CHẶN: Xóa file trong data/sources/
  # -------------------------------------------------------------------------
  if echo "$command" | grep -qE "rm.*data/sources/"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⛔  CHẶN: Không được xóa file trong data/sources/              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  data/sources/ chứa văn bản pháp luật gốc — KHÔNG BAO GIỜ XÓA. ║
║                                                                  ║
║  Nếu cần sửa nội dung → sửa file trong data/raw/*.md            ║
║  Nếu cần thêm văn bản → thêm file mới vào data/sources/         ║
║  và cập nhật data/sources/manifest.md                           ║
║                                                                  ║
║  Xem CLAUDE.md phần "QUY TẮC TUYỆT ĐỐI" mục 2.                ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    exit 2
  fi

  # -------------------------------------------------------------------------
  # CHẶN: Xóa file data/raw/*.md trực tiếp
  # -------------------------------------------------------------------------
  if echo "$command" | grep -qE "rm.*data/raw/.*\.md"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⛔  CHẶN: Không được xóa file data/raw/*.md trực tiếp          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  data/raw/*.md là output đã qua xử lý Phase 1 (cross-checked).  ║
║                                                                  ║
║  Nếu cần xóa → dùng: git rm data/raw/[filename].md             ║
║  và giải thích lý do trong commit message.                       ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    exit 2
  fi

  # -------------------------------------------------------------------------
  # CHẶN: Dùng cypher-shell hoặc neo4j-admin trực tiếp
  # -------------------------------------------------------------------------
  if echo "$command" | grep -qE "(cypher-shell|neo4j-admin)"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⛔  CHẶN: Không dùng cypher-shell hoặc neo4j-admin trực tiếp   ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Tất cả thao tác Neo4j phải đi qua Python driver.               ║
║                                                                  ║
║  ✅ ĐÚNG: python src/ingestion/graph_builder.py                  ║
║  ✅ ĐÚNG: Cypher queries trong Python với neo4j driver           ║
║                                                                  ║
║  Xem CLAUDE.md phần "QUY TẮC TUYỆT ĐỐI" mục 1.                ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    exit 2
  fi

  # -------------------------------------------------------------------------
  # CẢNH BÁO (không chặn): Chạy graph_builder hoặc vectorizer
  # Nhắc nhở verify Phase 1 đã xong
  # -------------------------------------------------------------------------
  if echo "$command" | grep -qE "python src/ingestion/(graph_builder|vectorizer)\.py"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️   NHẮC NHỞ: Chạy ingestion pipeline                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Trước khi tiếp tục, xác nhận:                                  ║
║                                                                  ║
║  [ ] TASK-07 (Cross-check Phase 1) đã HOÀN THÀNH               ║
║  [ ] data/raw/review_log.md có sign-off của cả 2 thành viên    ║
║  [ ] python src/utils/validate_metadata.py data/raw/ PASS       ║
║                                                                  ║
║  Nếu chưa → dừng lại, hoàn thành Phase 1 trước.                ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    # exit 0 = cho phép tiếp tục (chỉ là cảnh báo)
  fi

  # -------------------------------------------------------------------------
  # CẢNH BÁO (không chặn): pip install package mới
  # -------------------------------------------------------------------------
  if echo "$command" | grep -qE "pip install [^-]" && ! echo "$command" | grep -q "\-r requirements.txt"; then
    local pkg
    pkg=$(echo "$command" | sed 's/pip install //' | awk '{print $1}')
    cat >&2 <<EOF
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️   NHẮC NHỞ: Cài package mới — cập nhật requirements.txt    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Sau khi cài "${pkg}", hãy chạy:                 
║                                                                  ║
║    pip freeze | grep ${pkg} >> requirements.txt  
║                                                                  ║
║  để đảm bảo môi trường của 2 thành viên đồng bộ.               ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    # exit 0 = cho phép tiếp tục
  fi

  exit 0
}

# =============================================================================
# EVENT: pre_write — chạy trước khi Claude Code write/edit file
# =============================================================================
handle_pre_write() {
  local file_path=""
  if command -v jq &>/dev/null; then
    file_path=$(echo "$INPUT_JSON" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || echo "")
  fi

  # -------------------------------------------------------------------------
  # CHẶN: Ghi vào data/sources/
  # -------------------------------------------------------------------------
  if echo "$file_path" | grep -q "data/sources/"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⛔  CHẶN: Không được sửa file trong data/sources/              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  data/sources/ là raw data bất biến. Chỉ được thêm file mới,   ║
║  không bao giờ sửa file đã có.                                  ║
║                                                                  ║
║  Nếu muốn sửa nội dung → sửa file tương ứng trong data/raw/    ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    exit 2
  fi

  # -------------------------------------------------------------------------
  # CẢNH BÁO (không chặn): Sửa file data/raw/*.md
  # -------------------------------------------------------------------------
  if echo "$file_path" | grep -qE "data/raw/.*\.md" && \
     ! echo "$file_path" | grep -qE "(mapping_table|specified_in_map|crossref_decisions|review_log)\.md"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️   NHẮC NHỞ: Sửa file văn bản pháp luật                     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Sau khi sửa, nhớ:                                              ║
║  1. Chạy validate: python src/utils/validate_metadata.py data/raw/
║  2. Ghi vào data/raw/review_log.md — ai sửa, sửa gì, ngày nào  ║
║  3. Nếu sửa ảnh hưởng đến Neo4j → cần chạy lại graph_builder   ║
║     (pipeline idempotent — MERGE sẽ update, không duplicate)    ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    # exit 0 = cho phép tiếp tục
  fi

  # -------------------------------------------------------------------------
  # CẢNH BÁO (không chặn): Sửa .env thật (không phải .env.example)
  # -------------------------------------------------------------------------
  if echo "$file_path" | grep -qE "^\.env$|/\.env$"; then
    cat >&2 <<'EOF'
╔══════════════════════════════════════════════════════════════════╗
║  ⚠️   NHẮC NHỞ: Đang sửa file .env                             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Đảm bảo .env nằm trong .gitignore trước khi tiếp tục.         ║
║  TUYỆT ĐỐI KHÔNG commit file .env thật lên Git.                ║
║                                                                  ║
║  Kiểm tra: grep "^\.env$" .gitignore                           ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    # exit 0 = cho phép tiếp tục
  fi

  exit 0
}

# =============================================================================
# EVENT: post_write — chạy sau khi Claude Code write/edit file thành công
# =============================================================================
handle_post_write() {
  local file_path=""
  if command -v jq &>/dev/null; then
    file_path=$(echo "$INPUT_JSON" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || echo "")
  fi

  # -------------------------------------------------------------------------
  # Sau khi sửa src/ingestion/*.py hoặc src/retrieval/*.py
  # Nhắc chạy tests
  # -------------------------------------------------------------------------
  if echo "$file_path" | grep -qE "src/(ingestion|retrieval)/.*\.py"; then
    local module_name
    module_name=$(basename "$file_path" .py)
    cat >&2 <<EOF
[hook] Đã sửa ${file_path}
[hook] Gợi ý: pytest tests/test_${module_name}.py -v
EOF
  fi

  # -------------------------------------------------------------------------
  # Sau khi sửa data/raw/*.md (văn bản pháp luật)
  # Nhắc validate
  # -------------------------------------------------------------------------
  if echo "$file_path" | grep -qE "data/raw/.*\.md" && \
     ! echo "$file_path" | grep -qE "(mapping_table|specified_in_map|crossref_decisions|review_log)\.md"; then
    cat >&2 <<'EOF'
[hook] Gợi ý: python src/utils/validate_metadata.py data/raw/
EOF
  fi

  exit 0
}

# =============================================================================
# EVENT: on_stop — chạy khi Claude Code kết thúc một task/response
# =============================================================================
handle_on_stop() {
  cat >&2 <<'EOF'

╔══════════════════════════════════════════════════════════════════╗
║  📋  NHẮC NHỞ CUỐI SESSION                                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Nếu task vừa hoàn thành (tất cả DoD items đã checked):         ║
║                                                                  ║
║  1. Cập nhật PROJECT_STATUS.md:                                  ║
║     - Thêm changelog entry (reverse-chronological)              ║
║     - Tick [x] toàn bộ DoD items của task                       ║
║     - Điền "Completed: YYYY-MM-DD"                              ║
║     - Cập nhật §1.1 Đã hoàn thành                              ║
║                                                                  ║
║  2. Commit với format: [TASK-XX] type: mô tả                    ║
║                                                                  ║
║  Nếu task chưa xong → cập nhật §1.2 "Đang thực hiện"           ║
║  và ghi chú những gì còn lại.                                   ║
╚══════════════════════════════════════════════════════════════════╝
EOF
  exit 0
}

# =============================================================================
# DISPATCH
# =============================================================================
case "$EVENT" in
  "pre_bash")
    handle_pre_bash
    ;;
  "pre_write")
    handle_pre_write
    ;;
  "post_write")
    handle_post_write
    ;;
  "on_stop")
    handle_on_stop
    ;;
  *)
    # Event không nhận dạng được — cho phép tiếp tục
    exit 0
    ;;
esac
