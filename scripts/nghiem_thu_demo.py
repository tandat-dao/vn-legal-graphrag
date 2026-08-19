#!/usr/bin/env python3
"""Nghiệm thu hai cổng demo trước khi bảo vệ — chạy được lặp lại, không cần sửa tay.

Kiểm sáu điều, mỗi điều là một thứ đã từng hỏng thật:

  1. Hai cổng có ĐÚNG cấu hình khác nhau (đã từng chỉ khác 1/3 cơ chế mà nhìn
     giao diện không phát hiện được).
  2. Mọi câu demo chạy không lỗi.
  3. Mọi câu đều TRÚNG bộ nhớ đệm (trượt là phải gọi mô hình, cần mạng + hạn ngạch).
  4. Không câu nào còn viết "sắp có hiệu lực" cho mốc đã qua.
  5. Mọi trích dẫn tra được nguyên văn (đã từng hỏng với Phụ lục nhiều mục).
  6. Ba câu trình bày trả đúng số trích dẫn mong đợi.

Dùng:  python scripts/nghiem_thu_demo.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
TEP_CAU_HOI = GOC / "ui/docs/DEMO_QUESTIONS.md"

# Cụm chỉ đúng khi mốc nằm ở TƯƠNG LAI. Mọi mốc trong kho đều đã qua, nên xuất
# hiện cụm này = mô hình đang tự đoán ngày hiện tại.
THI_SAI = r"sắp (?:có|hết) hiệu lực|sẽ có hiệu lực từ|quy định hiện hành \(có hiệu lực đến"

# Ba câu trình bày và số trích dẫn đã đo. Lệch = có gì đó đã đổi.
BA_CAU = {
    "Hạn mức giao đất ở cho cá nhân do cơ quan nào quy định": 5,
    "Hồi trước nghe nói ở TP.HCM một hộ được tới 300 mét vuông": 2,
    "Đăng ký lại khai sinh mà không còn bản sao giấy khai sinh": 7,
}


def cau_hoi_demo() -> list[str]:
    return [d.strip() for d in TEP_CAU_HOI.read_text(encoding="utf-8").splitlines()
            if d.strip() and not d.startswith("#")]


def cho_ranh(cong: int, giay: float = 30.0) -> None:
    """Đợi máy chủ nhả khoá trước khi hỏi câu tiếp.

    Máy chủ chỉ chạy MỘT câu một lúc; khoá được nhả trong khối `finally` của
    luồng sự kiện, tức là hơi TRỄ so với lúc byte cuối tới nơi. Người trình bày
    bấm câu sau cách vài giây nên không bao giờ chạm vào cửa sổ đó, nhưng bản
    kiểm này bắn liên tiếp thì chạm — và vì câu bị từ chối trả lời TỨC THÌ,
    một lần trượt sẽ kéo mọi câu còn lại trượt theo trong cùng một cửa sổ.
    Đó là cách bản kiểm từng báo 9 lỗi giả.
    """
    import time
    het = time.time() + giay
    while time.time() < het:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{cong}/api/mode", timeout=5) as r:
                if not json.loads(r.read()).get("dang_ban"):
                    return
        except Exception:                      # máy chủ chưa sẵn sàng — thử lại
            pass
        time.sleep(0.5)


def hoi(cong: int, q: str) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{cong}/api/ask",
        data=json.dumps({"question": q}).encode(),
        headers={"Content-Type": "application/json"})
    ra = {"loi": "", "cache_hit": None, "citations": [], "answer": ""}
    with urllib.request.urlopen(req, timeout=300) as r:
        for dong in r:
            dong = dong.decode("utf-8").strip()
            if not dong.startswith("data: "):
                continue
            ev = json.loads(dong[6:])
            d = ev.get("data") or {}
            if ev.get("kind") == "error":
                ra["loi"] = d.get("thong_bao", "?")
            if ev.get("step") == "generate" and "cache_hit" in d:
                ra["cache_hit"] = d["cache_hit"]
            if ev.get("step") == "generate" and ev.get("kind") == "result":
                ra["answer"] = d.get("answer", "")
                ra["citations"] = d.get("citations") or []
    return ra


def tra_nguyen_van(cong: int, c: dict) -> bool:
    tham = {"norm_id": c["van_ban"], "dieu": c["dieu"]}
    if c.get("khoan"):
        tham["khoan"] = c["khoan"]
    if c.get("diem"):
        tham["diem"] = c["diem"]
    u = f"http://127.0.0.1:{cong}/api/text?" + urllib.parse.urlencode(tham)
    return bool(json.loads(urllib.request.urlopen(u, timeout=20).read()).get("tim_thay"))


def cau_hinh(cong: int) -> dict:
    """Đọc biến môi trường THỰC của tiến trình đang nghe cổng đó."""
    import subprocess
    pids = subprocess.run(["pgrep", "-f", "uvicorn ui.server:app"],
                          capture_output=True, text=True).stdout.split()
    for pid in pids:
        args = subprocess.run(["ps", "-o", "args=", "-p", pid],
                              capture_output=True, text=True).stdout
        if f"--port {cong}" not in args:
            continue
        moi = subprocess.run(["ps", "eww", pid], capture_output=True, text=True).stdout
        return {k: v for k, v in
                (x.split("=", 1) for x in moi.split() if "=" in x and x.split("=")[0].isupper())}
    return {}


def main() -> int:
    loi: list[str] = []
    print("\n" + "=" * 62)
    print("  NGHIỆM THU DEMO")
    print("=" * 62)

    # ── 1. Cấu hình hai cổng
    print("\n── 1. Cấu hình hai cổng")
    mong_doi = {
        8000: {"UI_RERANK_MODE": "", "SF_DENSE_POOL_MIN": "50"},
        8001: {"UI_RERANK_MODE": "trong-norm", "UI_REFERS_MODE": "khoan",
               "UI_CHUYEN_TIEP": "1", "SF_DENSE_POOL_MIN": "100",
               "SF_RARITY_ALPHA": "0"},
    }
    for cong, can in mong_doi.items():
        moi = cau_hinh(cong)
        if not moi:
            # Cổng 8000 chỉ mở khi chạy `bao-ve.sh --doi-chieu`. Không mở là
            # bình thường; thiếu cổng TRÌNH BÀY mới là lỗi.
            if cong == 8000:
                print("   · cổng 8000 không mở (bình thường — chỉ mở khi --doi-chieu)")
            else:
                loi.append(f"cổng {cong} không chạy")
                print(f"   ✗ cổng {cong} không chạy")
            continue
        sai = [k for k, v in can.items() if moi.get(k, "") != v]
        if sai:
            loi.append(f"cổng {cong} sai biến: {sai}")
            print(f"   ✗ cổng {cong} sai: {sai}")
        else:
            print(f"   ✓ cổng {cong} đúng {len(can)} biến")
        # Ngày CHỈ đặt cho cổng trình bày. Cổng 8000 giữ lời nhắc cũ để bộ
        # nhớ đệm sẵn có của nó vẫn trúng.
        if cong == 8001 and not moi.get("UI_NGAY_HOM_NAY"):
            loi.append("cổng 8001 chưa cấp ngày cho lời nhắc")
            print("   ✗ cổng 8001 thiếu UI_NGAY_HOM_NAY")
        elif cong == 8001:
            print(f"   ✓ cổng 8001 ngày lời nhắc = {moi['UI_NGAY_HOM_NAY']}")

    # ── 2..6 trên cổng trình bày
    ds = cau_hoi_demo()
    print(f"\n── 2–6. {len(ds)} câu demo trên cổng 8001")
    tong_cit = tra_duoc = 0
    for i, q in enumerate(ds, 1):
        cho_ranh(8001)
        r = hoi(8001, q)
        van_de = []
        if "đang xử lý câu hỏi trước" in r["loi"]:
            cho_ranh(8001)                     # vẫn dính → đợi hẳn rồi thử lại
            r = hoi(8001, q)
        if r["loi"]:
            van_de.append(f"LỖI: {r['loi'][:40]}")
        if r["cache_hit"] is not True:
            van_de.append("TRƯỢT CACHE")
        thi = re.findall(THI_SAI, r["answer"])
        if thi:
            van_de.append(f"thì sai×{len(thi)}")
        for c in r["citations"]:
            tong_cit += 1
            if tra_nguyen_van(8001, c):
                tra_duoc += 1
            else:
                van_de.append(f"không tra được {c['van_ban']} Đ{c['dieu']}")
        for mau, so in BA_CAU.items():
            if mau in q and len(r["citations"]) != so:
                van_de.append(f"số trích dẫn {len(r['citations'])} ≠ {so} đã đo")
        if van_de:
            loi.append(f"câu {i}: {'; '.join(van_de)}")
        print(f"   {'✓' if not van_de else '✗'} [{i:>2}] {len(r['citations'])} tr.dẫn  "
              f"{q[:44]}{'' if not van_de else '  ← ' + '; '.join(van_de)}")

    print(f"\n   trích dẫn tra được nguyên văn: {tra_duoc}/{tong_cit}")

    print("\n" + "=" * 62)
    if loi:
        print(f"  ✗ {len(loi)} VẤN ĐỀ")
        for x in loi:
            print(f"    · {x}")
        return 1
    print("  ✓ TẤT CẢ ĐỀU QUA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
