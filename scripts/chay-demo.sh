#!/usr/bin/env bash
# Khởi động demo UI bằng MỘT lệnh, dùng cho buổi bảo vệ.
#
#   ./scripts/chay-demo.sh            → chế độ live (gọi pipeline thật)
#   ./scripts/chay-demo.sh replay     → chế độ phát lại fixture (không cần DB)
#   ./scripts/chay-demo.sh live 8010  → đổi cổng
#
# Script lo hết những chỗ dễ vấp lúc căng thẳng: chọn đúng bản Python, dựng
# Docker và CHỜ hai CSDL trả lời, kiểm .env, xử lý cổng đang bận, rồi tự mở
# trình duyệt khi server thật sự sẵn sàng. Mọi lỗi đều kèm cách chữa.

set -uo pipefail

CHE_DO="${1:-live}"
CONG="${2:-8000}"
GOC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$GOC" || exit 1

do_() { printf '\033[31m%s\033[0m\n' "$*"; }      # đỏ
vang() { printf '\033[33m%s\033[0m\n' "$*"; }     # vàng
xanh() { printf '\033[32m%s\033[0m\n' "$*"; }     # xanh
mo()   { printf '\033[2m%s\033[0m\n' "$*"; }      # mờ

chet() { echo; do_ "✗ $1"; [ $# -gt 1 ] && echo "  → $2"; exit 1; }

# Mở trình duyệt kèm dấu thời gian ở query string.
# Vì sao không mở URL trần: trên macOS, `open` với URL ĐÃ mở sẵn trong Chrome
# chỉ CHUYỂN sang tab đó chứ không tải lại — nên sửa giao diện xong chạy lại
# script vẫn thấy bản cũ, và không header cache nào cứu được vì trình duyệt
# không hề xin lại trang. URL khác nhau mỗi lần thì buộc phải tải mới.
# Ứng dụng bỏ qua tham số lạ nên `?t=…` vô hại.
mo_trinh_duyet() {
  command -v open >/dev/null || return 0
  open "http://127.0.0.1:$CONG/?t=$(date +%s)"
}

echo
echo "════════════════════════════════════════════════════════════"
echo "  DEMO GraphRAG Pháp luật Việt Nam — chế độ: ${CHE_DO}"
echo "════════════════════════════════════════════════════════════"

# ── 0. Cổng đang bận? GHI NHẬN thôi, KHÔNG thoát sớm ────────────────────────
# Trước đây chỗ này `exit 0` ngay khi thấy UI trả lời — nhưng UI sống KHÔNG có
# nghĩa là CSDL sống. Gặp đúng ca đó (2026-08-06): một UI cũ còn sót lại giữ
# cổng, Docker thì đã tắt, script báo "sẵn sàng" rồi mọi câu hỏi đều lỗi
# "Connection refused". Nay chỉ ghi cờ, vẫn chạy tiếp bước 4 để dựng và kiểm
# CSDL; tới bước 5 mới quyết định có cần khởi động server mới hay không.
UI_DANG_CHAY=0
if lsof -nP -iTCP:"$CONG" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -sf -m 3 "http://127.0.0.1:$CONG/api/mode" >/dev/null 2>&1; then
    UI_DANG_CHAY=1
    mo "  UI đã chạy sẵn ở cổng $CONG — vẫn kiểm CSDL trước khi mở."
  else
    chet "Cổng $CONG đang bị chương trình khác chiếm." \
         "Xem ai giữ: lsof -nP -iTCP:$CONG -sTCP:LISTEN — hoặc chạy lại với cổng khác: ./scripts/chay-demo.sh $CHE_DO 8010"
  fi
fi

# ── 1. Python: cài gcloud đổi `python3` sang bản thiếu deps của dự án ────────
PY=""
for ung_vien in \
  "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" \
  "$(command -v python3 || true)"
do
  [ -n "$ung_vien" ] && [ -x "$ung_vien" ] || continue
  if "$ung_vien" -c "import uvicorn, fastapi" >/dev/null 2>&1; then PY="$ung_vien"; break; fi
done
[ -n "$PY" ] || chet "Không tìm thấy bản Python có đủ fastapi + uvicorn." \
                     "Cài bằng: python3 -m pip install -r requirements.txt"
mo "  Python: $PY"

# ── 2. Nhánh: cảnh báo nếu đang ở nhánh không mang bản UI ───────────────────
# Từ 2026-08-03 cả `main` lẫn `develop` đều có UI (develop đã gộp vào main).
# Nhánh khác hai cái đó thì có thể là bản cũ hoặc nhánh thử nghiệm.
NHANH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
case "$NHANH" in
  main|develop) ;;
  *) vang "⚠ Đang ở nhánh '$NHANH' — có thể không phải bản UI mới nhất."
     echo "  → Chuyển: git checkout main" ;;
