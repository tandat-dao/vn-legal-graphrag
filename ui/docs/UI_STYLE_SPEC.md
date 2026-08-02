# UI_STYLE_SPEC — Ngôn ngữ thị giác kế thừa từ bản UI Cổng DVC

> **Đối tượng đọc:** Claude Code (người implement UI của `vn-legal-graphrag`).
> **Nguồn:** trích xuất từ `frontend/` của repo `dichvucong` (Next.js 14 + Tailwind 3), bản UI mô phỏng dichvucong.gov.vn.
> **Vai trò của file này:** cung cấp **design token + giải phẫu component** để tái dựng cảm giác thị giác đó trong `ui/static/index.html` của dự án mới. **Không** phải lệnh sao chép nguyên trạng.

---

## 0. Đọc trước — ba câu chốt

1. **Cái cần lặp lại là *ngôn ngữ thị giác*** (palette, nhịp chữ, khung header/footer, cách viền–bo–hover của thẻ), **không phải cấu trúc trang**. Dự án mới là **một trang hỏi–đáp duy nhất** (xem `docs/UI_DEMO_SPEC.md` mục 6) — không có nav đa cấp, không có life-events grid, không có tab.
2. **UI mới ưu tiên hơn UI cũ.** Chỗ nào token cũ làm trang mới xấu đi hoặc gây hiểu nhầm học thuật → bỏ token cũ. Danh sách bắt buộc bỏ ở mục 7.
3. **Chỉ đổi lớp trình bày.** `ui/static/index.html` đã chạy được; giữ nguyên **toàn bộ `id`** và cấu trúc DOM mà JS đang truy vấn (mục 6.0). Đây là công việc **restyle**, không phải viết lại.

---

## 1. Bảng màu

Repo cũ tồn tại **hai** palette chồng nhau: bảng cũ hardcode trong `tailwind.config.ts` (thế hệ 1, bám sát dichvucong.gov.vn) và bảng CSS variable trong `globals.css` (thế hệ 2, đã tinh chỉnh). **Dùng bảng thế hệ 2 làm chuẩn duy nhất**, lấy vài giá trị thế hệ 1 làm màu chức năng.

### 1.1 Token chính (thế hệ 2 — copy nguyên vào `:root`)

```css
:root {
  /* Navy — quyền uy, nền tảng. Dùng cho chữ tiêu đề, chip trích dẫn, node tier cao */
  --navy:             #1B2B4B;
  --navy-mid:         #2D4A7A;
  --navy-light:       #E8EDF5;
  --navy-faint:       #F0F3F8;

  /* Terracotta — điểm nhấn, tính người. Dùng cho chrome (header), accent, trạng thái đang chạy */
  --terracotta:       #CE7A58;
  --terracotta-dk:    #B8694A;
  --terracotta-lt:    #F0EBE6;
  --terracotta-faint: #FAF5F2;

  /* Neutral — thang xám ám ấm, KHÔNG dùng slate/gray của Tailwind */
  --white:            #FFFFFF;
  --warm-white:       #F8F6F3;
  --gray-50:          #F9F9F8;
  --gray-100:         #F0EFED;
  --gray-200:         #E2E0DC;
  --gray-300:         #C8C5BF;
  --gray-500:         #8A8680;
  --gray-700:         #4A4844;
  --gray-900:         #1C1B19;

  /* Ngữ nghĩa */
  --bg-page:        var(--warm-white);
  --bg-card:        var(--white);
  --bg-section:     var(--terracotta-faint);
  --border-card:    var(--gray-200);
  --border-accent:  var(--terracotta);
  --text-primary:   var(--gray-900);
  --text-secondary: var(--gray-700);
  --text-muted:     var(--gray-500);
}
```

### 1.2 Màu chức năng lấy từ thế hệ 1

| Vai trò | Hex | Dùng ở đâu trong UI mới |
|---|---|---|
| CTA vàng | `#FFC251` (hover `#F0B340`), chữ **đen**, `font-bold` | chip gợi ý câu hỏi, nút Hỏi phụ |
| Đỏ nâu footer | `#903938` | thanh footer, badge "HẾT HIỆU LỰC" |
| Xanh điểm số | `#28A745` | điểm similarity vượt ngưỡng, dấu ✓ bước đã xong |
| Xanh link | `#2A6EBB` | link phụ, "xem nguyên văn" |
| Xanh hồ sơ | `#4A7AA8` | node đồ thị tier 3 |
| Xanh công dân | `#3D9E8D` | dự phòng, ví dụ trạng thái cache HIT ($0) |
| Viền xám | `#DDDDDD` | viền các nhóm input dạng "government flat" |
| **Vàng đối chiếu** | nền `#FFF4DE` · chữ `#8A5A12` · viền `#F0D08A` | **màu thứ ba** cho chip trích dẫn trạng thái `gan-dung` (xem 1.2.1) |

### 1.2.1 Ba màu trạng thái chip trích dẫn — danh sách đóng

`citation_links[].khop` do backend trả về có **đúng ba** giá trị. Palette phải có **ba** bộ màu phân biệt được từ cuối phòng, không được gộp hai trạng thái vào một màu:

| `khop` | Nền | Chữ | Viền | Nghĩa |
|---|---|---|---|---|
| `chinh-xac` | `#EAF6EC` | `#1E7A34` | `#A8DDB5` | trích dẫn khớp đúng một block trong context |
| `gan-dung` | `#FFF4DE` | `#8A5A12` | `#F0D08A` | khớp văn bản nhưng lệch cấp Khoản/Điểm |
| `khong-tim-thay` | `#FDECEC` | `#903938` | `#E8C4C4` | trích dẫn không có trong context — tín hiệu thật |

Trạng thái thứ tư (**không phải** `khop`): chip trong văn xuôi không tìm được `citation_links` tương ứng (`!link` trong `chipCitation`) → xám trung tính `var(--gray-100)` / `var(--text-secondary)` / `var(--border-card)`, để không bị nhầm với ba trạng thái đối chiếu thật.

### 1.3 Hai chế độ bảng màu A / B — có công tắc trên UI

Cặp *terracotta + nền kem ấm* là một hướng rất phổ biến hiện nay và **không phải** bản sắc thật của dichvucong.gov.vn (cổng thật dùng xanh dương/đỏ cờ). Thay vì chốt cứng một phương án trên giấy, `index.html` **cài sẵn cả hai** và đổi được ngay trong bảng thiết lập ở bánh răng góc phải (hai nút `A` / `B`) — để so trực tiếp trên máy chiếu thật rồi mới chốt.

