#!/usr/bin/env bash
# MỘT LỆNH DUY NHẤT cho buổi bảo vệ.
#
#     ./scripts/bao-ve.sh
#
# Dựng Docker, chờ CSDL, mở HAI cổng đối chiếu với ĐÚNG cấu hình, rồi mở trình
# duyệt. Không cần nhớ biến môi trường nào.
#
#     cổng 8000  →  TRƯỚC cải tiến
#     cổng 8001  →  SAU cải tiến (đủ ba cơ chế + cảnh báo quy định đã thay đổi)
#
# Vì sao gói vào đây: bản sau cải tiến cần NĂM biến môi trường đặt đúng. Thiếu
# một biến là demo chỉ thể hiện một phần mức cải tiến, mà nhìn giao diện KHÔNG
# phát hiện được. Gõ tay năm biến trước hội đồng là chỗ dễ sai nhất.

set -uo pipefail
GOC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$GOC" || exit 1

do_()  { printf '\033[31m%s\033[0m\n' "$*"; }
vang() { printf '\033[33m%s\033[0m\n' "$*"; }
xanh() { printf '\033[32m%s\033[0m\n' "$*"; }
mo()   { printf '\033[2m%s\033[0m\n' "$*"; }

echo
echo "════════════════════════════════════════════════════════════"
echo "  DEMO BẢO VỆ — hai cổng đối chiếu trước/sau cải tiến"
echo "════════════════════════════════════════════════════════════"
echo

# ── 1. Docker ───────────────────────────────────────────────────────────────
if ! docker info >/dev/null 2>&1; then
  do_ "✗ Docker chưa chạy."
  echo "  → Mở Docker Desktop, đợi biểu tượng hết quay, rồi chạy lại lệnh này."
  exit 1
fi
xanh "✓ Docker đang chạy"

for c in graphrag-neo4j graphrag-qdrant; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$c"; then
    mo "  khởi động $c…"
    docker start "$c" >/dev/null 2>&1 || docker compose up -d >/dev/null 2>&1
  fi
done

printf "  chờ CSDL"
for _ in $(seq 1 60); do
  if nc -z localhost 7687 2>/dev/null && nc -z localhost 6333 2>/dev/null; then break; fi
  printf "."; sleep 2
done
echo
if ! nc -z localhost 7687 2>/dev/null; then
  do_ "✗ Neo4j (cổng 7687) không lên sau 2 phút."
  echo "  → docker compose logs neo4j | tail -20"
  exit 1
fi
xanh "✓ Neo4j và Qdrant đã sẵn sàng"

# ── 2. Kiểm dữ liệu, tránh demo trên CSDL rỗng ──────────────────────────────
PY=""
for ung_vien in /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 python3 python; do
  if "$ung_vien" -c "import uvicorn, fastapi" >/dev/null 2>&1; then PY="$ung_vien"; break; fi
done
[ -n "$PY" ] || { do_ "✗ Không tìm thấy Python có fastapi + uvicorn."; exit 1; }

# Cổng bolt MỞ trước khi Neo4j sẵn sàng nhận truy vấn — phải thử lại,
# không được kết luận "CSDL hỏng" ngay lần đầu.
printf "  chờ Neo4j nhận truy vấn"
KQ=""
for _ in $(seq 1 30); do
  KQ="$("$PY" - <<'EOF' 2>/dev/null
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
# load_dotenv() KHÔNG tự tìm được .env khi mã đọc từ luồng vào chuẩn
# (find_dotenv cần khung ngăn xếp của tệp) -> phải chỉ đường tường minh.
load_dotenv(os.path.join(os.getcwd(), ".env"))
try:
    d = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                             auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
    with d.session() as s:
        n = s.run("MATCH (n:Norm) RETURN count(n) AS c").single()["c"]
        r = s.run("MATCH ()-[x:REFERS_TO]->() RETURN count(x) AS c").single()["c"]
    print("OK %d %d" % (n, r))
except Exception as e:
    print("LOI %s" % str(e)[:60])
EOF
)"
  case "$KQ" in OK*) break ;; esac
  printf "."; sleep 3
done
echo
set -- $KQ
if [ "${1:-}" != "OK" ]; then
  do_ "✗ Neo4j không nhận truy vấn sau 90 giây."
  echo "  → ${KQ:-(không có phản hồi)}"
  echo "  → Kiểm mật khẩu NEO4J_PASSWORD trong .env, hoặc:"
  echo "     docker compose logs neo4j | tail -20"
  exit 1
fi
SO_VB="$2"; SO_DC="$3"
if [ "$SO_VB" -lt 30 ]; then
  do_ "✗ CSDL chỉ có $SO_VB văn bản — thiếu dữ liệu."
  echo "  → Khôi phục: docker compose down && tar xzf ~/Documents/University/2526_Sem2/Thesis/SAO-LUU-CSDL-KHONG-XOA/csdl-demo-truoc-nap-lao-dong-20260818.tar.gz && docker compose up -d"
  exit 1
