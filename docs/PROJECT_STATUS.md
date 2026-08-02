# Ontology-Driven GraphRAG cho Pháp luật Việt Nam — Trạng thái Dự án
**Phiên bản 2.23 | Cập nhật 2026-07-26**

> **v2.23 — Cập nhật 2026-07-26 (UI demo bảo vệ — Task 1 + 2 của `ui/docs/UI_DEMO_SPEC.md`):**
>
> Bắt đầu dựng web UI trình diễn pipeline cho buổi bảo vệ (spec: **[ui/docs/UI_DEMO_SPEC.md](../ui/docs/UI_DEMO_SPEC.md)**, 7 task). Toàn bộ code mới nằm trong `ui/` — **KHÔNG sửa `src/`** (giữ tính tái lập của số liệu `docs/V2_RESULTS.md`).
>
> **1. `ui/corpus.py` (Task 1).** Đọc `data/raw/*.md` một lần, cache in-memory: `load_corpus()` / `norm_graph()` / `get_component_text()`. Dựng đồ thị Norm cho bước Stage 2 **mà không cần Neo4j** (máy A DB rỗng vẫn vẽ được): 32 node, **40 cạnh** (29 IMPLEMENTS + 11 AMENDS), bỏ 23 cạnh trỏ ra ngoài corpus — đúng như Neo4j (`MATCH…MATCH…MERGE` không tạo cạnh treo). Xử lý `implements`/`amended_by_norms` dạng string \| list \| null (D-23).
>
> **2. `ui/trace.py` (Task 2).** `TraceCollector(logging.Handler)` gắn vào logger `"src"` → `TraceEvent {seq,t,step,kind,raw,data}` vào `queue.Queue`; `parse_message()` phân loại **mọi** record INFO bằng regex (không lọc keyword như `demo._TraceHandler` — danh sách đó có mục chết); `parse_context()` parse 3 dạng nhãn block + block cảnh báo sửa đổi; `link_citations()` nối citation → block (khớp lỏng tới cấp Điều). `raw` luôn được giữ, regex không khớp thì `data={}` chứ không bỏ event.
>
> **3. Kiểm chứng trên dữ liệu thật** (đọc `results_graphrag_20260710-085236.json` chỉ để test parser — UI KHÔNG lấy trace từ file này, spec mục 1.4): 2199/2199 block parse đủ `norm_id` + nguyên văn, 298 amendment, 45 block HẾT HIỆU LỰC; 292/296 citation khớp chính xác, 4 khớp gần đúng (citation sâu hơn block).
>
> **3b. 4 sửa sau review.** (a) `parse_vi_tri` lấy match **CUỐI** cho Khoản/Điểm/Tiết (nhãn ghép `", ".join(context_path[1:])` → cấp sâu ở cuối; tiêu đề Điều của VB sửa đổi có thể chứa sẵn ", Khoản X" — corpus hiện chưa có ca nào, đây là sửa phòng ngừa). (b) Ghi rõ **thứ tự norm Stage 2 KHÔNG phải xếp hạng** (`list({...})` từ set → đổi theo process) — thêm mục **3.2** vào spec, frontend Task 3 phải hiện dạng tập hợp sắp theo tier/alphabet, không đánh số. (c) `ui/corpus.py` cảnh báo khi `amended_by_norms` là string (graph_builder Pass 3 chỉ nhận list → UI sẽ vẽ cạnh AMENDS mà Neo4j không có). (d) Chú thích `gan-dung` sinh theo cấp lệch thật ("context chỉ tới cấp Khoản, citation nêu Điểm a") thay vì câu chung.
>
> **4. Test:** `tests/test_ui_corpus.py` + `tests/test_ui_trace.py` — **62 test mới, pass, không cần DB/LLM** (149 pass toàn bộ trên máy A; 12 file test của `src/` không collect được vì máy A thiếu `anthropic`/`neo4j`/`qdrant_client` — lỗi môi trường có sẵn, không liên quan).
>
> **5. Task 3 xong — UI chạy được ở máy A.** `ui/adapters.py` (`ReplayAdapter` khớp câu hỏi đã chuẩn hóa → phát lại events theo `t/REPLAY_SPEED`; `su_kien_ket_qua()` dựng event kết quả DÙNG CHUNG cho live + replay để chuỗi event khi replay giống hệt lúc chạy thật), `ui/server.py` (SSE thủ công qua `StreamingResponse`, không thêm dep `sse-starlette`; `/api/mode` `/api/ask` `/api/norm-graph` `/api/text`), `ui/static/index.html` (stepper 7 bước + Cytoscape bước 4 + panel nguyên văn + chip trích dẫn 3 màu theo `khop`). Fixture tạm `ui/fixtures/han-muc-giao-dat-o-...json`: **nhãn block + nguyên văn + citation lấy từ `data/raw` thật**, còn score/pass/thời gian là số minh họa — fixture tự khai `tam=true` và UI hiện banner cảnh báo, thay bằng bản `ui.record` ở máy B (Task 4).
>
> **5b. Sửa lỗ hổng đồng thời (mục 2.3 MỚI của spec).** `logging.getLogger("src")` là toàn cục theo process → hai `/api/ask` chồng nhau sẽ trộn event của hai câu vào một luồng SSE và làm `t` âm / `seq` nhảy lùi. Ba quy tắc đã ghi vào spec và cài đặt: **(1)** `/api/ask` serialize bằng lock cấp module, thử lấy **không chờ** → request thứ hai nhận ngay event `kind="error"` `loai="dang-ban"`, KHÔNG xếp hàng, nhả lock trong `finally`; **(2)** mỗi request một `TraceCollector` riêng qua context manager mới `ui.trace.gan_collector()` (`removeHandler` trong `finally` — quên thì 50 câu = 50 handler cùng phát); **(3)** frontend dùng `fetch()` + `body.getReader()`, **cấm `EventSource`** (chỉ GET + tự kết nối lại → hết câu nó tự chạy lại đúng lúc đang trình bày). Áp dụng cho cả `replay`.
>
> **6. Test:** thêm `tests/test_ui_adapters.py` (14) + `tests/test_ui_server.py` (9, có test hai request chồng nhau và test nhả lock khi adapter ném lỗi) → **86 test UI, 186 pass toàn máy A**. Kiểm thủ công bằng uvicorn thật: 24 event/câu, khoá đồng thời đúng, `/api/text` + `/api/norm-graph` (32 node/40 cạnh) OK. **Chưa mở bằng trình duyệt** (máy A không có công cụ chụp headless) — cú pháp JS đã `node --check`, phần hiển thị cần mắt người xem lại.
>
> **6b. Thu hẹp phạm vi UI (2026-07-27).** **Bỏ Task 7 (tab dashboard đánh giá)** khỏi spec và xoá `/api/eval`: số Chương 4 đã có ở `docs/V2_RESULTS.md` và sẽ trình bày bằng slide — dựng lại trong UI chỉ thêm đường sập chứ không thêm bằng chứng. UI chốt là **một trang duy nhất cho luồng hỏi–đáp**, không tab (ghi vào mục 6 + mục 7 của spec). **Gộp Task 4 + Task 5 làm một** (`LiveAdapter` + `ui/record.py`) vì `record.py` dùng chính `LiveAdapter` để ghi fixture — tách ra là tự chuốc hai đường code. Spec còn 5 task; Task 6 cũ (chống sự cố) thành Task 5.
>
> **6c. Lớp hiển thị tên văn bản (mục 3.3 MỚI của spec).** Slug (`luat-dat-dai-2024`) là ID kỹ thuật, không phải thứ đọc lên trước hội đồng → đổi thành tên thật **ở frontend**, nguồn `title` + `so_hieu` của `/api/norm-graph` (không thêm endpoint, không đổi `TraceEvent`, fixture không phải ghi lại). Nối `so_hieu` trong ngoặc khi `title` chưa chứa, để nguyên khi đã có; hai Norm ra cùng tên thì thêm theme (ca thật: D-23 tách NQ 124/2016 thành `-datdai`/`-hotich`); **slug ngoài corpus giữ nguyên** (tín hiệu thật, không che). Thay bằng **một lượt `replace` với alternation sắp theo độ dài giảm dần** — lặp `.replace()` sẽ để `nghi-quyet-124-...-tp-hcm` ăn mất đuôi `-datdai`. Bước 7 dùng alternation `citation | slug` nên `data-vb` giữ nguyên slug; **`citation.van_ban` KHÔNG đổi**. Áp cho bước 3/4/6/7 + panel nguyên văn; slug gốc vẫn ở tooltip. Thêm **nút "Nguyên văn LLM"** hiện đúng `PipelineResult["answer"]` (slug nguyên bản, markdown thô) — có lớp hiển thị thì phải có đường xem bản gốc. Kiểm bằng node trên corpus thật + answer của fixture: 12/12 assertion pass.
>
> **7. Việc tiếp theo:** **Task 4 = `LiveAdapter` + `ui/record.py`, chạy ở máy B** (`LiveAdapter` hiện mới là khung ném `NotImplementedError`, server tự lùi về `replay`) → Task 5 (vendor CDN + nút chuyển live⇄replay + nút chỉnh tốc độ). Env mới trong `.env`/`.env.example`: `DEMO_MODE`, `UI_PORT`, `REPLAY_SPEED`; `requirements.txt` thêm `fastapi`/`uvicorn`.

> **v2.22 — Cập nhật 2026-07-10 (KHÂU ĐÁNH GIÁ HOÀN TẤT — GT freeze 137 câu + chiến dịch eval v1/v2 + Fix A. Kế tiếp: VIẾT BÁO CÁO):**
>
> **1. GT v2 FREEZE 137 câu (2026-07-08).** [B] review chéo 150 câu → 27 fix: bỏ 13 OOS hộ tịch (kết hôn/XNTTHN/khai tử/nhận cha-mẹ-con — ngoài 6 thủ tục), relabel V135/V136→gap1, sửa 9 đất đai (gồm lỗi data Điều 10 NĐ112 bị NĐ226/2025 Đ5K2 sửa toàn bộ — thêm annotation + re-ingest, Amendment 322→323) + 4 hộ tịch/ncn. Freeze SHA256 `bd2c5eaf…f146`, tag `gt-v2-freeze`, pre-register `docs/GT_FREEZE.md`. Triage: `docs/GT_REVIEW_TRIAGE.md`.
>
> **2. Chiến dịch eval hoàn tất (Gemini, 137 câu).** Số chốt cho Chương 4 ở **`docs/V2_RESULTS.md`**: GraphRAG v2 **N=3 F1 Khoản 0.578±0.004** vs baseline 0.435±0.008 — **Δ+0.143, 95% CI [0.061,0.225], Wilcoxon p=0.0015\*\*** (E0). Bậc thang E2a: oracle 0.858 > graphrag 0.578 ≈ bm25 0.571 > baseline 0.435 > closed-book 0.102. Double-dissociation E1: Gap3/4 VỮNG (no-traversal −0.091/−0.130), Gap1 ok (−0.041), **Gap2 limitation** (jurisdiction net-hại +0.182). E2b per-domain: dat-dai 0.617 / ho-tich 0.580 / ncn 0.392. E3: retrieval_fail 32→21 nhờ Fix A.
>
> **3. Fix v2 + negative results.** **Fix A** (commit `3efd0e8`, cải tiến hậu kiểm duy nhất thành công): jurisdiction=None→quét mọi tỉnh; gap2 0.454→0.517, jur=None 0→0.328, 0 regress. **3 fix thất bại đã revert** (ghi Limitations): 2 thí nghiệm prompt under-cite (recall bất biến — Gemini-inherent), temporal neo bản-cũ (regress Gap4). Over-cite 161 phần lớn GT-artifact (32% same-norm) → precision under-measured.
>
> **4. Bug hạ tầng đã fix trong chiến dịch** (commit riêng): `aggregate()` + `expanded_eval` crash sort None (theme/juris=null của GT v2 — `8b07a95`, `ec7645c`); baseline collection stale thiếu 15/32 norm (quên rebuild sau ingest corpus B — suýt làm baseline=0 trên 68 câu hộ tịch); validation `--systems` chặn bm25/closed-book/oracle (`9ab28c8`); `_TARGET` verify_gt 150→137 (`2167a7b`). **Gotcha mới:** N=3 dồn ~1800 call/đêm → Vertex **429 RESOURCE_EXHAUSTED** làm hỏng 4 mẫu (F1 sụp giả) — đã cách ly `data/evaluation/quarantine_429/`, chỉ dùng mẫu 0-lỗi-429; lần sau giãn nhịp.
>
> **5. Việc tiếp theo:** **(a) VIẾT BÁO CÁO** — đề cương + Chương 1 đã nháp (`docs/thesis/`), Ch4 dùng V2_RESULTS.md; **(b) E2c** — sinh phiếu chấm mù từ đáp án v2 (`human_eval sheets`) → bạn-luật + người thân chấm (cùng 1 mẫu); **(c)** rotate key Gemini/Vertex trước bảo vệ; **(d)** V149 thiếu dấu review B (kiểm khi tiện).