**Token ở 1.1 KHÔNG đổi giữa hai chế độ.** Chỉ **vai trò** của chúng đảo:

| Chế độ | Chrome (header · thanh trạng thái · hero · footer) | Navy | Terracotta |
|---|---|---|---|
| **A — Terracotta chrome** *(mặc định)* | `--terracotta` / `--terracotta-dk` | chữ tiêu đề, chip `navy-faint`, thang tier của đồ thị | vừa chrome vừa accent |
| **B — Navy chrome** | `--navy` / `--navy-mid` | màu chrome | **chỉ** accent: bước đang chạy, vạch nhãn, viền hover, cạnh `AMENDS`, tier 4 |

Điểm đáng quan sát khi so: ở **A**, terracotta phải gánh **hai vai** (chrome + accent) nên "bước đang chạy" và "cạnh AMENDS" kém nổi hơn — chúng cùng màu với dải header. Ở **B**, terracotta rảnh tay nên tín hiệu accent bật hẳn lên. Đây chính là lập luận chọn B, nhưng giờ **nhìn được** thay vì phải tin lời.

#### Cách cài đặt — bắt buộc theo đúng cơ chế này

Năm **biến ngữ nghĩa** trong `:root` (chế độ A), và chế độ B là **một khối `:root[data-theme="b"]` ghi đè**. Không viết hai bộ class Tailwind song song:

```css
:root {                                   /* A */
  --chrome-bg:     var(--terracotta);
  --chrome-bg-2:   var(--terracotta-dk);
  --chrome-text:   var(--white);
  --accent:        var(--terracotta);
  --accent-strong: var(--terracotta-dk);
}
:root[data-theme="b"] {                   /* B — chỉ ghi đè vai trò */
  --chrome-bg:     var(--navy);
  --chrome-bg-2:   var(--navy-mid);
  --accent:        var(--terracotta);
  --accent-strong: var(--terracotta-dk);
}
```

Mọi chỗ dùng màu chrome/accent phải đi qua 5 biến này (`.chrome-1`, `.chrome-2`, `.dai-hero`, `.vach-accent`, `.chu-accent`, `.nut-chinh`, `.thanh-token-fill`, `.buoc-chay`, focus ring, scrollbar hover…). Công tắc chỉ làm một việc: `document.documentElement.dataset.theme = "a" | "b"`.

**Bộ vai trò thứ hai — xương sống bảy bước** (`--buoc-*`): khác 5 biến trên ở chỗ nó dùng **cả hai** màu chủ đạo cùng lúc và **đảo chúng** giữa hai chế độ — vòng tròn số mang màu chủ đạo của chế độ, đường nối mang màu còn lại. Đây là chỗ duy nhất trong trang cố tình đặt hai màu cạnh nhau, để chuỗi bảy bước không chìm vào một sắc duy nhất.

```css
:root {                                   /* A: chủ đạo terracotta */
  --buoc-tron:     var(--terracotta);   --buoc-ray:      var(--navy);
  --buoc-tron-chu: var(--gray-900);     --buoc-ray-nhat: var(--navy-light);
}
:root[data-theme="b"] {                   /* B: chủ đạo navy — hoán vai */
  --buoc-tron:     var(--navy);         --buoc-ray:      var(--terracotta);
  --buoc-tron-chu: var(--navy);         --buoc-ray-nhat: var(--terracotta-lt);
}
```

`--buoc-tron-chu` là **chữ số lúc bước còn chờ** (nền pha loãng 20%), không phải màu chữ chung: chế độ A không dùng được terracotta-dk vì chỉ đạt tương phản **3.1:1**, dưới ngưỡng 4.5:1 — họ terracotta không có sắc nào đủ tối nên phải mượn mực trung tính; chế độ B giữ navy vì navy đã đạt 8.9:1.

**Không lưu lựa chọn** — `localStorage`/`sessionStorage` bị cấm (mục 1.5). Mỗi lần tải lại trang là **A**.

#### Đồ thị Cytoscape — token riêng, phải nạp lại thủ công

Canvas **không** kế thừa CSS var, nên đồ thị có bộ token riêng (`--node-t1…t4`, `--node-t4-text`, `--node-text`, `--node-seed`, `--edge`, `--edge-amends`, `--edge-text`, `--graph-bg`) và đọc qua:

```js
const mauToken = (ten) =>
  getComputedStyle(document.documentElement).getPropertyValue(ten).trim();
```

`styleDoThi()` dựng **tươi** cả mảng style từ `mauToken()`; đổi chế độ thì `veLaiMauDoThi()` gọi `CY.style(styleDoThi())` — giữ nguyên layout đã chạy, chỉ thay màu.

Thang tier khác nhau giữa hai chế độ ở **tier 4**, và đó là chủ ý:

| | tier 1 | tier 2 | tier 3 | tier 4 (địa phương) |
|---|---|---|---|---|
| **A** | `#1B2B4B` | `#2D4A7A` | `#4A7AA8` | `#7B9BC2` chữ `#16233D` — terracotta đang bận làm chrome nên đồ thị giữ **đơn sắc navy** |
| **B** | `#1B2B4B` | `#2D4A7A` | `#4A7AA8` | `#CE7A58` chữ trắng — terracotta rảnh nên tier 4 tách hẳn khỏi thang navy |

Nghiệm thu: đổi chế độ **lúc đồ thị đang hiện** → node tier 4 phải đổi màu ngay, không cần chạy lại câu hỏi.

#### Hai thứ phải kiểm riêng vì nền đổi

1. **Ba trạng thái chip trích dẫn** (1.2.1) dùng **hex cố định, nằm ngoài khối `[data-theme]`** → giống hệt ở A và B. Chúng luôn nằm trên **thẻ trắng**, không bao giờ nằm trên dải chrome, nên đổi chrome không làm chúng chìm. Lưu ý sẵn có (không phải do A/B): ba nền pha nhạt chỉ chênh nhau ~1.05:1 về độ sáng — thứ phân biệt chúng là **sắc + màu chữ + viền**, nên **không được bỏ viền chip**.
2. **Badge "PHÁT LẠI"** vàng `#FFC251` trên thanh trạng thái: ở **B** (nền `--navy-mid`) đạt 5.5:1, nhưng ở **A** (nền `--terracotta-dk`) chỉ 2.5:1 — vàng trên nâu-cam quá gần nhau. Vì vậy badge **bắt buộc có `ring-2 ring-white/80`**, đẩy mức tách khỏi nền lên 4.1:1 ở A và 8.9:1 ở B. Vòng viền này nằm trong chuỗi `className` mà JS gán ở `khoiDong()` — **gán ở đó ghi đè class tĩnh trong HTML**, nên sửa markup thôi là vô tác dụng.

