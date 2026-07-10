# CHƯƠNG 1. MỞ ĐẦU

## 1.1. Lý do chọn đề tài

Hệ thống pháp luật Việt Nam có quy mô đồ sộ và cấu trúc phân mảnh. Một vấn đề pháp lý cụ thể của người dân — chẳng hạn chuyển mục đích sử dụng đất, đăng ký khai sinh hay nhận nuôi con nuôi — thường không được điều chỉnh bởi một văn bản duy nhất, mà bởi một tập hợp văn bản đan xen: luật của Quốc hội, nghị định hướng dẫn của Chính phủ, thông tư của bộ ngành, và các văn bản của chính quyền địa phương. Các văn bản này lại liên tục được sửa đổi, bổ sung, thay thế theo thời gian. Việc tra cứu thủ công đòi hỏi người dùng phải tự xác định đúng lĩnh vực, đúng địa phương, đúng tầng hiệu lực và đúng phiên bản còn hiệu lực — một rào cản lớn ngay cả với người có chuyên môn.

Sự phát triển gần đây của các mô hình ngôn ngữ lớn (Large Language Model — LLM) mở ra khả năng trả lời câu hỏi pháp lý bằng ngôn ngữ tự nhiên. Tuy nhiên, LLM sử dụng độc lập bộc lộ hai hạn chế nghiêm trọng trong bối cảnh pháp luật: (1) hiện tượng "bịa" (hallucination) — mô hình tạo ra nội dung hoặc trích dẫn điều khoản không tồn tại; và (2) tri thức tham số tĩnh — mô hình không nắm được các văn bản mới hoặc các sửa đổi sau thời điểm huấn luyện. Trong lĩnh vực pháp luật, một câu trả lời sai hoặc một trích dẫn không có thật có thể gây hậu quả pháp lý thực sự, nên khả năng **trích dẫn chính xác nguồn** là yêu cầu bắt buộc, không phải tùy chọn.

Kỹ thuật Truy hồi tăng cường sinh (Retrieval-Augmented Generation — RAG) khắc phục một phần các hạn chế trên bằng cách nạp các đoạn văn bản liên quan vào ngữ cảnh trước khi sinh câu trả lời. Tuy nhiên, RAG "thuần" (naive RAG) — chia nhỏ văn bản thành đoạn rồi tìm kiếm theo độ tương đồng ngữ nghĩa — không nắm bắt được **cấu trúc quan hệ** đặc thù của hệ thống pháp luật: quan hệ hướng dẫn thi hành giữa nghị định và luật, quan hệ sửa đổi giữa các văn bản, hiệu lực theo địa phương, hay tính thời điểm của từng phiên bản điều khoản. Chính bốn đặc thù này tạo thành **bốn thách thức (bốn khoảng trống — gap)** mà đề tài đặt ra để giải quyết:

- **Gap 1 — Đa lĩnh vực:** phân biệt và định tuyến đúng lĩnh vực pháp lý của câu hỏi (đất đai, hộ tịch, nuôi con nuôi).
- **Gap 2 — Đa địa phương:** trả về đúng quy định áp dụng cho địa phương được hỏi (toàn quốc, TP.HCM, Đồng Nai).
- **Gap 3 — Đa tầng văn bản:** liên kết đúng các tầng luật – nghị định – thông tư có quan hệ hướng dẫn thi hành.
- **Gap 4 — Đa phiên bản:** trả về đúng phiên bản điều khoản còn hiệu lực tại thời điểm quan tâm, xử lý các sửa đổi/bổ sung.

Đề tài đề xuất một hệ thống hỏi–đáp pháp luật **có trích dẫn**, kết hợp **Đồ thị tri thức (Knowledge Graph)** để mô hình hóa tường minh các quan hệ pháp lý nói trên với **Tìm kiếm vector (vector search)** để định vị nội dung theo ngữ nghĩa. Cách tiếp cận này được dẫn dắt bởi một **ontology pháp luật** — một mô hình tri thức mô tả các loại thực thể (văn bản, điều khoản, phiên bản, địa phương…) và quan hệ giữa chúng — nên được gọi là **GraphRAG dẫn dắt bởi ontology (Ontology-Driven GraphRAG)**.

## 1.2. Mục tiêu nghiên cứu

### 1.2.1. Mục tiêu tổng quát

Xây dựng và đánh giá một hệ thống hỏi–đáp pháp luật Việt Nam có khả năng trả lời câu hỏi bằng ngôn ngữ tự nhiên kèm trích dẫn chính xác đến cấp điều khoản, thông qua việc kết hợp Đồ thị tri thức và Tìm kiếm vector dưới sự dẫn dắt của một ontology pháp luật, nhằm giải quyết bốn thách thức đa lĩnh vực, đa địa phương, đa tầng văn bản và đa phiên bản.

### 1.2.2. Mục tiêu cụ thể

1. Thiết kế **mô hình ontology** biểu diễn cấu trúc và quan hệ của hệ thống văn bản quy phạm pháp luật (VBQPPL) Việt Nam.
2. Xây dựng **pipeline hoàn chỉnh** từ thu thập – chuẩn hóa dữ liệu, nạp vào đồ thị và kho vector, đến truy hồi và sinh câu trả lời có trích dẫn.
3. Thiết kế các **cơ chế truy hồi** (định tuyến theo lĩnh vực, lọc theo địa phương, duyệt đồ thị theo quan hệ hướng dẫn/sửa đổi, lọc theo thời điểm) nhằm giải quyết trực tiếp từng gap.
4. Xây dựng **khung đánh giá** đủ chặt để không chỉ chứng minh hệ thống vượt trội so với baseline, mà còn cô lập và chứng minh **vai trò cần thiết của từng cơ chế** đối với gap tương ứng.