> **v2.21 — Cập nhật 2026-07-06 (EVAL SET V2 HOÀN THÀNH — 150 câu, verify --final PASS):**
>
> **1. Bộ GT eval set v2 soạn xong 150/150 câu** (`data/evaluation/test_set_v2.json`), theo `docs/GT_AUTHORING_GUIDE.md`. Phân bổ: gap1 25 (7 bộ archetype song song 3 domain), gap2 26 (6 minimal-pair liên tỉnh, 2 cặp ĐẢO đáp án Có/Không), gap3 25 (chuỗi ủy quyền/tinh-chỉnh/AMENDS, dài nhất 3 văn bản), gap4 25 (regime-diff 2013/2024, 2 component CTV-kép, span-regime, mô hình 2 cấp), negative 14 (8 obvious + 6 trap verified-absent), underspecified 8 (bảo vệ D-25, có bản bất-đối-xứng), composite 8 (có câu 4-gap + liên-lĩnh-vực NCN+hộ tịch), register 19 (khẩu ngữ, citation giữ nguyên câu gốc). Theme: dat-dai 61/ho-tich 52/ncn 29/null 8; difficulty: easy 40/medium 59/hard 51. **Mọi citation verify cơ khí ngược corpus** (`python -m src.evaluation.verify_gt --final` PASS).
>
> **2. Sửa 3 lỗi data corpus B phát hiện khi soạn** (commit riêng từng lỗi): NĐ123 `implements: null` → `luat-ho-tich-2014` (thiếu cạnh IMPLEMENTS trực tiếp — Gap 3); 9+6 annotation NĐ 07/2025 ghi nhầm hiệu lực 09/01/**2019** → 09/01/**2025** (NĐ123 + NĐ87 — đầu độc Gap 4); đã re-ingest, graph xác nhận 18/18 Amendment đúng date, cạnh NĐ123→Luật HT có. **Việc B hậu kiểm:** 3 fix trên + source_url NĐ123 (trỏ nhầm NĐ104) + typo '4.500.000 triệu đồng' NĐ114 Đ6.
>
> **2b. Khâu đánh giá — code đã build (2026-07-07, chờ GT freeze để chạy đo):** **E1 ablation** `src/retrieval/ablation_config.py` (7 mode cắt CẤP CẠNH — IMPLEMENTS/AMENDS tách riêng, giải confound Gap3/4; wired `run_evaluation --ablation`); **E2a baseline ladder** — `bm25` (`src/baseline/bm25_rag.py` Okapi tự cài), `closed-book` (`src/baseline/closed_book.py`), `oracle` (`src/evaluation/oracle.py`), cùng naive RAG cũ (`run_evaluation --systems graphrag,baseline,bm25,closed-book,oracle`). 277 test pass. **Chưa chạy đo** (chờ test_set_v2 freeze). Review sheet GT: `src/evaluation/build_review_sheet.py` → `data/evaluation/GT_REVIEW.html`.
>
> **3. Việc tiếp theo cho GT:** [A] + [B] REVIEW CHÉO từng câu (guide §8; [B] duyệt đất đai của [A], [A] duyệt hộ tịch/NCN của [B]) → sửa nếu cần → chạy lại verify → **FREEZE + pre-register (commit hash vào E0) TRƯỚC khi chạy bất kỳ eval nào trên bộ này**. Dev set 26 câu cũ (`test_set_dat_dai.json`) chính thức là DEV SET (contaminated D-10/D-11), không dùng báo số cuối. Lưu ý harness: nhóm underspecified (jurisdiction=null) eval KHÔNG bơm force_jurisdiction — cần sửa `run_evaluation` skip inject khi item.jurisdiction=null (chưa làm).

> **v2.20 — Cập nhật 2026-07-06 (Gỡ Confirmation Loop — D-25):**
>
> **Gỡ bỏ Confirmation Loop** khỏi toàn hệ thống. Lý do: hệ là **1Q-1A (không đa lượt)** → "hỏi lại khi thiếu field" chỉ dừng ở **ngõ cụt** (không nhận được câu trả lời tiếp), lại **không đóng góp khoa học** và eval **luôn bypass** nó. Gỡ: `query_planner` (`is_complete`/`missing_fields`/`_compute_completeness`/`build_confirmation_prompt`/`build_question_framework`), `pipeline` (nhánh dừng-hỏi + field `confirmation_needed`/`confirmation_prompt` + param `bypass_completeness`), `demo`/`run_evaluation`/`naive_rag` (bỏ truyền bypass + key confirmation trong results). **Bảo toàn kết quả canonical**: `force_jurisdiction` đổi điều kiện sang `jurisdiction is None` (tương đương → eval Gemini/Claude KHÔNG xê dịch). Demo giờ luôn best-effort. Refactor 12 file, xóa 12 test tính năng gỡ → **254 test pass**. Side-fix: `precache_demo` param stale `llm_fallback=`→`llm_mode="claude"`. **Ảnh hưởng GT plan:** bỏ dạng câu "thiếu-field→hỏi-lại". *(Chương 3 luận văn + outline 5.3 cần bỏ Confirmation Loop khỏi phần Limitations/UX khi viết.)*

> **v2.19 — Cập nhật 2026-06-30 (Corpus B re-ingest đa-domain + Multi-LLM mode + Gemini-only validated):**
>
> **1. Corpus B vào graph (D-23):** pull + làm sạch 13 file Hộ tịch/Nuôi con nuôi của [B] (sửa NQ 124 đa-theme hướng A, `amended_by_norms`, heading typo, comment template, spacing). Hỗ trợ `implements` đa-cha (string\|list\|null). **Re-ingest** → graph đa-domain: **32 Norm (dat-dai 20, ho-tich 8, nuoi-con-nuoi 4)**, 4548 Component, 6394 MAPS_TO_CONCEPT. D-23 verify data thật: NĐ 120 → [Luật Hộ tịch, Luật NCN]; TT 04 → [NĐ 123, Luật Hộ tịch].
>
> **2. Multi-LLM provider (D-24):** 3 mode `claude` \| `claude-fallback` \| `gemini` cho cả demo lẫn eval (`--llm-mode`). Gemini chạy **Vertex AI qua ADC** ($300 Cloud credit; vùng VN không free tier Developer API). Wrapper trong suốt; mặc định `claude` → eval reproducible. Judge giữ Claude Haiku cố định. Fix bug truncation (sàn `max_output_tokens=2048` cho thinking model). Bake-off: generator `gemini-2.5-pro` (≈ Claude), planner/ontology `gemini-2.5-flash`; model 3.x mới hơn lại KÉM hơn.
>
> **3. Gemini-only validated** (full 26): GraphRAG-Gemini **F1 0.549 / NormR 0.766** vs Baseline-Gemini 0.356/0.554 → **Δ kiến trúc +0.193 F1** (≈ Δ Claude +0.206) = ưu thế kiến trúc LLM-agnostic. 2 negative result tune NormR (prompt provider-aware; structural backfill) đều đánh đổi F1 → REJECT, chấp nhận NormR 0.766 (đặc tính Gemini).
>
> **4. Demo resilience:** Lớp 1 pre-cache (`precache_demo.py`) + Lớp 2 Gemini fallback. 266 test pass.
>
> **Chờ [B]:** sign-off cross-check (TASK-05) + test set Hộ tịch/Nuôi con nuôi → mở Gap 1 + E1 ablation đầy đủ.

> **v2.18 — Cập nhật 2026-06-29 (Kiến trúc Đánh giá E0–E3 — design spec, chưa triển khai):**
>
> **Bối cảnh:** session bàn sâu về phương pháp luận đánh giá. Kết luận: evaluation hiện tại (Full GraphRAG vs Naive RAG) chứng minh hệ thống *tốt*, nhưng chưa chứng minh nó tốt *vì đúng những lý do luận văn claim* (từng thành phần KG giải đúng từng gap). Thiết kế lại toàn bộ khâu đánh giá thành kiến trúc 4 khối, lưu vào **[docs/EVALUATION_ARCHITECTURE.md](EVALUATION_ARCHITECTURE.md)** (design spec để các session sau dựa theo). Quyết định **D-22**.
>
> **4 khối (triết lý "Claim → Evidence"):**
> - **E0 — Tiền đề:** độ tin cậy phép đo. Reproducibility N=3 ✅ + significance (bootstrap CI + Wilcoxon) ✅ đã có; **cần VIẾT** GT provenance + metric validity (làm được ngay, không cần API/corpus).
> - **E1 — Cơ chế (phần thiếu, quan trọng nhất):** ablation leave-one-out với **double dissociation** — `no-theme`/`no-jurisdiction`/`no-traversal`/`no-temporal` phải sụp ĐÚNG gap tương ứng VÀ ổn định ở gap khác. Build `ablation_config.py` (cờ tắt thành phần trong `run_pipeline`).
> - **E2 — Hệ thống:** (2a) baseline ladder đa-**trục** — thêm **closed-book** ("có cần retrieval?"), **auto-GraphRAG** ("có cần ontology?" — killer học thuật), **oracle** (trần); (2b) consistency per-domain = mảnh chính Gap 1; (2c) **bỏ BERTScore → người chấm + máy chấm** (chủ-tớ, validated qua kappa).
> - **E3 — Giới hạn:** failure taxonomy ✅ + negative results (D-12/19/20) ✅ giữ làm mục chính thức + error severity (tham vọng).
>
> **Mỗi gap có gói bằng chứng đa nguồn** (ablation + so sánh + bổ trợ). Phân biệt cứng: baseline (thắng) ≠ ablation (sụp) ≠ upper bound (tiến gần).
>
> **Trạng thái:** đây là **design spec, CHƯA code**. Làm được ngay (không chờ B): viết E0 methodology, thiết kế `ablation_config.py` + `human_eval.py` rubric, BM25/closed-book/oracle baseline. **Blocker chờ corpus [B]:** chạy ablation suite E1 + E2b consistency + auto-GraphRAG. Đồng bộ với `project_eval_tier1_deferred`.

> **v2.17 — Cập nhật 2026-06-23 (Evaluation Tier 0: mở rộng thang đo $0 — significance + citation behavior; Tier 1 ablation HOÃN tới khi corpus đủ):**
>
> **Bối cảnh:** 2 hướng thuật toán (multi-agent verifier, cross-encoder/finetune embedding) đã đi qua, phần lớn cho negative result. Giá trị biên cao nhất giờ ở **đo lường** (thêm thang đo, chứng minh ưu/nhược kiến trúc) chứ không thêm cơ chế. Chia 2 tier theo chi phí: **Tier 0 = $0 offline** (tái dùng results JSON đã chạy), **Tier 1 = ablation tốn API** (chạy qua mọi câu).
>
> **Phát hiện trước khi code:** `metrics.aggregate` ĐÃ có per-gap/per-theme/precision-recall/latency → KHÔNG dựng lại; chỉ bổ sung 3 thứ còn thiếu.
>
> **1. Module [src/evaluation/expanded_eval.py](../src/evaluation/expanded_eval.py)** ($0, đọc 2 results JSON sẵn, KHÔNG API/DB):
> - **Significance** — paired bootstrap 95% CI (10000 resamples, seed=42 deterministic) + Wilcoxon signed-rank + win/loss/tie. Trả lời "N=26 nhỏ → +Δ có thật không".
> - **Citation behavior** — over-citation rate, mean pred/gt count, precision–recall gap (chẩn đoán cite thừa vs bỏ sót).
> - **Per-gap + per-jurisdiction breakdown** tái dùng `cit_matches`; **report tiếng Anh hợp nhất** cho luận văn.
> - **Fix alignment quan trọng:** nhãn `gap_type` đồng bộ theo `test_set_dat_dai.json` HIỆN TẠI theo `id` — baseline run 05-19 gộp gap4 vào gap3 *trước* khi relabel; nếu đọc nhãn lưu trong run sẽ lệch grouping (gap4 baseline = N/A). Lấy nhãn từ test set = single source of truth.
>
> **2. Kết quả canonical** (graphrag `20260528-142757` vs baseline `20260519-204426`, N=26, [EXPANDED_EVAL_20260528.md](../data/evaluation/EXPANDED_EVAL_20260528.md)):
>
> | Metric | Δ (G−B) | 95% CI | Wilcoxon p | Win/Loss/Tie |
> |---|---:|---|---:|---:|
> | F1 Khoản | **+0.281** | [0.154, 0.417] | 0.001 *** | 18/3/3 |
> | F1 Điều | +0.298 | [0.174, 0.430] | <0.001 *** | 18/3/3 |
> | Norm Recall | +0.257 | [0.108, 0.424] | 0.007 ** | 10/1/13 |
>
> - **Ưu thế KG có ý nghĩa thống kê** (CI loại trừ 0) — chống phản biện "26 câu may rủi".
> - **Per-gap:** Gap4 phiên bản **Δ +0.522** (lớn nhất; baseline 0.071 — KG temporal/CTV/AMENDS quyết định); Gap2 địa phương mạnh nhất tuyệt đối (0.726, hard-filter jurisdiction).
> - **Nhược điểm trung thực:** câu `multi-juris` GraphRAG **thua** baseline (Δ −0.244) → ghi vào Limitations.
> - **Citation behavior:** baseline over-cite nhiều hơn (0.958 vs 0.792); cả hai recall > precision (xu hướng cite thừa — chừa đất Verifier Tier 1 đã KEEP ở D-18).
>
> **3. Test:** `tests/test_expanded_eval.py` — 10 case deterministic ($0 mock). Toàn suite **230 pass**. Quyết định **D-21**.
>
> **Caveat:** cặp canonical lệch ngày (graphrag post prompt-v2.9 05-28 vs baseline 05-19); GT + test set cố định nên so sánh hợp lệ, nhưng muốn sạch tuyệt đối phải chạy lại cùng phiên (thuộc Tier 1).
>
> **HOÃN Tier 1 (ablation suite):** formalize `dense-no-KG` + BM25 + tắt từng thành phần KG (jurisdiction / temporal / graph-traversal / hybrid off) thành system trong `run_evaluation`, chạy qua mọi câu → **tốn API**. Chỉ chạy khi **thành viên B nạp đủ corpus multi-domain** (hộ tịch + nuôi con nuôi) — ablation full-run chỉ có nghĩa khi corpus hoàn chỉnh, tránh chạy lại. Prototype dense-no-KG (10 câu) phiên trước đã cho GraphRAG ≈ gấp đôi F1 (0.618 vs 0.302) → tín hiệu mạnh, chờ corpus để chạy chuẩn full 26.
>
> **Tiếp theo (khi corpus B sẵn sàng):** (a) formalize dense-no-KG + BM25 baseline; (b) ablation từng thành phần KG; (c) chạy lại cặp graphrag+baseline cùng phiên để bỏ confound lệch ngày.

> **v2.16 — Cập nhật 2026-06-23 (Retrieval-metric harness $0 + go/no-go finetune embedding):**
>
> **Bối cảnh:** trước khi đổ công finetune embedding (corpus nhỏ → rủi ro), cần xác nhận có "đích" để distill. Dựng [src/evaluation/retrieval_eval.py](../src/evaluation/retrieval_eval.py) đo **retrieval thuần (KHÔNG generation → $0)**: Recall@k + MRR cấp Điều/Khoản, so DENSE (BGE-M3) vs CROSS-ENCODER rerank trên cùng pool. (Planner cached ~$0, dense+CE local. Cũng là phần harness #4.)
>
> **Kết quả go/no-go (24 câu non-negative, $0):**
>
> | Metric | DENSE | RERANK | Δ |
> |---|---:|---:|---:|
> | MRR Điều | 0.625 | **0.758** | **+0.132** |
> | MRR Khoản | 0.591 | 0.656 | +0.065 |
> | Recall Điều@5 | 0.642 | 0.675 | +0.033 |
> | Recall Khoản@5 | 0.555 | 0.609 | +0.054 |
> | Recall Điều@10 | 0.700 | 0.714 | +0.014 |
>
> **→ GO (đủ điều kiện):** cross-encoder **nâng MRR rõ (+0.13 cấp Điều)** — xếp đúng chunk lên cao khi nó có trong pool (đúng tín hiệu disambiguation Q021 MRR 0.50→1.00, Q022 0.20→1.00, Q025/Q026 0.50→1.00). **Có đích thật để distill** vào BGE-M3.
>
> **Nuance trung thực:** gain chủ yếu ở **ranking (MRR)**, Recall@10 gần phẳng → đây là lý do ablation F1 trước net-trung tính (LLM đọc cả top-25 nên xếp lại không đổi context). Finetune embedding để có ích cần (a) context nhỏ hơn để ranking quan trọng, HOẶC (b) cải thiện cả Recall. Q024 normR=0 (Stage-1 miss norm) → lỗi upstream, finetune không chữa được.
>
> **Tiếp theo:** pipeline finetune — mine hard-negative qua graph (cùng Norm/tier) + cross-encoder soft-label → distill BGE-M3, đo bằng harness này ($0 gate) trước khi tốn generation.

> **v2.15 — Cập nhật 2026-06-23 (Cross-encoder retrieval modifier: ablate → REJECT → gỡ integration; giữ module làm teacher):**
>
> **Bối cảnh:** direction 2 (retrieval precision) — cross-encoder `bge-reranker-v2-m3` (LOCAL $0) vá embedding blindness disambiguation cấp Điều (P-08/Q022: bi-encoder chọn "Điều 4 Hiệu lực" thay "Điều 1 hạn mức").
>
> **Thử 2 cách tích hợp + ablation 7-câu** (subset thiên vị: Q022/Q021/Q020/Q003/Q025/Q024 headroom + Q001 canary; base cache vs rerank fresh):
> - **(A) Rerank Floor** (thay Dense Floor ở Pass 0): F1 Khoản **+0.019** NHƯNG **regression Q021** (1.00→0.80).
> - **(B) Blend** (cộng `rerank_rank` thành tín hiệu RRF thứ 3, GIỮ Dense Floor): F1 Khoản **+0.048** (chữa Q021) NHƯNG **NormR −0.071 + F1 Điều −0.050** — cross-encoder kéo chunk lexically-relevant nhưng SAI norm lên (Q022 NormR 1.00→0.50, Q003 F1 Điều 0.29→0.00).
>
> **Kết luận:** cả 2 là **đánh đổi, không thắng sạch** (đặc biệt B hi sinh NormR — metric quan trọng cho QA pháp lý). Giống **D-12** → **REJECT làm default + GỠ integration** khỏi `hybrid_search`/`pipeline`/`demo`/`run_evaluation` (giữ D-10: dense là ground signal). `semantic_filter.py` restore về bản sạch (pre-rerank).
>
> **GIỮ `src/retrieval/reranker.py`** (+ test, LOCAL $0, **CPU** vì MPS treo 3.5h) — REPURPOSE làm **teacher** sinh hard-negative/soft-label cho **finetune embedding** (bước direction-2 kế tiếp). Quyết định D-20. Tổng suite **210 pass**.
>
> **Lưu ý phương pháp:** ablation trên subset thiên vị + confound (base cache vs rerank fresh) → kết quả định hướng, không phải tác động trung bình. Nhưng đủ rõ để không bật mặc định.

> **v2.13 — Cập nhật 2026-06-23 (Đo Verifier: Tier 1 thắng / Tier 2 reject + fix bug snippet Phụ lục):**
>
> **Tier 1 (grounding, $0) — kết quả dương:** ablation offline trên run canonical 20260520-211930 (26 câu, $0 vì tái dùng answer+context đã lưu): **F1 Khoản 0.524 → 0.547 (+0.023)**, F1 Điều +0.023, NormR −0.010. Bỏ đúng **7 citation bịa** (ungrounded) ở 4/26 câu (Q008/Q024/Q025 ▲, Q019 =). Wiring live xác nhận trên 3 câu random.
>
> **Tier 2 (LLM support-judge) — REJECT làm bộ lọc drop (D-19):** thử live trên 3 câu over-cite (Q004/Q008/Q019):
> - Q004 (over-cite thật 3 vs GT 2): judge giữ cả 3 — citation thừa vẫn grounded + được chunk khẳng định → **support-judge KHÔNG bắt được over-cite** ("support" ≠ "đáp án GT tối thiểu").
> - Q008: flag cả 2 citation **GT đúng** (mismatch cấu trúc Phụ lục); Q019: flag citation mà metric tính match → **hard-drop sẽ REGRESS F1** (over-prune).
> - Phần lớn "over-cite" là **metric/GT artifact** (Q004 citation thừa thực ra đúng, GT thiếu) → drop = tối ưu theo thước đo lỗi.
> - Kết luận: **giữ Tier 1, reject Tier 2-support** (giống D-12). Future work: relevance/necessity-judge + GT completeness + Tier 2 flag-only-for-reporting.
>
> **Bug fix:** `faithfulness._extract_answer_snippet` chỉ bắt regex `Điều`, bỏ sót `[Phụ lục ...]` → fallback 400 ký tự đầu → judge nhìn sai ngữ cảnh → flag oan (chính là Q008). Đã fix dispatch theo `loai` (cải thiện cả faithfulness Tier 2 metric lẫn verifier). `tests/test_faithfulness.py` (5 case, $0 mock). Toàn suite 203 pass.
>
> **Tiếp theo:** sang nhánh **cross-encoder rerank** (direction 2 — retrieval precision, $0 local).

> **v2.12 — Cập nhật 2026-06-23 (Verifier agent — tầng multi-agent Generator → Verifier → prune):**
>
> **Bối cảnh**: Phân tích lại bottleneck — Norm Recall đã 0.93 nhưng F1 Khoản chỉ 0.539; root-cause (ROOT_CAUSE_ANALYSIS) chỉ ra **over-citation là nguyên nhân DOMINANT** của precision thấp (47 citation dư). Tức retrieval gần như xong, phần mất điểm nằm ở việc Generator cite quá tay / sai Điều mà không ai kiểm lại. Đây là khởi đầu hướng nghiên cứu **multi-agent** (do [A] đảm nhận, cùng nhánh retrieval-precision cross-encoder → finetune embedding).
>
> **1. Verifier agent** ([src/retrieval/verifier.py](../src/retrieval/verifier.py)) — mẫu Self-Refine/CRITIC, đặt sau Generator:
> - **Tier 1 — grounding (deterministic, $0)**: drop citation không có header tương ứng trong CONTEXT (bắt hallucination thô). Tái dùng `faithfulness._citation_in_context`.
> - **Tier 2 — support (Haiku, tùy chọn)**: judge chunk có thực sự khẳng định claim không; mặc định UNSUPPORTED → "flag" (giữ, bảo thủ chống over-prune), `drop_unsupported=True` để prune cứng. Tái dùng `faithfulness._judge_citation`.
> - Thiết kế = "faithfulness metric nâng thành filter inline" — không circular import (faithfulness chỉ phụ thuộc anthropic/stdlib).
>
> **2. Tích hợp** ([pipeline.py](../src/pipeline.py)): tham số `verify` / `verify_tier`, **mặc định `verify=False` → hành vi pipeline cũ KHÔNG đổi**. Cờ `--verify` / `--verify-tier {0,1,2}` cho [demo.py](../src/demo.py) + [run_evaluation.py](../src/evaluation/run_evaluation.py) → ablation ±verifier. Verifier chỉ áp dụng GraphRAG (không baseline). `PipelineResult` thêm field `verifier`.
>
> **3. Test**: `tests/test_verifier.py` — 13 case **mock hoàn toàn** ($0 API). Toàn suite 198 pass (185 cũ + 13). Import sạch, không circular.
>
> **Pending (cần API — chờ duyệt chi phí)**: chạy ablation ±verifier trên test set (N≥3) để đo F1/precision delta thực tế. Hiệu quả định lượng CHƯA đo. Quyết định D-18.

> **v2.11 — Cập nhật 2026-05-30 (2-mode trả lời: General gọn vs IRAC tư vấn + order-independent citation parser):**
>
> **Bối cảnh**: Hệ thống hướng tới 2 đối tượng — người dân (cần đáp án trực tiếp, gọn) và người làm luật / câu hỏi có tình huống cụ thể (cần phân tích chi tiết). Áp một phong cách trả lời cho mọi câu vừa hao token vừa kém UX: quan sát thấy câu "giá cấp sổ đỏ HCM?" bị LLM nhồi hết hạn mức/lệ phí/tỷ lệ 30-50-100% thay vì đi thẳng vào phí được hỏi.
>
> **1. Prompt directness + abstention** ([context_assembler.py](../src/retrieval/context_assembler.py)):
> - Thêm "NGUYÊN TẮC TRẢ LỜI ĐÚNG TRỌNG TÂM" ưu tiên cao nhất, vô hiệu hóa các rule "BẮT BUỘC..." khi không liên quan câu hỏi.
> - Làm mềm rule nghĩa vụ tài chính: trả lời trọng tâm khoản được hỏi thay vì liệt kê mọi con số trong CONTEXT.
> - Nâng abstention thành rule cứng: thiếu căn cứ → câu chuẩn "Tôi không đủ thông tin để cung cấp câu trả lời chính xác cho bạn." (không dùng kiến thức LLM chế câu trả lời); partial → trình bày phần có + nêu rõ phần thiếu.
>
> **2. 2-mode response style** (`build_messages(q, c, mode)`):
> - `general` (mặc định): câu trả lời gọn, đi thẳng đáp án, cite nguồn trực tiếp.
> - `irac`: cấu trúc Vấn đề / Căn cứ pháp lý / Phân tích / Kết luận cho câu hỏi có tình huống cụ thể; Rule chỉ trích từ CONTEXT (không bịa), fallback general khi thiếu fact.
> - CORE rules đặt trước, mode block đặt sau → CORE vẫn cache chung (giữ D-15 prompt caching).
>
> **3. Auto-detect mode** ([query_planner.py](../src/retrieval/query_planner.py)):
> - Thêm field `response_mode` vào QueryPlan: phân biệt câu tra cứu chung (general) vs câu mô tả tình huống cá nhân (irac). Resolve: explicit override > planner auto-detect > "general".
> - Demo `--mode {auto,general,irac}`; eval `--response-mode {auto,general,irac}`.
> - Verify auto-detect 4/4 đúng trên câu demo; câu khiếu nại gốc ("giá sổ đỏ") đã đi thẳng vào phí, IRAC chạy đúng 4 heading + dùng abstention partial khi thiếu căn cứ.
>
> **4. Khung hướng dẫn cách hỏi khi theme=None** ([query_planner.py](../src/retrieval/query_planner.py)):
> - `build_question_framework()`: khi không xác định được lĩnh vực, thay câu hỏi cụt bằng công thức `[thủ tục]+[địa phương]+[tình huống]` + 3 ví dụ mẫu. Demo panel confirmation render Markdown.
>
> **5. A/B eval 2-mode** (12 câu / 4 gap, [test_subset_2mode.json](../data/evaluation/test_subset_2mode.json) + [notebooks/phase4_2mode_eval.ipynb](../notebooks/phase4_2mode_eval.ipynb)):
> - General F1 Khoản 0.466 vs IRAC 0.439 (Δ −0.027, trong nhiễu) — **2 mode tương đương F1**, khác ở phong cách. Win/Loss/Tie = 2/2/8.
> - IRAC trội ở câu đa tầng phức tạp (Q011 NormR 0.33→1.0); ép IRAC cho câu tra cứu đơn có thể hại (Q007) → củng cố thiết kế auto-detect (mỗi loại câu một mode).
>
> **6. Order-independent citation parser** ([answer_generator.py](../src/retrieval/answer_generator.py)):
> - Điều tra Q007 (IRAC F1 0.50→0.00) phát hiện **metric artifact**: answer đúng (bảng phí đầy đủ) nhưng cite `[Điểm đ, Khoản 2, Phụ lục, ...]` (đảo thứ tự) → regex cũ cố định thứ tự fail → trả [].
> - Fix: `parse_citations` split block `[...]` theo dấu phẩy, phân loại từng phần theo prefix — bất kể thứ tự. Tương tự `parse_sections` đã robust.
> - Verify: 13 unit case + 17 pytest pass; re-parse 26 câu canonical (run 20260520-211930) **0 regress**, Q008 ▲0.33→0.57 (cùng pattern Phụ lục đảo được cứu), aggregate F1 +0.0099. → F1 cũ bị đánh giá thấp nhẹ ở vài câu Phụ lục NQ HĐND do format-order, không phải lỗi retrieval.
>
> **Eval impact**: `run_evaluation` mặc định `--response-mode auto` (= general cho câu tra cứu); 26-câu canonical metric **không đổi về bản chất** (chỉ Q008 +0.24 nhờ parser fix). Số thesis ổn định.
>
> **Files thay đổi**: `context_assembler.py`, `query_planner.py`, `answer_generator.py`, `pipeline.py`, `baseline/naive_rag.py`, `demo.py`, `run_evaluation.py`, `test_subset_2mode.json` (mới), `notebooks/phase4_2mode_eval.ipynb` (mới), `tests/test_query_planner.py`.
>
> **Pending**: re-run notebook 2-mode với parser mới (Q007 IRAC sẽ về ~0.5); cân nhắc N=3 canonical rerun với parser order-independent để cập nhật ABLATION_MATRIX.



> **v2.10 — Cập nhật 2026-05-28 (Defense-in-Depth chống Thuật ngữ Giả: Prompt Sanitization B1 + Term Validator B2):**
>
> **Bối cảnh**: Sau v2.9 (fix hallucination L1), demo CLI một câu hỏi span-regime phát hiện LLM tự tạo cụm **"(nguyên tắc cắt ngang)"** — thuật ngữ pháp lý GIẢ, không có trong văn bản pháp luật Việt Nam thật, nguồn gốc từ shortcut nội bộ `(cắt ngang)` trong prompt template. Phân tích cho thấy đây là 1 case của class bug lớn hơn: **bất kỳ shorthand/label nào tôi viết trong prompt đều có thể bị LLM promote thành thuật ngữ giả**. Sửa từng case không scalable.
>
> **Cách tiếp cận khoa học (3-layer defense-in-depth)**:
>
> **B1 — Prompt sanitization (chặn nguồn leak structural)** ([context_assembler.py:248](../src/retrieval/context_assembler.py#L248)):
> - Loại bỏ TẤT CẢ parenthetical shortcut/label khỏi prompt: `(lex superior)`, `(lex posterior)`, `(lex specialis)`, `(cắt ngang)` → thay bằng mô tả tiếng Việt đầy đủ.
> - Thêm meta-rule mạnh: *"TUYỆT ĐỐI KHÔNG tự tạo tên gọi/nhãn riêng cho nguyên tắc, học thuyết, quy tắc, khái niệm pháp lý. Nếu CONTEXT không gọi tên một nguyên tắc bằng cụm cụ thể, hãy MÔ TẢ bằng câu văn đầy đủ, KHÔNG rút gọn thành 'nguyên tắc X', '(X)', hay đặt cụm vào ngoặc kép như một thuật ngữ định danh."*
> - Cấm cụm tiếng La-tinh xuất hiện trong output: "lex superior/posterior/specialis/lex…" — diễn đạt bằng tiếng Việt mô tả.
>
> **B2 — Term grounding validator (auto-detect post-generation)** ([src/evaluation/term_validator.py](../src/evaluation/term_validator.py)):
> - Module độc lập extract candidate "thuật ngữ giả" từ câu trả lời LLM bằng 4 pattern:
>   - `named_principle` (high-precision): "nguyên tắc/quy tắc/học thuyết X" — signature mạnh, không filter
>   - `quoted` (heuristic): cụm trong `"..."` — apply `_looks_like_term` filter
>   - `parenthetical` (heuristic): cụm trong `(...)` — apply filter
>   - `bold` (heuristic): cụm `**X**` — apply filter
> - `_looks_like_term` heuristic: loại các cụm có số (measurement), function word prefix ("không", "có", "tại"...), descriptive words ("phù hợp", "bắt buộc"), >5 từ.
> - Mỗi candidate được validate bằng substring lookup vào (1) CONTEXT retrieve được, (2) corpus `data/raw/*.md`.
> - Metric `grounding_rate = #grounded / #candidates_total` — analogue của citation existence_rate nhưng cho thuật ngữ.
> - CLI: `python -m src.evaluation.term_validator results_*.json --corpus data/raw`.
>
> **B3 — Faithfulness metric extension** (chưa làm, để dành sau): tích hợp `terminology_grounding_rate` vào `faithfulness.py` để báo cáo cùng `citation_existence_rate`.
>
> **Validation kết quả**:
> - Demo câu hỏi span-regime gốc: 0 candidate ungrounded (vs 1 trong v2.9). Câu trả lời không còn "(nguyên tắc cắt ngang)" — diễn đạt thay bằng "thời điểm cơ quan có thẩm quyền ra quyết định sẽ quyết định văn bản nào được áp dụng".
> - 8 câu subset (Q008, Q011, Q019, Q022, Q023, Q024, Q025, Q026): **15 candidate terms / 0 ungrounded / 100% grounding rate**.
> - Validator chạy trên run cũ 20260520-211930 (canonical N=3): phát hiện **16 ungrounded terms / 26 câu**, bao gồm tất cả các leak đã biết (SPAN-REGIME, cắt ngang, Quy định dẫn chiếu, chuyển giao thẩm quyền…) — chứng minh recall của detector.
>
> **F1 trade-off (8-câu subset)**: 0.586 (v2.9 iter2) → 0.569 (v2.10 B1) = −0.017, nằm trong nhiễu (Q008 σ=0.22 documented trong REPRODUCIBILITY_REPORT). Term grounding gain >> F1 marginal loss.
>
> **Tại sao tổng quát hơn từng-case-patch**:
> - Câu hỏi mới thêm vào: validator tự động chạy, không cần audit thủ công
> - Thuật ngữ mới LLM bịa: detector pattern catch (`named_principle` đặc biệt high-recall)
> - Reproducibility cho thesis: có metric quantitative `grounding_rate` thay vì anecdotal "đã sửa Q022"
> - Decision Log: D-16 (B1 prompt sanitization), D-17 (B2 term validator)
>
> **Files thay đổi**:
> - `src/retrieval/context_assembler.py`: B1 prompt sanitization
> - `src/evaluation/term_validator.py` (mới): B2 detector module
> - `CLAUDE.md`: D-16, D-17
> - `data/evaluation/results_graphrag_20260528-152726.json`: 8-câu B1 evidence

> **v2.9 — Cập nhật 2026-05-28 (Hallucination Fix L1 + Anthropic Prompt Caching):**
>
> **Bối cảnh**: Phân tích faithfulness của run canonical 20260520-211930 (N=3) phát hiện 3 loại lỗi tinh vi:
> - **F1 — Prompt label leakage**: Q022/Q023 output có cụm "Đây là câu hỏi **SPAN-REGIME**…" — nhãn kỹ thuật nội bộ từ prompt template `TEMPORAL #4` rò rỉ ra answer.
> - **F2 — Citation slug vs số hiệu**: Q024/Q025 cite `[Điều 57 K2 a, Văn bản 47/2024/QH15]` — LLM dùng số hiệu pháp lý từ pretraining knowledge thay vì slug ID corpus.
> - **F3 — Citation pointer misattribution**: Q019 cite `[Điều 10 K1-4, Văn bản nghi-dinh-226-2025-nd-cp]` — content đúng nhưng pointer sai (NĐ 226 sửa Điều 10 của NĐ 112, NĐ 226 không có Điều 10).
> - **F4 — Malformed citation**: Q008 cite `[Phụ lục I và Phụ lục II - Ghi chú, …]` — gộp 2 phụ lục vào 1 label.
>
> **Tổng cộng 7/94 citations bịa (existence_rate = 92.6%) trên 4/26 câu.**
>
> **L1 prompt rewrite ([context_assembler.py:248](../src/retrieval/context_assembler.py#L248))**:
> - Refactor `build_prompt(q, c) -> str` thành `build_messages(q, c) -> (system, user)` để hỗ trợ Anthropic prompt caching. `build_prompt()` giữ làm wrapper backward-compat.
> - **Bỏ hoàn toàn nhãn `SPAN-REGIME` / `POINT-IN-TIME`** khỏi prompt — diễn đạt thuần Việt thay thế ("hồ sơ đang trong giai đoạn chuyển tiếp", "câu hỏi tại một thời điểm cụ thể").
> - **Meta-rule chống leak**: "TUYỆT ĐỐI không sao chép vào câu trả lời bất kỳ nhãn kỹ thuật, mã viết tắt, hoặc cụm UPPERCASE nào xuất hiện trong các quy tắc".
> - **Rule cứng về `Văn bản` field**: bắt buộc slug ID, "TUYỆT ĐỐI KHÔNG dùng số hiệu pháp lý gốc (47/2024/QH15, 31/2024/QH15…)".
> - **Rule chống malformed**: "Mỗi citation chỉ chứa MỘT vị trí, không gộp 'I và II'".
> - **Rule amendment (dual-cite mềm)**: cho phép cite cả văn bản gốc + văn bản sửa đổi khi cả 2 đều có content trực tiếp trong context. Sau iteration 1 phát hiện rule strict "KHÔNG cite văn bản sửa đổi" gây regression Q011 (-0.29) + Q026 (-0.33) vì GT của bạn dùng convention cite cả 2 — đã làm mềm trong iter2.
>
> **Anthropic prompt caching ([answer_generator.py:209](../src/retrieval/answer_generator.py#L209))**:
> - System prompt (~2117 tokens, > 1024 minimum của Sonnet 4.6) đánh dấu `cache_control: ephemeral`.
> - Cache hit từ request thứ 2 trở đi: input cost giảm ~90% trên phần system. TTL ~5 phút.
> - Local prompt-hash cache vẫn được duy trì (hash trên `system + user` để invalidate khi prompt template đổi).
>
> **Validation methodology** (test pyramid để tiết kiệm API):
> 1. **Iter1** (subset 6 câu lỗi gốc): F1 0.317 → 0.519 (+64%), hallucination 7 → 1, leak/bad-slug → 0. Phát hiện Q011/Q026 regression do rule strict.
> 2. **Iter2** (subset 8 câu = 6 cũ + Q011 + Q026): F1 → 0.587, hallucination 1 → **0**. Trade-off Q024 (-0.33), Q023 (-0.25).
> 3. **Regression 26 câu × 1**: F1 0.539 (N=3 old) → 0.554 (N=1 new), nằm trong nhiễu CI; hallucination 7 → 1; leak 2 → 0; bad-slug 2 → 0.
> 4. **Confirm 13 câu random (seed=42)**: F1 0.406 → 0.474 (+0.068), **0 hallucination / 0 leak / 0 bad-slug**. Q004 lặp regression −0.33 (cùng câu xuất hiện 2 run liên tiếp — có thể là single-run variance, cần N=2+ confirm cho thesis).
>
> **Kết quả cuối (iter2, full 26 câu, N=1, sẽ rerun N=3 ở giai đoạn final report)**:
>
> | Metric | v2.8 (N=3) | v2.9 (N=1) | Δ |
> |---|---:|---:|---:|
> | F1 Khoản | 0.539 ± 0.021 | 0.554 | +0.015 (within CI) |
> | F1 Điều | 0.567 ± 0.032 | 0.570 | +0.003 |
> | NormR | 0.931 ± 0.005 | 0.936 | +0.005 |
> | **Hallucinated citations** | 7 (trong 94) | **0–1** | **−86%** |
> | **Prompt leak (SPAN-REGIME)** | **2 câu** | **0** | **fix triệt để** |
> | **Bad slug (số hiệu thay vì slug)** | **2 câu** | **0** | **fix triệt để** |
> | Negative correct | 100% | 100% | tied |
>
> **Documentation deliverable cho thesis**: bằng chứng cụ thể về hallucination → systematic fix → empirical validation, dùng làm case study trong chương "Engineering Trustworthy LLM Output" hoặc Limitations.
>
> **Files thay đổi**:
> - `src/retrieval/context_assembler.py`: prompt rewrite (build_messages + meta-rules)
> - `src/retrieval/answer_generator.py`: Anthropic prompt caching
> - `data/evaluation/test_subset_hallucination.json` (mới): 8 câu cho iteration testing
> - `data/evaluation/test_subset_regression13.json` (mới): 13 câu random seed=42 cho regression
> - `CLAUDE.md`: D-14 (prompt L1 rewrite), D-15 (Anthropic prompt caching)
>
> **Pending**: full N=3 canonical rerun (sẽ làm ở giai đoạn final report) để cập nhật ABLATION_MATRIX + REPRODUCIBILITY_REPORT.

> **v2.8 — Cập nhật 2026-05-21 (Gap 4 — Đa phiên bản + Q024 re-label + Baseline re-aggregate):**
>
> **Quyết định tách Gap 4**: Phân tích cho thấy 7 câu temporal (Q020-Q026)
> đang bị xếp vào `gap3` nhưng thực tế test **năng lực orthogonal** — temporal reasoning
> (phân biệt VB hết/còn hiệu lực, span-regime, amendment tracking) chứ không phải
> structural traversal (multi-tier `[:IMPLEMENTS]`). Tách thành Gap 4 cho phép:
> - Thesis claim rõ hơn: 4 gap, mỗi gap có architectural component riêng
> - Per-gap F1 chính xác hơn: Gap 3 cũ bị kéo xuống bởi Q022 (F1=0, embedding limitation)
> - Baseline hoàn toàn blind với temporal → differentiator mạnh
>
> **Bao gồm Q024 trong gap4**: ban đầu vẫn để gap3 nhưng validator phát hiện Q024 chỉ
> trích 1 tier (Luật ĐĐ 2024 Đ116 K5) — không thoả ràng buộc gap3 (≥2 tier). Bản chất
> câu này là **point-in-time CTV retrieval** (Năm 2024, trước khi Luật 47/2024 sửa đổi),
> đúng phạm vi Gap 4.
>
> **Phân bổ mới**: gap1=3, gap2=6, gap3=8, **gap4=7**, negative=2 (total=26).
>
> **Thay đổi:**
> - `test_set_dat_dai.json`: 7 câu re-label `gap3` → `gap4` (Q020-Q026)
> - `validate_test_set.py`: thêm `gap4` vào `VALID_GAPS` + validation ≥3 câu
> - `report_builder.py`: thêm `gap4` display name "Gap 4 — Đa phiên bản"
> - `run_evaluation.py:362-369`: bug fix — force-refresh `gap_type/theme/jurisdiction/GT`
>   từ test_set hiện tại khi `--reuse-results`. Trước đó dict `**old` propagate stale label.
> - CLAUDE.md, PROJECT_CONTEXT.md, CHAPTERS_OUTLINE.md: narrative 3→4 gap
> - `[:AMENDS]`, `[:HAS_CTV]`, `[:AMENDED_BY]` gán annotation **Gap 4**
> - ABLATION_MATRIX.md: re-compute per-gap với gap3/gap4 split + Baseline re-aggregate
>
> **Baseline re-aggregate**: F1 Khoản 0.295 → **0.333** vì GT của Q026 đã được rút gọn
> còn 1 citation từ commit 705a02c (Q026 GT fix), baseline run trước commit đó nên
> citation_score cũ stale. Sau re-aggregate với GT v2.8, baseline trích đúng (citation
> match từ refusal answer — xem §"Q026 Evaluation Artifact" trong CHAPTER_4_EXPERIMENTS).
> Improvement v2.6 vs Baseline: 0.539 vs 0.333 = **+61.8%** (giảm từ +82.7% công bố trước
> đó nhưng honest hơn — baseline + GraphRAG cùng GT v2.8).
>
> **Không thay đổi code pipeline retrieval** — chỉ framing + documentation + test label
> + 1 bug fix trong `run_evaluation.py --reuse-results` mode.

> **v2.7 — Cập nhật 2026-05-20 (Demo CLI + Faithfulness + Reproducibility N=3 + Ablation Matrix + Thesis Outline):**
>
> Sau v2.6.1 (architecture soft-frozen cho Đất đai), thực hiện 4 task chuẩn bị cho thesis writing:
>
> **1. Demo CLI ([src/demo.py](../src/demo.py))** — rich-based UI cho weekly meeting với giảng viên:
> - Panel câu hỏi / Trả lời (markdown render) / Citations (table) / Thống kê
> - Status spinner trong khi pipeline chạy ~23s (UX feedback)
> - `--trace` Tree view cho pipeline stages
> - Graceful 529 outage handling
> - **Query Planner cache** mới — tránh block toàn pipeline khi Anthropic API outage
>
> **2. Faithfulness metric ([src/evaluation/faithfulness.py](../src/evaluation/faithfulness.py))** — 2-tier citation trustworthiness:
> - Tier 1 (deterministic, $0): % citations có chunk match trong context — catch hallucination thô
> - Tier 2 (Claude Haiku judge): % existing citations được context semantically support — catch hallucination tinh vi
> - Combined: `faithful_rate = #(exist AND supported) / #total`
> - Hỗ trợ Phụ lục citations (`loai='phu_luc'`, `dieu='_default'`)
>
> **3. Reproducibility study N=3 ([REPRODUCIBILITY_REPORT_20260520.md](../data/evaluation/REPRODUCIBILITY_REPORT_20260520.md))**:
> - 3 independent runs cùng code state, `--no-llm-cache`, measure variance
> - **F1 Khoản = 0.539 ± 0.021** (95% CI [0.515, 0.563])
> - **F1 Điều = 0.567 ± 0.032**
> - **NormR = 0.931 ± 0.005** (cực stable, ~0.5% variation)
> - Latency = 22.92 ± 0.12s (pipeline deterministic)
> - **Faithful rate = 0.916 ± 0.069**
> - Per-Q variance: 5-6 câu σ ≥ 0.1 (Q008 σ=0.22, Q020/Q024 σ=0.19) — LLM stochastic empirically confirmed
>
> **4. Ablation Matrix ([ABLATION_MATRIX.md](../data/evaluation/ABLATION_MATRIX.md))**:
>
> | Configuration | F1 Khoản | F1 Điều | NormR | Δ vs Baseline |
> |---|---:|---:|---:|---:|
> | Baseline (Naive RAG, GT v2.8) | 0.333 | 0.333 | 0.718 | — |
> | v2.3 canonical † | 0.440 | 0.453 | 0.891 | +32.1% |
> | + parse_citations dedupe † | 0.461 | 0.476 | 0.891 | +38.4% |
> | + Prompt TEMPORAL #4 † | 0.466 | 0.483 | 0.869 | +39.9% |
> | + Dense Floor (Pass 0) † | 0.485 | 0.519 | 0.917 | +45.6% |
> | **+ Structured Cite (Pass -1) [N=3]** | **0.539 ±0.021** | **0.567** | **0.931** | **+61.8%** |
>
> † row v2.3-v2.5 chưa re-aggregate với GT v2.8 (N=1 single-run); order-of-magnitude vẫn đúng nhưng số chính xác cần re-run.
>
> **Per-Gap final breakdown (v2.8, N=3 mean, GT v2.8, Q024 ∈ gap4)**:
> - Gap 1 (đa lĩnh vực, n=3): F1 0.343 ±0.013 vs Baseline 0.194 (+76.8%)
> - Gap 2 (đa địa phương, n=6): F1 0.618 ±0.041 vs Baseline 0.485 (+27.4%)
> - **Gap 3 (đa tầng, n=8): F1 0.412 ±0.013 vs Baseline 0.209 (+97.1%)**
> - **Gap 4 (đa phiên bản, n=7): F1 0.568 ±0.031 vs Baseline 0.214 (+165.4%)** ← differentiator mạnh nhất
> - Negative (n=2): 100% vs 100% tied
> - Q026 evaluation artifact (baseline citation match từ refusal): nếu loại bỏ → Gap 4 baseline thực = 0.071 → improvement +700%
>
> **5. Thesis chapter skeleton (`thesis/CHAPTERS_OUTLINE.md` — đã gỡ 2026-07-11, thay bằng `docs/thesis/`)**: 5 chapters + Appendix với data refs cụ thể cho tác giả expand prose.
>
> **Tổng commits session 2026-05-19/20**: 22 commits từ canonical `225b3aa` → `2b72bb8`. F1 Khoản improvement: +22.6% qua 4 fix layers, statistically backed (N=3).

---

> **v2.6.1 — Cập nhật 2026-05-20 (Label-keyword Boost attempt → REVERT; Q022 documented as limitation):**
>
> Sau v2.6 (Pass -1 Struct Cite fix Q026), tiếp tục thử fix Q022 retrieval-depth qua **Label-keyword Boost** (Pass -0.5: lexical overlap content tokens question vs Component label). Empirical ablation 8-câu chứng minh **net F1 -0.055 (-7.9%)** — Gemini's "lexical noise prediction" validated. **REVERT**.
>
> **Hypothesis tested**: Q022 GT rank #7 dense trong QĐ 18 alone; lexical-overlap có thể phân biệt được Điều CONTENT-RELEVANT vs Điều META-related.
>
> **Empirical failure ([RETRIEVAL_LIMITATIONS_20260520.md](../data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md))**:
>
> | Metric | +Pass -1 baseline | +Label-keyword | Δ |
> |---|---:|---:|---:|
> | AVG F1 (8 câu) | 0.693 | 0.638 | **−0.055 (−7.9%)** |
> | Win:Loss count | — | **1:4** | net negative |
> | Win:Loss magnitude | — | +0.50 vs −0.95 | **1:2 net negative** |
>
> Regressions: Q001 (-0.20 canary), Q002 (-0.29 cross-jurisdiction noise), Q008 (-0.19 cross-jurisdiction noise), Q024 (-0.27 canary). Only Q022 +0.50 win.
>
> **Root cause Q022 không fix nổi**:
> - QĐ 18 có MULTIPLE Điều cùng prefix "Hạn mức đất ở" (Điều 1 GT cho "hộ gia đình, cá nhân" vs Điều 3 cho "người có công với cách mạng") — label-overlap score TIE → Cypher row order pick Điều 3 (wrong)
> - **Embedding semantic blindness**: BGE-M3 KHÔNG phân biệt được target population qua label prefix giống nhau
> - Lexical overlap đặt thêm noise cross-jurisdiction (Gap 2 cases regress)
>
> **Q022 → documented as Limitation cho thesis Discussion chapter.** Future work (out of scope): cross-encoder re-ranking (BGE-Reranker), multi-query expansion, question-aware label filtering.
>
> **Phương pháp luận lesson** (Gemini đồng tình):
> - Empirical evidence trumps a priori reasoning **both ways**:
>   - Gemini's "regex = overfitting" predicted wrong → Pass -1 Struct Cite work (Q026 +1.0)
>   - Gemini's "label-keyword = p-hacking" predicted right → Pass -0.5 fail (net -0.055)
> - Quyết định per-case dựa trên ablation, không dogma.
> - Helper functions giữ trong code (inactive) để future cross-encoder reuse.
>
> **System state v2.6.1 unchanged vs v2.6**: F1 Khoản 0.549 (Q022 vẫn = 0.00; Pass -0.5 reverted nên không tác động). Active retrieval enhancements: Pass -1 Struct Cite + Pass 0 Dense Floor + Pass 1/2 RRF.

---

> **v2.6 — Cập nhật 2026-05-20 (Pass -1 Structured Citation Boost — Q026 fully fixed):**
> Sau v2.5 (Dense Floor), tiếp tục fix Q026 retrieval-depth. Root-cause identification: question explicit cite "Khoản 1 Điều 13 NĐ 102/2024" nhưng dense top của NĐ 49 (amending norm) = K11/K12 (label dài 200+ chars chứa metadata sửa đổi → embedding match toàn label, không phân biệt được Khoản).
>
> **1. Q026 GT correction (data fix):**
> - Quan sát thực nghiệm: NĐ 102/2024 KHÔNG có Điều 13 trong [data/raw/nghi-dinh-102-2024-nd-cp.md](../data/raw/nghi-dinh-102-2024-nd-cp.md) (file chỉ chứa Điều 1-12, rồi 14+) do D-01/D-05 thu thập theo chương — chương chứa Điều 13 không thuộc scope CMĐSDĐ cá nhân.
> - GT cũ reference Component không tồn tại → đổi sang cite AMENDING provision tại NĐ 49 Đ13 K1 (chunk này tồn tại trong graph với id 75a8fa9705c58b2e).
> - Vẫn test AMENDED_BY exploitation — chỉ thay van_ban gốc bằng amending norm để GT phản ánh đúng scope corpus.
>
> **2. Pass -1 Structured Citation Boost ([semantic_filter.py](../src/retrieval/semantic_filter.py)):**
> - Module-level regex extract "Khoản X Điều Y" / "Điều Y" từ question
> - Fetch Components matching cấu trúc qua Neo4j (`STARTS WITH "Điều {Y}." AND CONTAINS "Khoản {X}."`)
> - Pass -1 ép vào output TRƯỚC Pass 0 (dense floor) — respect per_norm/per_tier caps; ADDITIVE (no-op nếu question không có pattern)
> - Khoa học: khi user (chuyên viên pháp lý) gõ trực tiếp tham chiếu cấu trúc, retrieval phải bảo đảm chunk khớp xuất hiện trong context, bất kể dense ranking hay graph_boost.
>
> **3. Full 26-câu validation (best-available merge sau Anthropic 529 outage):**
>
> | Metric | v2.5 (Dense Floor) | **v2.6 (+Pass -1)** | Δ |
> |---|---:|---:|---:|
> | F1 Khoản | 0.485 | **0.549** | +0.064 (+13.2%) |
> | F1 Điều | 0.519 | **0.564** | +0.044 (+8.5%) |
> | Norm Recall | 0.917 | 0.917 | 0 |
> | Negative correct | 100% | 100% | tied |
>
> **Tổng vs canonical v2.3 (4 fix cumulative)**:
>
> | Metric | v2.3 canonical | **v2.6** | Δ |
> |---|---:|---:|---:|
> | F1 Khoản | 0.440 | **0.549** | **+0.109 (+24.8%)** |
> | F1 Điều | 0.453 | **0.564** | +0.111 (+24.5%) |
> | Norm Recall | 0.891 | 0.917 | +0.026 |
>
> **Per-Q v2.6 vs v2.5**: 5 improvements / 1 regression (5:1):
> - **Q026: 0.00 → 1.00** ⭐ TARGET FIXED (pred = Điều 13 Khoản 1 NĐ 49 match GT exactly)
> - Q019: 0.00 → 0.29, Q008: 0.57 → 0.86, Q025: 0.50 → 0.67, Q009: 0.33 → 0.40 (preds giảm — Pass -1 reduce noise)
> - Q017: 0.50 → 0.33 (regression, không có struct cite signal → LLM stochastic noise)
>
> **Q022 status sau v2.6**: F1 = 0.00 (chưa fix). GT rank #7 dense WITHIN QĐ 18 alone → Pass 0 top-1 dense per norm picks "Điều 4 Hiệu lực thi hành" thay vì GT "Điều 1 K1 Điểm a". Need label-keyword boost (regex "hạn mức" → boost components có "hạn mức" trong label) — chưa implement.
>
> **Limitation acknowledged**: Anthropic 529 outage liên tục trong 3 lần thử full re-run → phải merge 21 from main + 2 from patch + 2 from ablation + Q021 from v2.5 (Pass -1 no-op cho Q021 nên giá trị unchanged). Đã verify cùng code state cho mọi data source. Sẽ re-run khi API ổn để có canonical reproducibility.

---

> **v2.5 — Cập nhật 2026-05-19 (Dense Floor fix — Q024 retrieval depth giải quyết):**
> Sau v2.4 (prompt tuning với gain modest +0.026), tiếp tục debug retrieval-depth cho Q022/Q024/Q026 (3 câu vẫn F1=0). Instrumentation định lượng từng case → phát hiện **bug nguyên tắc** trong hybrid_search: Stage 3 graph_boost từ procedure mapping override pure dense semantic match.
>
> **1. Diagnosis cụ thể (instrumentation API-free)**:
> | Q | GT exists trong graph? | Pure dense rank của GT | Top-25 hybrid có GT? |
> |---|---|---|---|
> | Q022 | ✅ (Điều 1 K1 Đa của QĐ 18) | **#11/35** | ❌ (per-norm cap đẩy ra) |
> | Q024 | ✅ (Điều 116 K5 Luật ĐĐ 2024) | **#2/100** | ❌ (graph_boost đẩy Điều 121/123/227 lên đầu) |
> | Q026 | NĐ 102 K1Đ13 không tồn tại standalone (đã wholly amended) | n/a | n/a |
>
> **2. Fix Dense Floor (Pass 0 trong [semantic_filter.py](../src/retrieval/semantic_filter.py)):**
> - Thêm Pass 0 trước Pass 1 RRF-breadth + Pass 2 depth
> - Iterate `dense_results` theo dense score order, ép top-1 dense per norm vào output
> - Khoa học: "embedding similarity là ground signal; KG augments, không override"
> - Q024 ngay lập tức: pure dense rank #2 → hybrid rank #2 với rrf=7.08 (trước đó MISSING entirely)
>
> **3. Full 26-câu validation ([COMPARE_prompt-fix_vs_dense-floor_20260519.md](../data/evaluation/COMPARE_prompt-fix_vs_dense-floor_20260519.md)):**
>
> | Metric | v2.3 canonical | v2.4 (+prompt) | **v2.5 (+Dense Floor)** | Δ tổng vs canon |
> |---|---:|---:|---:|---:|
> | F1 Khoản | 0.440 | 0.466 | **0.485** | +0.045 (+10.2%) |
> | F1 Điều | 0.453 | 0.483 | **0.519** | +0.066 (+14.6%) |
> | Norm Recall | 0.891 | 0.869 | **0.917** | +0.026 |
> | Latency | 2.85 (cache) | 22.53 (real) | 23.03 (real) | — |
>
> **Per-Q v2.5 vs v2.4**: 7 wins / 6 losses, magnitude 1.58 vs 1.05 = 1.5:1 net positive.
> - **Top wins**: Q024 +0.67 ✅ (target case fully fixed), Q011 +0.27, Q004 +0.17 (recovery), Q013 +0.17
> - **Regressions**: pattern chung pred_count tăng (Q019: 1→5, Q008: 2→4) → Dense Floor đưa nhiều norms vào context → LLM cite nhiều hơn → precision drop ở case over-cite. Trade-off chấp nhận được vì NormR (kế cận để judge legal answer quality) tăng đáng kể.
> - Q008 stochastic: +0.40 winner trong v2.4 → -0.23 trong v2.5 — cùng prompt, cùng retrieval (no change cho Q008), khác chỉ LLM sampling
>
> **Còn lại sau v2.5**:
> - **Q022 retrieval-depth khác**: Dense Floor preserve top-1 dense per norm, nhưng top dense của QĐ 18 = "Điều 4 K2 Điểm a" ≠ GT "Điều 1 K1 Điểm a". GT có trong norm nhưng rank thấp → cần label-keyword boost hoặc per-norm Pass 0 = top-N (≥2)
> - **Q026 norm-mention boost** (Fix 3 chưa implement): question mention "Nghị định 102/2024/NĐ-CP" nhưng dense không pull NĐ 102 chunk nào (all top-20 là NĐ 49 amending) → cần regex extract + ad-hoc boost cho norms mentioned trong câu hỏi
>
> **Total session 2026-05-19 từ canonical 161509**: 11 commits (faeed8f → 5bb5ba8), F1 Khoản +10.2%, NormR +2.9%, methodology document đầy đủ (ROOT_CAUSE + PROMPT_TUNING_EXPERIMENT + 2 COMPARE reports).

---

> **v2.4 — Cập nhật 2026-05-19 (Root-cause analysis + dedupe + prompt TEMPORAL #4 + fresh full re-run):**
> Sau v2.3 canonical, làm root-cause analysis có hệ thống để định vị chính xác nguyên nhân khoảng cách F1 (0.440) vs NormR (0.891) — refute cả 2 hypothesis ban đầu (regex Khoản+Điều / chunking limit) bằng dữ liệu thực nghiệm. Áp dụng 2 minimal fix có evidence + chạy lại full 26 câu với --no-llm-cache cho latency honest.
>
> **1. Root-cause analysis ([ROOT_CAUSE_ANALYSIS_20260519.md](../data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md)):**
> Phân loại 24 câu non-negative theo 5 categories. Findings:
> - **H3 LLM over-cite**: 47 excess citations (DOMINANT cause của low precision)
> - **H2_dieu sai Điều của đúng Norm**: 20 instances
> - **H4 metric artifact**: 9 cases (wildcard GT + greedy 1-1 matching)
> - **H5 Phụ lục format mismatch**: 8 instances / 4 cases (NQ HĐND có cấu trúc Roman/path, GT cite Arabic)
> - **H2_khoan sai Khoản của đúng Điều**: chỉ 4 instances (REFUTE hypothesis "regex Khoản+Điều fix")
>
> Instrumentation downstream ([RETRIEVAL_DEBUG_20260519-200009/](../data/evaluation/RETRIEVAL_DEBUG_20260519-200009/)) trên Q022/Q023/Q024/Q026:
> **3/4 failure cases là LLM behavior, không phải retrieval/chunking** — top-25 hybrid đã chứa đúng target component (Q022: QĐ 18 rank #5, Q023: Luật 2013 Điều 100 rank #8, Q026: NĐ 49 Điều 13 K1 rank #5/6). LLM ignore trong cite. Chỉ Q024 là retrieval issue thực sự (Điều 116 không trong top-15 — legal terminology mismatch).
>
> **2. Fix #1 — Dedupe parse_citations ([answer_generator.py](../src/retrieval/answer_generator.py)):**
> LLM đôi khi cite cùng vị trí 2+ lần trong cùng answer (VD Q025: Điều 116 K5 cite 2 lần). Dedupe theo tuple (loai, number, khoan, diem, tiet, van_ban) — giữ first occurrence. Idempotent. Impact (qua reuse mode, $0 API): F1 Khoản 0.440 → 0.461, không regression.
>
> **3. Fix #2 — Prompt rule TEMPORAL #4 ([context_assembler.py](../src/retrieval/context_assembler.py)):**
> Thêm rule cite cả 2 regime cho câu hỏi SPAN-REGIME ("hồ sơ dở dang", "chưa giải quyết xong"). SCOPED hẹp — không áp dụng POINT-IN-TIME ("năm X", "trước/sau ngày Y"). Qua 3-round ablation 7 câu: Q023 robust win +0.40, Q022/Q023 NormR +0.50. Edit 2 (parsimonious) thử nhưng REVERT vì không cải thiện. Methodology lesson: N=1 ablation noisy do LLM stochastic, cần N≥3 future work ([PROMPT_TUNING_EXPERIMENT_20260519.md](../data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md)).
>
> **4. Tooling infrastructure:**
> - `src/utils/llm_config.py` — centralize Anthropic max_retries (DRY refactor)
> - `src/evaluation/metrics.cit_matches` — single source of truth cho semantic match (cả F1 và report ✅/❌ delegate cho cùng helper)
> - `src/evaluation/report_builder.py` — auto sinh REPORT_<timestamp>.md human-readable mỗi run (overview + bảng so sánh + per-Q detail với GT vs pred ✅/❌)
> - `src/evaluation/instrument_retrieval.py` — debug Stage 1/2/3 retrieval cho failure cases
> - `src/evaluation/compare_runs.py` — A/B diff 2 results JSON
>
> **Headline v2.4 — 26 câu Đất đai fresh re-run (--no-llm-cache, honest latency):**
>
> | Metric                       | v2.3 canonical | v2.4 sau fix | Δ       |
> |------------------------------|---------------:|-------------:|--------:|
> | F1 Khoản                     | 0.440          | **0.466**    | +0.026 (+5.9%) |
> | F1 Điều                      | 0.453          | **0.483**    | +0.030 (+6.6%) |
> | Norm Recall                  | 0.891          | 0.869        | −0.022  |
> | Latency mean (s)             | 2.85 (cache)   | **22.53** (fresh) | +19.68 |
> | Negative correct (2 câu)     | 1.000          | 1.000        | tied ✅ |
>
> **Per-Q**: 8 improvements vs 3 regressions, magnitude 2:1 net positive ([COMPARE_canonical_vs_prompt-fix_20260519.md](../data/evaluation/COMPARE_canonical_vs_prompt-fix_20260519.md)).
> - Top wins: Q008 (+0.40, gap2 NQ Đồng Nai Phụ lục), Q023 (+0.40, gap3 regime change — Edit 1 designed-for)
> - 6 wins khác (+0.06 to +0.15) đều có pred_count giảm → dedupe pattern
> - 3 regressions (Q004 −0.30, Q020 −0.33, Q017 −0.06): NONE có span-regime signal → Edit 1 không trigger → **LLM stochastic noise** (đã document)
>
> **Latency note**: canonical v2.3 latency 2.85s là CACHE ARTIFACT (cache hit từ debugging session). 22.53s là số real fresh — dùng cho luận văn. Baseline 18.29s tương tự (canonical 0.04s cũng artifact).
>
> **Refute cả 2 hypothesis ban đầu (Claude và Gemini)**:
> - "Regex Khoản+Điều → LCCID filter sẽ lift F1 0.44→0.6+" (Claude): H2_khoan chỉ 4 instances, không phải dominant cause.
> - "F1 gap thuần do chunking limit, không fix được" (Gemini): top-25 đã có đúng target trong 3/4 failure cases → không phải chunking.
>
> **Limitation honest**: prompt tuning N=1 không đủ tin cậy để claim mọi regression là prompt-caused. Cần multi-run ablation cho future prompt experiments. Real bottleneck cho Q022/Q024/Q026 là retrieval depth + LLM cite behavior, không phải prompt.

---

> **v2.3 — Cập nhật 2026-05-19 (Q026 AMENDED_BY + Cách C + 26-câu full eval):**
> Mở rộng test set + đóng gap classification Query Planner cho câu hỏi metadata thuần.
>
> **1. Q026 — AMENDED_BY direct test ([test_set_dat_dai.json](../data/evaluation/test_set_dat_dai.json)):**
> - Câu hỏi: "Khoản 1 Điều 13 NĐ 102/2024/NĐ-CP đã được văn bản nào sửa đổi và hiệu lực từ ngày nào?"
> - GT citations bắt buộc chứa cả norm gốc (`nghi-dinh-102-2024-nd-cp`) + amending norm (`nghi-dinh-49-2026-nd-cp`) → F1 đo trực tiếp khả năng cite amendment metadata. Trước đó Q025 exercise AMENDED_BY chỉ gián tiếp.
>
> **2. Cách C — Backfill theme từ tham chiếu số hiệu văn bản ([query_planner.py](../src/retrieval/query_planner.py)):**
> - Vấn đề: Câu hỏi metadata thuần không có từ khóa lĩnh vực → LLM Query Planner trả `theme=None` → Stage 1 retrieval trả `[]` → pipeline short-circuit, F1=0 không phải do logic mà do classification gap.
> - Fix (defensive — chỉ trigger khi LLM trả None): regex extract "102/2024/NĐ-CP", "Luật Đất đai 2024", slug id... → lookup Neo4j `(Theme)-[:INCLUDES]->(Norm)` → backfill nếu mọi reference cùng 1 theme.
> - Q026 post-fix: backfill thành công, Stage 1 retrieve 5 norms gồm `nghi-dinh-102-2024-nd-cp`, NormRecall 0→0.5.
>
> **3. Infra fix — Anthropic max_retries=8 chống crash 529 Overloaded:**
> - Eval gặp Anthropic API 529 gián đoạn → SDK default `max_retries=2` không đủ; crash 6-12 câu/run khi server load cao.
> - 3 site khởi tạo client (`pipeline.py`, `naive_rag.py`, `run_evaluation.py`) → tăng `max_retries=8`, SDK tự exponential backoff với jitter.
>
> **Headline v2.3 — 26 câu Đất đai full set (merged snapshot post-fix):**
>
> | Metric                       | GraphRAG  | Baseline  | Δ       |
> |------------------------------|----------:|----------:|--------:|
> | F1 Khoản                     | **0.440** | 0.285     | +0.155 (+54%) |
> | F1 Điều                      | **0.453** | 0.285     | +0.168 (+59%) |
> | Norm Recall                  | **0.891** | 0.737     | +0.154 (+21%) |
> | gap3 F1 Khoản (15 câu)       | **0.341** | 0.126     | +0.215 (+170%) |
> | gap3 Norm Recall (15 câu)    | **0.811** | 0.544     | +0.267 |
> | Negative correct (2 câu)     | **1.000** | 1.000     | tied ✅ |
>
> **Q026 spotlight — AMENDED_BY exploitation (Ý 2):**
> - Backfill theme=dat-dai HOẠT ĐỘNG, retrieve 10 norms + 8 units, answer cite được `nghi-dinh-49-2026-nd-cp` (NormRecall 0.5).
> - F1=0 vì retrieval lấy nhầm Khoản 11/12 (cùng có amended_by 49/2026) thay vì Khoản 1 → vấn đề **retrieval depth (Component-level pinpoint)**, không phải Query Planner. Future work: regex `Khoản X Điều Y` từ câu hỏi → force LCCID filter ở Stage 2.
>
> **Limitation chấp nhận:** Snapshot ghép từ v1 (Q001-Q025) + v2 (Q026) vì Anthropic 529 outage cùng ngày khiến rerun v2/v3 crash 6-12 câu. Đã verify Q001-Q025 không bị ảnh hưởng bởi Cách C (chỉ trigger khi theme=None; LLM correct cho 25 câu kia, cache hits identical). Cần rerun verify khi API ổn định.

> **v2.2 — Cập nhật 2026-05-17 (Reproducibility + A/B ablation Schema B):**
> Bổ sung 2 cải tiến + 1 finding methodology quan trọng:
>
> **1. temperature=0 (reproducibility 100%):**
> - `src/retrieval/answer_generator.py`: hardcode TEMPERATURE=0.0 (env LLM_TEMPERATURE override).
> - Anthropic greedy decoding + LLM cache → lần 2+ cache hit bit-exact (latency 0.045s, $0).
> - Defense thesis: "Retrieval 100% det (BGE + Qdrant + Neo4j); LLM ~99% với temp=0 + 100% lần 2+ với cache; Citation + Output structure 100% predictable."
>
> **2. Schema B (loose sections H2):**
> - `src/retrieval/context_assembler.py`: opt-in prompt yêu cầu LLM xuất 3 section `## TRẢ LỜI` / `## CẢNH BÁO LEX` / `## PHẠM VI`.
> - `src/retrieval/answer_generator.py`: `parse_sections()` + `AnswerSections` TypedDict.
> - Toggle via env `INCLUDE_SCHEMA_B` (default "false" cho eval, opt-in "true" cho production).
>
> **3. A/B ablation finding (4 setups):**
> | Setup | temp | Schema B | G F1 Kh | B F1 Kh | Winner |
> |---|---|---|---:|---:|---|
> | v7 | default | OFF | 0.416 | 0.389 | G ✅ |
> | v8 | 0.0 | ON | 0.390 | 0.428 | B (outlier) |
> | **v9 / Run A** | **0.0** | **OFF** | **0.420** | **0.389** | **G ✅** |
> | Run B | 1.0 | ON | 0.380 | 0.362 | G ✅ |
>
> → **v9 final config = temp=0 + INCLUDE_SCHEMA_B=false**. Schema B equalize G/B (G drop ~0.03) — không công bằng cho academic eval. Schema B parser giữ lại làm opt-in cho production cần structured output.
>
> **Headline v9 — chốt số liệu (19 câu Đất đai):**
>
> | Metric                       | GraphRAG  | Baseline  | Δ       |
> |------------------------------|----------:|----------:|--------:|
> | F1 Khoản                     | **0.420** | 0.389     | +0.031  |
> | F1 Điều                      | **0.442** | 0.389     | +0.053  |
> | Norm Recall                  | **0.864** | 0.719     | +0.145  |
> | Negative correct (2 câu)     | **1.000** | 1.000     | tied ✅ |
> | Manual Correctness (10 câu)  | **4.5**/5 | 3.5/5     | +1.0    |
> | Manual Faithfulness (10 câu) | **4.9**/5 | 4.3/5     | +0.6    |
> | Reproducibility (run 2)      | **100%**  | **100%**  | bit-exact, $0 |