`#903938` **không phải màu chrome ở chế độ nào**: nó là màu chức năng thuần (badge "HẾT HIỆU LỰC", chip `khong-tim-thay`, bảng lỗi). Phần 4.2 mô tả footer `#903938` là **của UI cũ** — UI mới dùng `--chrome-bg`.

---

## 2. Chữ và nhịp

| Thuộc tính | Giá trị cũ | Áp dụng cho dự án mới |
|---|---|---|
| Font | **Be Vietnam Pro** 300/400/500/600/700 (Google Fonts) | Giữ. Đây là font Việt tốt, khớp cảm giác cổng dịch vụ công. *(`tailwind.config.ts` ghi `Nunito` nhưng `body` trong `globals.css` ghi Be Vietnam Pro — Be Vietnam Pro thắng, Nunito là rác cấu hình.)* |
| Cỡ nền | `font-size: 14px` | Giữ 14px cho thân, nhưng xem cảnh báo `zoom` ở mục 7. |
| Thang cỡ | 11 / 12 / 13 / 14 / 16 / 20 / 24px | Giữ. Chữ nhỏ (11–13px) dùng cho metadata, chip, nhãn — đây là đặc trưng "cổng hành chính". |
| Nhãn section | `text-sm font-semibold uppercase tracking-wider` | Giữ nguyên — dùng cho tiêu đề 7 bước. |
| Eyebrow | `text-sm font-medium tracking-widest uppercase text-muted` | Giữ — dùng cho dòng phụ trên tiêu đề trang. |

**Offline:** máy trình diễn có thể không có mạng (spec mục 2.1 + Task 5). Tải Be Vietnam Pro về `ui/static/vendor/fonts/` và khai `@font-face`; fallback stack: `'Be Vietnam Pro', 'Segoe UI', system-ui, sans-serif`.

---

## 3. Hình học và tương tác

```
Bo góc      mặc định 4px · lg/xl/2xl 6px      → chrome, input, nút (cảm giác "flat hành chính")
            thẻ nội dung 12px (rounded-xl)     → thẻ 7 bước, thẻ panel
Container   max-width 1170px, mx-auto, px-4
Breakpoint  sm 768px · md 992px · lg 1200px    (KHÔNG dùng mặc định 640/768/1024 của Tailwind)
Focus ring  outline 2px solid var(--terracotta); outline-offset 2px
Selection   background var(--terracotta-lt); color var(--navy)
Scrollbar   width 6px; track var(--gray-100); thumb var(--gray-300); thumb:hover var(--terracotta)
Transition  colors 150–200ms ease  (mọi hover)
```

> Repo cũ dùng **cả hai** thang bo góc (4/6px ở chrome, 12/16px ở thẻ trang chủ đời sau) — đó là hệ quả của việc refactor dở dang. Trong UI mới, quy tắc rõ ràng: **chrome bo 6px, thẻ nội dung bo 12px**, không có gì bo 16px.

---

## 4. Giải phẫu khung trang cũ

### 4.1 Header — 2 tầng (`components/layout/Header.tsx`)

```
┌──────────────────────────────────────────────────────────────┐
│ TẦNG 1  bg: var(--terracotta) · border-b black/10            │
│ max-w 1170 · px-6 py-3 · flex justify-between                │
│  ○ 55×55 tròn, bg white/20, glyph trắng 24px                 │
│  │ Tiêu đề  text-2xl font-semibold text-white leading-tight  │
│  └ Phụ đề   text-[13px] text-white/60                        │
├──────────────────────────────────────────────────────────────┤
│ TẦNG 2  bg: var(--terracotta-dk) · h-12 · border-b black/10  │
│  mục nav: px-4, text-sm, text-white/80                       │
│  hover: text-white + bg-white/10                             │
│  active: text-white font-medium + bg-white/15                │
└──────────────────────────────────────────────────────────────┘
```

Dropdown (nếu cần): panel `bg-white`, viền `var(--border-card)`, `shadow-lg`, `min-w-[220px]`, item `px-4 py-2 text-sm`, hover `bg-[var(--terracotta-faint)] text-[var(--terracotta)]`. **Trang mới nhiều khả năng không cần dropdown** — xem 6.1.

### 4.2 Footer (`components/layout/Footer.tsx`)

Hai phần:
1. **Dải hỗ trợ**: nền trắng, `border-t #DDDDDD`, `py-5`, grid 2 cột. Mỗi ô: viền `#DDDDDD`, `p-4`, icon tròn 48px nền `#F5E8DF` chữ terracotta; hover → viền terracotta + tròn đổi thành nền terracotta chữ trắng.
2. **Thanh chính**: `bg #903938`, chữ trắng, `py-4`, một dòng canh giữa, các mục ngăn bằng `|`.

### 4.3 Hero (`components/home/HeroBanner.tsx`)

```css
background-color: #CE7A58;
background-image:
  radial-gradient(circle at 15% 50%, rgba(255,255,255,.06) 0%, transparent 50%),
  radial-gradient(circle at 85% 50%, rgba(255,255,255,.04) 0%, transparent 40%);
min-height: 220px;
```
Bên trong: khối `max-w-[860px]` gồm thanh tìm kiếm + hàng 3 nút CTA vàng `#FFC251`, chữ đen `font-bold`, `py-3 px-4`, bo 4px, canh giữa.

### 4.4 SearchBar — nhóm input liền mạch (`components/ui/SearchBar.tsx`)

Đặc trưng "cổng hành chính": ba phần dính nhau, không có khoảng hở.

```
[ input                     ][ Tìm kiếm nâng cao ][🔍]
  bo trái 4px                  chữ 12px #2A6EBB    nền #F5F5F5
  viền #DDDDDD                 viền trên/dưới      bo phải 4px
  focus → viền #CE7A58                             hover #E8E8E8
```

### 4.5 Thẻ nội dung — treatment chuẩn (`src/app/page.tsx`, bản home đời sau)

Đây là **mẫu thẻ đáng tái sử dụng nhất** cho 7 bước:

