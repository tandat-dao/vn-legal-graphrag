"""Kiểm toán tài liệu cải tiến — chạy trước mỗi lần chốt số liệu.

Ba lớp kiểm:
  1. Số trong tài liệu KHỚP dữ liệu đo thật (bắt lỗi sao chép tay)
  2. Số trích từ báo cáo KHỚP baocao.pdf (báo cáo là nguồn sự thật duy nhất)
  3. Không dùng thuật ngữ/cách phát biểu đã bị cấm

    python scripts/kiem_toan_tai_lieu.py
"""
from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
from pathlib import Path

TAI_LIEU = Path("docs/CAI_TIEN_SAU_PHAN_BIEN.md")
BAO_CAO = Path.home() / "Documents/University/2526_Sem2/Thesis/Bản cứng/baocao.pdf"
SO_CHOT = Path("data/evaluation/v2_chot_sau_gop.json")

loi: list[str] = []
canh_bao: list[str] = []


def _text_bao_cao() -> str:
    """Trích text báo cáo. Thiếu pdftotext thì BỎ QUA lớp 2 chứ không im lặng."""
    if not BAO_CAO.exists():
        canh_bao.append("không thấy baocao.pdf — BỎ QUA lớp kiểm 2")
        return ""
    try:
        r = subprocess.run(["pdftotext", "-layout", str(BAO_CAO), "-"],
                           capture_output=True, text=True, timeout=120)
        return r.stdout
    except FileNotFoundError:
        canh_bao.append("không có pdftotext — BỎ QUA lớp kiểm 2")
        return ""


def _tinh_tu_du_lieu() -> dict[str, float | int]:
    """Tính lại mọi con số của §3.1 từ tệp kết quả, không tin số chép tay."""
    d = json.load(open(SO_CHOT, encoding="utf-8"))
    k = [x for x in d[0] if x not in ("id", "gap_type")]
    b, c = k[0], k[-1]
    n = len(d)
    out = {
        "moc": sum(r[b]["khoan"] for r in d) / n,
        "cuoi": sum(r[c]["khoan"] for r in d) / n,
        "delta": sum(r[c]["khoan"] - r[b]["khoan"] for r in d) / n,
        "N": n,
        "da_tran": sum(1 for r in d if r[b]["khoan"] >= 1.0),
    }
    duoi = [r for r in d if r[b]["khoan"] < 1.0]
    out["con_cho"] = len(duoi)
    out["chua_duoc"] = sum(1 for r in duoi if r[c]["khoan"] > r[b]["khoan"])
    out["delta_kho"] = sum(r[c]["khoan"] - r[b]["khoan"] for r in duoi) / len(duoi)
    g = collections.defaultdict(list)
    for r in d:
        g[r["gap_type"]].append(r)
    for gp, rs in g.items():
        out["gap_" + gp] = sum(r[c]["khoan"] - r[b]["khoan"] for r in rs) / len(rs)
        out["n_" + gp] = len(rs)
    return out


def _so_vn(x: float, chu_so: int = 3) -> str:
    return ("%.*f" % (chu_so, x)).replace(".", ",")