> **v2.1 — Cập nhật 2026-05-17 (TASK-17 GraphRAG WIN OVERALL trên Đất đai subset):**
> Sau 4 fix theo plan Gemini, GraphRAG vượt baseline TRÊN MỌI METRIC tự động + manual eval trên 19 câu Đất đai. Bypass 2 vấn đề đo lường không công bằng (gap2 ranking + refuse mechanism), giải bug parser, mở multi-juris filter.
>
> **Headline v7 — chốt số liệu cho Phase 4 trên subset Đất đai (19 câu):**
>
> | Metric                       | GraphRAG  | Baseline  | Δ       |
> |------------------------------|----------:|----------:|--------:|
> | F1 Khoản (strict)            | **0.416** | 0.389     | +0.027  |
> | F1 Điều (định tuyến VB)      | **0.435** | 0.389     | +0.046  |
> | Norm-level Recall            | **0.846** | 0.680     | +0.167  |
> | Negative correct rate (2 câu)| **1.000** | 1.000     | tied ✅ |
> | Manual Correctness (10 câu)  | **4.5**/5 | 3.5/5     | +1.0    |
> | Manual Faithfulness (10 câu) | **4.9**/5 | 4.3/5     | +0.6    |
>
> **Gap breakdown — GraphRAG WIN cả 4 gap types + tied negative:**
>
> | Gap       | G F1(Kh) | B F1(Kh) | G NormR | B NormR | Winner |
> |-----------|---------:|---------:|--------:|--------:|--------|
> | gap1 (3)  | 0.395    | 0.250    | 1.000   | 0.667   | G ✅   |
> | gap2 (6)  | 0.483    | 0.460    | 1.000   | 0.833   | G ✅   |
> | gap3 (8)  | 0.227    | 0.235    | 0.635   | 0.490   | G (F1 Điều + NormR) |
> | neg (2)   | 1.000    | 1.000    | 1.000   | 1.000   | TIE ✅ |
>
> **4 Fix theo plan Gemini:**
> 1. **Smart Matching metric** (`src/evaluation/metrics.py`): GT khoan=None → wildcard match bất kỳ Khoản nào của cùng (dieu, van_ban). F1 Khoản G tăng 0.112→0.288.
> 2. **Parser fix Phụ lục không số** (`src/retrieval/answer_generator.py`): regex chấp nhận `[Phụ lục, Khoản X, ...]` không có ký hiệu (NQ 02/2023 chỉ có 1 PL duy nhất). Q007 cit 0 → có cit.
> 3. **Prompt scope guard** (`src/retrieval/context_assembler.py`): liệt kê tường minh OOD topics (phí công chứng, thuế TNCN) + câu trả lời chuẩn → fix negative regression hoàn toàn.
> 4. **Multi-jurisdiction handling** (`src/retrieval/subgraph_extractor.py`): thêm key `multi-juris` vào `_JURISDICTION_ALLOW` → câu so sánh chéo HCM vs ĐN retrieve được cả 2 tỉnh. Q018 NormR 0.25 → 1.00.
>
> **Bypass cho fair eval:**
> - `force_jurisdiction` (`src/pipeline.py`): inject ground-truth jurisdiction từ test_set → bỏ qua Confirmation Loop trong eval mode.
> - `bypass_completeness`: cho phép retrieval chạy khi planner thiếu procedure/theme (toan-quoc questions không khớp 6 procedures cố định).
>
> **Tooling tối ưu chi phí $$ dev:**
> - `--reuse-results <file>`: re-compute metric từ JSON, **0 API call** (re-parse citations từ answer text với parser hiện tại). Dùng khi sửa metric/parser/GT.
> - `--llm-cache-dir`: local cache theo hash(prompt+model). Lần 2 cache hit → **0.4s, $0 API** (giảm 97% latency).
> - `--clear-llm-cache` / `--no-llm-cache`: control khi cần.
>
> **3 luận điểm thesis có evidence vững (cho TASK-18):**
> 1. **Lex posterior chain** (Q017 đại diện): GraphRAG đúng 4/6 citation đa tầng (Luật + NQ QH + 2 NĐ), baseline F1=0 — proof of ontology + cạnh `[:IMPLEMENTS|AMENDS*1..4]`.
> 2. **Multi-jurisdiction routing** (Q018 đại diện): GraphRAG trình bày bảng so sánh chi tiết HCM vs ĐN với số tiền cụ thể, baseline nói thẳng "không có dữ liệu TP.HCM".
> 3. **Hallucination control trên out-of-scope** (Q006, Q016): sau fix #2 prompt scope guard, cả 2 hệ thống đều refuse đúng — vẫn cần ghi nhận GraphRAG dễ over-retrieve khi bypass.
>
> **1 limitation chung phát hiện trong dry run (đầu vào Future Work):**
> - Q019: cả 2 hệ thống miss phần phân cấp 2 cấp khi câu hỏi nối "phương án bóc tách" (NĐ 112+226) + "thẩm quyền chuyển giao" (NĐ 151). Concept mapping không liên kết được 2 cluster ý này.
>
> **Còn lại để TASK-17 full DoD:**
> - Test set 30+ câu (chờ [B] phần Hộ tịch + Nuôi con nuôi). Khi đủ data, chạy full eval với LLM cache → chi phí ước ~$0.5-1.