```html
<!-- Nhãn nhóm: vạch accent + chữ hoa -->
<div class="flex items-center gap-3 mb-4">
  <div class="w-1 h-5 bg-[var(--terracotta)] rounded-full"></div>
  <h2 class="text-sm font-semibold text-[var(--navy)] uppercase tracking-wider">Nhãn</h2>
</div>

<!-- Thẻ -->
<div class="bg-white border border-[var(--border-card)] rounded-xl p-5
            hover:border-[var(--terracotta)] hover:shadow-md hover:-translate-y-0.5
            transition-all duration-200 group">
  <p class="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--navy)] mb-2">Tiêu đề</p>
  <!-- gạch chân động: 8px → 12px khi hover -->
  <div class="w-8 h-0.5 bg-[var(--terracotta-lt)] group-hover:bg-[var(--terracotta)]
              group-hover:w-12 transition-all duration-300 rounded-full"></div>
</div>
```

### 4.6 Bảng tài liệu — `.procedure-doc-table` (copy nguyên, dùng lại 100%)

Đây là tài sản dùng lại được **nguyên xi** cho bảng block context ở bước 6.

```css
.procedure-doc-table { width:100%; border-collapse:collapse; font-size:.875rem; }
.procedure-doc-table th {
  background: var(--navy-faint); color: var(--navy);
  font-size:.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.05em;
  padding:.625rem 1rem; text-align:left; border-bottom:2px solid var(--border-card);
}
.procedure-doc-table td {
  padding:.75rem 1rem; border-bottom:1px solid var(--gray-100);
  vertical-align:top; color: var(--text-primary); line-height:1.6;
}
.procedure-doc-table tr:last-child td { border-bottom:none; }
.procedure-doc-table tr:hover td      { background: var(--terracotta-faint); }
.procedure-doc-table a { color: var(--terracotta); font-size:.75rem; text-decoration:none; }
.procedure-doc-table a:hover { text-decoration:underline; }
```

### 4.7 Chat / trích dẫn (`components/chat/ChatWidget.tsx`)

| Phần | Style |
|---|---|
| Bong bóng người dùng | `bg-[var(--navy)] text-white`, bo 6px, `max-w-[80%]`, `px-3 py-2 text-sm` |
| Bong bóng trợ lý | `bg-white border border-[var(--border-card)]`, cùng bo/padding |
| Bong bóng lỗi | `bg-red-50 border-red-200`, tiền tố `⚠️` |
| **Chip trích dẫn** | `bg-[var(--navy-faint)] text-[var(--navy)] border border-[var(--navy-light)]`, `text-[11px] px-1.5 py-0.5`, bo 4px, hover → `bg-[var(--navy-light)]` |
| Header widget | `bg-[var(--terracotta)]`, tiêu đề trắng `text-sm font-medium` + phụ đề `text-white/70 text-xs` |
| Ô nhập | `textarea` nền `var(--warm-white)`, viền `--border-card`, bo 12px, focus → viền terracotta |
| Nút gửi | `bg-[var(--terracotta)] hover:bg-[var(--terracotta-dk)] text-white`, bo 12px |
| Dấu ba chấm chờ | 3 chấm 6px `bg-[var(--gray-300)]`, `animate-bounce`, delay 0/150/300ms |

### 4.8 Class mồ côi — phải tự dựng lại

`SectionTitle.tsx`, `LifeEventsGrid.tsx`, `ScoreBadge.tsx` tham chiếu `.section-title`, `.service-item`, `.score-badge` — **các class này không còn tồn tại** trong `globals.css` (đã bị xóa khi refactor home). Nếu cần, dựng lại theo tinh thần cũ:

```css
.section-title {
  display:inline-block; font-size:1rem; font-weight:700; color:var(--navy);
  padding-bottom:.5rem; border-bottom:2px solid var(--terracotta);
}
.service-item {
  display:flex; align-items:center; gap:.75rem;
  padding:.5rem .25rem; border-bottom:1px solid var(--gray-100);
  font-size:.875rem; color:var(--navy); text-decoration:none;
}
.service-item:hover { color:var(--terracotta); }
.score-badge {
  display:inline-block; background:#28A745; color:#fff;
  font-size:.6875rem; font-weight:700; padding:.125rem .375rem; border-radius:3px;
}
```

---

## 5. Trang chủ cũ — hai phiên bản, lấy gì từ đâu

Repo cũ có **hai** thiết kế home chồng lên nhau:

| | **V1 — bám dichvucong.gov.vn** | **V2 — hiện đang chạy** (`src/app/page.tsx`) |
|---|---|---|
| Trạng thái | code còn (`HeroBanner`, `LifeEventsGrid`) nhưng **không được render** | đang hoạt động |
| Bố cục | Hero cam + search + 3 CTA vàng → lưới sự kiện đời sống 2 cột (Công dân / Doanh nghiệp) | Hero nền kem, eyebrow + H1 → **thẻ chat inline 520px** → nhóm thẻ thủ tục 3 cột |
| Cảm giác | dày đặc, nhiều link, đúng chất cổng nhà nước | thoáng, tập trung vào một hành động (hỏi) |

**Lấy gì:**
- **Từ V1**: khung header 2 tầng, footer, dải hero màu đặc, nhóm input liền mạch, CTA vàng, mật độ chữ nhỏ.
- **Từ V2**: treatment thẻ (4.5), vạch accent + nhãn hoa, hero "một hành động duy nhất", thẻ chat bo 12px.

**V2 gần với dự án mới hơn** (một trang, một hành động, trọng tâm là ô hỏi) → lấy V2 làm sườn, V1 làm lớp chrome bao ngoài.

---

## 6. Ánh xạ sang UI mới (`ui/static/index.html`)

### 6.0 Ràng buộc bất di dịch

Restyle **không được đổi** các `id` sau (JS đang bám vào):

```
badge-mode · canh-bao-fixture · bang-loi · goi-y
o-cau-hoi · o-juris · o-mode · nut-hoi
cac-buoc · do-thi · bang-block
panel-nguyen-van · nut-dong-panel · nut-nguyen-van-llm
```

Các class trạng thái `.buoc-cho / .buoc-chay / .buoc-xong / .cit-chip` cũng do JS gắn — **đổi định nghĩa CSS, giữ nguyên tên class**.

#### Bốn họ `id` sinh trong JS — cũng bất di dịch

Danh sách trên chỉ là `id` viết tay trong HTML. `dungStepper()` còn **sinh thêm 4 họ `id` bằng template literal** (`id="buoc-${b.id}"`…), và các hàm khác truy vấn lại chúng bằng **tên ghép chuỗi** (`$("noi-dung-" + key)`). Vì tên được ghép lúc chạy, đổi hay bỏ một phần tử **không gây lỗi hiển thị nào** — bước tương ứng chỉ lặng lẽ trống, lỗi duy nhất nằm ở `console`. Grep theo tên đầy đủ sẽ **không** tìm ra chỗ dùng; phải grep theo tiền tố.

