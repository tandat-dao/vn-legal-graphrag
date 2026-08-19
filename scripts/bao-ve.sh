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

# Ngày cấp cho lời nhắc. Lời nhắc nhắc tới "thời điểm câu hỏi" ở nhiều chỗ nhưng
# không chỗ nào nói đó là ngày nào, nên mô hình suy từ tri thức huấn luyện và
# viết "sắp có hiệu lực" cho mốc đã qua gần hai năm.
#
# CỐ Ý ghi cứng chứ KHÔNG lấy $(date): ngày nằm trong lời nhắc nên nó nằm trong
# khóa bộ nhớ đệm. Lấy ngày hệ thống thì hâm cache hôm nay, hôm sau demo là
# trượt sạch — phải gọi mô hình trực tiếp, cần mạng và hạn ngạch.
# Đổi ngày ở đây thì PHẢI hâm lại cache (xem cuối tệp này).
NGAY_LOI_NHAC="19/08/2026"

# Đặt cho CẢ HAI cổng: đây là sửa lỗi ở khâu sinh, không phải một trong ba cơ
# chế đang đối chiếu. Chỉ đặt một cổng là thêm biến khác biệt thứ tư, làm bẩn
# phép so trước/sau.
export UI_NGAY_HOM_NAY="$NGAY_LOI_NHAC"

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
mo   "  ngày cấp cho lời nhắc: $NGAY_LOI_NHAC"
[ "$SO_DC" -lt 1 ] && vang "  ⚠ Chưa có quan hệ dẫn chiếu — cổng 8001 sẽ không khác cổng 8000."

# ── 3. Dọn cổng cũ ──────────────────────────────────────────────────────────
pkill -f "uvicorn ui.server:app" >/dev/null 2>&1 && { mo "  dọn server cũ…"; sleep 2; }

# ── 4. Hai cổng, hai cấu hình ───────────────────────────────────────────────
LOG0="$(mktemp -t demo8000)"; LOG1="$(mktemp -t demo8001)"

# TRƯỚC cải tiến — tắt hết, dùng đúng tham số mặc định của báo cáo
env UI_REFERS_MODE= UI_RERANK_MODE= UI_CHUYEN_TIEP= \
    UI_NGAY_HOM_NAY="$NGAY_LOI_NHAC" \
    SF_DENSE_POOL_MIN=50 SF_RARITY_ALPHA=1.5 DEMO_MODE=live \
    "$PY" -m uvicorn ui.server:app --port 8000 >"$LOG0" 2>&1 &
PID0=$!

# SAU cải tiến — ĐỦ NĂM biến. Thiếu một cái là demo sai.
env UI_REFERS_MODE=khoan UI_RERANK_MODE=trong-norm UI_CHUYEN_TIEP=1 \
    UI_NGAY_HOM_NAY="$NGAY_LOI_NHAC" \
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

# ── 6. Hâm nóng: chạy trước một câu ở MỖI cổng ──────────────────────────────
# Mô hình nhúng và cross-encoder chỉ được nạp ở lần hỏi ĐẦU TIÊN của tiến
# trình (~50 giây cho cross-encoder). Không hâm ở đây thì câu hỏi đầu tiên
# TRƯỚC HỘI ĐỒNG chính là câu chậm nhất buổi. Câu dùng để hâm đã có sẵn trong
# bộ nhớ đệm nên không gọi mô hình sinh, không tốn tiền, không cần mạng.
ham() {   # $1 = cổng
  curl -sN -m 300 -X POST "http://127.0.0.1:$1/api/ask" \
       -H 'Content-Type: application/json' \
       --data-binary '{"question":"Hạn mức giao đất ở cho cá nhân do cơ quan nào quy định, và con số cụ thể hiện nay tại TP.HCM được quy định ở văn bản nào?"}' \
       2>/dev/null | grep -c '"step": *"done"'
}
printf "  hâm nóng cổng 8001 (nạp cross-encoder, 60–120 giây)"
H1="$(ham 8001)"; printf "\n"
[ "${H1:-0}" -ge 1 ] && xanh "✓ Cổng 8001 đã hâm — câu đầu tiên sẽ chạy với tốc độ ổn định" \
                     || vang "  ⚠ Hâm cổng 8001 không xong; câu hỏi đầu tiên sẽ chậm hơn bình thường."
printf "  hâm nóng cổng 8000"
H0="$(ham 8000)"; printf "\n"
[ "${H0:-0}" -ge 1 ] && xanh "✓ Cổng 8000 đã hâm" \
                     || vang "  ⚠ Hâm cổng 8000 không xong."

echo
xanh "════════════════════════════════════════════════════════════"
xanh "  SẴN SÀNG"
xanh "════════════════════════════════════════════════════════════"
echo "    http://127.0.0.1:8001   ←  SAU cải tiến — CỔNG TRÌNH BÀY CHÍNH"
echo "    http://127.0.0.1:8000   ←  TRƯỚC cải tiến (chỉ để đối chiếu khi cần)"
echo
mo   "    Ba câu nên trình bày, theo thứ tự:"
mo   "     1. Hạn mức giao đất ở cho cá nhân do cơ quan nào quy định, và con số"
mo   "        cụ thể hiện nay tại TP.HCM được quy định ở văn bản nào?"
mo   "     2. Hồi trước nghe nói ở TP.HCM một hộ được tới 300 mét vuông đất ở,"
mo   "        sao giờ nghe nói chỉ còn 250? Người ta đổi quy định hồi nào vậy?"
mo   "     3. Đăng ký lại khai sinh mà không còn bản sao giấy khai sinh cũ thì"
mo   "        cần giấy tờ gì?"
echo
mo   "    Câu 2 là câu đối chiếu rõ nhất: 8001 hiện thêm KHỐI CẢNH BÁO"
mo   "    'quy định đã thay đổi' mà 8000 không có."
echo
mo   "    Mỗi câu trên cổng 8001 mất 13–22 giây (cross-encoder chạy trên CPU)."
mo   "    Dừng: Ctrl-C"
echo

command -v open >/dev/null && {
  open "http://127.0.0.1:8000/?t=$(date +%s)" 2>/dev/null
  sleep 1
  open "http://127.0.0.1:8001/?t=$(date +%s)" 2>/dev/null
}

wait "$PID0" "$PID1"