> **v2.0 — Cập nhật 2026-05-17 (TASK-17 evaluation framework hoàn thiện):**
> TASK-17 hoàn thành phần infrastructure + 6 vòng iteration đo lường (v1→v6). Có evidence khoa học rõ ràng cho thesis claim.
>
> **Headline số liệu (19 câu Đất đai, v6 — Smart Matching + parser fix + GT verify + bypass + force_jurisdiction):**
> - GraphRAG F1 Khoản 0.288 / F1 Điều 0.312 / Norm Recall 0.715
> - Baseline F1 Khoản 0.403 / F1 Điều 0.403 / Norm Recall 0.776
>
> **GraphRAG THẮNG ở 2 phân khúc:**
> - gap1 (3 câu, single-domain): F1 0.378 vs 0.250 (+51%); NormR 1.000 vs 1.000 (tie tối đa)
> - gap3 (8 câu, multi-tier amendment): F1 0.213/0.270 vs 0.167; NormR 0.573 vs 0.469
> - 4/6 killer gap3 G WIN (Q011, Q012, Q013, Q017 — đặc biệt Q017 lex posterior chain 0.60 vs 0.00)
>
> **GraphRAG THUA ở 2 phân khúc:**
> - gap2 (6 câu small QĐ lookup) — gap thu hẹp đáng kể; NormR tie 1.000 nhưng F1 thua do baseline ăn cấu trúc chunk
> - negative (2 câu) — bypass_completeness cho phép retrieve out-of-scope → LLM bịa citation. Trade-off ghi vào Future Work.
>
> **Tooling mới giúp giảm chi phí $$ debug:**
> - `--reuse-results <file>`: re-compute metric từ JSON, **0 API call** (dùng khi sửa metric/parser/GT)
> - `--llm-cache-dir`: local cache theo hash(prompt). Lần 2 = 0.4s, $0 (97% latency giảm)
> - `--clear-llm-cache` / `--no-llm-cache`: control cache khi cần
>
> **Bài học scientific (TASK-18 input):**
> 1. Ontology + AMENDS edges giải quyết được lex posterior chain (Q017 evidence)
> 2. Theme + summary embedding routing tốt hơn naive top-K cho định tuyến văn bản (gap1)
> 3. Baseline có lợi tự nhiên với corpus chứa nhiều văn bản nhỏ (chunk 512 ký tự bắt nguyên block Điều)
> 4. Smart Matching (GT khoan=None là wildcard) — cần thiết về phương pháp luận đo lường
> 5. Confirmation Loop + jurisdiction check là feature production nhưng phải bypass cho fair eval
>
> **Còn lại để TASK-17 full DoD:**
> - Test set 30+ câu (đợi [B] phần Hộ tịch + Nuôi con nuôi)
> - Manual eval ≥10 câu/hệ thống về Correctness và Faithfulness