| Họ | Sinh ở | Được truy vấn ở | Hậu tố hợp lệ |
|---|---|---|---|
| `buoc-*` | `dungStepper()` | `batBuoc()`, `dispatch()` nhánh `done` (gỡ `.buoc-chay`/`.buoc-cho`) | 7 giá trị `BUOC[].id`: `question` `plan` `stage1` `stage2` `stage3` `hybrid` `generate` |
| `tg-*` | `dungStepper()` | `batBuoc()` (mốc `t`), `$("tg-generate")` ở `done` | như trên |
| `noi-dung-*` | `dungStepper()` | toàn bộ `renderCauHoi/Plan/Stage1/Stage2/Stage3/Hybrid/CauTraLoi/Verifier` | như trên |
| `log-*` | `dungStepper()` | `themLog()` (nối `ev.raw` vào `<pre>`) | như trên |

Lưu ý kèm theo: `GOP = {temporal→plan, context→hybrid, verify→generate, done→generate}` gộp 4 bước phụ vào 4 họ trên, nên **7 thẻ bước phải luôn tồn tại đủ 7** ngay từ lúc `dungStepper()` chạy — không được lazy-render hay bỏ thẻ khi rỗng.

#### Hook JS không phải `id` — cũng bất di dịch

| Hook | Sinh ở / bind ở | Ràng buộc khi restyle |
|---|---|---|
| `.goi-y-nut` | sinh trong `khoiDong()`; bind qua `querySelectorAll(".goi-y-nut")` | giữ nguyên tên class + xem cảnh báo `textContent` bên dưới |
| `.goi-y-loi` | sinh trong nhánh `ev.kind === "error"` của `dispatch()`; bind tương tự | như trên |
| `.cit-chip` | sinh ở `chipCitation()` **và** danh sách trích dẫn cuối bước 7; bind ở `ganSuKienChip()` | giữ nguyên tên class |
| `tr[data-block]` | sinh ở `renderBangBlock()`; bind qua `querySelectorAll("tr[data-block]")` | phần tử bấm được **phải là `<tr>`** và **phải giữ `data-block="${b.index}"`**. Bọc thêm `<div>`, đổi sang `<li>`/thẻ card, hay chuyển `data-block` xuống `<td>` đều làm mất toàn bộ khả năng bấm ở bước 6 |
| `data-vb` · `data-dieu` · `data-khoan` · `data-diem` | đặt trên `.cit-chip`; đọc ở `ganSuKienChip()` → `moNguyenVan()` | giữ **đủ cả 4**. `data-vb` **phải là slug gốc** (`citation.van_ban`), tuyệt đối không thay bằng tên hiển thị — `moNguyenVan()` dùng nó làm `norm_id` gọi `/api/text`; `data-dieu` giữ nguyên sentinel `_default` của Phụ lục |

> **⚠ Chip gợi ý không được chèn ký tự trang trí dạng text.**
> Cả `khoiDong()` lẫn nhánh lỗi đều bind `b.onclick = () => { $("o-cau-hoi").value = b.textContent; … }` → **`textContent` của nút chính là câu hỏi được gửi vào pipeline**. Mọi thứ thêm vào *bên trong* nút — dấu `»` `▸` `+` `#`, số thứ tự `1.`, emoji, dấu ngoặc kép, hay một `<span>` phụ chứa chữ — đều lọt thẳng vào câu hỏi. Ở chế độ `replay` điều này còn làm **trượt khớp fixture** → rơi vào nhánh lỗi và demo chết trên sân khấu. Muốn trang trí thì dùng **CSS thuần**: `::before` / `::after`, `background-image`, viền, nền, `padding` — những thứ không vào `textContent`. Ràng buộc y hệt áp cho `.goi-y-loi`.

#### Phần lớn class cần sửa KHÔNG nằm trong HTML tĩnh

`index.html` chỉ có khoảng 60 dòng markup thật (header, cảnh báo fixture, ô nhập, 2 container rỗng, panel phải). **Toàn bộ phần còn lại được sinh bằng template literal trong `<script>`**: 7 thẻ bước (`dungStepper`), chip nhãn dùng chung (`chip`), bảng Stage 1 (`renderStage1`), chip norm Stage 2 (`renderStage2`), khối Stage 3 (`renderStage3`), dải phân bổ pass + thanh token budget (`renderHybrid`), bảng block (`renderBangBlock`), chip trích dẫn (`chipCitation`), thân câu trả lời (`renderCauTraLoi`), dòng verifier (`renderVerifier`), panel nguyên văn (`hienBlock`, `moNguyenVan`).

Riêng màu đồ thị nằm trong **mảng `style` của Cytoscape** ở `veDoThi()` — là **chuỗi hex thuần**, Tailwind không đụng tới và class CSS cũng không áp được vào canvas.

Hệ quả thực tế:
1. Grep của checklist mục 9 **phải quét cả khối `<script>`**, không chỉ phần `<body>` markup.
2. Một số màu **bắt buộc viết hex hoặc `var(--…)` trực tiếp** (Cytoscape, `.procedure-doc-table`, class trạng thái bước) — không dùng được class Tailwind.
3. Sửa style ở đây là sửa **chuỗi trong JS**: dễ làm hỏng cú pháp template literal hoặc lồng nhầm dấu nháy. Sau mỗi lượt sửa phải mở lại trang và chạy đủ 7 bước, không chỉ nhìn HTML tĩnh.

### 6.1 Bảng ánh xạ từng khối