esac

# ── 3. .env ─────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  chet "Chưa có tệp .env." "Chép mẫu rồi điền mật khẩu Neo4j + khóa mô hình: cp .env.example .env"
fi
mo "  .env: có"

# ── 4. Docker + CHỜ hai CSDL trả lời (chế độ live mới cần) ──────────────────
csdl_song() {
  curl -sf -m 2 "http://127.0.0.1:7474" >/dev/null 2>&1 \
  && curl -sf -m 2 "http://127.0.0.1:6333/readyz" >/dev/null 2>&1
}

if [ "$CHE_DO" = "live" ]; then
  if csdl_song; then
    # Container có thể đã được dựng từ lần trước hoặc từ một project compose
    # khác (tên trùng → `compose up` sẽ báo conflict). Đang sống thì đừng đụng.
    xanh "  ✓ Neo4j + Qdrant đã chạy sẵn"
  else
    docker info >/dev/null 2>&1 || chet "Docker chưa chạy." "Mở Docker Desktop rồi chạy lại lệnh này."
    echo "  Dựng Neo4j + Qdrant…"
    # KHÔNG chết theo mã thoát của compose: nó báo lỗi cả khi container cũ vẫn
    # chạy tốt (trùng tên). Cứ chờ CSDL trả lời rồi mới kết luận.
    ket_qua_compose="$(docker compose up -d 2>&1)"

    printf "  Chờ CSDL sẵn sàng"
    san_sang=0
    for _ in $(seq 1 60); do
      if csdl_song; then san_sang=1; break; fi
      printf "."; sleep 2
    done
    echo
    if [ "$san_sang" != 1 ]; then
      do_ "✗ Neo4j hoặc Qdrant không trả lời sau 2 phút."
      [ -n "$ket_qua_compose" ] && { echo "  docker compose nói:"; echo "$ket_qua_compose" | sed 's/^/    /' | tail -6; }
      echo "  → Xem thêm: docker compose logs --tail 30"
      exit 1
    fi
    xanh "  ✓ Neo4j + Qdrant sẵn sàng"
  fi

  # ── 4b. CSDL TRẢ LỜI KHÔNG CÓ NGHĨA LÀ CÓ DỮ LIỆU ────────────────────────
  # Neo4j trắng tinh vẫn trả HTTP 200. Sáng 2026-08-06 đúng ca đó: container
  # trỏ vào một thư mục đã bị xoá, Docker tự tạo lại thư mục rỗng, Neo4j khởi
  # tạo CSDL mới — mọi phép kiểm "còn sống" đều xanh, mà đồ thị thì 0 node.
  # Đếm qua Python cho đúng quy tắc dự án (không truy vấn thẳng CSDL bằng curl).
  printf "  Kiểm dữ liệu…"
  KQ_DL="$("$PY" - <<'PYEOF' 2>&1
import os, warnings
warnings.filterwarnings("ignore")
try:
    from dotenv import load_dotenv
    load_dotenv(".env")
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient
    drv = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")))
    with drv.session() as s:
        n = s.run("MATCH (n:Norm) RETURN count(n) AS c").single()["c"]
        k = s.run("MATCH ()-[r:MAPS_TO_CONCEPT]->() RETURN count(r) AS c").single()["c"]
    q = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"),
                     port=int(os.getenv("QDRANT_PORT", "6333")))
    ten = [c.name for c in q.get_collections().collections]
    p = q.count("legal_texts").count if "legal_texts" in ten else 0
    print(f"OK {n} {p} {k}")