fi
xanh "✓ Dữ liệu đủ — $SO_VB văn bản · $SO_DC quan hệ dẫn chiếu"
[ "$SO_DC" -lt 1 ] && vang "  ⚠ Chưa có quan hệ dẫn chiếu — cổng 8001 sẽ không khác cổng 8000."

# ── 3. Dọn cổng cũ ──────────────────────────────────────────────────────────
pkill -f "uvicorn ui.server:app" >/dev/null 2>&1 && { mo "  dọn server cũ…"; sleep 2; }

# ── 4. Hai cổng, hai cấu hình ───────────────────────────────────────────────
LOG0="$(mktemp -t demo8000)"; LOG1="$(mktemp -t demo8001)"

# TRƯỚC cải tiến — tắt hết, dùng đúng tham số mặc định của báo cáo
env UI_REFERS_MODE= UI_RERANK_MODE= UI_CHUYEN_TIEP= \
    SF_DENSE_POOL_MIN=50 SF_RARITY_ALPHA=1.5 DEMO_MODE=live \
    "$PY" -m uvicorn ui.server:app --port 8000 >"$LOG0" 2>&1 &
PID0=$!

# SAU cải tiến — ĐỦ NĂM biến. Thiếu một cái là demo sai.
env UI_REFERS_MODE=khoan UI_RERANK_MODE=trong-norm UI_CHUYEN_TIEP=1 \
    SF_DENSE_POOL_MIN=100 SF_RARITY_ALPHA=0 DEMO_MODE=live \
    "$PY" -m uvicorn ui.server:app --port 8001 >"$LOG1" 2>&1 &
PID1=$!

don_dep() { kill "$PID0" "$PID1" 2>/dev/null; }
trap don_dep EXIT INT TERM

echo
printf "  nạp mô hình nhúng (40–90 giây)"
SAN0=0; SAN1=0
for _ in $(seq 1 90); do
  kill -0 "$PID0" 2>/dev/null || { echo; do_ "✗ Cổng 8000 tắt giữa chừng:"; tail -15 "$LOG0"; exit 1; }
  kill -0 "$PID1" 2>/dev/null || { echo; do_ "✗ Cổng 8001 tắt giữa chừng:"; tail -15 "$LOG1"; exit 1; }
  curl -sf -m 2 http://127.0.0.1:8000/api/mode >/dev/null 2>&1 && SAN0=1
  curl -sf -m 2 http://127.0.0.1:8001/api/mode >/dev/null 2>&1 && SAN1=1
  [ "$SAN0" = 1 ] && [ "$SAN1" = 1 ] && break
  printf "."; sleep 2
done
echo
[ "$SAN0" = 1 ] || { do_ "✗ Cổng 8000 không trả lời."; tail -15 "$LOG0"; exit 1; }
[ "$SAN1" = 1 ] || { do_ "✗ Cổng 8001 không trả lời."; tail -15 "$LOG1"; exit 1; }

# ── 5. Tự kiểm: hai cổng có THẬT SỰ khác cấu hình không ─────────────────────
KT_SAI=0
for p in $(pgrep -f "uvicorn ui.server:app"); do
  cong="$(ps -o args= -p "$p" | grep -oE '\-\-port [0-9]+' | awk '{print $2}')"
  moi="$(ps eww "$p" 2>/dev/null | tr ' ' '\n' | grep -c '^UI_RERANK_MODE=trong-norm')"
  case "$cong:$moi" in
    8000:0|8001:1) ;;
    *) do_ "✗ Cổng $cong có cấu hình SAI (UI_RERANK_MODE khớp=$moi)"; KT_SAI=1 ;;
  esac
done
[ "$KT_SAI" = 1 ] && { do_ "Dừng lại — cấu hình hai cổng không đúng."; exit 1; }

echo
xanh "════════════════════════════════════════════════════════════"
xanh "  SẴN SÀNG"
xanh "════════════════════════════════════════════════════════════"
echo "    http://127.0.0.1:8000   ←  TRƯỚC cải tiến"
echo "    http://127.0.0.1:8001   ←  SAU cải tiến (đủ ba cơ chế)"
echo
mo   "    Câu đối chiếu nên dùng: A4 — 'Hồi trước nghe nói ở TP.HCM một hộ được"
mo   "    tới 300 mét vuông đất ở, sao giờ nghe nói chỉ còn 250?…'"
mo   "    8001 hiện thêm KHỐI CẢNH BÁO quy định đã thay đổi mà 8000 không có"
echo
mo   "    Dừng: Ctrl-C"
echo

command -v open >/dev/null && {
  open "http://127.0.0.1:8000/?t=$(date +%s)" 2>/dev/null
  sleep 1
  open "http://127.0.0.1:8001/?t=$(date +%s)" 2>/dev/null
}

wait "$PID0" "$PID1"