| Khối UI mới | Kế thừa từ | Phải sửa |
|---|---|---|
| **Header** | Tầng 1 (4.1) nguyên vẹn | Đổi glyph ★ → biểu tượng đồ thị (3 node nối cạnh, SVG inline). Tiêu đề → *"Ontology-Driven GraphRAG cho Pháp luật Việt Nam"*, phụ đề → *"Trình diễn luồng xử lý: câu hỏi → 7 bước → câu trả lời có trích dẫn"*. **Bỏ toàn bộ nội dung Cổng DVC Quốc gia** (xem mục 7). |
| **Thanh trạng thái** | Tầng 2 (4.1) | **ĐÃ BỎ HẲN.** Badge chế độ (`#badge-mode`) và dòng tốc độ (`#tt-toc-do`) chuyển vào bảng thiết lập; dòng "Neo4j · Qdrant · LLM" bỏ luôn. Hệ quả phải bù: badge "PHÁT LẠI" **không còn nhìn thấy được nếu không mở bảng thiết lập**, nên **dải `#canh-bao-fixture` trở thành tín hiệu phát-lại DUY NHẤT luôn hiển thị** — nó bắt buộc phải bật ở mọi lượt `replay` và phải in cả hệ số tua. Xóa hoặc làm nhạt dải này là mất hẳn cảnh báo, vi phạm spec mục 4.2. `--chrome-bg-2` tạm không có chỗ dùng nhưng vẫn giữ trong bộ 5 token vai trò của mục 1.3. |
| **Bảng thiết lập** (`#nut-setting` → `#bang-setting`) | mới | Bánh răng SVG 38px ở **góc phải header tầng 1**; bấm mở panel trắng bo 12px thả xuống (`position:absolute; right:0`), đổ bóng, rộng 300px. Ba nhóm ngăn bằng vạch `--gray-100`: **Chế độ chạy** (`#nut-mode-live` / `#nut-mode-replay`) · **Tốc độ phát lại** (`#nhom-toc-do`, ẩn khi ở `live`) · **Bảng màu** (`#nut-mau-a` / `#nut-mau-b`). Đóng khi bấm ra ngoài, bấm `×`, hoặc `Esc`. `.nut-mau` nay nằm trên **nền trắng** nên phải đổi hệ màu: nghỉ = viền `--border-card` chữ `--text-secondary`, hover = viền `--accent`, đang chọn = nền `var(--navy)` chữ trắng. **Không** dùng lại kiểu trắng-mờ cũ (kiểu đó chỉ đọc được trên dải chrome tối). |
| **Ô nhập câu hỏi** | Hero (4.3) + SearchBar (4.4) | Dải hero `var(--chrome-bg)` có radial gradient, bên trong là card trắng bo 12px chứa `textarea` + **2 `select`** + nút Hỏi. Nút Hỏi: `bg-[var(--accent)]`, hover `--accent-strong`, disabled `var(--gray-300)`. **`#o-juris` không còn lựa chọn rỗng**: mặc định `toan-quoc`, nhãn hiển thị là tên tiếng Việt (`Toàn quốc` / `TP. Hồ Chí Minh` / `Đồng Nai`) nhưng **`value` giữ nguyên slug** — đó là danh sách đóng `VALID_JURISDICTIONS`, đổi value là gãy `force_jurisdiction`. **Checkbox Verifier đã gỡ** (không còn `#o-verify`); `run_pipeline` chạy với `verify=False` mặc định. |
| **Chip gợi ý câu hỏi** (`#goi-y`) | 3 nút CTA vàng (4.3) | **Đã bỏ nền vàng `#FFC251`** — mảng vàng đặc dưới ô nhập hút mắt hơn cả nút Hỏi và làm dải nhập liệu rối. Nay chip là **pill viền nhạt**: nền `--gray-50`, viền `--border-card`, chữ `--text-secondary` `12px`, bo tròn `999px`, hover viền `--accent` nền trắng. **Chỉ bày `SO_CHIP_GOI_Y = 2` câu** (hai câu đầu nhóm A — cặp đổi đúng một biến địa phương), một dòng, cắt bằng `text-overflow: ellipsis` với `title` = nguyên câu. **Cắt bằng CSS, không cắt chuỗi** — `textContent` phải giữ đúng câu hỏi gửi đi (mục 6.0). Nhãn `THỬ NHANH` (`#nhan-goi-y`) đứng ngoài nút, ẩn khi không có chip. Mọi câu còn lại nằm trong bảng "Câu hỏi mẫu". |
| **Bảng câu hỏi mẫu** (`#nut-cau-hoi-mau` → `#bang-cau-hoi`) | mới | Nút viền đứt cạnh chip, mở panel trắng 620px thả xuống (cùng khuôn với bảng thiết lập). Trong panel: mỗi nhóm một nhãn hoa `--navy` + mô tả `--text-muted`, mỗi câu là một nút full-width, **ghi chú của câu để ở thẻ anh em bên dưới, KHÔNG nhét vào trong nút** — `textContent` của nút chính là câu hỏi gửi đi (mục 6.0). Đóng khi bấm ra ngoài / `×` / `Esc`. Nút tự ẩn khi không có gì thêm ngoài các chip đang bày. |
| **Thẻ 7 bước** (`#cac-buoc`) | Thẻ 4.5 + nhãn vạch accent | Mỗi bước = một thẻ trắng bo 12px, viền `--border-card`. Nhãn: `<div class="w-1 h-5 bg-terracotta rounded-full">` + số bước + tên `uppercase tracking-wider text-navy`. Vòng tròn số dùng **một màu duy nhất `--buoc-tron`**, ba trạng thái khác nhau ở độ đậm: chờ = pha loãng 20% với `--bg-page` + chữ `--buoc-tron-chu` · chạy = đặc + quầng `0 0 0 4px` (pha 26%) · xong = đặc (chính là dạng mặc định của `.so-buoc`) + dấu ✓ `#28A745`. Đường nối: `--buoc-ray-nhat` (chưa tới) / `--buoc-ray` (đã qua). Thẻ đang chạy vẫn viền + ring `--accent`. Trạng thái mờ: `.buoc-cho > :not(.so-buoc){opacity:.6}` · `.buoc-chay{box-shadow:0 0 0 2px var(--accent)}` *(thay ring indigo)* · đã xong = gỡ cả hai class. **Opacity phải đặt lên phần nội dung, KHÔNG đặt lên cả `.the-buoc`**: số thứ tự `.so-buoc` là con của thẻ, nền trắng của nó mờ theo sẽ để lộ xương sống chạy xuyên qua chữ số (và opacity < 1 tạo stacking context mới, khóa luôn `z-index` của số). Xương sống: `#cac-buoc::before/::after` ở `left:22px` `top:39px` (= tâm số thứ tự, khớp hằng `RAY_TOP` trong JS), `z-index:0`; `.so-buoc` `z-index:1`; `.the-buoc:last-child::before` che phần đuôi thò xuống dưới số 7. Mốc thời gian `t` in `text-[11px] text-[var(--text-muted)]` bên phải. |
| **Bước 3 — điểm Stage 1** | `.score-badge` (4.8) | Norm vượt ngưỡng 0.3 → badge `#28A745`; norm bị loại → badge `var(--gray-300)` chữ `--gray-700` + gạch ngang chữ. Có đánh số `1. 2. 3.` **được phép** ở bước này (có rank thật). |
| **Bước 4 — đồ thị** | Bảng màu tier | Nền `#do-thi` → `var(--gray-50)` (thay `#f8fafc`). Node theo tier: 1 `#1B2B4B` · 2 `#2D4A7A` · 3 `#4A7AA8` · 4 `#CE7A58`, chữ trắng. Node seed: viền 2px `#FFC251`. Cạnh `IMPLEMENTS`: `var(--gray-300)` liền. Cạnh `AMENDS`: `var(--terracotta)` **nét đứt**. **Không đánh số thứ tự** ở bước này (spec mục 3.2). |
| **Bước 6 — bảng block** (`#bang-block`) | `.procedure-doc-table` (4.6) | Dùng **nguyên xi**. Cột: vị trí · tier · hiệu lực · norm. Hàng hết hiệu lực: badge `#903938` chữ trắng `text-[11px]`. Khối AMENDMENT WARNING: nền `var(--terracotta-faint)`, viền trái 3px `var(--terracotta)`, chữ `--text-secondary`. Dải phân bổ pass: các chip `var(--navy-faint)` chữ `--navy` (dạng tổng hợp, **không gắn badge cho từng dòng**). |
| **Thanh token budget** | mới | Track `var(--gray-200)`, fill `var(--terracotta)`; vượt 90% → fill `#903938`. |
| **Bước 7 — câu trả lời** | Bong bóng trợ lý + chip trích dẫn (4.7) | Thân câu trả lời trong thẻ trắng viền `--border-card`. **Chip trích dẫn phải giữ ĐỦ BA trạng thái** `chinh-xac` / `gan-dung` / `khong-tim-thay` theo `citation_links[].khop`, dùng đúng ba bộ màu ở **1.2.1** — **không được gộp `gan-dung` vào `chinh-xac` hay vào `khong-tim-thay`**: "gần đúng" nghĩa là khớp đúng văn bản nhưng lệch cấp Khoản/Điểm, đây là thông tin học thuật thật mà hội đồng sẽ hỏi tới. `khong-tim-thay` giữ tooltip "không tìm thấy trong context" — tín hiệu thật, phải nhìn rõ, không được che hay làm nhạt đi. Chip xám trung tính chỉ dành cho trường hợp thứ tư `!link`. Áp cho **cả hai** nơi sinh chip: `chipCitation()` (inline trong văn xuôi) và danh sách trích dẫn cuối bước 7 — hai nơi này phải **cùng một bảng màu**. Ba dòng đếm ở chân bước 7 (`… khớp context · … khớp gần đúng · … không có trong context`) tô đúng ba màu tương ứng. Nút "Nguyên văn LLM" (`#nut-nguyen-van-llm`): kiểu link `#2A6EBB` `text-xs`. |
| **Panel nguyên văn** (`#panel-nguyen-van`) | Thẻ + header widget (4.7) | Card trắng bo 12px, header nền `var(--navy-faint)` chữ `--navy`. **Cả cột phải (`#cot-nguyen-van`) ẩn mặc định**, chỉ hiện khi bấm một trích dẫn ở bước 7 / một dòng ở bước 6 / một node đồ thị; nút `×` và việc hỏi câu mới đều đóng lại (nguyên văn đang hiện thuộc về câu trước). Đóng panel **CHỈ ẩn cột phải, KHÔNG được đụng vào lưới**: track 380px luôn giữ chỗ. Nếu thu track lại, cột 7 bước sẽ giãn ra mỗi lần bật/tắt — bảng block và câu trả lời dàn lại, chữ nhảy chỗ ngay giữa lúc trình bày. Chấp nhận một khoảng trống 380px bên phải khi đóng; đó là cái giá rẻ hơn nhiều so với việc nội dung chạy qua chạy lại. Tên văn bản hiển thị đầy đủ, **slug in dưới bằng `font-mono text-[11px] text-[var(--text-muted)]`** (spec mục 3.3 bắt buộc có đường tra slug gốc). |
| **Bảng lỗi** (`#bang-loi`) | Bong bóng lỗi (4.7) | Nền `#FDECEC`, viền `#E8C4C4`, chữ `#903938`, tiền tố ⚠️. Nêu rõ lỗi gì + cách xử lý (đổi sang `replay`), không chỉ báo "đã có lỗi". |
| **Cảnh báo fixture** (`#canh-bao-fixture`) | — | Nền `#FFF7E6`, viền dưới `#FFC251`, chữ `var(--gray-900)`, `text-xs px-6 py-2`. **Vai trò nay quan trọng hơn hẳn**: từ khi thanh trạng thái bị bỏ, đây là chỗ DUY NHẤT hội đồng thấy được hệ đang phát lại mà không phải mở bảng thiết lập. Phải bật ở mọi lượt `replay`, tắt khi sang `live`, và in cả hệ số tua (`veDaiCanhBaoFixture()` vẽ lại mỗi lần đổi tốc độ). |
| **Footer** | Thanh chính (4.2) | Nền `var(--chrome-bg)` chữ trắng một dòng canh giữa (mục 1.3 **ghi đè** `#903938` của 4.2 — `#903938` nay chỉ còn là màu chức năng). **Thay toàn bộ nội dung** thành: tên đề tài · nhóm thực hiện · GVHD · *"Sản phẩm nghiên cứu — không thay thế tư vấn pháp lý"*. Bỏ dải hỗ trợ 2 ô (không có trang FAQ để trỏ tới). |