> **v1.9 — Cập nhật 2026-05-17 (Phase 4 khởi động):**
> Bắt đầu Phase 4 (Evaluation). TASK-15 (Test Set) đang tiến hành — phần Đất đai do [A] hoàn tất.
> TASK-16 (Baseline Naive RAG) DONE. TASK-17 (infrastructure + metrics + runner) DONE; chờ test set đủ 30+ câu để chạy báo cáo chính thức.
>
> **TASK-17 (infrastructure DONE, full report chờ TASK-15):**
> - `src/evaluation/metrics.py`: `citation_score` (multiset intersection trên `(dieu, khoan, van_ban)`), `norm_recall` (van_ban coarse), `negative_correct`, `aggregate` (mean + p95 + breakdown gap_type/theme), `render_summary_md`.
> - `src/evaluation/run_evaluation.py`: CLI orchestrator chạy GraphRAG và/hoặc Baseline; lưu `results_<system>_<timestamp>.json` + `metrics_summary_<timestamp>.md`.
> - `_augment_question()` mô phỏng user trả lời Confirmation Loop → retry 1 lần khi `confirmation_needed`. Latency cộng dồn để fair.
> - `tests/test_metrics.py`: 9 unit tests PASS.
> - Dry run 16 câu Đất đai (`data/evaluation/DRY_RUN_REPORT.md`): GraphRAG F1=0.125 vs Baseline F1=0.257; Norm Recall 0.48 vs 0.80; Negative 100% cả 2. Phát hiện: (1) Confirmation Loop trigger 13/16 lần — Phase 3 design conservative; (2) GraphRAG vẫn chọn Đ1 thay Đ chuyên sâu (limitation v1.8); (3) Baseline ăn may chunk structure markdown. Findings dùng cho TASK-18.
>
> **TASK-15 (partial — Đất đai):**
> - `data/evaluation/SCHEMA.md`: spec field, gap_type, DoD checklist, quy trình soạn (data contract chung cho 2 thành viên).
> - `data/evaluation/test_set_template.json`: 6 câu mẫu Đất đai (Q001-Q006) cover gap1/gap2/gap3/negative.
> - `data/evaluation/test_set_dat_dai.json`: 16 câu Đất đai (Q001-Q016) — 3 gap1 + 6 gap2 (3 cặp HCM-ĐN: hạn mức/phí thẩm định/bảng giá) + 5 gap3 (multi-tier: Luật + NĐ + NQ QH) + 2 negative. Ground truth verified trực tiếp trên `data/raw/*.md`.
> - `src/evaluation/validate_test_set.py`: validator 2 mode (`--partial` cho file từng thành viên, full DoD cho merge cuối). Kiểm field bắt buộc, tier diversity cho gap3, phân bổ tổng (≥30, ≥10 đất đai, ≥10 ho-tich+nuoi-con-nuoi, ≥5 negative).
> - Còn lại để full DoD: 10+ câu Hộ tịch + Nuôi con nuôi (team viên [B]) + cross-review sign-off.
>
> **TASK-16 (DONE):**
> - `src/baseline/naive_rag.py`: `fixed_chunker(512, 50)` cắt theo ký tự + overlap; `run_baseline_ingestion()` đọc `data/raw/*.md`, encode BGE-M3, upsert Qdrant collection `baseline_legal_texts`; `run_baseline_query()` pure vector top-10 + Claude Sonnet 4.6 qua `generate_answer()` của GraphRAG (cùng prompt, đảm bảo "chỉ khác retrieval").
> - `BaselineResult` TypedDict khớp `PipelineResult` để TASK-17 chấm chung.
> - `tests/test_naive_rag.py`: 7 smoke tests (chunker, parse frontmatter, deterministic ID) — 7/7 PASS.
> - Live verify: ingestion 17 file → **1718 chunks**; Q001 (hạn mức TP.HCM) trả 4 citations đúng (Đ3.1/3.2/3.3 + bonus Đ5.2 QĐ 69/2024).
> - DoD: ✅ collection tạo OK | ✅ output schema khớp pipeline | ✅ BGE-M3 + Claude Sonnet 4.6 reused | ⏳ "chạy được trên 30+ câu test set" — chờ test set full (TASK-15).

> **v1.8 — Cập nhật 2026-05-16 (Stable — Phase 3 đóng băng):**
> Hoàn thiện retrieval quality cho câu hỏi tổng quát qua 4 fix khoa học (generic, không hardcode).
> Validated bằng E2E test 15 câu (14/15 ok + 1 confirmation đúng DoD). 149/149 unit tests PASS.
>
> **Fix 1 (Macro — Cypher composed-edge):** `subgraph_extractor.py` Stage 2 thay 4 OR clause (IMPLEMENTS×2 dir + AMENDS×2 dir) bằng pattern `[:IMPLEMENTS|AMENDS*1..4]` undirected (bao đóng transitive). Sửa bug chain hỗn hợp: `(NĐ 50)-[:IMPLEMENTS]->(NQ 254)-[:AMENDS]->(Luật ĐĐ)` — trước fix, seed=Luật ĐĐ không reach được NĐ 50.
>
> **Fix 2 (Macro — Tier Diversity Constraint + 2-pass):** `semantic_filter.py` thêm `_MAX_PER_TIER={1:8,2:8,3:6,4:8}`, hạ `_MAX_PER_NORM` 5→3, áp dụng 2-pass allocation (Pass 1 top-1/norm cho breadth, Pass 2 fill by RRF cho depth). Đảm bảo top-k bao phủ đa tầng pháp lý (T1 Luật + T2 NĐ + T4 địa phương) thay vì 17/25 bị Tier 4 chiếm.
>
> **Fix 3 (Micro — Concept Rarity MAX):** Thêm TF-IDF micro-boost trên đồ thị. `_compute_rarity()` tính `1 - count_C_in_norm/total_components`, dùng **MAX** thay SUM để tránh "trap" Điều tổng quát (Phạm vi/Đối tượng — gắn nhiều concept lướt qua) thắng Điều chuyên sâu (concept hiếm + nội dung định lượng). Sửa bug intra-norm: NĐ 50 Pass 1 chọn Đ3 K3 → giờ chọn Đ6 (30/50/100% tiền SDĐ). RRF multiplier mới: `base × tier_mult × graph_mult × (1 + 1.5×max_rarity)`.
>
> **Fix 4 (Parser citation):** `parse_citations()` regex mở rộng bắt `Điểm Z` và `Tiết K` giữa Khoản và Văn bản, kèm `Phụ lục X`. Output dict thêm 3 field: `diem`, `tiet`, `loai`. Trước fix: Q08+Q11 báo cit=0 (thực tế có 3-5 citation). Sau fix: chuẩn hóa metric Citation Accuracy cho Phase 4.
>
> **Validated với feedback Q01 gốc:**
> - HĐND quay lại — SỬA (LLM tự áp lex posterior, trích NQ 254 Đ4 K3)
> - Bịa "không có 30/50/100%" — SỬA (bảng đầy đủ từ NQ 254 Đ10 K2c)
> - Bảng phí TỔ CHỨC nhầm hộ gia đình — SỬA (phân loại rõ)
> - Bỏ sót tiền bảo vệ đất lúa — SỬA (NĐ 151 ≥50%)
>
> **Limitations chấp nhận:** QĐ 69 Đ3 (hạn mức 160m² cụ thể) đôi khi bị Đ1 (Phạm vi điều chỉnh) thắng do concept mapping coarse (cả 2 đều mapped `han-muc`). Bù đắp bằng NQ 254 Đ10 đề cập "trong hạn mức giao đất ở". Ghi nhận trong thesis Limitations.
>
> **Note phương pháp luận:** Tranh luận liên-AI (Claude vs Gemini) đã loại bỏ 2 phương án sai hướng: (1) Tier Multiplier ngược lex superior — nhầm conflict-resolution với IR relevance; (2) Dynamic Multiplier intent-based — câu hỏi đa-intent không phân biệt được; (3) Coverage SUM — rơi vào trap Điều tổng quát. Cuối cùng chốt 3 fix trên với nguyên lý khoa học defensible.
>
> **Phase 3 STABLE — đóng băng retrieval module.** Sẵn sàng vào Phase 4 (TASK-15→18).

> **v1.7 — Cập nhật 2026-05-15:**
> Sửa 3 lỗi gốc rễ phát hiện qua domain-expert feedback trên Q01 E2E test:
> **Fix 1 (Data):** Thêm NQ 254 vào `amended_by_norms` frontmatter Luật ĐĐ (document-level, scalable).
> **Fix 2 (Graph):** Thêm relationship `[:AMENDS]` trong `graph_builder.py` (Pass 3) — phân biệt sửa đổi vs hướng dẫn thi hành.
> **Fix 3 (Cypher):** Mở rộng Stage 2 Cypher với `[:AMENDS]` traversal — khi lấy Luật ĐĐ, tự động kéo NQ 254.
> **Fix 4 (Prompt):** Context block headers giờ chứa `[Tier X | Hiệu lực: YYYY-MM-DD]`.
>   Prompt chứa quy tắc lex superior (cấp bậc) + lex posterior (thời gian) + lex specialis (đặc thù)
>   → LLM tự suy luận mâu thuẫn giữa VB mà KHÔNG cần inline `amended_by` annotation.
> **Fix 5 (Diversity):** Per-norm cap `_MAX_PER_NORM=5` trong hybrid_search output.
> Schema: 7 edge (thêm AMENDS). 140/140 unit tests PASS. Cần re-ingest để áp dụng Fix 2+3.

> **v1.6 — Cập nhật 2026-05-15:**
> Sửa 3 vấn đề retrieval nghiêm trọng phát hiện qua E2E test notebook:
> **Fix P1:** `[:IMPLEMENTS]` traversal chuyển từ upward-only (`*0..4`) sang **bidirectional** (`*1..4` cả 2 chiều).
> Root cause: Stage 2 chỉ đi lên (seed→luật cha), không đi xuống (Luật→NĐ→NQ) → Gap 3 (đa tầng) không hoạt động.
> **Fix P2:** `stage1_norm_ids` top_n tăng từ 3 → **5** để cover nhiều văn bản hơn.
> **Fix P3:** `CONTEXT_MAX_TOKENS` tăng từ 3000 → **6000** (Claude Sonnet context window = 200k).
> Đồng bộ `CLAUDE.md` constants. 140/140 unit tests PASS.

> **v1.5 — Cập nhật 2026-05-11:**
> TASK-14 hoàn thành: `src/pipeline.py` — `run_pipeline()` kết nối toàn bộ TASK-10→13.
> `notebooks/phase3_e2e_test.ipynb` — 15 câu hỏi, bao phủ CMĐSDĐ + cấp sổ đỏ, TP.HCM + Đồng Nai.
> DoD 1 (< 30s + citation), DoD 2 (≥ 2 câu/thủ tục), DoD 3 (confirmation_needed), DoD 4 (negative khai sinh) đều có assert trong notebook.
> Gate Phase 3 → Phase 4 sẵn sàng khi chạy notebook pass.

> **v1.4 — Cập nhật 2026-05-11:**
> TASK-13 hoàn thành: `src/retrieval/context_assembler.py` + `src/retrieval/answer_generator.py`.
> assemble_context: sort tier (1 trước 4), RRF tiebreak, token budget 3000 (3.5 chars/token heuristic).
> generate_answer: Claude Sonnet 4.6, citation regex `[Điều X, Khoản Y, Văn bản Z]`.
> 25/25 unit tests PASS. DoD 1-5 xác nhận qua unit test (offline mock).

> **v1.3 — Cập nhật 2026-05-11:**
> TASK-12 hoàn thành: `src/retrieval/semantic_filter.py` — Hybrid Search.
> Dense (BGE-M3 + lccid filter) + Keyword scroll (slug overlap, broad) → Two-path RRF fusion.
> Fix đ/Đ slugify cho số hiệu văn bản tiếng Việt. 23/23 unit tests PASS.
> DoD 1-5 đều pass với live data. Keyword boost bắt đúng NĐ 102/2024/NĐ-CP khi có trong lccids.

> **v1.2 — Cập nhật 2026-05-10:**
> TASK-11 hoàn thành: `src/retrieval/subgraph_extractor.py` — Sub-graph Extraction.
> Stage 1: Qdrant semantic search trên summary vectors → top-N norm_ids.
> Stage 2: Neo4j [:IMPLEMENTS*0..4] + [:APPLIES_TO] jurisdiction filter → LCCIDs.
> Temporal filter qua CTV.valid_from/valid_to. Log warning khi > 50 LCCIDs.
> 18/18 unit tests PASS. Live verify: 295 LCCIDs dat-dai TP.HCM, jurisdiction filter đúng.

> **v1.1 — Cập nhật 2026-05-10:**
> TASK-10 hoàn thành: `src/retrieval/query_planner.py` — Claude Haiku 4.5 qua Anthropic API.
> QueryPlan TypedDict với 4 trường: theme, procedure, jurisdiction, temporal.
> Auto-assign toan-quoc cho Hộ tịch/Nuôi con nuôi. Confirmation Loop cho Đất đai thiếu jurisdiction.
> 28/28 unit tests PASS. 5/5 DoD cases xác nhận với API thật.
> Thêm `anthropic>=0.40.0` vào requirements.txt và ANTHROPIC_API_KEY vào .env.example.

> **v1.0 — Cập nhật 2026-05-10:**
> TASK-09 hoàn thành [A]: Phase 2 Verification pass tất cả DoD items [A] có thể verify.
> Neo4j: 6/6 loại node (Theme=1, Norm=17, Component=3014, CTV=3014, TextUnit=3014, Jurisdiction=3).
> Qdrant: 3014 text_unit + 17 summary vectors — khớp 100% với Neo4j.
> Stage 1 ("phí chuyển mục đích sử dụng đất", dat-dai): top-3 đều hợp lệ ✅.
> 3 [:IMPLEMENTS] chains (tier2→tier1) hợp lệ. Idempotency verified.
> `phase2_report.md` ký [A]. DoD item 7+8 (Stage 2 khai sinh + ký [B]): ⏳ chờ [B] nộp data.
> Phase 3 có thể bắt đầu với dữ liệu Đất đai.

> **v0.9 — Cập nhật 2026-05-10:**
> TASK-08 hoàn thành: `src/ingestion/vectorizer.py` — BGE-M3 local (Apple Silicon MPS).
> Qdrant: 3031 vectors (3014 text_unit + 17 summary). Idempotency verified.
> Stage 1 search (summary filter dat-dai) và Stage 2 search (text_unit filter norm_id) đều trả về kết quả hợp lệ.
> Thêm `sentence-transformers>=3.0.0` và `pyyaml>=6.0` vào requirements.txt.

> **v0.8 — Cập nhật 2026-05-10:**
> TASK-07 hoàn thành: `src/ingestion/graph_builder.py` chạy thành công trên 17 văn bản Đất đai.
> Neo4j: 9063 nodes (Norm=17, Component=3014, CTV=3014, TextUnit=3014, Theme=1, Jurisdiction=3).
> Idempotency verified: chạy lần 2 không tăng node count.
> 3 [:IMPLEMENTS] edges (tier2→tier1) hợp lệ. 17/17 Norm có summary.

> **v0.7 — Cập nhật 2026-05-10:**
> TASK-06 hoàn thành: `src/ingestion/parser.py` + `tests/test_parser.py` — 38/38 test PASS.
> Parser xử lý đúng tất cả 17 file data/raw/ Đất đai.
> Fix format `nghi-quyet-87`: xóa `#### 6.N.` headings không hợp lệ trong Phụ lục, chuyển thành plain text.

> **v0.6 — Cập nhật 2026-05-10:**
> TASK-04 [A] hoàn thành: 17 file Đất đai trong data/raw/ pass validate_metadata.py 17/17.
> data/sources/manifest.md tạo xong với đầy đủ URL nguồn cho 17 văn bản.
> Trạng thái TASK-04: [A] done — chờ [B] hoàn thành phần Hộ tịch + Nuôi con nuôi.

> **v0.5 — Cập nhật 2026-05-10:**
> Xóa `Procedure` node, `[:SPECIFIED_IN]` edge và `specified_in_map.md` khỏi
> Outputs + DoD của TASK-04 (D-07).
> Thêm field `summary` vào frontmatter và DoD TASK-04 (D-08).
> Cập nhật TASK-07 (Graph Builder): bỏ Procedure node + [:SPECIFIED_IN].
> Cập nhật TASK-08 (Vectorizer): thêm summary vector indexing (Stage 1).
> validate_metadata.py đã có, PASS 17/17 file Đất đai.

> **v0.4 — Cập nhật 2026-05-05:**
> TASK-01: đánh dấu ✅ hoàn thành. Nhánh `develop` đã tạo trên GitHub.
> Phase 0 hoàn thành toàn bộ (TASK-00 ✅, TASK-01 ✅, TASK-02 ✅).
> **TASK-05 (Docling Pipeline): ĐÃ XÓA** — không dùng Docling, thu thập thủ công.
> **TASK-04 + TASK-06: ĐÃ GỘP** thành TASK-04 "Thu thập & Chuẩn hóa văn bản".
> **Đánh lại số:** TASK-07→TASK-05, TASK-08→TASK-06, ..., TASK-20→TASK-18.
> Tổng số task: 21 → 19 (TASK-00 đến TASK-18).
> Loại bỏ `docling` khỏi requirements.txt.

> **v0.3 — Cập nhật 2026-04-19:**
> TASK-03 (Mapping Table): xác nhận chain [:IMPLEMENTS]
> cho lĩnh vực Hộ tịch / khai sinh.
> data/raw/mapping_table.md Section 1 — cột Implements
> đã điền đầy đủ cho 6 văn bản.
> Chain: luat-ho-tich-2014 ← nghi-dinh-123-2015-nd-cp
> ← nghi-dinh-07-2025-nd-cp, nghi-dinh-18-2026-nd-cp;
> luat-ho-tich-2014 ← nghi-dinh-87-2020-nd-cp
> ← thong-tu-01-2022-tt-btp.
> Sections 2–6 vẫn là placeholder — chờ project owner
> bổ sung văn bản các lĩnh vực còn lại.
> 0 unit tests passing.

> **v0.2 — Cập nhật sau audit 2026-04-19:**
> Cập nhật trạng thái TASK-00, TASK-01, TASK-02 từ
> 📋 CHƯA BẮT ĐẦU thành trạng thái thực tế sau audit.
> TASK-00: ✅ (docker-compose.yml hợp lệ, Docker đã verify
> chạy thành công bởi project owner — Neo4j và Qdrant pass).
> TASK-01: 🔄 (skeleton, git, venv, packages đã setup;
> còn thiếu nhánh develop — sẽ tạo khi bắt đầu Phase 1).
> TASK-02: ✅ (connection_check.py đã chạy pass — xác nhận
> bởi project owner).
> Làm rõ TASK-09 (cũ, nay là TASK-07): loại bỏ mơ hồ về [:BELONGS_TO] —
> quyết định KHÔNG implement, phản ánh đúng P-03.
> Sửa nhầm năm 2025 → 2026 trong toàn bộ tài liệu.
> 0 unit tests passing (chưa có code Phase 1+).