except Exception as e:
    print(f"LOI {type(e).__name__}: {e}")
PYEOF
)"
  echo
  case "$KQ_DL" in
    OK\ *)
      set -- $KQ_DL
      SO_NORM="$2"; SO_DIEM="$3"; SO_KN="$4"
      if [ "$SO_NORM" -lt 1 ] || [ "$SO_DIEM" -lt 1 ]; then
        do_ "✗ CSDL chạy nhưng RỖNG — Neo4j $SO_NORM văn bản, Qdrant $SO_DIEM điểm."
        echo "  → Khôi phục từ bản sao lưu (nhanh nhất, ~2 phút):"
        echo "      docker compose down"
        echo "      tar xzf ~/Documents/University/2526_Sem2/Thesis/SAO-LUU-CSDL-KHONG-XOA/csdl-DAY-DU.tar.gz"
        echo "      docker compose up -d"
        echo "  → Hoặc nạp lại từ đầu (~2,5 giờ):"
        echo "      $PY -m src.ingestion.graph_builder && $PY -m src.ingestion.vectorizer"
        exit 1
      fi
      xanh "  ✓ Dữ liệu đủ — $SO_NORM văn bản · $SO_DIEM điểm vector · $SO_KN ánh xạ khái niệm"
      [ "$SO_KN" -lt 1 ] && vang "  ⚠ Chưa có ánh xạ khái niệm — xếp hạng sẽ khác bản đã đo."
      ;;
    *)
      do_ "✗ Không kiểm được dữ liệu: $KQ_DL"
      echo "  → Kiểm mật khẩu NEO4J_PASSWORD trong .env, hoặc: docker compose logs --tail 30"
      exit 1
      ;;
  esac
fi

# ── 5. UI đã chạy sẵn thì thôi, chỉ mở trình duyệt (CSDL đã kiểm ở bước 4) ───
if [ "$UI_DANG_CHAY" = 1 ]; then
  echo
  xanh "✓ SẴN SÀNG — http://127.0.0.1:$CONG"
  mo   "    UI đang chạy từ một cửa sổ terminal khác — dừng nó ở đúng cửa sổ đó."
  echo
  mo_trinh_duyet
  exit 0
fi

# ── 5b. Khởi động server, chờ đến khi thật sự trả lời rồi mới mở trình duyệt ─
echo "  Khởi động UI (nạp mô hình nhúng, khoảng 40–60 giây)…"
LOG="$(mktemp -t demo-ui)"
DEMO_MODE="$CHE_DO" "$PY" -m uvicorn ui.server:app --port "$CONG" >"$LOG" 2>&1 &
PID=$!

don_dep() { kill "$PID" 2>/dev/null; }
trap don_dep EXIT INT TERM

printf "  Chờ server"
len=0
for _ in $(seq 1 90); do
  kill -0 "$PID" 2>/dev/null || { echo; do_ "✗ Server tắt giữa chừng. 20 dòng log cuối:"; tail -20 "$LOG"; exit 1; }
  if curl -sf -m 2 "http://127.0.0.1:$CONG/api/mode" >/dev/null 2>&1; then len=1; break; fi
  printf "."; sleep 2
done
echo
[ "$len" = 1 ] || { do_ "✗ Server không trả lời sau 3 phút. Log:"; tail -20 "$LOG"; exit 1; }

MODE_THAT="$(curl -s "http://127.0.0.1:$CONG/api/mode" | sed -n 's/.*"mode":"\([a-z]*\)".*/\1/p')"
LLM="$(grep -o 'llm_mode=[a-z-]*' "$LOG" | head -1 | cut -d= -f2)"

echo
xanh "✓ SẴN SÀNG — http://127.0.0.1:$CONG"
echo "    chế độ: ${MODE_THAT:-$CHE_DO}${LLM:+  ·  mô hình: $LLM}"
mo   "    log: $LOG      dừng: Ctrl-C"
echo
mo_trinh_duyet

wait "$PID"