### 6.2 Bố cục tổng

Lưới **cố định** `grid-cols-1 xl:grid-cols-[minmax(0,1fr)_380px]`, panel phải `sticky`. Bật/tắt panel nguyên văn KHÔNG đổi lưới — chỉ ẩn/hiện `#cot-nguyen-van`, để bề ngang cột 7 bước không đổi. Chỉ **đổi `max-w-[1600px]` → giữ nguyên** — 1170px của repo cũ quá hẹp cho stepper + đồ thị + panel; đây là ví dụ điển hình của "không ép theo UI cũ".

---

## 7. KHÔNG mang sang — danh sách cứng

1. **`body { zoom: 1.25 }`.** Hack này trong `globals.css` sẽ **phá Cytoscape**: `zoom` làm lệch hệ tọa độ con trỏ so với canvas, node bấm không trúng. Muốn chữ to hơn khi chiếu thì đặt `html{font-size:15px}` hoặc nâng thẳng thang cỡ chữ.
2. **Mọi nhận dạng của cơ quan nhà nước**: chuỗi "Cổng Dịch vụ công Quốc gia", "Văn phòng Chính phủ", "www.dichvucong.gov.vn", hotline "18001096", email "dichvucong@chinhphu.vn", ngôi sao vàng / quốc huy. Demo khóa luận **không được** trình bày như cổng chính phủ thật — sai về học thuật và không đúng thực tế.
3. **Nav đa cấp + subnav** (`MAIN_NAV`, `SUB_NAV`): trang mới chỉ có một trang, link chết trên UI trình bảo vệ là điểm trừ nặng.
4. **`LifeEventsGrid` + icon emoji** (👶🎓💼…): hệ icon emoji không hợp ngữ cảnh pháp lý và render lệch giữa các máy. Cần icon thì dùng SVG inline (đã có sẵn tinh thần từ `lucide-react`, nhưng dự án mới **không có npm** → chép path SVG trực tiếp).
5. **`PinGate`, `FloatingChatWidget`, `NavigationProgress`, `TabBar`, `Breadcrumb`**: không có luồng tương ứng ở dự án mới.
6. **Hai palette / hai thang bo góc song song**: chọn một (mục 1 và mục 3). *Công tắc A/B ở mục 1.3 KHÔNG vi phạm điều này* — nó vẫn là **một** bộ token duy nhất (1.1), chỉ đảo vai trò qua 5 biến ngữ nghĩa; cái bị cấm là hai bảng màu độc lập chồng nhau như repo cũ.
7. **`localStorage` / `sessionStorage`** — repo cũ dùng `zustand/persist`; dự án mới cấm tuyệt đối (`UI_DEMO_SPEC.md` mục 1.5).
8. **Bất kỳ dependency npm nào.** Tailwind qua CDN, cấu hình bằng `tailwind.config = {...}` inline **trước** khi dùng class; không build step.