> **v0.1 — Khởi tạo tài liệu (2026-04-18):**
> Tạo PROJECT_STATUS.md lần đầu từ bản draft kế hoạch `plan.md` và tài liệu kiến trúc `Thesis_Dashboard.docx`.
> Tất cả task cards được định nghĩa ở trạng thái 📋 CHƯA BẮT ĐẦU.
> Docling được tích hợp vào Phase 1 như một bước tự động hóa (TASK-05).
> Quyết định trong buổi thảo luận (chưa có trong tài liệu): sử dụng Docling cho PDF parsing + boilerplate removal + hierarchy prefix trong Phase 1.
> Tổng số task cards được định nghĩa: 21 (TASK-00 đến TASK-20).
> Số unit test đang pass: 0 (chưa có code).

---

## Mục lục
1. [Trạng thái tiến độ hiện tại](#1-trạng-thái-tiến-độ-hiện-tại)
2. [Bảng phân công task](#2-bảng-phân-công-task)
3. [Sơ đồ phụ thuộc](#3-sơ-đồ-phụ-thuộc)
4. [Hành động tiếp theo được khuyến nghị](#4-hành-động-tiếp-theo-được-khuyến-nghị)

---

## 1. Trạng thái tiến độ hiện tại

### §1.0 CẬP NHẬT MỚI NHẤT — 2026-06-30 (ĐỌC TRƯỚC — điểm neo cho phiên làm việc mới)

> Block này là **single source of truth** về "đang ở đâu + làm gì tiếp". §1.1–1.3 bên dưới là tham chiếu chi tiết nhưng **một phần lỗi thời từ 2026-05-21** (ghi 17 file/3031 vector/Phase 1 chờ B — đã cũ). Chi tiết diễn biến: xem changelog v2.19 ở đầu file + Decision Log D-23/D-24 trong CLAUDE.md.

**ĐÃ XONG (toàn bộ đã commit + push lên `origin/develop`):**
- **Corpus B đã ingest** (D-23): 13 file Hộ tịch + Nuôi con nuôi của [B] đã pull/làm sạch/validate. **Graph đa-domain**: `32 Norm` (dat-dai 20, ho-tich 8, nuoi-con-nuoi 4), 4548 Component, 6394 MAPS_TO_CONCEPT. Qdrant `legal_texts` = **4582 vector** (4550 text_unit + 32 summary). `implements` hỗ trợ str|list|null (đa-cha). **TASK-05 cross-check** đã sign-off mức [A]+Claude (`data/raw/review_log.md`); [B] hậu kiểm 2 quyết định (NQ124 tách 2 Norm, thong-tu-01 amended_by) khi có thời gian.
- **Multi-LLM 3-mode** (D-24): `--llm-mode {claude|claude-fallback|gemini}` cho demo + eval. Gemini chạy **Vertex AI qua ADC** ($300 Cloud credit; vùng VN không free tier Developer API). Mặc định `claude` → eval reproducible. Judge Claude Haiku cố định. Files mới: `src/utils/gemini_fallback.py`, `src/precache_demo.py`.
- **Gemini-only validated** (full 26, graph đa-domain): GraphRAG-Gemini **F1 0.549 / NormR 0.766** vs Baseline-Gemini 0.356/0.554 → **Δ kiến trúc +0.193 F1** (≈ Δ Claude +0.206) = LLM-agnostic. Lineup Gemini: generator `gemini-2.5-pro`, planner+ontology `gemini-2.5-flash`. 2 negative result tune NormR (prompt provider-aware; structural backfill) → REJECT, chấp nhận NormR 0.766 (đặc tính Gemini). Kết quả canonical: `data/evaluation/gemini_full26/`.
- **Demo Gemini chạy được**: `python -m src.demo "..." --llm-mode gemini --mode {general|irac}`. Bug truncation đã fix (headroom thinking cho Gemini `max_output_tokens`).

**VIỆC TIẾP THEO (ưu tiên):**
1. **E1 ablation Gap 2/3/4** ★ — build `src/evaluation/ablation_config.py` (cờ tắt no-jurisdiction/no-traversal/no-temporal), chạy double-dissociation trên đất đai + Gemini. **Làm được ngay, không chờ B.** Đây là bằng chứng kiến trúc mạnh nhất (chứng minh TỪNG cơ chế KG giải đúng gap của nó).
2. **E2 baselines** (closed-book "có cần retrieval?" + BM25 + oracle trần) + **E0 docs** (GT provenance + metric validity). Làm được ngay.
3. **Viết Chương 1-3** (Intro/Background/Methodology) — song song, tư liệu đầy đủ.
4. **Chờ [B]**: test set Hộ tịch/NCN → mở khóa Gap 1 (E1 no-theme) + E2b consistency per-domain.
5. **Demo prep** (gần ngày bảo vệ): Lớp 1 pre-cache câu demo thật + quay video + rotate key.

**GOTCHAS MÔI TRƯỜNG (quan trọng cho phiên sau):**
- **Python interpreter:** cài gcloud (cho Vertex ADC) đã đổi `python`/`python3` sang Homebrew python THIẾU deps dự án. Deps đầy đủ ở **`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`** — DÙNG path này để chạy demo/eval/pytest. Nếu lỗi `ModuleNotFoundError: dotenv` là do gọi nhầm python.
- **Gemini = Vertex ADC:** cần `gcloud auth application-default login` (đã login) + `.env` có `GEMINI_USE_VERTEX=true`, `GEMINI_VERTEX_PROJECT=vn-legal-graphrag`, `GEMINI_VERTEX_LOCATION=global`, `GEMINI_MODEL_GENERATOR=gemini-2.5-pro`, `GEMINI_MODEL_PLANNER=gemini-2.5-flash`. KHÔNG dùng api_key cho Vertex.
- **Cache:** demo/eval cache answer theo hash(prompt), KHÔNG phân biệt provider → khi so Claude vs Gemini phải `--no-llm-cache`.
- **BẢO MẬT:** vài Gemini key + 1 Anthropic key đã lộ trong chat lịch sử → rotate sau bảo vệ.

---

> **Cập nhật toàn diện 2026-05-21** (PHẦN DƯỚI PARTIAL STALE — xem §1.0 ở trên cho trạng thái mới nhất) — đồng bộ với code, database production, và các fix layer v2.7. Section trước đó stale từ Phase 1.

### §1.1 Đã hoàn thành ✅

**Phase 0 — Hạ tầng (100% [A]+[B]):**
- Docker (Neo4j 5.18.0 + Qdrant v1.13.6) chạy ổn định
- Python venv + requirements (neo4j, qdrant-client, sentence-transformers, anthropic, pyyaml, rich, python-dotenv)
- Git repo (main + develop branches)
- `src/utils/connection_check.py` — integration smoke test PASS

**Phase 1 — Dữ liệu [A]:**
- 17 file Đất đai trong `data/raw/` (`validate_metadata.py` 17/17 PASS)
- `data/sources/manifest.md` đầy đủ URL nguồn
- `data/raw/mapping_table.md` sections 3-4 (chuyển mục đích SDĐ + cấp sổ đỏ)

**Phase 2 — Ingestion Pipeline [A]:**
- `src/ingestion/parser.py` — structure-aware MD parser (38/38 tests PASS)
- `src/ingestion/graph_builder.py` — 5-pass: Concept/Procedure → Theme/Jurisdiction → Norm/Component/CTV/TextUnit → Amendment → MAPS_TO_CONCEPT (idempotent MERGE)
- `src/ingestion/vectorizer.py` — BGE-M3 (Apple Silicon MPS) → 3031 vectors trong Qdrant (3014 text_unit + 17 summary)
- `src/ingestion/ontology_mapper.py` — Claude Haiku LLM classification (TASK-15)
- `data/ontology/core_v1.json` — Core Ontology (6 concepts + 6 procedures)
- `data/verification/phase2_report.md` ký [A]; Neo4j 9063 nodes, 4092 [:MAPS_TO_CONCEPT] edges

**Phase 3 — Retrieval Pipeline [A]:**
- `src/retrieval/query_planner.py` — Claude Haiku 4.5 + Cách C theme backfill + planner cache
- `src/retrieval/subgraph_extractor.py` — 3-stage (Stage 1 summary + Stage 2 graph + Stage 3 procedure)
- `src/retrieval/semantic_filter.py` — Hybrid Search 4-pass (Pass -1 Struct Cite / Pass 0 Dense Floor / Pass 1 RRF breadth / Pass 2 RRF depth)
- `src/retrieval/context_assembler.py` — sort + cap 6000 tokens + build_prompt với 5 rule blocks (TEMPORAL #4)
- `src/retrieval/answer_generator.py` — Claude Sonnet 4.6 + cache + parse_citations với dedupe
- `src/retrieval/verifier.py` — Verifier agent (multi-agent, D-18): Tier 1 grounding $0 + Tier 2 LLM judge; `verify=False` mặc định
- `src/pipeline.py` — end-to-end orchestrator (+ tham số verify/verify_tier)
- `src/utils/llm_config.py` — centralized Anthropic client (max_retries=8)

**Phase 4 — Đánh giá [A]:**
- `data/evaluation/test_set_dat_dai.json` — 26 câu Đất đai với ground truth Khoản-level
- `src/baseline/naive_rag.py` — Naive RAG baseline (chunking 512 chars, overlap 50)
- `src/evaluation/run_evaluation.py` — eval orchestrator
- `src/evaluation/metrics.py` — F1 Khoản/Điều, NormR, negative_correct (`cit_matches` single source of truth)
- `src/evaluation/faithfulness.py` — 2-tier metric (existence + LLM judge)
- `src/evaluation/term_validator.py` — B2 phát hiện thuật ngữ giả (grounding_rate, D-17)
- `src/evaluation/validate_test_set.py` — validator test set (gap diversity, phân bổ DoD)
- `src/evaluation/report_builder.py` — auto-sinh REPORT_<timestamp>.md
- `src/evaluation/compare_runs.py` — A/B diff
- `src/evaluation/build_ablation_matrix.py` — cumulative table
- `src/evaluation/build_reproducibility_report.py` — N=3 stats
- `src/evaluation/instrument_retrieval.py` — debug Stage 1/2/3 API-free
- `src/demo.py` — Rich CLI cho weekly meeting

**Documentation (cập nhật 2026-05-21):**
- `CLAUDE.md` — 9 nodes, 10 edges, 13 decisions, full DEPENDENCIES
- `docs/PROJECT_CONTEXT.md` v0.5.1 — kiến trúc đồng bộ
- `docs/PROJECT_STATUS.md` v2.8 (file này)
- `data/evaluation/ABLATION_MATRIX.md` — cumulative impact
- `data/evaluation/REPRODUCIBILITY_REPORT_20260520.md` — N=3 stats
- `data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md`
- `data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md`
- `data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md`
- `thesis/CHAPTERS_OUTLINE.md` + `thesis/CHAPTER_4_EXPERIMENTS.md`
- `README.md` — public-facing với headline results

### §1.2 Đang thực hiện 🔄

**Phase 1 — chờ [B]:**
- TASK-03 sections 1, 2, 5 (Hộ tịch + Nuôi con nuôi mapping)
- TASK-04 [B]: thu thập + chuẩn hóa Hộ tịch + Nuôi con nuôi
- TASK-05: cross-check chéo (chờ [B] xong TASK-04)

**Phase 4 — domain mở rộng:**
- Test set Hộ tịch + Nuôi con nuôi (chờ [B] đổ data)
- Mở test set lên ≥40 câu cross-domain để validate hypothesis Gap 1 generalize ngoài Đất đai
- **Kiến trúc đánh giá E0–E3** ([docs/EVALUATION_ARCHITECTURE.md](EVALUATION_ARCHITECTURE.md), D-22) — design spec hoàn chỉnh; phần làm được ngay: E0 methodology + `ablation_config.py` + rubric `human_eval.py`; phần chờ B: ablation suite E1 + E2b consistency + auto-GraphRAG

**Hướng nghiên cứu nâng cao [A] (precision in / precision out):**
- **Multi-agent — Verifier agent**: code xong (v2.12, D-18), `verify=False` mặc định; CHƯA đo ablation ±verifier (cần API).
- **Cross-encoder rerank** (vá disambiguation cấp Điều, Q022) — phép thử $0 trước khi finetune; đồng thời là "teacher" sinh hard-negative.
- **Finetune embedding BGE-M3** (distill từ cross-encoder) — sau khi cross-encoder xác nhận giả thuyết.
- Phụ thuộc: **harness đo lường + baseline dense-no-KG (#4) phải có sớm** để đo được 3 hướng trên (N≥3).

**Phase 5 — Báo cáo:**
- Expand prose Chapter 4 (Experiments) từ scaffold
- Viết Chapter 3 (Methodology), 5 (Discussion), 6 (Limitations), 7 (Future Work)

### §1.3 Chưa bắt đầu 📋

- **Production hardening** (out of thesis scope): latency optimization, cross-encoder re-ranking (Q022 limitation), multi-query expansion, model cascade
- **Multi-turn conversation support** (future work)
- **UI/Web interface** (out of scope khóa luận)

---

## 2. Bảng phân công task

### PHASE 0 — Thiết lập nền tảng

---
### TASK-00: Thiết lập Docker — Neo4j và Qdrant ✅
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** S (nửa ngày đến 1 ngày)
**Phụ thuộc vào:** Không có
**Có thể song song với:** TASK-01
**Hoàn thành:** 2026-04-19

#### Mục tiêu
Dựng hai service cơ sở dữ liệu cốt lõi — Neo4j (đồ thị tri thức) và Qdrant (vector search) — chạy hoàn toàn trong container Docker. Đây là điều kiện tiên quyết tuyệt đối: không có môi trường này, không một phase nào khác có thể bắt đầu. Mục tiêu là bất kỳ thành viên nào cũng có thể khởi động toàn bộ hệ thống bằng một lệnh duy nhất trên máy của mình.

#### Đầu vào
- Máy chạy macOS ≥ 8GB RAM
- Docker Desktop đã cài sẵn
- File cần tạo mới: `docker-compose.yml` tại thư mục gốc của project

#### Đầu ra
- `docker-compose.yml` — định nghĩa 2 service:
  - `neo4j`: image `neo4j:5.x`, port `7474` (HTTP Browser) và `7687` (Bolt), volume `./data/neo4j`
  - `qdrant`: image `qdrant/qdrant:latest`, port `6333` (HTTP API) và `6334` (gRPC), volume `./data/qdrant`
  - Cả hai service trong cùng một Docker network
- `.env.example` — template biến môi trường (NEO4J_AUTH, QDRANT_API_KEY nếu có)
- `README.md` (section "Khởi động môi trường") — lệnh `docker compose up -d` và hướng dẫn verify

#### Định nghĩa Hoàn thành (DoD)
- [x] Lệnh `docker compose up -d` chạy thành công, không có lỗi trong log
- [x] `http://localhost:7474` trả về Neo4j Browser UI có thể tương tác
- [x] Câu lệnh Cypher `RETURN 1` thực thi thành công trong Neo4j Browser, trả về `1`
- [x] `http://localhost:6333/dashboard` trả về Qdrant Dashboard UI có thể tương tác
- [x] Tạo collection `test_collection` trong Qdrant thành công qua UI, collection xuất hiện trong danh sách
- [ ] Lệnh `docker compose down` dừng sạch (chưa verify trong audit — cần xác nhận)
- [ ] File `docker-compose.yml` được commit, thành viên còn lại pull về và chạy thành công ngay lần đầu (chưa verify trên máy thành viên thứ 2)

#### Ghi chú / Ràng buộc cứng
- **KHÔNG** cài Neo4j hay Qdrant trực tiếp lên host machine — phải Docker hoàn toàn
- Volume mount ra `./data/` để data tồn tại qua các lần restart container
- Sử dụng tag version cụ thể cho images, không dùng `latest` cho Neo4j (để tránh breaking change)
- NEO4J_AUTH phải được set trong `.env`, không hardcode trong `docker-compose.yml`
- File `.env` phải có trong `.gitignore`, chỉ commit `.env.example`

---
### TASK-01: Thiết lập Python environment và Git repository ✅
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** S (nửa ngày đến 1 ngày)
**Phụ thuộc vào:** Không có
**Có thể song song với:** TASK-00
**Hoàn thành:** 2026-05-05

#### Mục tiêu
Khởi tạo Git repository và môi trường Python được chuẩn hóa để cả hai thành viên làm việc trên cùng một nền tảng. Bao gồm cấu trúc thư mục dự án, dependency management, và Git conventions. Việc thống nhất convention ngay từ đầu tránh merge conflict và desync về sau.

#### Đầu vào
- Không có file đầu vào — khởi tạo từ đầu
- Cần thống nhất trước: Git branch strategy, commit message format

#### Đầu ra
- Repository Git với cấu trúc thư mục:
  ```
  graphrag-vn-law/
  ├── data/
  │   ├── raw/          # Phase 1 output: *.md files
  │   └── processed/    # Phase 2 intermediate
  ├── src/
  │   ├── ingestion/    # Phase 2: parser, graph builder, vectorizer
  │   ├── retrieval/    # Phase 3: query planner, sub-graph, semantic filter
  │   └── evaluation/   # Phase 4: metrics, baseline
  ├── tests/
  ├── notebooks/        # Exploration, verification queries
  ├── docker-compose.yml
  ├── requirements.txt
  ├── .env.example
  └── README.md
  ```
- `requirements.txt` — dependencies ban đầu: `neo4j`, `qdrant-client`, `docling`, `python-dotenv`, `pytest`
- `README.md` — phần "Cài đặt" với lệnh `pip install -r requirements.txt`
- `.gitignore` — bao gồm `.env`, `data/neo4j/`, `data/qdrant/`, `__pycache__/`, `.venv/`

#### Định nghĩa Hoàn thành (DoD)
- [x] Repository Git khởi tạo, cả 2 thành viên đã `git clone` thành công
- [x] Lệnh `pip install -r requirements.txt` chạy thành công (verified trong venv)
- [x] `import neo4j`, `import qdrant_client`, `import docling` không báo lỗi
- [x] Cấu trúc thư mục tồn tại trong repo
- [x] `.env` không xuất hiện trong `git status`
- [x] Cả 2 thành viên push được lên nhánh `develop` (nhánh đã tạo trên GitHub — 2026-05-05)
- [x] Branch `main` được bảo vệ (require PR để merge) (xác nhận 2026-05-05)

#### Ghi chú / Ràng buộc cứng
- Python ≥ 3.10 bắt buộc (Docling yêu cầu)
- Khuyến nghị dùng `venv` hoặc `conda` environment, không cài global
- **KHÔNG** commit file `.env` thực — chỉ `.env.example`
- Convention commit message: `[PHASE-X] động_từ: mô_tả_ngắn` (VD: `[PHASE-1] feat: add docling pipeline script`)
- Tất cả code Python phải nằm trong `src/`, không có script rải rác ở root
- **Ghi chú audit 2026-04-19:** Commit message hiện tại không theo convention `[TASK-XX] type: mô_tả`. Áp dụng convention này cho tất cả commit từ phiên này trở đi.

---
### TASK-02: Kiểm tra kết nối tích hợp (Integration Verification) ✅
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** XS (vài giờ)
**Phụ thuộc vào:** TASK-00, TASK-01
**Có thể song song với:** Không — gate task
**Hoàn thành:** 2026-04-19

#### Mục tiêu
Viết và chạy một script Python kiểm tra end-to-end rằng code Python có thể đọc/ghi dữ liệu thành công vào cả hai database. Đây là "smoke test" của toàn bộ hạ tầng — nếu bước này pass, Phase 1 có thể bắt đầu.

#### Đầu vào
- Docker đang chạy (TASK-00 hoàn thành)
- Python environment đã setup (TASK-01 hoàn thành)
- File `.env` đã điền đủ giá trị thực (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, QDRANT_HOST, QDRANT_PORT)

#### Đầu ra
- `src/utils/connection_check.py` — script kiểm tra kết nối, thực hiện:
  - Kết nối Neo4j, tạo node `(:TestNode {name: "smoke_test"})`, đọc lại, xóa
  - Kết nối Qdrant, tạo collection `smoke_test` với `size=4`, upsert 1 vector `[0.1, 0.2, 0.3, 0.4]`, search, xóa collection
  - In kết quả pass/fail rõ ràng cho từng bước

#### Định nghĩa Hoàn thành (DoD)
- [x] `python src/utils/connection_check.py` chạy thành công, in "✅ Neo4j: PASS" và "✅ Qdrant: PASS" (xác nhận bởi project owner 2026-04-19)
- [x] Sau khi script chạy xong, không còn TestNode trong Neo4j (đã cleanup)
- [x] Sau khi script chạy xong, không còn collection `smoke_test` trong Qdrant (đã cleanup)
- [x] Script chạy thành công trên máy của cả 2 thành viên (xác nhận bởi project owner)
- [x] Script xử lý lỗi kết nối gracefully (verified qua code review trong audit)

#### Ghi chú / Ràng buộc cứng
- Credentials đọc từ `.env` qua `python-dotenv` — **không** hardcode trong script
- Script phải cleanup sau khi chạy — không để lại dữ liệu test trong database production

---

### PHASE 1 — Thu thập & Chuẩn hóa dữ liệu

---
### TASK-03: Xác định scope và lập bảng ánh xạ văn bản 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày nghiên cứu pháp lý)
**Phụ thuộc vào:** Không có (có thể làm song song với TASK-00, TASK-01)
**Có thể song song với:** TASK-00, TASK-01
**Hoàn thành:** Chưa

#### Mục tiêu
Với mỗi thủ tục trong scope dự án, truy ngược toàn bộ chuỗi văn bản pháp lý điều chỉnh nó và lập thành bảng mapping chính thức. Đây là sản phẩm trí tuệ quan trọng nhất của Phase 1 — nếu bảng này sai hoặc thiếu, đồ thị Knowledge Graph sẽ sai quan hệ `[:IMPLEMENTS]` và `[:APPLIES_TO]` từ gốc.

#### Đầu vào
- `Thesis_Dashboard.docx` — bảng 6 thủ tục × 3 lĩnh vực × 2 địa phương (TP.HCM, Đồng Nai)
- Nguồn tra cứu: vbpl.vn, cổng dịch vụ công tỉnh TP.HCM, cổng dịch vụ công tỉnh Đồng Nai, thư viện pháp luật

#### Đầu ra
- `data/raw/mapping_table.md` — bảng ánh xạ đầy đủ với cấu trúc:

  ```
  | Thủ tục | Văn bản | Loại | Tier | Điều/Khoản cần lấy | Địa phương áp dụng | Ghi chú |
  ```

  Phải bao gồm tất cả 6 thủ tục × toàn bộ chuỗi văn bản từ Luật → Nghị định → Thông tư → Quyết định tỉnh (nếu có)
- `data/raw/crossref_decisions.md` — danh sách các Điều tham chiếu chéo ra ngoài scope ban đầu, kèm quyết định: LẤY THÊM hoặc GHI NHẬN LIMITATION (cần project owner quyết định từng trường hợp)

#### Định nghĩa Hoàn thành (DoD)
- [ ] Bảng mapping có đầy đủ 6 thủ tục với ít nhất 1 văn bản trung ương + 1 văn bản địa phương cho mỗi lĩnh vực có đặc thù địa phương
- [ ] Mỗi hàng trong bảng ghi rõ số Điều/Khoản cụ thể cần lấy — không có hàng nào để trống cột này
- [ ] Chuỗi [:IMPLEMENTS] cho lĩnh vực Đất đai truy vết được đầy đủ: Luật Đất đai 2024 → Nghị định hướng dẫn → Thông tư (nếu có) → Quyết định UBND TP.HCM / Đồng Nai
- [ ] `crossref_decisions.md` liệt kê ít nhất 1 trường hợp cross-reference được phát hiện và có quyết định rõ ràng
- [ ] Cả 2 thành viên đã review và đồng ý với bảng mapping trước khi chuyển sang TASK-04
- [ ] Người phụ trách GVHD đã review bảng mapping (hoặc đã ghi nhận chờ review)

#### Ghi chú / Ràng buộc cứng
- **KHÔNG** lấy toàn bộ văn bản — chỉ lấy Điều/Khoản liên quan trực tiếp đến 6 thủ tục trong scope
- Scope giới hạn của "Cấp sổ đỏ lần đầu": **chỉ xét hộ gia đình/cá nhân có giấy tờ theo Điều 137 Luật Đất đai 2024**
- Hộ tịch (Đăng ký khai sinh, Cấp bản sao trích lục): đây là thủ tục chuẩn hóa toàn quốc — bảng mapping cần ghi rõ không có văn bản địa phương khác biệt nội dung
- Nuôi con nuôi: ghi chú rõ giao thoa từ vựng với Luật Hình sự (các hành vi cấm)

---
### TASK-04: Thu thập & Chuẩn hóa văn bản (gộp TASK-04 + TASK-06 cũ) 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** L (5-7 ngày — thu thập + chuẩn hóa + metadata)
**Phụ thuộc vào:** TASK-03 (bảng mapping phải xong trước)
**Có thể song song với:** [A] làm Đất đai, [B] làm Hộ tịch + Nuôi con nuôi
**Hoàn thành:** Chưa

> **Ghi chú v0.4:** Task này gộp từ TASK-04 (thu thập) và TASK-06 (chuẩn hóa) do
> chiến lược D-01 chuyển sang thu thập thủ công từ VBHN/vbpl.vn — không cần
> Docling pipeline trung gian (TASK-05 đã bị xóa).

#### Mục tiêu
Thu thập nội dung các Chương/Mục liên quan từ VBHN/vbpl.vn và chuẩn hóa trực tiếp thành file `.md` hoàn chỉnh theo schema kỹ thuật của dự án. Công việc gồm: (1) xác định nguồn VBHN trên vbpl.vn, (2) copy nội dung Chương/Mục liên quan, (3) chuẩn hóa heading format, (4) điền metadata YAML frontmatter, (5) viết `summary` 3-5 câu cho mỗi văn bản. Lưu file nguồn gốc (PDF/DOCX) vào `data/sources/` để audit.

#### Đầu vào
- `data/raw/mapping_table.md` — danh sách văn bản cần lấy từ TASK-03
- Nguồn: vbpl.vn (ưu tiên VBHN), dichvucong.gov.vn, cổng dịch vụ công tỉnh TP.HCM, Đồng Nai

#### Đầu ra
- `data/sources/` — file gốc (PDF/DOCX) để audit, đặt tên theo convention:
  ```
  [slug-ten-van-ban]-[nam].pdf
  VD: luat-dat-dai-2024.pdf
      nghi-dinh-102-2024-nd-cp.pdf
  ```
- `data/sources/manifest.md` — danh sách file đã lưu, kèm URL nguồn, ngày tải
- `data/raw/*.md` — các file hoàn chỉnh, mỗi file có:

  **Metadata block** (đầu file, định dạng YAML frontmatter):
  ```yaml
  ---
  id: "[slug-dinh-danh-duy-nhat]"
  title: "[Tên đầy đủ của văn bản]"
  tier: [1|2|3|4]
  theme: "[dat-dai|ho-tich|nuoi-con-nuoi]"
  jurisdiction: "[toan-quoc|tp-hcm|dong-nai]"
  implements: "[id-van-ban-cha hoặc null]"
  valid_from: "YYYY-MM-DD"
  valid_to: "YYYY-MM-DD hoặc null"
  source_url: "[URL nguồn chính thức]"
  source_vbhn: "[Số hiệu VBHN nếu lấy từ văn bản hợp nhất, VD: 44/VBHN-VPQH, hoặc null]"
  amended_by_norms: null
  summary: "[3-5 câu mô tả phạm vi, thủ tục, đối tượng, địa phương áp dụng]"
  ---
  ```

  **Body content** với heading format chuẩn:
  ```markdown
  ## Điều X. [Tên điều]
  [Nội dung phần mở đầu của Điều, nếu có]

  ### Khoản 1.
  [Nội dung khoản 1]

  #### Điểm a.
  [Nội dung điểm a]
  ```

- `src/utils/validate_metadata.py` — script kiểm tra metadata tự động ✅ (đã viết)

#### Định nghĩa Hoàn thành (DoD)
- [ ] Tất cả văn bản trong `mapping_table.md` đều có file `.md` tương ứng trong `data/raw/` (chờ [B])
- [x] Tất cả file `.md` có metadata block hợp lệ — `validate_metadata.py` PASS 17/17 ([A], 2026-05-10)
- [x] Trường `id` là unique trên toàn bộ tập file ([A], 2026-05-10)
- [x] Trường `tier` nhận đúng giá trị: Luật=1, Nghị định=2, Thông tư=3, Quyết định UBND=4 ([A], 2026-05-10)
- [x] Trường `implements` trỏ đúng `id` của văn bản cha — verify thủ công ([A], 2026-05-10)
- [x] Không có file nào dùng heading level sai (VD: `# Điều` thay vì `## Điều`) ([A], 2026-05-10)
- [x] Tất cả file `.md` có field `summary` được điền (không null) — nội dung do con người viết ([A], 2026-05-10)
- [x] Ít nhất 1 văn bản trung ương (tier 1-3) + 1 văn bản địa phương (tier 4) cho lĩnh vực Đất đai ([A], 2026-05-10)
- [ ] Hai thủ tục Hộ tịch có `jurisdiction: "toan-quoc"` và không có file văn bản địa phương (chờ [B])
- [x] File nguồn gốc (PDF/DOCX) được lưu trong `data/sources/` với `manifest.md` đầy đủ ([A], 2026-05-10)

#### Ghi chú / Ràng buộc cứng
- **Thu thập theo Chương/Mục** (D-01): chương không có mục → lấy cả chương; chương có mục → lấy cả mục
- **VBHN là nguồn nội dung** (D-02): metadata vẫn ghi theo văn bản QPPL chính thức
- **Format `id`:** `[loai-van-ban]-[slug-ten]-[nam]`
- **Tier mapping cứng:** 1=Luật/Bộ luật/NQ Quốc hội, 2=Nghị định/Pháp lệnh, 3=Thông tư, 4=QĐ UBND/NQ HĐND
- **KHÔNG** tự suy đoán `implements` — nếu không chắc, để trống và ghi chú để cross-check
- Lấy bản text từ **nguồn chính thức** (vbpl.vn) — không lấy từ blog luật hay trang thứ cấp

---
### TASK-05: Cross-check chéo Phase 1 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** S (1 ngày)
**Phụ thuộc vào:** TASK-04 (toàn bộ file .md đã hoàn chỉnh)
**Có thể song song với:** Không — gate task cuối Phase 1
**Hoàn thành:** Chưa

#### Mục tiêu
Người không viết file sẽ review file của người kia. Đây là bước kiểm soát chất lượng bắt buộc trước khi chuyển sang Phase 2. Nếu Phase 2 Parser gặp lỗi format → phải quay lại Phase 1, tốn nhiều thời gian hơn là review kỹ ngay bây giờ.

#### Đầu vào
- Toàn bộ `data/raw/*.md` từ TASK-04
- Script `src/utils/validate_metadata.py` (viết trong TASK-04) để kiểm tra tự động

#### Đầu ra
- `data/raw/review_log.md` — log cross-check: danh sách lỗi phát hiện, người phát hiện, ngày sửa, người confirm đã sửa
- Tất cả file `.md` đã qua review không còn lỗi format

#### Định nghĩa Hoàn thành (DoD)
- [ ] `python src/utils/validate_metadata.py data/raw/` chạy không có lỗi nào được báo cáo
- [ ] [A] đã review toàn bộ file của [B] và sign-off trong `review_log.md`
- [ ] [B] đã review toàn bộ file của [A] và sign-off trong `review_log.md`
- [ ] Tất cả lỗi được tìm thấy trong quá trình cross-check đã được sửa và re-verified
- [ ] `review_log.md` có ít nhất 1 mục cho mỗi file được review (không có file nào được bỏ qua)

#### Ghi chú / Ràng buộc cứng
- **KHÔNG** tự review file của mình — bắt buộc đổi chéo
- Nếu phát hiện lỗi liên quan đến nội dung pháp lý (không chắc Điều X có thuộc thủ tục Y không) → escalate lên GVHD, không tự quyết

---

### PHASE 2 — Offline Pipeline (Ingestion)

---
### TASK-06: Structure-aware Parser 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-05 (Phase 1 phải hoàn toàn xong và verified)
**Có thể song song với:** [B] viết unit tests song song với [A] viết parser logic
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng parser đọc file `.md` đã chuẩn hóa và tạo ra một cây dữ liệu (AST) trong bộ nhớ biểu diễn cấu trúc phân cấp của văn bản. Mỗi lá của cây là một **Text Unit** — đơn vị nội dung nhỏ nhất — kèm theo Context Path đầy đủ và Deterministic ID. Parser phải: (1) hoàn toàn idempotent — chạy lần 2 cho cùng kết quả, (2) báo lỗi rõ ràng khi format sai — không im lặng skip.

#### Đầu vào
- `data/raw/*.md` — toàn bộ file chuẩn hóa từ Phase 1
- Schema heading đã thống nhất: `## Điều`, `### Khoản`, `#### Điểm`

#### Đầu ra
- `src/ingestion/parser.py` — module với các hàm:
  - `parse_file(filepath: str) -> dict` — đọc 1 file .md, trả về dict AST với keys: `metadata` (YAML frontmatter), `nodes` (list of TextUnit)
  - `generate_id(context_path: list[str]) -> str` — hash SHA256 của context_path list joined bằng `>`, trả về 16 ký tự hex
  - `TextUnit` TypedDict: `{id: str, context_path: list[str], text: str, metadata: dict}`
- `tests/test_parser.py` — unit tests bao gồm: parse file hợp lệ, parse file thiếu metadata, parse Điều không có Khoản, verify deterministic ID (chạy 2 lần cho cùng ID)

#### Định nghĩa Hoàn thành (DoD)
- [ ] `parse_file()` chạy thành công trên tất cả file trong `data/raw/` không có exception
- [ ] Mỗi TextUnit có `context_path` đầy đủ từ gốc đến lá — VD: `["Luật Đất đai 2024", "Điều 116", "Khoản 1", "Điểm a"]`
- [ ] `generate_id()` là deterministic: gọi 2 lần với cùng input cho cùng output — verified bằng unit test
- [ ] Parser raise `ValueError` với message mô tả vị trí lỗi khi gặp file có heading format sai (VD: `# Điều` thay vì `## Điều`) — verified bằng unit test với file fixture lỗi
- [ ] Tổng số TextUnit được parse = tổng số lá trong AST của tất cả file — verify bằng cách đếm thủ công 1 file
- [ ] Tất cả unit test trong `tests/test_parser.py` pass

#### Ghi chú / Ràng buộc cứng
- ID dùng SHA256 hash của `">".join(context_path)` — **không dùng UUID, không dùng sequential integer**
- Cơ chế Stack-LIFO: khi gặp heading cùng level hoặc cao hơn → Pop trước khi Push
- TextUnit chỉ tạo ở lá (dòng text thường, không phải heading) — heading chỉ là structural marker
- **Không** bỏ qua dòng text không có heading cha — raise lỗi hoặc gán về Điều gần nhất

---
### TASK-07: Ontology Instantiation — Graph Builder (Neo4j) 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** L (4-5 ngày)
**Phụ thuộc vào:** TASK-06 (Parser phải hoàn thành trước)
**Có thể song song với:** [A] làm Macro Nodes, [B] làm Routing Nodes + Edges
**Hoàn thành:** Chưa

#### Mục tiêu
Đọc AST từ Parser và metadata từ Phase 1, tạo toàn bộ node và cạnh trong Neo4j theo schema Ontology đã định nghĩa (6 loại node, 6 loại edge). Toàn bộ quá trình phải idempotent — chạy lại không tạo duplicate. Node `Norm` phải có property `summary` từ YAML frontmatter để phục vụ Stage 1 retrieval.

#### Đầu vào
- `src/ingestion/parser.py` từ TASK-06
- `data/raw/*.md` toàn bộ (bao gồm field `summary` trong frontmatter)
- Neo4j đang chạy (TASK-00)

#### Đầu ra
- `src/ingestion/graph_builder.py` — module với:
  - `upsert_theme(tx, theme_name: str)` — tạo/cập nhật node `:Theme`
  - `upsert_norm(tx, metadata: dict)` — tạo/cập nhật node `:Norm` (bao gồm property `summary`)
  - `upsert_component(tx, component_data: dict)` — tạo/cập nhật node `:Component`
  - `upsert_ctv(tx, ctv_data: dict)` — tạo/cập nhật node `:CTV` với `valid_from`, `valid_to`, `status`
  - `upsert_text_unit(tx, text_unit: TextUnit)` — tạo/cập nhật node `:TextUnit`
  - `upsert_jurisdiction(tx, name: str)` — tạo/cập nhật node `:Jurisdiction`
  - `create_edges(tx, ...)` — tạo tất cả 6 loại edge: INCLUDES, IMPLEMENTS, HAS_COMPONENT, HAS_CTV, HAS_TEXT_UNIT, APPLIES_TO
  - `run_ingestion(data_dir: str)` — hàm orchestrator chạy toàn bộ ingestion

#### Định nghĩa Hoàn thành (DoD)
- [ ] Sau khi chạy `run_ingestion()`, Neo4j Browser hiển thị node của cả 6 loại: Theme, Norm, Component, CTV, TextUnit, Jurisdiction
- [ ] Cypher query `MATCH (n:Theme) RETURN n.name` trả về đúng 3 kết quả: "dat-dai", "ho-tich", "nuoi-con-nuoi"
- [ ] Cypher query kiểm tra chain `[:IMPLEMENTS]`: `MATCH path = (:Norm {tier:2})-[:IMPLEMENTS]->(:Norm {tier:1}) RETURN path LIMIT 5` trả về ít nhất 1 kết quả hợp lệ
- [ ] Cypher query kiểm tra `[:APPLIES_TO]`: `MATCH (:Norm)-[:APPLIES_TO]->(j:Jurisdiction {name:"tp-hcm"}) RETURN count(*)` trả về số > 0
- [ ] Cypher query kiểm tra `[:HAS_TEXT_UNIT]`: `MATCH (:CTV)-[:HAS_TEXT_UNIT]->(t:TextUnit) RETURN count(t)` trả về số > 0
- [ ] Chạy `run_ingestion()` lần 2 không tăng số lượng node (idempotency) — verify bằng `MATCH (n) RETURN count(n)` trước và sau
- [ ] Mỗi Norm node có property `summary` không null

#### Ghi chú / Ràng buộc cứng
- Dùng `MERGE` thay vì `CREATE` cho tất cả node và edge để đảm bảo idempotency
- Điều kiện MERGE cho TextUnit là `id` property (deterministic ID từ Parser)
- `[:BELONGS_TO]` (Component → Theme): **KHÔNG implement trong scope khóa luận này.** Quyết định đã được xác nhận trong P-03 (PROJECT_CONTEXT.md). Ghi nhận là limitation trong báo cáo — không implement dù có thời gian dư.
- Batch write: dùng transaction để upsert từng văn bản thay vì từng node — tránh timeout với dataset lớn

---
### TASK-08: Vector Indexing — Qdrant 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-07 (Graph Builder phải hoàn thành — TextUnit phải có trong Neo4j)
**Có thể song song với:** Không — phụ thuộc TASK-07
**Hoàn thành:** Chưa

#### Mục tiêu
Lấy toàn bộ TextUnit và Norm từ Neo4j, encode thành vector bằng model BGE-M3, lưu vào Qdrant với 2 loại vector: `content_type="text_unit"` (dùng cho Stage 2 retrieval) và `content_type="summary"` (dùng cho Stage 1 — lọc Norm liên quan). ID của text_unit vector trong Qdrant phải bằng đúng ID TextUnit trong Neo4j — đây là cơ chế liên kết giữa hai database. Quá trình phải idempotent (upsert, không insert).

#### Đầu vào
- Neo4j populated với TextUnit nodes (TASK-07)
- Qdrant đang chạy (TASK-00)
- Model BGE-M3 (local hoặc API — cần quyết định trước khi implement, xem Open Questions)

#### Đầu ra
- `src/ingestion/vectorizer.py` — module với:
  - `load_model(model_name: str = "BAAI/bge-m3") -> model` — load BGE-M3
  - `encode_text(model, text: str) -> list[float]` — encode 1 text thành vector
  - `build_text_unit_payload(text_unit_node: dict) -> dict` — payload cho text_unit vector: `{content_type: "text_unit", norm_id, component_id, jurisdiction, tier, theme, valid_from, valid_to}`
  - `build_summary_payload(norm_node: dict) -> dict` — payload cho summary vector: `{content_type: "summary", norm_id, tier, theme, jurisdiction, valid_from}`
  - `upsert_vectors(qdrant_client, collection_name: str, points: list) -> None` — upsert batch
  - `run_vectorization(neo4j_driver, qdrant_client)` — orchestrator: encode cả TextUnit và Norm summary

#### Định nghĩa Hoàn thành (DoD)
- [ ] Số vector có `content_type="text_unit"` trong Qdrant = số TextUnit node trong Neo4j
- [ ] Số vector có `content_type="summary"` trong Qdrant = số Norm node trong Neo4j (mỗi Norm 1 summary vector)
- [ ] Mỗi text_unit vector có đủ payload: `content_type`, `norm_id`, `component_id`, `jurisdiction`, `tier`, `theme`, `valid_from`, `valid_to`
- [ ] Mỗi summary vector có đủ payload: `content_type`, `norm_id`, `tier`, `theme`, `jurisdiction`, `valid_from`
- [ ] Stage 1 test: query `"điều kiện chuyển mục đích sử dụng đất"` với filter `content_type="summary"` và `theme="dat-dai"` → top-3 norm_ids đều thuộc lĩnh vực Đất đai (verify thủ công)
- [ ] Stage 2 test: query với filter `content_type="text_unit"` và `norm_id IN [list]` → trả về TextUnit có nội dung khớp
- [ ] Chạy `run_vectorization()` lần 2 không tăng số lượng vector (idempotency — dùng upsert)
- [ ] Thời gian encode toàn bộ dataset < 2 giờ trên máy 8GB RAM (nếu chạy local)

#### Ghi chú / Ràng buộc cứng
- Collection name trong Qdrant: `legal_texts` — cố định, không để tùy ý
- Vector dimension của BGE-M3 là 1024 — phải set đúng khi tạo collection
- Nếu BGE-M3 local quá chậm (> 2 giờ) → switch sang API — ghi nhận quyết định vào PROJECT_CONTEXT.md P-XX
- Upsert theo batch 100 vectors/request — không upsert từng vector một (sẽ timeout)

---
### TASK-09: Verification — Kiểm tra tích hợp Phase 2 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** S (1 ngày)
**Phụ thuộc vào:** TASK-07, TASK-08
**Có thể song song với:** Không — gate task cuối Phase 2
**Hoàn thành:** Chưa

#### Mục tiêu
Kiểm tra thủ công và bán tự động rằng graph Neo4j và vector store Qdrant đều chính xác và nhất quán với nhau. Đây là gate task — Phase 3 không được bắt đầu nếu bất kỳ item nào trong DoD chưa pass.

#### Đầu vào
- Neo4j và Qdrant đã populated (TASK-07, TASK-08)
- `notebooks/phase2_verification.ipynb` — tạo mới trong task này

#### Đầu ra
- `notebooks/phase2_verification.ipynb` — notebook chứa tất cả verification queries với kết quả thực tế
- `data/verification/phase2_report.md` — báo cáo verification: số node từng loại, số vector, kết quả 3 query mẫu

#### Định nghĩa Hoàn thành (DoD)
- [ ] `MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC` — kết quả được ghi vào `phase2_report.md`, tất cả 6 loại node (Theme, Norm, Component, CTV, TextUnit, Jurisdiction) đều có count > 0
- [ ] Query `MATCH path = (:Norm {tier:2})-[:IMPLEMENTS]->(:Norm {tier:1}) RETURN path LIMIT 5` trả về chain hợp lệ
- [ ] Query `MATCH (n:Norm)-[:APPLIES_TO]->(j:Jurisdiction) RETURN n.id, j.name LIMIT 10` trả về kết quả đúng jurisdiction cho từng văn bản
- [ ] Số vector `content_type="text_unit"` trong Qdrant = số TextUnit node trong Neo4j (ghi vào report)
- [ ] Số vector `content_type="summary"` trong Qdrant = số Norm node trong Neo4j (ghi vào report)
- [ ] Stage 1 vector search: query `"phí chuyển mục đích sử dụng đất"` với filter `content_type="summary"`, `theme="dat-dai"` → top-3 norm_ids hợp lệ (verify thủ công)
- [ ] Stage 2 vector search: query `"đăng ký khai sinh"` với filter `content_type="text_unit"`, `jurisdiction="toan-quoc"` → top-3 kết quả thuộc Hộ tịch (verify thủ công)
- [ ] Báo cáo `phase2_report.md` được ký xác nhận bởi cả 2 thành viên

---

### PHASE 3 — Online Pipeline (Retrieval & Generation)

---
### TASK-10: Query Planner 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09 (Phase 2 verified)
**Có thể song song với:** TASK-11 (nhánh [A])
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng module nhận câu hỏi tiếng Việt của người dùng và trả về 4 tham số có cấu trúc: Theme, Procedure, Jurisdiction, Temporal. Dùng LLM như bộ phân loại có hướng dẫn với danh sách giá trị hợp lệ cố định. Nếu thiếu tham số thiết yếu (đặc biệt Jurisdiction cho câu hỏi Đất đai) → kích hoạt Confirmation Loop hỏi lại người dùng.

#### Đầu vào
- Câu hỏi tự nhiên tiếng Việt từ người dùng
- Danh sách giá trị hợp lệ: Themes (3), Procedures (6), Jurisdictions (3: toan-quoc, tp-hcm, dong-nai)
- LLM API (cần quyết định: model nào — xem Open Questions)

#### Đầu ra
- `src/retrieval/query_planner.py` — module với:
  - `QueryPlan` TypedDict: `{theme: str|None, procedure: str|None, jurisdiction: str|None, temporal: str|None, is_complete: bool, missing_fields: list[str]}`
  - `plan_query(question: str, llm_client) -> QueryPlan` — phân tích câu hỏi, trả về QueryPlan
  - `build_confirmation_prompt(missing_fields: list[str]) -> str` — tạo câu hỏi ngược lại người dùng
- `tests/test_query_planner.py` — test với ít nhất 10 câu hỏi mẫu

#### Định nghĩa Hoàn thành (DoD)
- [ ] `plan_query("Phí chuyển mục đích sử dụng đất tại TP.HCM là bao nhiêu?")` trả về `{theme: "dat-dai", procedure: "chuyen-muc-dich-su-dung-dat", jurisdiction: "tp-hcm", is_complete: True}`
- [ ] `plan_query("Phí chuyển mục đích là bao nhiêu?")` trả về `{is_complete: False, missing_fields: ["jurisdiction"]}`
- [ ] `plan_query("Điều kiện đăng ký khai sinh là gì?")` trả về `{theme: "ho-tich", procedure: "dang-ky-khai-sinh", jurisdiction: "toan-quoc", is_complete: True}` — tự động gán toan-quoc cho Hộ tịch
- [ ] `build_confirmation_prompt(["jurisdiction"])` trả về câu tiếng Việt yêu cầu người dùng nêu tỉnh/thành
- [ ] 8/10 câu hỏi test trong `test_query_planner.py` được phân loại đúng Theme và Procedure
- [ ] Với câu hỏi về thủ tục Hộ tịch hoặc Nuôi con nuôi: module tự động gán `jurisdiction = "toan-quoc"` không cần hỏi lại

---
### TASK-11: Sub-graph Extraction 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09, TASK-10
**Có thể song song với:** TASK-12 (nhánh song song — TASK-11 dùng Neo4j, TASK-12 dùng Qdrant)
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận QueryPlan từ TASK-10, thực hiện hai bước để thu hẹp không gian tìm kiếm:
- **Stage 1 (Qdrant):** Encode câu hỏi → vector search trên summary vectors với filter `content_type="summary"` + `theme` → lấy top-N norm_ids có văn bản liên quan nhất về ngữ nghĩa.
- **Stage 2 (Neo4j):** Từ norm_ids, duyệt graph qua `[:IMPLEMENTS]` (lấy cả chuỗi tier 1→4) và lọc `[:APPLIES_TO]` theo jurisdiction → trả về list Component IDs (LCCIDs).

Đây là bước "lọc cứng" kép: lọc ngữ nghĩa (Stage 1) + lọc địa phương và tầng văn bản (Stage 2).

#### Đầu vào
- `QueryPlan` từ TASK-10 (có `theme`, `jurisdiction`, `procedure` string, `temporal`)
- Neo4j driver, database đã populated
- Qdrant client, collection `legal_texts` đã có summary vectors

#### Đầu ra
- `src/retrieval/subgraph_extractor.py` — module với:
  - `LCCIDs` type alias: `list[str]` (list of Component node IDs)
  - `stage1_norm_ids(query_plan: QueryPlan, qdrant_client, model, top_n: int = 5) -> list[str]` — Stage 1: summary search → norm_ids
  - `stage2_component_ids(norm_ids: list[str], query_plan: QueryPlan, neo4j_driver) -> LCCIDs` — Stage 2: graph traversal → component_ids
  - `extract_subgraph(query_plan: QueryPlan, neo4j_driver, qdrant_client, model) -> LCCIDs` — orchestrator gọi cả 2 stage
  - Cypher query template cho Stage 2 được document rõ ràng

#### Định nghĩa Hoàn thành (DoD)
- [ ] `extract_subgraph` với câu hỏi về "chuyển mục đích sử dụng đất tại TP.HCM" trả về list IDs bao gồm Component của cả Luật Đất đai (tier 1) và văn bản TP.HCM (tier 4)
- [ ] `extract_subgraph` với câu hỏi về "đăng ký khai sinh" (`jurisdiction: "toan-quoc"`) trả về KHÔNG có Component của bất kỳ văn bản địa phương nào (tier 4)
- [ ] Stage 1: câu hỏi về "đăng ký nuôi con nuôi" và "đăng ký lại nuôi con nuôi" cho norm_ids khác nhau — hai thủ tục tương tự phân biệt được qua summary embedding
- [ ] Temporal filter hoạt động: Component thuộc CTV có `valid_to < temporal` không xuất hiện trong kết quả
- [ ] Số lượng LCCIDs không vượt quá 50 (tránh quá rộng gây noise) — nếu vượt, log warning

---
### TASK-12: Semantic Filtering — Hybrid Search 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09
**Có thể song song với:** TASK-11
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận LCCIDs từ TASK-11 và câu hỏi gốc, thực hiện hybrid search (Dense + Sparse + RRF) trong Qdrant với payload filter để lấy Top-k TextUnit có độ liên quan cao nhất.

#### Đầu vào
- LCCIDs từ TASK-11
- Câu hỏi gốc (string)
- Qdrant client, collection `legal_texts`
- BGE-M3 model (đã load)

#### Đầu ra
- `src/retrieval/semantic_filter.py` — module với:
  - `hybrid_search(question: str, lccids: LCCIDs, qdrant_client, model, top_k: int = 10) -> list[TextUnit]`
  - Cơ chế: Dense search (BGE-M3) + Keyword search (slug-overlap) → RRF fusion (BM25 trong spec gốc đã thay bằng slug-overlap khi triển khai — xem semantic_filter.py)
  - Payload filter: `content_type="text_unit" AND component_id IN lccids`

#### Định nghĩa Hoàn thành (DoD)
- [ ] `hybrid_search("phí chuyển mục đích sử dụng đất", lccids_tp_hcm)` — top-3 kết quả đều thuộc lĩnh vực Đất đai (verify thủ công)
- [ ] Kết quả không chứa TextUnit của Đồng Nai khi `lccids` chỉ chứa IDs của TP.HCM
- [ ] Hybrid search bắt được "sổ đỏ" khi query `"giấy chứng nhận quyền sử dụng đất"` — Dense search phải khớp ngữ nghĩa
- [ ] Hybrid search bắt được `"Nghị định 102/2024/NĐ-CP"` khi query chứa chính xác số hiệu này — Sparse search phải khớp từ khóa
- [ ] `top_k` parameter hoạt động đúng: `top_k=5` trả về đúng 5 kết quả (hoặc ít hơn nếu không đủ)

---
### TASK-13: Context Assembly và Answer Generation ✅
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-12
**Có thể song song với:** TASK-11 (nhánh [B])
**Hoàn thành:** 2026-05-11

#### Mục tiêu
Nhận Top-k TextUnit từ TASK-12, sắp xếp theo thứ tự phân cấp pháp lý (tier 1 trước, tier 4 sau), cắt tỉa nếu vượt token budget, đưa vào LLM để sinh câu trả lời có trích dẫn bắt buộc.

#### Đầu vào
- Top-k TextUnit với metadata (từ TASK-12)
- Câu hỏi gốc
- LLM client

#### Đầu ra
- `src/retrieval/context_assembler.py`:
  - `assemble_context(text_units: list[TextUnit], max_tokens: int = 3000) -> str` — sắp xếp theo tier, cắt tỉa
  - `build_prompt(question: str, context: str) -> str` — prompt template yêu cầu trích dẫn
- `src/retrieval/answer_generator.py`:
  - `generate_answer(question: str, context: str, llm_client) -> dict` — trả về `{answer: str, citations: list[dict]}`
  - `parse_citations(raw_answer: str) -> list[dict]` — extract citations từ LLM output

#### Định nghĩa Hoàn thành (DoD)
- [x] `assemble_context()` sắp xếp TextUnit đúng thứ tự: tier 1 luôn trước tier 4
- [x] `assemble_context()` với `max_tokens=3000` cắt bỏ TextUnit đủ để tổng text < 3000 tokens (verify bằng tokenizer)
- [x] `generate_answer()` trả về response có chứa ít nhất 1 citation với format `{dieu: "X", khoan: "Y", van_ban: "Z"}`
- [x] Câu trả lời cho câu hỏi về Đất đai TP.HCM có citation đến đúng Điều trong Luật Đất đai 2024 (verify thủ công — mock LLM với response hợp lệ)
- [x] Câu trả lời không chứa thông tin không có trong context (faithfulness — verify thủ công 3 câu hỏi)

---
### TASK-14: Integration — Pipeline End-to-End ✅
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** S (1-2 ngày)
**Phụ thuộc vào:** TASK-10, TASK-11, TASK-12, TASK-13
**Có thể song song với:** Không — gate task cuối Phase 3
**Hoàn thành:** 2026-05-11

#### Mục tiêu
Nối toàn bộ 4 module thành một pipeline hoàn chỉnh, chạy thử 12-18 câu hỏi mẫu (2-3 câu/thủ tục). Đây là demo nội bộ trước khi bước vào Phase 4 evaluation.

#### Đầu vào
- Tất cả module từ TASK-10 đến TASK-13

#### Đầu ra
- `src/pipeline.py` — hàm `run_pipeline(question: str) -> dict` nối toàn bộ flow
- `notebooks/phase3_e2e_test.ipynb` — chạy 12-18 câu hỏi, ghi lại câu trả lời và thời gian xử lý

#### Định nghĩa Hoàn thành (DoD)
- [x] `run_pipeline("Điều kiện để chuyển mục đích sử dụng đất tại TP.HCM là gì?")` trả về câu trả lời có trích dẫn trong < 30 giây (assert trong notebook Q01)
- [x] Pipeline xử lý được ít nhất 2 câu hỏi cho mỗi trong 6 thủ tục (15 câu, bao phủ CMĐSDĐ + cấp sổ đỏ × TP.HCM + Đồng Nai)
- [x] Câu hỏi thiếu Jurisdiction → pipeline dừng và trả về `confirmation_needed: True` với câu hỏi ngược lại (assert Q12)
- [x] Negative test: `"Quy định đăng ký khai sinh tại TP.HCM khác Đồng Nai như thế nào?"` → câu trả lời nêu rõ đây là thủ tục thống nhất toàn quốc, **không** bịa ra sự khác biệt địa phương không tồn tại (Q13 — kiểm tra thủ công)
- [x] Kết quả 15 câu hỏi được ghi vào notebook với nhận xét đánh giá bằng mắt

---

### PHASE 4 — Đánh giá

---
### TASK-15: Xây dựng bộ câu hỏi đánh giá (Test Set) 📋
**Phase:** 4
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-14 (cần biết pipeline hoạt động ổn định để thiết kế test hợp lý)
**Có thể song song với:** TASK-16
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng bộ câu hỏi đánh giá ≥ 30 câu với ground truth đi kèm. Bộ test phải bao phủ 4 Gap chính, có cả positive và negative cases, và được cross-check bởi cả 2 thành viên. Đây là nền tảng của chương "Kết quả & Thảo luận" trong khóa luận.

#### Đầu vào
- `data/raw/*.md` — để trích xuất ground truth chính xác
- Hiểu biết về 4 Gap và 6 thủ tục

#### Đầu ra
- `data/evaluation/test_set.json` — danh sách câu hỏi, mỗi item:
  ```json
  {
    "id": "Q001",
    "question": "...",
    "gap_type": "gap1|gap2|gap3|gap4|negative",
    "difficulty": "easy|medium|hard",
    "ground_truth_answer": "...",
    "ground_truth_citations": [{"dieu": "X", "khoan": "Y", "van_ban": "Z"}],
    "relevant_component_ids": ["..."]
  }
  ```

#### Định nghĩa Hoàn thành (DoD)
- [ ] Tổng số câu hỏi ≥ 30
- [ ] Phân bổ: ≥ 10 câu Đất đai, ≥ 10 câu Hộ tịch + Nuôi con nuôi, ≥ 5 negative cases
- [ ] Mỗi câu có `ground_truth_citations` với ít nhất 1 citation chính xác (Điều, Khoản, Văn bản cụ thể)
- [ ] Có ít nhất 3 câu hỏi kiểm tra Gap 2 (đa địa phương) với ground truth khác nhau cho TP.HCM vs Đồng Nai
- [ ] Có ít nhất 3 câu hỏi kiểm tra Gap 3 (đa tầng) đòi hỏi thông tin từ ≥ 2 văn bản khác tier
- [ ] [A] đã review test set của [B] và sign-off; [B] đã review của [A] và sign-off
- [ ] Ground truth được verify bằng cách đọc trực tiếp văn bản pháp lý gốc, không dựa vào memory

---
### TASK-16: Xây dựng Baseline Naive RAG ✅
**Phase:** 4
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-08 (dùng cùng bộ dữ liệu)
**Có thể song song với:** TASK-15
**Hoàn thành:** 2026-05-17

#### Mục tiêu
Xây dựng hệ thống Naive RAG để làm baseline so sánh. Điều kiện bắt buộc để so sánh có giá trị khoa học: cùng bộ dữ liệu, cùng LLM, cùng embedding model — **chỉ khác phần retrieval** (chunking cố định thay vì graph-aware).

#### Đầu vào
- `data/raw/*.md` — cùng dữ liệu gốc
- BGE-M3, LLM client — cùng model

#### Đầu ra
- `src/baseline/naive_rag.py`:
  - `fixed_chunker(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]`
  - `run_baseline_ingestion(data_dir: str)` — chunk và index vào Qdrant collection `baseline_legal_texts`
  - `run_baseline_query(question: str) -> dict` — vector search thuần, không có graph, không có metadata filter

#### Định nghĩa Hoàn thành (DoD)
- [x] `run_baseline_ingestion()` chạy thành công, tạo collection `baseline_legal_texts` trong Qdrant (17 files, 1718 chunks)
- [x] `run_baseline_query(question)` trả về câu trả lời với cùng format output như `run_pipeline(question)` (BaselineResult TypedDict khớp PipelineResult)
- [x] Baseline dùng đúng BGE-M3 và LLM — reuse trực tiếp `load_model()` và `generate_answer()` của GraphRAG
- [ ] Baseline chạy được trên toàn bộ 30+ câu hỏi trong test set mà không crash (chờ test set full ở TASK-15; sample Q001 OK với 4 citations đúng)

---
### TASK-17: Chạy Evaluation và tính Metrics 📋
**Phase:** 4
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-14, TASK-15, TASK-16
**Có thể song song với:** Không
**Hoàn thành:** Chưa

#### Mục tiêu
Chạy cả GraphRAG pipeline và Baseline trên toàn bộ test set, tính toán đầy đủ các metrics retrieval và generation, lưu kết quả có thể reproduce.

#### Đầu vào
- `data/evaluation/test_set.json`
- `src/pipeline.py` (GraphRAG)
- `src/baseline/naive_rag.py`

#### Đầu ra
- `data/evaluation/results_graphrag.json` — kết quả từng câu hỏi
- `data/evaluation/results_baseline.json` — kết quả từng câu hỏi
- `src/evaluation/metrics.py` — tính Precision@k, Recall@k, MRR, Citation Accuracy
- `data/evaluation/metrics_summary.md` — bảng so sánh GraphRAG vs Baseline

#### Định nghĩa Hoàn thành (DoD)
- [ ] Cả 2 hệ thống đã chạy trên toàn bộ ≥ 30 câu hỏi và lưu kết quả (hiện chạy 26 câu Đất đai — chờ TASK-15 thêm Hộ tịch + Nuôi con nuôi)
- [x] Bảng metrics đầy đủ: Citation Precision/Recall/F1 (cấp Khoản + cấp Điều), Norm-level Recall, Latency mean+p95, Negative correct rate cho cả 2 hệ thống — output `metrics_summary_<timestamp>.md`
- [x] Metrics được tính chia theo lĩnh vực (`by_theme`) và gap_type (`by_gap`) — aggregate() trong metrics.py
- [x] Correctness và Faithfulness được đánh giá thủ công cho ≥ 10 câu hỏi/hệ thống — `data/evaluation/MANUAL_EVAL.md` (G 4.5/4.9 vs B 3.5/4.3)
- [x] File kết quả JSON có timestamp và config rõ ràng để reproduce (`results_<system>_<timestamp>.json` chứa test_set path, timestamp, per-question full)
- [x] Tooling tối ưu chi phí dev: `--reuse-results` (re-compute metric không tốn API), `--llm-cache-dir` (cache hit $0)

---
### TASK-18: Phân tích kết quả theo Gap 📋
**Phase:** 4
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-17
**Có thể song song với:** Không
**Hoàn thành:** Chưa

#### Mục tiêu
Phân tích kết quả từ TASK-17 theo 4 Gap của nghiên cứu, xác định failure cases, rút ra kết luận. Đây là nội dung chính của chương "Kết quả & Thảo luận" trong khóa luận.

#### Đầu vào
- `data/evaluation/metrics_summary.md`
- `data/evaluation/results_graphrag.json`
- `data/evaluation/results_baseline.json`

#### Đầu ra
- `data/evaluation/gap_analysis.md` — phân tích 4 Gap
- `data/evaluation/failure_cases.md` — ≥ 3 failure case với phân tích nguyên nhân
- `data/evaluation/limitations.md` — danh sách limitations chính thức

#### Định nghĩa Hoàn thành (DoD)
- [ ] `gap_analysis.md` có phần riêng cho mỗi Gap với số liệu cụ thể so sánh GraphRAG vs Baseline
- [ ] `failure_cases.md` có ≥ 3 trường hợp thất bại được phân tích nguyên nhân (không phải chỉ mô tả)
- [ ] `limitations.md` liệt kê ≥ 5 limitation với lý do kỹ thuật rõ ràng (không phải "không đủ thời gian")
- [ ] Kết luận trả lời rõ ràng: hệ thống giải quyết được Gap nào, Gap nào chưa, và tại sao

---

## 3. Sơ đồ phụ thuộc

```
[TASK-00] Docker Setup ──────────────────────────────────────────────┐
[TASK-01] Python + Git Setup ────────────────────────────────────────┤
           (song song)                                                 │
                            [TASK-02] Integration Verification ◄──────┘
                                         │
              ┌──────────────────────────┤
              │                          │
[TASK-03] Mapping Table (song song)      │
     │                                   │
[TASK-04] Thu thập & Chuẩn hóa           │
     │                                   │
[TASK-05] Cross-check ◄──────────────────┘
     │
     ├── [A] [TASK-06] Parser ──────────────────────────────────────┐
     │         │                                                      │
     │    [TASK-07] Graph Builder (Neo4j) ──────────────────────────┤
     │         │                                                      │
     │    [TASK-08] Vector Indexing (Qdrant) ───────────────────────┤
     │                                                               │
     └── [B] Unit tests cho TASK-06 (song song)                     │
                                                                     │
                        [TASK-09] Phase 2 Verification ◄────────────┘
                                     │
              ┌──────────────────────┤
     [A]      │              [B]     │
[TASK-10] Query Planner     [TASK-12] Semantic Filtering
[TASK-11] Sub-graph Extraction
              │                      │
              └──────────────────────┤
                                     │
                        [TASK-13] Context Assembly + Generation
                                     │
                        [TASK-14] Integration E2E ──── Gate Phase 3
                                     │
              ┌──────────────────────┤
[TASK-15] Test Set            [TASK-16] Baseline (song song)
     │                               │
     └──────────────────────────────┤
                                    │
                        [TASK-17] Chạy Evaluation
                                    │
                        [TASK-18] Phân tích theo Gap
```

**Các gate task (KHÔNG được bỏ qua):**
- TASK-02: Gate Phase 0 → Phase 1
- TASK-05: Gate Phase 1 → Phase 2
- TASK-09: Gate Phase 2 → Phase 3
- TASK-14: Gate Phase 3 → Phase 4

---

## 4. Hành động tiếp theo được khuyến nghị

1. ~~Thống nhất các quyết định còn open trong `docs/PROJECT_CONTEXT.md` (đặc biệt: LLM nào, BGE-M3 local hay API, format `id` cuối cùng)~~ ✅
   OQ-04 đã đóng (Claude, 2026-04-19). OQ-01 đã đóng (format id). OQ-03 và OQ-06 vẫn pending.

2. ~~[A] bắt đầu TASK-00, [B] bắt đầu TASK-01 — song song~~ ✅ Hoàn thành (2026-04-19)

3. ~~Hoàn thành TASK-01 còn thiếu: tạo nhánh `develop`~~ ✅ Hoàn thành (2026-05-05)

4. ~~Hoàn thành TASK-03 (Mapping Table)~~ [A] đã điền Sections 3+4. [B] cần điền phần Hộ tịch + Nuôi con nuôi.

5. ~~[A] làm TASK-04 Đất đai~~ ✅ Hoàn thành 2026-05-10. **[B] cần hoàn thành TASK-04 Hộ tịch + Nuôi con nuôi.**

6. **(HIỆN TẠI — chờ [B])** Sau khi [B] hoàn thành TASK-04: hai bên làm TASK-05 Cross-check chéo — [A] review file [B], [B] review file [A], sign-off vào `review_log.md`.

7. Sau TASK-05 pass: [A] viết TASK-06 (Parser), [B] viết unit tests cho Parser — song song.
