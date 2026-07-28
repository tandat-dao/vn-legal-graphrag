"""
Build review sheet — sinh trang HTML dễ đọc cho [A]+[B] review GT eval set v2.

Mỗi câu hiển thị: câu hỏi + đáp án GT + ĐOẠN LUẬT GỐC kéo từ corpus đặt cạnh
mỗi citation (để đối chiếu không cần mở file .md), + ghi chú soạn + 4 ô tick
tiêu chí + ô comment. Trạng thái review lưu trong localStorage của trình duyệt;
có nút "Xuất review" để tải kết quả (JSON) gửi lại.

Usage:
    python -m src.evaluation.build_review_sheet
    open data/evaluation/GT_REVIEW.html
"""
import html
import json
import re
import unicodedata
from pathlib import Path

from src.ingestion.parser import parse_file

_NON_NORM = {"mapping_table.md", "crossref_decisions.md", "review_log.md"}
_DIEU_RE = re.compile(r"^Điều\s+(\S+?)\.")
_KHOAN_RE = re.compile(r"^Khoản\s+(\S+?)\.")
_DIEM_RE = re.compile(r"^Điểm\s+(\S+?)\.")
_MAX_SNIPPET = 2200


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).lower().split())


def build_text_index(raw_dir: Path) -> dict:
    """{norm_id: [ {dieu,khoan,diem,pl,khoan_pl,text}, ... ]} theo leaf node."""
    idx: dict = {}
    for f in sorted(raw_dir.glob("*.md")):
        if f.name in _NON_NORM:
            continue
        parsed = parse_file(str(f))
        nid = parsed["metadata"]["id"]
        leaves = idx.setdefault(nid, [])
        for node in parsed["nodes"]:
            dieu = khoan = diem = pl = None
            for seg in node["context_path"][1:]:
                if seg.startswith("Phụ lục"):
                    pl = _norm(seg)
                    continue
                m = _DIEU_RE.match(seg)
                if m:
                    dieu = m.group(1)
                    continue
                m = _KHOAN_RE.match(seg)
                if m:
                    khoan = m.group(1)
                    continue
                m = _DIEM_RE.match(seg)
                if m:
                    diem = m.group(1)
            leaves.append({"dieu": dieu, "khoan": khoan, "diem": diem,
                           "pl": pl, "text": node["text"]})
    return idx


def resolve_citation(cit: dict, leaves: list) -> str:
    """Ghép text các leaf khớp citation. Trả về '' nếu không tìm thấy."""
    vb_dieu = str(cit.get("dieu") or "").strip()
    khoan = cit.get("khoan")
    khoan = str(khoan).strip() if khoan is not None else None
    diem = cit.get("diem")
    diem = str(diem).strip() if diem is not None else None
    is_pl = cit.get("loai") == "phu_luc" or vb_dieu.lower().startswith("phụ lục")

    matched = []
    for lf in leaves:
        if is_pl:
            if lf["pl"] is None:
                continue
            if vb_dieu != "_default":
                tgt = _norm(vb_dieu if vb_dieu.lower().startswith("phụ lục")
                            else f"phụ lục {vb_dieu}")
                if not (lf["pl"].startswith(tgt) or tgt.startswith(lf["pl"])):
                    continue
            if khoan is not None and lf["khoan"] != khoan:
                continue
        else:
            if lf["dieu"] != vb_dieu:
                continue
            if khoan is not None and lf["khoan"] != khoan:
                continue
            if diem is not None and lf["diem"] != diem:
                continue
        matched.append(lf["text"])
    txt = "\n\n".join(matched).strip()
    if len(txt) > _MAX_SNIPPET:
        txt = txt[:_MAX_SNIPPET] + "\n… (cắt bớt — xem file gốc nếu cần)"
    return txt


def cit_label(c: dict) -> str:
    parts = []
    if c.get("loai") == "phu_luc":
        d = c.get("dieu")
        parts.append("Phụ lục" if d == "_default" else f"Phụ lục {d}")
    elif c.get("dieu"):
        parts.append(f"Điều {c['dieu']}")
    if c.get("khoan"):
        parts.append(f"Khoản {c['khoan']}")
    if c.get("diem"):
        parts.append(f"Điểm {c['diem']}")
    return " ".join(parts) + f" — {c.get('van_ban')}"


_GAP_COLOR = {"gap1": "#7c3aed", "gap2": "#2563eb", "gap3": "#059669",
              "gap4": "#d97706", "negative": "#dc2626"}


