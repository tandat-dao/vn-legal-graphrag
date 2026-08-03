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

echo
echo "════════════════════════════════════════════════════════════"
echo "  DEMO GraphRAG Pháp luật Việt Nam — chế độ: ${CHE_DO}"
echo "════════════════════════════════════════════════════════════"

# ── 0. Cổng đang bận? Nếu chính UI này đang chạy thì mở luôn, khỏi dựng lại ──
if lsof -nP -iTCP:"$CONG" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -sf -m 3 "http://127.0.0.1:$CONG/api/mode" >/dev/null 2>&1; then
    xanh "✓ UI đã chạy sẵn ở cổng $CONG — mở trình duyệt luôn."
    command -v open >/dev/null && open "http://127.0.0.1:$CONG"
    exit 0
  fi
  chet "Cổng $CONG đang bị chương trình khác chiếm." \
       "Xem ai giữ: lsof -nP -iTCP:$CONG -sTCP:LISTEN — hoặc chạy lại với cổng khác: ./scripts/chay-demo.sh $CHE_DO 8010"
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

# ── 2. Nhánh: bản UI mới nhất nằm ở develop, main chưa có ───────────────────
NHANH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
if [ "$NHANH" != "develop" ]; then
  vang "⚠ Đang ở nhánh '$NHANH', không phải 'develop' — có thể đây là bản UI cũ."
  echo "  → Chuyển: git checkout develop"
fi

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
fi

# ── 5. Khởi động server, chờ đến khi thật sự trả lời rồi mới mở trình duyệt ──
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
command -v open >/dev/null && open "http://127.0.0.1:$CONG"

wait "$PID"