## 1.3. Đối tượng và phạm vi nghiên cứu

### 1.3.1. Đối tượng nghiên cứu

Đối tượng nghiên cứu là các văn bản quy phạm pháp luật Việt Nam thuộc ba lĩnh vực: **đất đai**, **hộ tịch** và **nuôi con nuôi**; cùng các kỹ thuật biểu diễn tri thức (đồ thị tri thức, ontology) và truy hồi thông tin (tìm kiếm vector, GraphRAG) áp dụng cho bài toán hỏi–đáp pháp luật có trích dẫn.

### 1.3.2. Phạm vi nghiên cứu

- **Về lĩnh vực và văn bản:** corpus gồm 32 văn bản (Norm) thuộc ba lĩnh vực nêu trên — 20 văn bản đất đai, 8 văn bản hộ tịch, 4 văn bản nuôi con nuôi — bao phủ đầy đủ bốn tầng hiệu lực (luật/nghị quyết Quốc hội, nghị định, thông tư, văn bản địa phương).
- **Về địa phương:** ba phạm vi hiệu lực — toàn quốc, Thành phố Hồ Chí Minh và Đồng Nai.
- **Về thủ tục:** tập trung vào các thủ tục hành chính tiêu biểu của mỗi lĩnh vực; riêng mảng đất đai giới hạn ở hai thủ tục chuyển mục đích sử dụng đất và cấp giấy chứng nhận lần đầu, với phạm vi chuyển mục đích thu hẹp ở trường hợp cá nhân, từ đất nông nghiệp (trừ đất lâm nghiệp) sang đất ở, nhằm hạn chế liên đới tới các luật chuyên ngành khác.
- **Về phiên bản:** ưu tiên bản hợp nhất hiện hành làm nguồn nội dung chính; mô hình dữ liệu hỗ trợ quản lý phiên bản theo thời gian để phục vụ minh họa tính đa phiên bản.

## 1.4. Phương pháp nghiên cứu

Đề tài kết hợp hai phương pháp. Thứ nhất, **phương pháp xây dựng hệ thống** (design science): đề xuất mô hình ontology và kiến trúc, hiện thực hóa thành một hệ thống chạy được đầu-cuối, tuân thủ các nguyên tắc kỹ thuật về tính tái lập (idempotency, định danh tất định). Thứ hai, **phương pháp đánh giá thực nghiệm định lượng**: xây dựng bộ dữ liệu kiểm thử có đáp án chuẩn (ground truth), đo các chỉ số khách quan (độ chính xác trích dẫn F1, độ bao phủ văn bản, độ trung thực), so sánh với các hệ baseline, thực hiện phân tích cô lập thành phần (ablation) và kiểm định ý nghĩa thống kê, có bổ sung đánh giá của con người được hiệu chuẩn qua hệ số đồng thuận.

## 1.5. Ý nghĩa khoa học và thực tiễn

### 1.5.1. Ý nghĩa khoa học

Đề tài đóng góp một mô hình ontology-driven GraphRAG cho miền pháp luật tiếng Việt — nơi các đặc thù về tầng hiệu lực, địa phương và thời gian chưa được các hệ RAG thông dụng xử lý tường minh. Bên cạnh đó, đề tài đề xuất một khung đánh giá theo triết lý "khẳng định – bằng chứng" với thiết kế phân ly kép (double dissociation), cho phép chứng minh vai trò cần thiết của từng cơ chế thay vì chỉ so sánh tổng thể — một đóng góp về phương pháp luận đánh giá có thể tái sử dụng cho các hệ thống tương tự.

### 1.5.2. Ý nghĩa thực tiễn

Về mặt ứng dụng, hệ thống cung cấp một công cụ tra cứu pháp luật trả lời bằng ngôn ngữ tự nhiên kèm trích dẫn đến cấp điều khoản, giúp người dùng nhanh chóng tiếp cận đúng quy định áp dụng cho hoàn cảnh của mình (đúng lĩnh vực, đúng địa phương, đúng phiên bản còn hiệu lực), đồng thời giảm thiểu rủi ro từ các câu trả lời không có nguồn dẫn chứng.

## 1.6. Bố cục luận văn

Ngoài phần mở đầu, luận văn được tổ chức thành năm chương:

- **Chương 1 — Mở đầu:** trình bày lý do chọn đề tài, mục tiêu, đối tượng và phạm vi, phương pháp và ý nghĩa của nghiên cứu.
- **Chương 2 — Tổng quan và cơ sở lý thuyết:** phân tích bài toán và bốn thách thức, trình bày các kỹ thuật nền tảng (RAG, tìm kiếm vector, đồ thị tri thức, ontology), khảo sát các công trình liên quan và định vị đóng góp của đề tài.
- **Chương 3 — Thiết kế hệ thống và phương pháp:** trình bày kiến trúc tổng thể, mô hình ontology, pipeline nạp dữ liệu, cơ chế truy hồi ba giai đoạn và sinh câu trả lời có trích dẫn.
- **Chương 4 — Đánh giá thực nghiệm và bàn luận:** trình bày khung đánh giá, bộ dữ liệu kiểm thử, kết quả thực nghiệm và phân tích.
- **Chương 5 — Kết luận và hướng phát triển:** tổng kết đóng góp, nêu các hạn chế và định hướng nghiên cứu tiếp theo.