def render(items: list, text_idx: dict) -> str:
    cards = []
    for it in items:
        gap = it["gap_type"]
        color = _GAP_COLOR.get(gap, "#666")
        sub = it.get("subtype") or ""
        meta = " · ".join(filter(None, [
            gap, sub, it.get("difficulty"),
            str(it.get("theme")), str(it.get("jurisdiction")),
            "synthesis" if it.get("synthesis") else "",
            f"↔{it['pair_id']}" if it.get("pair_id") else "",
        ]))
        cits_html = []
        for c in it["ground_truth_citations"]:
            src = resolve_citation(c, text_idx.get(c.get("van_ban"), []))
            ok = bool(src)
            badge = "" if ok else '<span class="missing">KHÔNG RESOLVE ĐƯỢC</span>'
            cits_html.append(
                f'<div class="cit"><div class="cit-h">📎 {html.escape(cit_label(c))}{badge}</div>'
                f'<pre class="src">{html.escape(src or "(trống)")}</pre></div>'
            )
        if not it["ground_truth_citations"]:
            cits_html.append('<div class="cit neg">⛔ Câu NEGATIVE — không có citation '
                             '(đáp án đúng = hệ phải từ chối / cảnh báo ngoài scope)</div>')
        qid = it["id"]
        cards.append(f'''
<div class="card" data-id="{qid}" data-theme="{it.get('theme')}" data-gap="{gap}" style="border-left:6px solid {color}">
  <div class="hd"><span class="id">{qid}</span><span class="meta">{html.escape(meta)}</span>
    <span class="status" id="st-{qid}"></span></div>
  <div class="q">❓ {html.escape(it['question'])}</div>
  <div class="a"><b>Đáp án GT:</b> {html.escape(it['ground_truth_answer'])}</div>
  <div class="cits">{''.join(cits_html)}</div>
  <div class="note-soan">📝 <i>Ghi chú soạn:</i> {html.escape(it.get('notes',''))}</div>
  <div class="review">
    <label><input type="checkbox" class="chk" data-k="dung"> Đáp án đúng luật</label>
    <label><input type="checkbox" class="chk" data-k="cit"> Citation đúng chỗ</label>
    <label><input type="checkbox" class="chk" data-k="gap"> Gán gap hợp lý</label>
    <label><input type="checkbox" class="chk" data-k="tunhien"> Câu tự nhiên</label>
    <span class="verdict">
      <label><input type="radio" name="v-{qid}" value="ok"> ✅ Đạt</label>
      <label><input type="radio" name="v-{qid}" value="fix"> ⚠️ Cần sửa</label>
    </span>
    <input type="text" class="who" placeholder="người duyệt (A/B)">
    <input type="text" class="cmt" placeholder="ghi chú của người duyệt (nếu cần sửa)">
  </div>
</div>''')

    total = len(items)
    return f'''<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<title>GT Review — eval set v2 ({total} câu)</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:0 auto;padding:16px;color:#1a1a1a;background:#fafafa}}
 .bar{{position:sticky;top:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px 14px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.08);z-index:10}}
 .bar h1{{font-size:16px;margin:0 0 6px}}
 .bar button{{margin:2px;padding:4px 10px;border:1px solid #ccc;border-radius:6px;background:#f3f3f3;cursor:pointer;font-size:13px}}
 .bar button.on{{background:#2563eb;color:#fff;border-color:#2563eb}}
 #prog{{font-weight:600}}
 .card{{background:#fff;border:1px solid #e3e3e3;border-radius:8px;padding:12px 14px;margin-bottom:12px}}
 .card.done{{opacity:.55}} .card.fix{{background:#fff7ed}}
 .hd{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
 .id{{font-weight:700;color:#111}} .meta{{font-size:12px;color:#777}} .status{{margin-left:auto;font-size:13px}}
 .q{{font-size:15px;font-weight:600;margin:8px 0}}
 .a{{background:#f0f6ff;border-radius:6px;padding:8px 10px;font-size:14px;line-height:1.5;margin-bottom:8px}}
 .cit{{margin:6px 0;border:1px solid #eee;border-radius:6px;overflow:hidden}}
 .cit-h{{background:#f6f6f6;padding:5px 8px;font-size:13px;font-weight:600}}
 .cit.neg{{background:#fef2f2;border-color:#fecaca;padding:8px;font-size:13px}}
 .src{{margin:0;padding:8px 10px;font-size:12.5px;white-space:pre-wrap;word-break:break-word;max-height:230px;overflow:auto;background:#fcfcfc;font-family:ui-monospace,Menlo,monospace;line-height:1.45}}
 .missing{{color:#fff;background:#dc2626;padding:1px 6px;border-radius:4px;font-size:11px;margin-left:8px}}
 .note-soan{{font-size:12.5px;color:#555;background:#fafafa;border-left:3px solid #ddd;padding:5px 8px;margin:8px 0}}
 .review{{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;border-top:1px dashed #ddd;padding-top:8px;font-size:13px}}
 .review label{{cursor:pointer}} .verdict{{margin-left:6px}}
 .who{{width:120px}} .cmt{{flex:1;min-width:220px;padding:3px 6px}}
 input[type=text]{{border:1px solid #ccc;border-radius:5px;font-size:13px}}
</style></head><body>
<div class="bar">
  <h1>Review GT — eval set v2 · <span id="prog">0/{total}</span> đã duyệt</h1>
  <div>
    <b>Lọc lĩnh vực:</b>
    <button class="f" data-f="theme" data-v="all">Tất cả</button>
    <button class="f" data-f="theme" data-v="dat-dai">Đất đai</button>
    <button class="f" data-f="theme" data-v="ho-tich">Hộ tịch</button>
    <button class="f" data-f="theme" data-v="nuoi-con-nuoi">Nuôi con nuôi</button>
    <button class="f" data-f="theme" data-v="None">Negative</button>
    &nbsp;|&nbsp;
    <button class="f2" data-hide="done">Ẩn câu đã duyệt</button>
    <button id="export">⬇︎ Xuất review (JSON)</button>
  </div>
</div>
{''.join(cards)}
<script>
const KEY='gt_review_v2';
let store=JSON.parse(localStorage.getItem(KEY)||'{{}}');
function save(){{localStorage.setItem(KEY,JSON.stringify(store));updateProg();}}
function updateProg(){{
  let n=Object.values(store).filter(x=>x&&x.v).length;
  document.getElementById('prog').textContent=n+'/{total}';
}}
document.querySelectorAll('.card').forEach(card=>{{
  const id=card.dataset.id; const s=store[id]||{{}};
  card.querySelectorAll('.chk').forEach(c=>{{c.checked=!!(s.chk&&s.chk[c.dataset.k]);}});
  if(s.v){{card.querySelector(`input[value="${{s.v}}"]`).checked=true;}}
  if(s.who)card.querySelector('.who').value=s.who;
  if(s.cmt)card.querySelector('.cmt').value=s.cmt;
  applyStatus(card);
  card.addEventListener('change',()=>collect(card));
  card.addEventListener('input',()=>collect(card));
}});
function collect(card){{
  const id=card.dataset.id; const o={{chk:{{}}}};
  card.querySelectorAll('.chk').forEach(c=>o.chk[c.dataset.k]=c.checked);
  const v=card.querySelector('input[type=radio]:checked'); o.v=v?v.value:'';
  o.who=card.querySelector('.who').value; o.cmt=card.querySelector('.cmt').value;
  store[id]=o; save(); applyStatus(card);
}}
function applyStatus(card){{
  const id=card.dataset.id; const s=store[id]||{{}};
  const st=document.getElementById('st-'+id);
  card.classList.remove('done','fix');
  if(s.v==='ok'){{st.textContent='✅ Đạt';card.classList.add('done');}}
  else if(s.v==='fix'){{st.textContent='⚠️ Cần sửa';card.classList.add('fix');}}
  else st.textContent='';
}}
document.querySelectorAll('.f').forEach(b=>b.onclick=()=>{{
  document.querySelectorAll('.f').forEach(x=>x.classList.remove('on'));b.classList.add('on');
  const v=b.dataset.v;
  document.querySelectorAll('.card').forEach(c=>{{
    c.style.display=(v==='all'||c.dataset.theme===v)?'':'none';
  }});
}});
document.querySelector('.f2').onclick=function(){{
  this.classList.toggle('on');const hide=this.classList.contains('on');
  document.querySelectorAll('.card.done').forEach(c=>c.style.display=hide?'none':'');
}};
document.getElementById('export').onclick=()=>{{
  const blob=new Blob([JSON.stringify(store,null,2)],{{type:'application/json'}});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='GT_REVIEW_ket_qua.json';a.click();
}};
updateProg();
</script></body></html>'''


def main():
    root = Path(".")
    items = json.loads((root / "data/evaluation/test_set_v2.json").read_text(encoding="utf-8"))
    text_idx = build_text_index(root / "data/raw")
    out = root / "data/evaluation/GT_REVIEW.html"
    out.write_text(render(items, text_idx), encoding="utf-8")
    # Cảnh báo citation không resolve được (để soạn giả tự soi)
    miss = 0
    for it in items:
        for c in it["ground_truth_citations"]:
            if not resolve_citation(c, text_idx.get(c.get("van_ban"), [])):
                miss += 1
                print(f"  ⚠️ {it['id']}: không resolve text — {cit_label(c)}")
    print(f"✅ Đã sinh {out} ({len(items)} câu). Citation không resolve text: {miss}")


if __name__ == "__main__":
    main()