def main() -> int:
    if not TAI_LIEU.exists():
        print("✗ không thấy %s" % TAI_LIEU)
        return 1
    doc = TAI_LIEU.read_text(encoding="utf-8")

    # ---- Lớp 1: số trong tài liệu vs dữ liệu đo thật ----
    print("── Lớp 1: tài liệu vs dữ liệu đo")
    s = _tinh_tu_du_lieu()
    can_co = [
        ("mốc", _so_vn(s["moc"])), ("cuối", _so_vn(s["cuoi"])),
        ("Δ", _so_vn(s["delta"])), ("Δ nhóm khó", _so_vn(s["delta_kho"])),
        ("số câu đã trần", str(s["da_tran"])), ("số câu còn chỗ", str(s["con_cho"])),
        ("số câu chữa được", str(s["chua_duoc"])),
    ]
    for gp in ("gap1", "gap2", "gap3", "gap4"):
        if "gap_" + gp in s:
            can_co.append((gp, _so_vn(s["gap_" + gp])))
    for ten, gia_tri in can_co:
        if gia_tri not in doc:
            loi.append("§3.1 thiếu hoặc sai số %s = %s" % (ten, gia_tri))
        else:
            print("   ✓ %-18s %s" % (ten, gia_tri))

    # ---- Lớp 1b: số của lĩnh vực lao động và kiểm thoái lui ----
    ld = Path("data/evaluation/lao_dong_baophu.json")
    kho36 = Path("data/evaluation/v2_chot_kho36.json")
    if ld.exists():
        e = json.load(open(ld, encoding="utf-8"))
        k2 = [x for x in e[0] if x not in ("id", "gap_type")]
        for ten, gt in (("lao động mốc", sum(r[k2[0]]["khoan"] for r in e) / len(e)),
                        ("lao động cuối", sum(r[k2[-1]]["khoan"] for r in e) / len(e))):
            v = _so_vn(gt)
            if v not in doc:
                loi.append("thiếu số %s = %s" % (ten, v))
            else:
                print("   ✓ %-18s %s" % (ten, v))
    else:
        canh_bao.append("chưa có lao_dong_baophu.json — bỏ qua kiểm lĩnh vực lao động")
    if kho36.exists():
        f = json.load(open(kho36, encoding="utf-8"))
        g36 = {r["id"]: r for r in f}
        g32 = {r["id"]: r for r in json.load(open(SO_CHOT, encoding="utf-8"))}
        kk = [x for x in f[0] if x not in ("id", "gap_type")]
        lech = sum(1 for i in set(g32) & set(g36) for x in kk
                   if abs(g32[i][x]["khoan"] - g36[i][x]["khoan"]) > 1e-9)
        if lech:
            loi.append("KIỂM THOÁI LUI: %d ô lệch giữa kho 32 và kho 36 — "
                       "tài liệu đang khẳng định 0" % lech)
        else:
            print("   ✓ kiểm thoái lui    0 ô lệch giữa kho 32 và kho 36")
    else:
        canh_bao.append("chưa có v2_chot_kho36.json — bỏ qua kiểm thoái lui")

    # ---- Lớp 1c: số của phép đo cấp ngày cho lời nhắc ----
    nl = Path("data/evaluation/ngay_loi_nhac.json")
    if nl.exists():
        t = json.load(open(nl, encoding="utf-8"))["tong"]
        # Số lỗi thì viết dạng chữ số trần trong tài liệu, F1 viết dạng dấu phẩy.
        for ten, giatri in (("lỗi thì (tắt)", str(t["loi_thi_tat"])),
                            ("F1 tắt ngày", _so_vn(t["f1_khoan_tat"])),
                            ("F1 bật ngày", _so_vn(t["f1_khoan_bat"]))):
            if giatri not in doc:
                loi.append("thiếu số %s = %s" % (ten, giatri))
            else:
                print("   ✓ %-18s %s" % (ten, giatri))
        if t["loi_thi_bat"] != 0:
            loi.append("tài liệu khẳng định lỗi thì về 0 nhưng dữ liệu đo %d"
                       % t["loi_thi_bat"])
        else:
            print("   ✓ %-18s %s" % ("lỗi thì (bật)", "0"))
    else:
        canh_bao.append("chưa có ngay_loi_nhac.json — bỏ qua kiểm phép đo cấp ngày")

    # ---- Lớp 2: số trích từ báo cáo ----
    print("\n── Lớp 2: tài liệu vs baocao.pdf")
    bc = _text_bao_cao()
    if bc:
        # (số trong tài liệu dùng dấu phẩy, trong PDF dùng dấu chấm)
        cap = ["0,617", "0,435", "0,182", "0,187", "88,1", "0,511",
               "0,402", "0,301", "0,239", "0,154", "0,131", "0,829"]
        for v in cap:
            if v not in doc:
                continue
            if v.replace(",", ".") not in bc:
                loi.append("số %s có trong tài liệu nhưng KHÔNG có trong báo cáo" % v)
            else:
                print("   ✓ %s" % v)
        if "67/32/24" in doc and "67/32/24" not in bc:
            loi.append("67/32/24 không khớp báo cáo")

    # ---- Lớp 3: cách phát biểu bị cấm ----
    print("\n── Lớp 3: thuật ngữ và phát biểu")
    cam = [
        (r"\bGap \d", "báo cáo dùng 'thách thức', không dùng 'Gap'"),
        (r"thắng trên mọi cấu hình(?!\")", "Bảng 4.13 có một hàng ÂM (−0,022)"),
        (r"cái nạng|câm với|đi đúng dây|pha loãng|món hời|quá tay",
         "lối nói ví von — phải diễn đạt trực tiếp"),
        # Bộ chấm 88.1% CHÍNH LÀ mô hình sinh (Bảng 3.6) và cho điểm CAO NHẤT.
        # Đó đúng chiều thiên lệch tự đề cao, KHÔNG phải bằng chứng bác bỏ.
        (r"không được số liệu ủng hộ|chiều ngược với dự đoán|chấm chặt nhất",
         "diễn giải NGƯỢC về thiên lệch tự đề cao — xem §3.4"),
        # Nhóm 'câu không nêu tỉnh' KHÔNG trả về rỗng — nó loại mất văn bản cấp
        # tỉnh. Gộp ba nhóm thành một kiểu hỏng là sai.
        (r"[Vv]ới ba nhóm\s*\n?này hệ trả về rỗng|ba nhóm câu.{0,40}trả về rỗng",
         "ba nhóm hỏng theo HAI kiểu khác nhau — xem §1"),
        (r"120/121", "con số đúng là 118/121 (đã kiểm lại bằng so ghép cặp)"),
    ]
    for mau, vi_sao in cam:
        for m in re.finditer(mau, doc):
            dong = doc[:m.start()].count("\n") + 1
            loi.append("dòng %d: '%s' — %s" % (dong, m.group(0), vi_sao))
    if not any("dòng" in e for e in loi):
        print("   ✓ không có thuật ngữ bị cấm")

    # ---- Lớp 4: khẳng định phải có mặt ----
    print("\n── Lớp 4: cảnh báo bắt buộc")
    bat_buoc = [
        ("−0,022", "phải nêu hàng âm của Bảng 4.13"),
        ("bốn trên năm", "phải nói rõ ưu thế giữ ở 4/5 cấu hình"),
        ("79,0%", "phải nêu cận dưới thận trọng của tỉ lệ hậu thuẫn"),
        ("da_duyet", None),  # bỏ qua, chỉ minh hoạ
    ]
    for chuoi, vi_sao in bat_buoc:
        if vi_sao and chuoi not in doc:
            loi.append("THIẾU cảnh báo: %s (%s)" % (chuoi, vi_sao))
        elif vi_sao:
            print("   ✓ %s" % chuoi)

    print("\n" + "═" * 52)
    for c in canh_bao:
        print("⚠  %s" % c)
    if loi:
        print("✗ %d LỖI:" % len(loi))
        for e in loi:
            print("   • %s" % e)
        return 1
    print("✓ TẤT CẢ KIỂM TRA ĐỀU QUA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