---

## 8. Khung cấu hình Tailwind CDN

Đặt trong `<head>`, **sau** thẻ `<script src="…tailwindcss">` và **trước** phần `<body>`:

```html
<script>
tailwind.config = {
  theme: {
    screens: { sm: '768px', md: '992px', lg: '1200px', xl: '1280px' },
    extend: {
      colors: {
        terracotta: { DEFAULT:'#CE7A58', dk:'#B8694A', lt:'#F0EBE6', faint:'#FAF5F2' },
        navy:       { DEFAULT:'#1B2B4B', mid:'#2D4A7A', light:'#E8EDF5', faint:'#F0F3F8' },
        warm:       { white:'#F8F6F3' },
        ink:        { 50:'#F9F9F8', 100:'#F0EFED', 200:'#E2E0DC', 300:'#C8C5BF',
                      500:'#8A8680', 700:'#4A4844', 900:'#1C1B19' },
        cta:        { DEFAULT:'#FFC251', hover:'#F0B340' },
        deep:       { red:'#903938' },
        ok:         { DEFAULT:'#28A745' },
        link:       { DEFAULT:'#2A6EBB' },
      },
      fontFamily: { sans: ['Be Vietnam Pro','Segoe UI','system-ui','sans-serif'] },
      borderRadius: { DEFAULT:'4px', md:'4px', lg:'6px', xl:'12px' },
      maxWidth: { container: '1170px' },
    },
  },
}
</script>
```

Đồng thời vẫn khai `:root` ở mục 1.1 trong `<style>` — CSS var dùng cho những chỗ viết CSS tay (Cytoscape style, `.procedure-doc-table`, class trạng thái bước).

---

## 9. Checklist nghiệm thu

- [ ] Không còn class `slate-*` / `indigo-*` / `amber-*` mặc định của Tailwind trong `index.html` (kể cả trong template literal của JS).
- [ ] Toàn bộ `id` ở mục 6.0 còn nguyên; bấm Hỏi ở chế độ `replay` vẫn chạy đủ 7 bước.
- [ ] Không có `zoom` trên `body`; bấm node Cytoscape trúng đúng node.
- [ ] Không còn chuỗi nào nhận dạng cơ quan nhà nước (grep: `dichvucong`, `Chính phủ`, `18001096`, `Quốc gia`).
- [ ] Badge "PHÁT LẠI" nổi bật, không thể nhầm với "TRỰC TIẾP", nhìn rõ từ cuối phòng.
- [ ] Chip trích dẫn **không khớp block** có màu khác rõ ràng với chip khớp.
- [ ] Bước 4 không đánh số thứ tự, không dùng từ "top"; bước 3 có đánh số và có điểm.
- [ ] Font Be Vietnam Pro và Cytoscape chạy được khi **rút mạng** (đã đưa về `ui/static/vendor/`).
- [ ] Focus keyboard nhìn thấy được trên `textarea`, `select`, nút Hỏi và chip gợi ý.
- [ ] Công tắc A/B: đổi chế độ **lúc đồ thị đang hiện** → node tier 4 đổi màu ngay; không dùng `localStorage`/`sessionStorage`; tải lại trang trở về **A**.
- [ ] Ba trạng thái chip trích dẫn phân biệt được ở **cả A và B**; badge "PHÁT LẠI" vẫn nổi ở **cả A và B** (badge phải còn `ring-2 ring-white/80`).
- [ ] Toàn bộ text hiển thị bằng tiếng Việt (theo `CLAUDE.md`).

---

## 10. Nguồn tham chiếu trong repo cũ

| Nội dung | Đường dẫn |
|---|---|
| Palette thế hệ 1, breakpoint, bo góc, container | `frontend/tailwind.config.ts` |
| Palette thế hệ 2 (CSS var), scrollbar, focus, `.procedure-doc-table` | `frontend/src/app/globals.css` |
| Header 2 tầng + dropdown | `frontend/src/components/layout/Header.tsx` |
| Footer 2 phần | `frontend/src/components/layout/Footer.tsx` |
| Hero cam + CTA vàng | `frontend/src/components/home/HeroBanner.tsx` |
| Nhóm input liền mạch | `frontend/src/components/ui/SearchBar.tsx` |
| Treatment thẻ + nhãn vạch accent | `frontend/src/app/page.tsx` |
| Bong bóng chat, chip trích dẫn, ô nhập, chấm chờ | `frontend/src/components/chat/ChatWidget.tsx` |
| Biến thể nút | `frontend/src/components/ui/Button.tsx` |
| Lưới sự kiện đời sống (tham khảo, không dùng) | `frontend/src/components/home/LifeEventsGrid.tsx` |
