**TRƯỜNG ĐẠI HỌC CÔNG NGHIỆP THÀNH PHỐ HỒ CHÍ MINH**

**KHOA CÔNG NGHỆ THÔNG TIN**

![ref1]

**– Tăng Thế Ngọc – MSSV: 22726651**

**– Trần Ngọc Duy Quang – MSSV: 22647891**


**KHÓA LUẬN TỐT NGHIỆP**

**TÊN ĐỀ TÀI**

**WEBSITE ĐẶT LỊCH MASSAGE TÍCH HỢP TRÍ TUỆ NHÂN TẠO HỘI THOẠI (CONVERSATIONAL AI)**

Ngành: Khoa học máy tính



**Giảng viên hướng dẫn: TS. Giảng Thanh Trọn**




**Thành phố Hồ Chí Minh, tháng ………… năm 2026**



**INDUSTRIAL UNIVERSITY OF HO CHI MINH CITY**

**FACULTY OF INFORMATION TECHNOLOGY**

![ref1]

**– Tang The Ngoc – Student ID: 22726651**

**– Tran Ngoc Duy Quang – Student ID: 22647891**


**GRADUATION THESIS**

**Massage Booking Website Integrated with Conversational AI**

Major: Computer Science



**Supervisor: Dr. Giang Thanh Tron**




**Ho Chi Minh City, …………, 2026**

# <a name="_toc246366690"></a>**MỤC LỤC**
[MỤC LỤC	i](#_toc246366690)

[LỜI CẢM ƠN	i](#_toc246366691)

[TÓM TẮT	i](#_toc246366692)

[ABSTRACT	i](#_toc246366693)

[DANH MỤC HÌNH	i](#_toc246366694)

[DANH MỤC BẢNG	i](#_toc246366695)

[DANH MỤC TỪ VIẾT TẮT	i](#_toc246366696)

[CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI	1](#_toc246366697)

[1.1. Lý do chọn đề tài	1](#_toc246366698)

[1.2. Mục tiêu nghiên cứu	1](#_toc246366699)

[1.3. Đối tượng và phạm vi nghiên cứu	1](#_toc246366700)

[1.4. Phương pháp nghiên cứu	1](#_toc246366701)

[1.5. Kết cấu khóa luận	1](#_toc246366702)

[CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ SỬ DỤNG	1](#_toc246366703)

[2.1. Hệ thống đặt lịch dịch vụ trực tuyến	1](#_toc246366704)

[2.2. Trí tuệ nhân tạo hội thoại (Conversational AI)	1](#_toc246366705)

[2.3. Công nghệ sử dụng	1](#_toc246366706)

[2.3.1. Giao diện người dùng (Frontend)	1](#_toc246366707)

[2.3.2. Dịch vụ API nghiệp vụ (Backend)	1](#_toc246366708)

[2.3.3. Dịch vụ trí tuệ nhân tạo hội thoại	1](#_toc246366709)

[2.4. Công cụ mô hình hóa UML	1](#_toc246366710)

[2.5. Kết luận chương 2	1](#_toc246366711)

[CHƯƠNG 3: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG	1](#_toc246366712)

[3.1. Khảo sát và phân tích hiện trạng	1](#_toc246366713)

[3.2. Yêu cầu hệ thống	1](#_toc246366714)

[3.2.1. Yêu cầu chức năng	1](#_toc246366715)

[3.2.2. Yêu cầu phi chức năng	1](#_toc246366716)

[3.3. Phân tích ca sử dụng (Use Case)	1](#_toc246366717)

[3.4. Biểu đồ lớp (Class Diagram)	1](#_toc246366718)

[3.5. Thiết kế cơ sở dữ liệu	1](#_toc246366719)

[3.6. Kết luận chương 3	1](#_toc246366720)

[CHƯƠNG 4: CÀI ĐẶT VÀ KIỂM THỬ HỆ THỐNG	1](#_toc246366721)

[4.1. Môi trường và công cụ cài đặt	1](#_toc246366722)

[4.2. Cấu trúc chương trình	1](#_toc246366723)

[4.3. Giao diện và chức năng chính của chương trình	1](#_toc246366724)

[4.4. Kế hoạch và kết quả kiểm thử	1](#_toc246366725)

[4.5. Đánh giá hệ thống	1](#_toc246366726)

[4.6. Kết luận chương 4	1](#_toc246366727)

[CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN	1](#_toc246366728)

[5.1. Kết luận	1](#_toc246366729)

[5.2. Hạn chế của đề tài	1](#_toc246366730)

[5.3. Hướng phát triển trong tương lai	1](#_toc246366731)

[TÀI LIỆU THAM KHẢO	1](#_toc246366732)

[PHỤ LỤC	1](#_toc246366733)

[PHỤ LỤC A. Hướng dẫn cài đặt và vận hành hệ thống	1](#_toc246366734)

[A.1. Cài đặt và chạy dịch vụ API nghiệp vụ (spa-booking-api)	1](#_toc246366735)

[A.2. Cài đặt và chạy giao diện web (spa-booking-frontend)	1](#_toc246366736)

[A.3. Cài đặt và chạy dịch vụ trí tuệ nhân tạo hội thoại (chatbot)	1](#_toc246366737)

[A.4. Khởi tạo dữ liệu mẫu	1](#_toc246366738)

[A.5. Chạy kiểm thử tự động	1](#_toc246366739)

[PHỤ LỤC B. Một số đoạn mã nguồn tiêu biểu	1](#_toc246366740)

[B.1. Tính khung giờ còn trống — SlotService.get_available_slots (trích, spa-booking-api/app/services/slot_service.py)	1](#_toc246366741)

[B.2. Tạo lịch hẹn và phân công nhân viên — BookingService.create (trích, spa-booking-api/app/services/booking_service.py)	1](#_toc246366742)

[B.3. Thực thi hành động của chatbot AI — ToolOrchestrator (trích, chatbot/conversation/tool_orchestrator.py)	1](#_toc246366743)

[PHỤ LỤC C. Danh sách API chính	1](#_toc246366744)

[PHỤ LỤC D. Ví dụ minh họa luồng hội thoại đặt lịch qua chatbot AI	1](#_toc246366745)




# <a name="_toc246366691"></a>**LỜI CẢM ƠN**
Để hoàn thành khóa luận tốt nghiệp với đề tài “Website đặt lịch massage tích hợp trí tuệ nhân tạo hội thoại”, chúng em xin gửi lời cảm ơn chân thành đến Quý Thầy Cô Khoa Công nghệ Thông tin, Trường Đại học Công nghiệp Thành phố Hồ Chí Minh đã tận tình giảng dạy và truyền đạt kiến thức trong suốt quá trình học tập.

Đặc biệt, chúng em xin bày tỏ lòng biết ơn sâu sắc đến TS. Giảng Thanh Trọn, người đã trực tiếp hướng dẫn, góp ý và định hướng tận tình trong suốt quá trình thực hiện đề tài, giúp chúng em hoàn thiện cả về mặt kỹ thuật lẫn phương pháp trình bày của khóa luận.

Chúng em cũng xin cảm ơn gia đình, bạn bè đã luôn động viên, hỗ trợ trong suốt thời gian học tập và thực hiện khóa luận.

Do kiến thức và thời gian còn hạn chế, bài khóa luận khó tránh khỏi thiếu sót. Chúng em rất mong nhận được sự góp ý của Quý Thầy Cô để đề tài được hoàn thiện hơn.

**Chúng em xin chân thành cảm ơn!**


# <a name="_toc246366692"></a>**TÓM TẮT**
Trong bối cảnh chuyển đổi số và nhu cầu đặt lịch dịch vụ trực tuyến ngày càng tăng, khóa luận trình bày quá trình phân tích, thiết kế và xây dựng một hệ thống đặt lịch massage trực tuyến có tích hợp trí tuệ nhân tạo hội thoại (Conversational AI), cho phép khách hàng tra cứu chi nhánh, dịch vụ, khung giờ trống theo thời gian thực, đặt lịch (đơn hoặc theo nhóm), và trò chuyện với chatbot để được tư vấn và đặt lịch tự động.

Hệ thống được xây dựng theo kiến trúc ba thành phần: giao diện web (Next.js/React/TypeScript), dịch vụ API quản lý nghiệp vụ đặt lịch (Flask, SQLAlchemy, SQLite) và một dịch vụ trí tuệ nhân tạo hội thoại độc lập (FastAPI) sử dụng mô hình ngôn ngữ lớn GPT-4o của OpenAI, có khả năng trích xuất ý định, lập kế hoạch và gọi trực tiếp các nghiệp vụ đặt lịch thông qua cơ chế tool-calling, kết hợp cơ sở tri thức dạng vector (RAG) để tư vấn dịch vụ.

Khóa luận đã khảo sát quy trình đặt lịch thủ công hiện tại, mô hình hóa hệ thống bằng UML, thiết kế cơ sở dữ liệu quan hệ cho các thực thể nghiệp vụ chính (khách hàng, chi nhánh, dịch vụ, nhân viên, ca làm việc, lịch hẹn), cài đặt đầy đủ các chức năng đặt lịch cho khách hàng và quản trị cho nhân viên, đồng thời xây dựng kế hoạch kiểm thử cho cả hai luồng: đặt lịch qua giao diện web và đặt lịch qua chatbot AI hội thoại. Kết quả là một hệ thống hoạt động được trong môi trường phát triển/kiểm thử, làm nền tảng để mở rộng sang các hướng như đặt lịch qua giọng nói, thanh toán trực tuyến và bảng điều khiển quản trị đầy đủ trong tương lai.

**Từ khóa: Đặt lịch trực tuyến, Trí tuệ nhân tạo hội thoại, Chatbot, GPT-4o, Website, UML.**


# <a name="_toc246366693"></a>**ABSTRACT**
In the context of digital transformation and the growing demand for online service booking, this thesis presents the analysis, design and development of an online massage booking system integrated with Conversational AI, allowing customers to browse shops, services and real-time available time slots, make single or group bookings, and chat with an AI assistant to receive consultation and complete bookings automatically.

The system follows a three-component architecture: a web frontend (Next.js/React/TypeScript), a booking business-logic API (Flask, SQLAlchemy, SQLite), and an independent Conversational AI service (FastAPI) built on OpenAI's GPT-4o large language model, capable of intent extraction, planning, and directly invoking booking operations through a tool-calling mechanism, combined with a vector-based knowledge base (RAG) for service consultation.

The thesis surveys the current manual booking process, models the system with UML, designs a relational database for the core business entities (customer, shop, course, therapist, shift, booking), implements the full customer-facing booking features and staff administration features, and establishes a test plan covering both the web booking flow and the AI chatbot booking flow. The result is a working system in a development/testing environment, providing a foundation for future extensions such as voice booking, online payment, and a full admin dashboard.

**Keywords: Online booking, Conversational AI, Chatbot, GPT-4o, Website, UML.**


# <a name="_toc246366694"></a>**DANH MỤC HÌNH**
***Lưu ý:** Danh sách hình dưới đây liệt kê thủ công theo nội dung đã viết. Có thể dùng Insert Caption cho từng hình rồi chèn trường References > Insert Table of Figures để Word tự cập nhật số trang.*

Hình 3.1: Sơ đồ lớp (Class Diagram) rút gọn của hệ thống

Hình 4.1: Sơ đồ kiến trúc tổng thể hệ thống


# <a name="_toc246366695"></a>**DANH MỤC BẢNG**
Bảng 3.1: Mô tả các bảng cơ sở dữ liệu chính

Bảng 4.1: Môi trường và công cụ phát triển

Bảng 4.2: Kịch bản kiểm thử các chức năng chính


# <a name="_toc246366696"></a>**DANH MỤC TỪ VIẾT TẮT**

|**Từ viết tắt**|Từ nguyên gốc|
| :- | :- |
|**AI**|Artificial Intelligence (Trí tuệ nhân tạo)|
|**LLM**|Large Language Model (Mô hình ngôn ngữ lớn)|
|**NLP**|Natural Language Processing (Xử lý ngôn ngữ tự nhiên)|
|**RAG**|Retrieval-Augmented Generation (Sinh văn bản có truy xuất)|
|**API**|Application Programming Interface|
|**REST**|Representational State Transfer|
|**ORM**|Object-Relational Mapping|
|**JWT**|JSON Web Token|
|**UI/UX**|User Interface / User Experience|
|**CSDL**|Cơ sở dữ liệu|
|**KLTN**|Khóa luận tốt nghiệp|
|**GVHD**|Giảng viên hướng dẫn|
|**CNTT**|Công nghệ Thông tin|
|**TP. HCM**|Thành phố Hồ Chí Minh|

ii
# <a name="_toc246366697"></a>**CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI**
## <a name="_toc246366698"></a>**1.1. Lý do chọn đề tài**
Ngành dịch vụ chăm sóc sức khỏe và làm đẹp, trong đó có massage/spa, đang phát triển nhanh tại các đô thị lớn. Tuy nhiên, phần lớn các cơ sở vẫn tiếp nhận đặt lịch theo phương thức thủ công: khách hàng gọi điện hoặc nhắn tin, nhân viên tự ghi nhận vào sổ sách hoặc bảng tính. Cách làm này tồn tại nhiều hạn chế: dễ trùng lịch giữa các khách hàng, mất thời gian xác nhận khung giờ còn trống, khó theo dõi lịch làm việc của từng nhân viên, và không có khả năng tư vấn tự động ngoài giờ hành chính.

Song song đó, sự phát triển của các mô hình ngôn ngữ lớn (Large Language Model – LLM) như GPT-4o đã mở ra khả năng xây dựng các trợ lý hội thoại (chatbot) có thể hiểu ngôn ngữ tự nhiên, trích xuất đúng ý định của người dùng và thực hiện hành động thay cho họ (ví dụ: tạo một lịch hẹn) thông qua cơ chế gọi công cụ (tool-calling), thay vì chỉ trả lời câu hỏi đơn thuần như các chatbot dựa trên kịch bản cố định trước đây.

Xuất phát từ thực tế đó, đề tài “Website đặt lịch massage tích hợp trí tuệ nhân tạo hội thoại” được thực hiện nhằm xây dựng một hệ thống đặt lịch trực tuyến hiện đại, đồng thời tích hợp một trợ lý hội thoại AI có khả năng tư vấn dịch vụ và trực tiếp thực hiện việc đặt lịch thay cho khách hàng, giúp tiết kiệm thời gian cho cả khách hàng và nhân viên vận hành.
## <a name="_toc246366699"></a>**1.2. Mục tiêu nghiên cứu**
- Khảo sát và phân tích quy trình đặt lịch dịch vụ massage hiện tại, xác định các hạn chế cần khắc phục.
- Thiết kế hệ thống theo hướng đối tượng bằng UML: xác định thực thể nghiệp vụ, mối quan hệ, các ca sử dụng chính.
- Xây dựng website đặt lịch (Next.js) và dịch vụ API nghiệp vụ (Flask) với đầy đủ chức năng đặt lịch cho khách hàng và quản trị cho nhân viên.
- Xây dựng dịch vụ trí tuệ nhân tạo hội thoại (FastAPI + GPT-4o) có khả năng trích xuất ý định, lập kế hoạch và gọi trực tiếp các nghiệp vụ đặt lịch thông qua tool-calling.
- Thiết lập kế hoạch kiểm thử và đánh giá hệ thống trên cả hai luồng: đặt lịch qua giao diện web và đặt lịch qua chatbot.
## <a name="_toc246366700"></a>**1.3. Đối tượng và phạm vi nghiên cứu**
**Đối tượng nghiên cứu:** Quy trình nghiệp vụ đặt lịch dịch vụ massage (khách hàng, chi nhánh, dịch vụ, nhân viên, ca làm việc, lịch hẹn) và kiến trúc trợ lý hội thoại AI ứng dụng mô hình ngôn ngữ lớn.

**Phạm vi thực hiện:**

- Website cho khách hàng: xem danh sách chi nhánh/dịch vụ, xem khung giờ trống theo thời gian thực, đặt lịch đơn hoặc theo nhóm, chọn nhân viên theo tên hoặc theo giới tính, tra cứu/hủy lịch hẹn theo số điện thoại.
- Chức năng quản trị: quản lý chi nhánh, dịch vụ, nhân viên, ca làm việc, danh sách khách hàng bị hạn chế (NG List), check-in/check-out khách hàng.
- Trợ lý hội thoại AI: tư vấn dịch vụ dựa trên cơ sở tri thức, trích xuất ý định đặt lịch từ hội thoại, gọi nghiệp vụ đặt lịch qua API sau khi được khách hàng xác nhận.

**Ngoài phạm vi (định hướng phát triển):**

- Đặt lịch qua cuộc gọi thoại tự động (voice booking qua Twilio) — hiện ở giai đoạn thiết kế khung, chưa đưa vào vận hành.
- Thanh toán trực tuyến, ứng dụng di động, giao diện quản trị đầy đủ trên web (hiện quản trị chủ yếu qua API).
## <a name="_toc246366701"></a>**1.4. Phương pháp nghiên cứu**
- Phương pháp khảo sát thực tế: tìm hiểu quy trình đặt lịch tại các cơ sở massage/spa và các hạn chế của cách làm thủ công.
- Phương pháp phân tích và thiết kế hướng đối tượng: sử dụng UML (Class Diagram, mô tả ca sử dụng) để mô hình hóa hệ thống.
- Phương pháp phát triển phần mềm: xây dựng theo kiến trúc client–server, tách biệt dịch vụ API nghiệp vụ và dịch vụ trí tuệ nhân tạo hội thoại (microservice riêng), áp dụng mẫu kiến trúc nhiều lớp (Presentation – Service – Data Access).
- Phương pháp kiểm thử: kiểm thử đơn vị/tích hợp bằng pytest cho tầng API và kiểm thử kịch bản chức năng theo luồng nghiệp vụ.
## <a name="_toc246366702"></a>**1.5. Kết cấu khóa luận**
Ngoài phần mở đầu, kết luận, tài liệu tham khảo và phụ lục, khóa luận được trình bày thành 5 chương:

- Chương 1 – Tổng quan đề tài: trình bày lý do chọn đề tài, mục tiêu, đối tượng, phạm vi và phương pháp nghiên cứu.
- Chương 2 – Cơ sở lý thuyết và công nghệ sử dụng: trình bày các khái niệm nền tảng về hệ thống đặt lịch trực tuyến, trí tuệ nhân tạo hội thoại, và công nghệ sử dụng.
- Chương 3 – Phân tích và thiết kế hệ thống: khảo sát hiện trạng, yêu cầu hệ thống, mô hình hóa UML và thiết kế cơ sở dữ liệu.
- Chương 4 – Cài đặt và kiểm thử hệ thống: môi trường, cấu trúc chương trình, giao diện chức năng, kế hoạch kiểm thử và đánh giá.
- Chương 5 – Kết luận và hướng phát triển: tổng kết kết quả đạt được, hạn chế và hướng phát triển trong tương lai.
# <a name="_toc246366703"></a>**CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ SỬ DỤNG**
## <a name="_toc246366704"></a>**2.1. Hệ thống đặt lịch dịch vụ trực tuyến**
Hệ thống đặt lịch trực tuyến (online booking system) là phần mềm cho phép khách hàng tự đặt, thay đổi hoặc hủy một cuộc hẹn dịch vụ thông qua Internet mà không cần liên hệ trực tiếp với nhân viên. So với phương thức thủ công, hệ thống đặt lịch trực tuyến mang lại một số lợi ích: hiển thị khung giờ trống theo thời gian thực dựa trên ca làm việc của nhân viên và các lịch hẹn đã có; giảm thiểu sai sót do nhập liệu/ghi chép thủ công; cho phép khách hàng đặt lịch ngoài giờ hành chính; và cung cấp dữ liệu tập trung phục vụ thống kê, quản lý.

Trong phạm vi đề tài, tính sẵn sàng của khung giờ (availability) được tính theo mô hình lạc quan (optimistic availability): hệ thống không giữ chỗ trước, số chỗ trống của một khung giờ được suy ra trực tiếp từ số nhân viên đang trong ca trừ đi số lịch hẹn đã có tại khung giờ đó; việc kiểm tra và xác nhận thực sự chỉ diễn ra tại thời điểm tạo lịch hẹn.
## <a name="_toc246366705"></a>**2.2. Trí tuệ nhân tạo hội thoại (Conversational AI)**
Trí tuệ nhân tạo hội thoại là lĩnh vực ứng dụng xử lý ngôn ngữ tự nhiên (Natural Language Processing – NLP) để xây dựng các hệ thống có khả năng giao tiếp với con người bằng ngôn ngữ tự nhiên. Có hai hướng tiếp cận phổ biến: chatbot dựa trên luật/kịch bản cố định (rule-based), phù hợp với các tình huống hội thoại đơn giản nhưng khó mở rộng; và chatbot dựa trên mô hình ngôn ngữ lớn (Large Language Model – LLM), có khả năng hiểu ngữ cảnh linh hoạt hơn và tổng hợp phản hồi tự nhiên hơn.

Đề tài sử dụng hướng tiếp cận thứ hai, cụ thể là mô hình GPT-4o của OpenAI, kết hợp với kỹ thuật tool-calling (gọi công cụ): thay vì chỉ sinh văn bản, mô hình được cung cấp một tập các “công cụ” (tool) tương ứng với các nghiệp vụ thực tế của hệ thống (ví dụ: tra cứu khung giờ trống, tạo lịch hẹn), và có thể quyết định gọi đúng công cụ với tham số phù hợp dựa trên nội dung hội thoại. Luồng xử lý một lượt hội thoại trong đề tài gồm 4 bước:

- Trích xuất ý định (Intent Extraction): phân tích câu nói của khách hàng để xác định ý định (ví dụ: tìm dịch vụ, đặt lịch, hủy lịch) và các tham số liên quan.
- Lập kế hoạch (Planning): dựa trên ý định và trạng thái hội thoại hiện tại, xác định công cụ cần gọi (đọc dữ liệu hay thực hiện một hành động ghi dữ liệu).
- Thực thi công cụ (Tool Orchestration): gọi API nghiệp vụ tương ứng; với các hành động ghi dữ liệu (ví dụ tạo lịch hẹn), hệ thống yêu cầu xác nhận của khách hàng trước khi thực sự thực thi, nhằm tránh đặt lịch ngoài ý muốn.
- Sinh phản hồi (Response Generation): tổng hợp kết quả thành câu trả lời tự nhiên gửi lại cho khách hàng.

Để tư vấn dịch vụ chính xác hơn, hệ thống còn sử dụng kỹ thuật sinh văn bản có truy xuất (Retrieval-Augmented Generation – RAG): nội dung mô tả dịch vụ được chia nhỏ (chunking), chuyển thành vector embedding và lưu trong kho vector (pgvector); khi cần trả lời, hệ thống truy xuất các đoạn nội dung liên quan nhất rồi đưa vào ngữ cảnh của mô hình ngôn ngữ trước khi sinh câu trả lời, giúp giảm hiện tượng mô hình “bịa” thông tin không có thật.
## <a name="_toc246366706"></a>**2.3. Công nghệ sử dụng**
## <a name="_toc246366707"></a>**2.3.1. Giao diện người dùng (Frontend)**
- Next.js 16 (App Router) kết hợp React 19 và TypeScript: xây dựng giao diện dạng Single Page Application, gọi trực tiếp API từ trình duyệt.
- Tailwind CSS 4: xây dựng giao diện responsive theo hướng utility-first.
- Axios: giao tiếp HTTP với tầng API theo kiểu type-safe.
## <a name="_toc246366708"></a>**2.3.2. Dịch vụ API nghiệp vụ (Backend)**
- Flask 3 (Python): xây dựng REST API theo mô hình blueprint (nhóm route theo chức năng).
- SQLAlchemy + Alembic: ánh xạ đối tượng – quan hệ (ORM) và quản lý migration cơ sở dữ liệu.
- SQLite: cơ sở dữ liệu quan hệ, không cần cấu hình máy chủ riêng, phù hợp môi trường phát triển/kiểm thử.
- Flask-JWT-Extended: xác thực bằng JSON Web Token cho các thao tác quản trị.
- Redis (tùy chọn): lưu phiên làm việc/cache, hệ thống vẫn hoạt động nếu không có Redis.
## <a name="_toc246366709"></a>**2.3.3. Dịch vụ trí tuệ nhân tạo hội thoại**
- FastAPI + Uvicorn: xây dựng dịch vụ chatbot độc lập, giao tiếp qua HTTP, tách biệt với dịch vụ API nghiệp vụ.
- OpenAI GPT-4o: mô hình ngôn ngữ lớn dùng để trích xuất ý định, lập kế hoạch và sinh phản hồi.
- pgvector + sentence-transformers (all-MiniLM-L6-v2): lưu trữ và truy vấn vector embedding phục vụ cơ chế RAG.
- Redis: lưu trạng thái phiên hội thoại và giới hạn tần suất gọi (rate limiting).
- Pydantic: định nghĩa và kiểm tra dữ liệu (schema) trao đổi giữa các thành phần.
## <a name="_toc246366710"></a>**2.4. Công cụ mô hình hóa UML**
UML (Unified Modeling Language) là ngôn ngữ mô hình hóa trực quan được sử dụng phổ biến trong phân tích và thiết kế hệ thống hướng đối tượng. Trong khóa luận, UML được dùng để: mô tả các ca sử dụng (use case) chính của hệ thống dưới dạng đặc tả chức năng, và xây dựng biểu đồ lớp (class diagram) thể hiện các thực thể nghiệp vụ cùng mối quan hệ giữa chúng, làm cơ sở cho thiết kế cơ sở dữ liệu ở Chương 3.
## <a name="_toc246366711"></a>**2.5. Kết luận chương 2**
Chương này đã trình bày cơ sở lý thuyết về hệ thống đặt lịch trực tuyến và trí tuệ nhân tạo hội thoại dựa trên mô hình ngôn ngữ lớn kết hợp tool-calling và RAG, đồng thời giới thiệu các công nghệ cụ thể được sử dụng ở ba thành phần: giao diện web, dịch vụ API nghiệp vụ và dịch vụ chatbot AI. Đây là nền tảng cho việc phân tích và thiết kế hệ thống ở Chương 3.
# <a name="_toc246366712"></a>**CHƯƠNG 3: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG**
## <a name="_toc246366713"></a>**3.1. Khảo sát và phân tích hiện trạng**
Qua khảo sát quy trình đặt lịch tại các cơ sở massage/spa hiện nay, quy trình phổ biến gồm các bước: khách hàng gọi điện hoặc nhắn tin cho cơ sở; nhân viên tiếp nhận kiểm tra lịch làm việc (thường bằng sổ tay hoặc bảng tính) để xác định khung giờ còn trống; nhân viên xác nhận lại với khách hàng; thông tin đặt lịch được ghi chép thủ công.

Cách làm này bộc lộ một số hạn chế: dễ xảy ra trùng lịch khi có nhiều khách đặt cùng lúc; phụ thuộc vào thời gian làm việc của nhân viên tiếp nhận, không thể phục vụ ngoài giờ; khó tổng hợp, thống kê dữ liệu khách hàng và lịch sử sử dụng dịch vụ; không có cơ chế ngăn chặn khách hàng từng vi phạm quy định (ví dụ: đặt lịch rồi không đến) tiếp tục đặt lịch.
## <a name="_toc246366714"></a>**3.2. Yêu cầu hệ thống**
## <a name="_toc246366715"></a>**3.2.1. Yêu cầu chức năng**
- Khách hàng xem danh sách chi nhánh, dịch vụ (dịch vụ chính và dịch vụ thêm) kèm giá và thời lượng.
- Khách hàng xem khung giờ còn trống theo thời gian thực của một chi nhánh theo ngày, số lượng khách và dịch vụ đã chọn.
- Khách hàng đặt lịch cho 1 người (có thể chỉ định nhân viên cụ thể hoặc theo giới tính) hoặc theo nhóm từ 2 người trở lên (hệ thống tự phân công nhân viên).
- Khách hàng tra cứu, chỉnh sửa (khi còn ở trạng thái Booked) hoặc hủy lịch hẹn theo số điện thoại.
- Khách hàng trò chuyện với trợ lý AI để được tư vấn dịch vụ phù hợp và đặt lịch trực tiếp qua hội thoại.
- Quản trị viên quản lý chi nhánh, dịch vụ, nhân viên và ca làm việc hằng tuần của từng nhân viên.
- Quản trị viên xem danh sách tất cả lịch hẹn, thực hiện check-in khi khách đến và check-out khi hoàn tất dịch vụ.
- Quản trị viên quản lý danh sách khách hàng bị hạn chế đặt lịch (NG List) kèm lý do.
## <a name="_toc246366716"></a>**3.2.2. Yêu cầu phi chức năng**
- Bảo mật: các thao tác quản trị yêu cầu xác thực bằng JWT; khách hàng được định danh qua số điện thoại, không yêu cầu đăng ký tài khoản.
- Hiệu năng: tính toán khung giờ trống phải phản ánh đúng trạng thái tại thời điểm truy vấn; việc tạo lịch hẹn phải được kiểm tra lại dưới khóa mức dòng (row-level lock) để tránh hai khách đặt trùng một nhân viên.
- Khả năng mở rộng: tách dịch vụ trí tuệ nhân tạo hội thoại thành một dịch vụ độc lập (microservice) để có thể phát triển, triển khai và mở rộng riêng biệt với dịch vụ API nghiệp vụ.
- Khả năng sử dụng: giao diện web rõ ràng theo từng bước (chọn chi nhánh → ngày/giờ → dịch vụ → xác nhận); chatbot phản hồi bằng ngôn ngữ tự nhiên, dễ sử dụng với người không rành công nghệ.
## <a name="_toc246366717"></a>**3.3. Phân tích ca sử dụng (Use Case)**
Hệ thống có ba tác nhân (actor) chính: Khách hàng, Trợ lý AI hội thoại (đóng vai trò trung gian thực hiện hành động thay khách hàng sau khi được xác nhận) và Quản trị viên. Các ca sử dụng chính được tóm tắt trong bảng dưới đây.

|Tác nhân|**Ca sử dụng**|Mô tả ngắn gọn|
| :- | :- | :- |
|Khách hàng|**Xem dịch vụ & khung giờ**|Xem chi nhánh, dịch vụ, khung giờ trống theo ngày/số khách.|
|Khách hàng|**Đặt lịch**|Chọn khung giờ, dịch vụ, (tùy chọn) nhân viên, nhập số điện thoại, xác nhận.|
|Khách hàng|**Tra cứu / Hủy lịch hẹn**|Tra cứu theo số điện thoại; hủy khi lịch hẹn còn ở trạng thái Booked.|
|Khách hàng|**Trò chuyện với chatbot AI**|Trao đổi ngôn ngữ tự nhiên để được tư vấn và đặt lịch.|
|Trợ lý AI|**Đặt lịch qua hội thoại**|Trích xuất ý định, đề xuất khung giờ, gọi API tạo lịch hẹn sau khi khách xác nhận.|
|Quản trị viên|**Quản lý danh mục**|Quản lý chi nhánh, dịch vụ, nhân viên, ca làm việc.|
|Quản trị viên|**Quản lý lịch hẹn**|Xem danh sách lịch hẹn, check-in, check-out.|
|Quản trị viên|**Quản lý NG List**|Thêm/gỡ hạn chế đặt lịch của khách hàng kèm lý do.|

**Đặc tả ca sử dụng “Đặt lịch qua hội thoại”:** (1) Khách hàng nhắn tin nêu nhu cầu; (2) Trợ lý AI trích xuất ý định và tham số (chi nhánh, ngày giờ, số người, dịch vụ); (3) Trợ lý AI gọi công cụ tra cứu khung giờ trống và đề xuất phương án phù hợp; (4) Khách hàng xác nhận lựa chọn; (5) Trợ lý AI gọi công cụ tạo lịch hẹn ở trạng thái chờ xác nhận (pending action), sau đó thực thi và trả về mã lịch hẹn; (6) Nếu khung giờ không còn trống tại thời điểm xác nhận, hệ thống thông báo và đề xuất khung giờ gần nhất.
## <a name="_toc246366718"></a>**3.4. Biểu đồ lớp (Class Diagram)**
Biểu đồ lớp rút gọn dưới đây thể hiện các thực thể nghiệp vụ chính và mối quan hệ giữa chúng, làm cơ sở cho thiết kế cơ sở dữ liệu ở mục 3.5.

![](Aspose.Words.396207f1-bfe1-4f21-8134-477e6a572cc3.002.png)

*Hình 3.1: Sơ đồ lớp rút gọn của hệ thống*
## <a name="_toc246366719"></a>**3.5. Thiết kế cơ sở dữ liệu**
Cơ sở dữ liệu được thiết kế theo mô hình quan hệ, gồm các bảng chính sau:

|**Bảng**|Vai trò|
| :- | :- |
|**users**|Tài khoản đăng nhập của quản trị viên/nhân viên (xác thực JWT).|
|**customers**|Hồ sơ khách hàng, định danh theo số điện thoại; lưu hạng thành viên, số lần ghé.|
|**shops**|Thông tin chi nhánh: tên, địa chỉ, giờ mở/đóng cửa.|
|**courses**|Dịch vụ của một chi nhánh: loại chính (main) hoặc thêm (addon), thời lượng, giá.|
|**therapists**|Nhân viên thực hiện dịch vụ, thuộc một chi nhánh.|
|**therapist\_shifts**|Ca làm việc hằng tuần của từng nhân viên.|
|**bookings**|Lịch hẹn: mã lịch hẹn, chi nhánh, thời gian, số khách, trạng thái.|
|**booking\_services**|Dịch vụ chính được chọn cho từng người trong một lịch hẹn.|
|**booking\_addons**|Dịch vụ thêm được chọn cho từng người trong một lịch hẹn.|
|**customer\_restrictions**|Danh sách hạn chế đặt lịch (NG List) kèm lý do và trạng thái.|

Một số ràng buộc nghiệp vụ quan trọng được áp dụng ở tầng thiết kế: mỗi người trong một lịch hẹn nhận đúng 1 dịch vụ chính và 0..N dịch vụ thêm; lịch hẹn từ 2 người trở lên không được chỉ định nhân viên cụ thể (hệ thống tự phân công theo nguyên tắc nhân viên có ít lịch hẹn nhất); nhân viên chỉ được phân công khi đang trong ca làm việc bao phủ khung giờ đặt và không bị trùng với lịch hẹn khác; lịch hẹn chỉ được chỉnh sửa khi còn ở trạng thái Booked, với các trạng thái hợp lệ Booked → CheckedIn → CheckedOut hoặc Booked → Cancelled.
## <a name="_toc246366720"></a>**3.6. Kết luận chương 3**
Chương này đã khảo sát hiện trạng, xác định yêu cầu chức năng/phi chức năng, mô hình hóa ca sử dụng và biểu đồ lớp, đồng thời thiết kế cơ sở dữ liệu quan hệ cho các thực thể nghiệp vụ chính. Đây là cơ sở để tiến hành cài đặt và kiểm thử hệ thống ở Chương 4.
# <a name="_toc246366721"></a>**CHƯƠNG 4: CÀI ĐẶT VÀ KIỂM THỬ HỆ THỐNG**
## <a name="_toc246366722"></a>**4.1. Môi trường và công cụ cài đặt**

|**Thành phần**|Công cụ / phiên bản|
| :- | :- |
|**Ngôn ngữ**|Python 3.11+ (backend, chatbot), TypeScript 5 (frontend)|
|**Frontend**|Next.js 16 (App Router), React 19, Tailwind CSS 4, Axios|
|**Backend API**|Flask 3, SQLAlchemy, Alembic, Flask-JWT-Extended|
|**Chatbot AI**|FastAPI, Uvicorn, OpenAI GPT-4o, pgvector, sentence-transformers|
|**Cơ sở dữ liệu**|SQLite (chính), Redis (cache/phiên hội thoại, tùy chọn)|
|**Kiểm thử**|pytest (backend), pytest-asyncio (chatbot)|
|**Khác**|Docker / Docker Compose để đóng gói triển khai|
## <a name="_toc246366723"></a>**4.2. Cấu trúc chương trình**
Hệ thống được tổ chức thành ba thành phần độc lập, giao tiếp với nhau qua HTTP/REST, như minh họa ở hình bên dưới: giao diện web (Next.js) gọi API của dịch vụ đặt lịch (Flask) để thực hiện các nghiệp vụ đặt lịch, đồng thời gọi API của dịch vụ chatbot (FastAPI) khi khách hàng trò chuyện với trợ lý AI; dịch vụ chatbot sử dụng mô hình GPT-4o để xử lý hội thoại và, khi cần, gọi ngược lại API của dịch vụ đặt lịch để tra cứu hoặc tạo lịch hẹn thay cho khách hàng.

![](Aspose.Words.396207f1-bfe1-4f21-8134-477e6a572cc3.003.png)

*Hình 4.1: Sơ đồ kiến trúc tổng thể hệ thống*

Về phía backend, mã nguồn được tổ chức theo lớp: tầng blueprints tiếp nhận yêu cầu HTTP và kiểm tra tham số; tầng services (BookingService, SlotService, TherapistService, CustomerService) xử lý nghiệp vụ; tầng models (SQLAlchemy) ánh xạ xuống cơ sở dữ liệu. Dịch vụ chatbot được tổ chức theo luồng xử lý hội thoại: intent\_extractor → planner → tool\_orchestrator → response\_generator, cùng với module knowledge phục vụ truy xuất tri thức (RAG) và module session lưu trạng thái hội thoại trên Redis.
## <a name="_toc246366724"></a>**4.3. Giao diện và chức năng chính của chương trình**
- Trang chủ (/): điểm vào hệ thống, dẫn hướng đến danh sách chi nhánh.
- Danh sách chi nhánh (/shops): hiển thị các chi nhánh cùng dịch vụ và giá.
- Bảng lịch nhân viên (/dashboard): hiển thị dạng lưới (Gantt) nhân viên theo hàng, khung giờ theo cột; ô màu thể hiện còn trống hay đã kín lịch; nhấn vào một ô để đặt lịch trực tiếp cho nhân viên đó.
- Đặt lịch (/reservation, /booking): biểu mẫu đặt lịch nhiều bước — chọn ngày/giờ, nhập thông tin khách hàng, chọn dịch vụ và tùy chọn nhân viên, xem lại và xác nhận; hệ thống đề xuất khung giờ thay thế nếu khung giờ đã chọn không còn trống.
- Tra cứu lịch hẹn (/my-bookings): khách hàng nhập số điện thoại để xem, chỉnh sửa hoặc hủy lịch hẹn.
- Trợ lý hội thoại AI: giao tiếp dạng chat, khách hàng mô tả nhu cầu bằng ngôn ngữ tự nhiên (ví dụ: đặt dịch vụ, khung giờ mong muốn); trợ lý tư vấn dịch vụ phù hợp, đề xuất khung giờ và thực hiện đặt lịch sau khi khách hàng xác nhận.
- Khu vực quản trị (API, xác thực JWT): quản lý chi nhánh/dịch vụ/nhân viên/ca làm việc, xem danh sách lịch hẹn, check-in/check-out, quản lý NG List.

***Lưu ý:** Chèn ảnh chụp màn hình thực tế của ứng dụng đang chạy (trang chủ, dashboard, luồng đặt lịch, khung chat với trợ lý AI, trang đăng nhập quản trị) vào các mục tương ứng ở trên — phần này cần ảnh thật từ hệ thống nên không thể tạo thay.*
## <a name="_toc246366725"></a>**4.4. Kế hoạch và kết quả kiểm thử**
Việc kiểm thử được thực hiện bằng pytest, Jest, Chromium/Playwright và các kịch bản HTTP chạy trên Flask, FastAPI, Redis và SQLite riêng cho Task 12. Kết quả đo tại môi trường phát triển ngày 27/11/2026 được ghi bên dưới; chi tiết lệnh chạy và phạm vi xác minh nằm trong `docs/progress/task-12.md`.

|**Mã TC**|**Kịch bản**|**Kết quả mong đợi**|**Kết quả thực tế**|
| :- | :- | :- | :- |
|TC-01|Đặt lịch 1 người, chỉ định nhân viên đang trong ca và còn trống.|Trả mã lịch hẹn và trạng thái Booked.|Đạt: yêu cầu HTTP thật trả 201, phân công đúng nhân viên; giao diện quản trị thấy lịch.|
|TC-02|Đặt lịch nhóm 2 người và thử chỉ định nhân viên cụ thể.|Từ chối yêu cầu có chỉ định; yêu cầu mới không chỉ định được phân công tự động.|Đạt: yêu cầu đầu trả 400; yêu cầu thứ hai trả 201 và hai nhân viên khác nhau. Không tự tạo lịch sau yêu cầu bị từ chối.|
|TC-03|Khách hàng thuộc NG List đặt lịch.|Từ chối tạo lịch; không lộ lý do hạn chế qua API công khai.|Đạt: trả 422 CUSTOMER_BLOCKED, không lộ lý do; quản trị viên xem được lý do và mở chặn để đặt lại.|
|TC-04|Hai khách cùng đặt một nhân viên trùng giờ.|Chỉ một lịch được xác nhận; lần còn lại bị từ chối và có thể chọn giờ khác.|Đạt: hai yêu cầu đồng thời qua Flask/SQLite trả một 201 và một 422; chatbot thật không báo thành công khi mất nhân viên. Đề xuất giờ khác trên web đã qua Playwright với phản hồi API giả lập, chưa chạy cuộc đua đồng thời qua trình duyệt.|
|TC-05|Hủy lịch đang Booked.|Chuyển Cancelled và không thể chỉnh sửa.|Đạt: Chromium hủy sau xác minh số điện thoại; Flask lưu Cancelled và từ chối PATCH tiếp theo.|
|TC-06|Check-in rồi check-out.|Booked → CheckedIn → CheckedOut đúng thứ tự, đúng vai trò.|Đạt: giao diện admin check-in và nhân viên được phân công check-out; HTTP xác nhận trạng thái cuối và từ chối thao tác lặp.|
|TC-07|Khách trò chuyện với chatbot để đặt lịch.|Chỉ tạo sau khi xác nhận cuối cùng.|Đạt: `/chat` thật thu thập cửa hàng, dịch vụ, ngày giờ, nhân viên và số điện thoại; sau xác nhận Flask lưu Booked. Ví dụ dịch vụ “vai gáy” chưa có trong dữ liệu mẫu nên chưa thử đúng câu ví dụ đó.|
|TC-08|Hỏi chatbot một câu chưa có trong hội thoại.|Trả lời dựa trên tri thức được lập chỉ mục và dẫn nguồn.|Đạt: `/chat` thật trả câu trả lời về hủy lịch với trích dẫn FAQ từ pgvector; đường sinh văn bản bằng LLM bên ngoài chưa thử trực tiếp.|
## <a name="_toc246366726"></a>**4.5. Đánh giá hệ thống**
**Ưu điểm:**

- Tách rõ ba thành phần (frontend, API nghiệp vụ, chatbot AI), thuận lợi cho phát triển và mở rộng độc lập.
- Áp dụng cơ chế tool-calling và xác nhận trước khi ghi dữ liệu (pending action) giúp trợ lý AI không tự ý tạo lịch hẹn ngoài ý muốn của khách hàng.
- Các ràng buộc nghiệp vụ quan trọng (NG List, phân công nhân viên theo nhóm, chống trùng lịch) được cài đặt ở tầng service, tách biệt với tầng giao diện.

**Hạn chế:**

- Bảng lịch chọn thời lượng từ các lựa chọn dịch vụ hiện có và hỗ trợ số lượng khách theo sức chứa; giờ còn trống chỉ là ảnh chụp tức thời trước khi xác nhận.
- Chức năng đặt lịch qua giọng nói (voice booking qua Twilio) mới ở mức khung sườn, chưa được kích hoạt.
- Giao diện quản trị đã có đặt lịch, ca làm việc và NG List; chưa có báo cáo thống kê đầy đủ.
- Cập nhật theo thời gian thực qua Socket.IO đã có trong mã nguồn nhưng chưa được kết nối vào giao diện.
- Chưa tích hợp thanh toán trực tuyến và thông báo email/SMS.
## <a name="_toc246366727"></a>**4.6. Kết luận chương 4**
Chương này đã trình bày môi trường, cấu trúc chương trình, các chức năng chính đã cài đặt và kế hoạch kiểm thử cho cả luồng đặt lịch qua web lẫn qua chatbot AI, đồng thời đánh giá khách quan ưu điểm và hạn chế của hệ thống hiện tại.
# <a name="_toc246366728"></a>**CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN**
## <a name="_toc246366729"></a>**5.1. Kết luận**
Khóa luận đã hoàn thành các mục tiêu đề ra ở Chương 1: khảo sát và phân tích quy trình đặt lịch dịch vụ massage, thiết kế hệ thống bằng UML, xây dựng website đặt lịch cùng dịch vụ API nghiệp vụ, và xây dựng chatbot hội thoại sử dụng công cụ Flask cùng RAG trên pgvector. Luồng đặt lịch hội thoại hiện có các bước và cổng xác nhận xác định; khóa LLM là tùy chọn để diễn đạt câu trả lời FAQ có căn cứ. Hệ thống hỗ trợ các chức năng cốt lõi cho khách hàng (xem dịch vụ, đặt lịch đơn/nhóm, tra cứu/sửa/hủy sau xác minh số điện thoại, trò chuyện với chatbot) và cho quản trị viên (quản lý danh mục, lịch hẹn, ca làm việc, NG List).
## <a name="_toc246366730"></a>**5.2. Hạn chế của đề tài**
- Đặt lịch qua giọng nói (voice booking) mới ở mức khung sườn, chưa thể sử dụng trong thực tế.
- Giao diện quản trị đã có các luồng chính nhưng chưa có báo cáo thống kê; cập nhật thời gian thực qua Socket.IO chưa được kết nối.
- Chưa tích hợp thanh toán trực tuyến, thông báo email/SMS và chương trình khách hàng thân thiết.
- Kết quả kiểm thử Task 12 chỉ xác minh môi trường phát triển cục bộ với dữ liệu mẫu; chưa đánh giá tải lớn, triển khai sản xuất, chống trùng trên PostgreSQL cho Flask, hoặc độ chính xác hội thoại trên tập dữ liệu thực tế.
## <a name="_toc246366731"></a>**5.3. Hướng phát triển trong tương lai**
- Hoàn thiện và kích hoạt luồng đặt lịch qua điện thoại (Twilio + nhận dạng giọng nói + tổng hợp giọng nói).
- Xây dựng giao diện quản trị đầy đủ trên web (quản lý danh mục, lịch hẹn, báo cáo thống kê).
- Kết nối Socket.IO để cập nhật khung giờ/lịch hẹn theo thời gian thực trên giao diện.
- Tích hợp thanh toán trực tuyến, thông báo email/SMS và chương trình tích điểm theo hạng thành viên.
- Mở rộng cơ sở tri thức và đánh giá định lượng độ chính xác của trợ lý AI hội thoại trên tập hội thoại thực tế.
# <a name="_toc246366732"></a>**TÀI LIỆU THAM KHẢO**
[1] M. Fowler, UML Distilled: A Brief Guide to the Standard Object Modeling Language, 3rd ed. Addison-Wesley, 2003.

[2] I. Sommerville, Software Engineering, 10th ed. Pearson, 2015.

[3] Flask Documentation. [Online]. Available: https://flask.palletsprojects.com/

[4] SQLAlchemy Documentation. [Online]. Available: https://docs.sqlalchemy.org/

[5] Next.js Documentation. [Online]. Available: https://nextjs.org/docs

[6] FastAPI Documentation. [Online]. Available: https://fastapi.tiangolo.com/

[7] OpenAI API Documentation. [Online]. Available: https://platform.openai.com/docs

[8] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Advances in Neural Information Processing Systems (NeurIPS), 2020.

***Lưu ý:** Bổ sung thêm tài liệu thực tế đã tham khảo trong quá trình làm bài (giáo trình môn học, tài liệu nội bộ dự án trong thư mục docs/, bài báo khác nếu có), trình bày theo đúng chuẩn trích dẫn Khoa yêu cầu.*
# <a name="_toc246366733"></a>**PHỤ LỤC**
## <a name="_toc246366734"></a>**PHỤ LỤC A. Hướng dẫn cài đặt và vận hành hệ thống**
Hệ thống gồm ba thành phần chạy độc lập: dịch vụ API nghiệp vụ (spa-booking-api), giao diện web (spa-booking-frontend) và dịch vụ trí tuệ nhân tạo hội thoại (chatbot). Yêu cầu môi trường: Python 3.11+, Node.js 18+, pip và npm.
## <a name="_toc246366735"></a>**A.1. Cài đặt và chạy dịch vụ API nghiệp vụ (spa-booking-api)**

|<p>cd spa-booking-api</p><p> </p><p># Tạo và kích hoạt môi trường ảo</p><p>python -m venv venv</p><p>source venv/bin/activate        # Windows: venv\Scripts\activate</p><p> </p><p># Cài thư viện</p><p>pip install -r requirements.txt</p><p> </p><p># Tạo file cấu hình</p><p>cp .env.example .env</p><p> </p><p># Khởi tạo cơ sở dữ liệu SQLite (tự tạo file spa\_booking.db)</p><p>python3 -c "from app import create\_app; from app.extensions import db; \</p><p>app = create\_app(); app.app\_context().push(); db.create\_all()"</p><p> </p><p># (Tuỳ chọn) áp dụng migration bằng Alembic</p><p>flask db upgrade</p><p> </p><p># Chạy server — mặc định http://localhost:5000</p><p>python run.py</p>|
| :- |

*Phụ lục A.1: Lệnh cài đặt và chạy dịch vụ API nghiệp vụ*
## <a name="_toc246366736"></a>**A.2. Cài đặt và chạy giao diện web (spa-booking-frontend)**

|<p>cd spa-booking-frontend</p><p>npm install</p><p> </p><p># Cấu hình địa chỉ API backend</p><p>echo NEXT\_PUBLIC\_API\_URL=http://localhost:5000/api > .env.local</p><p> </p><p># Chạy server phát triển — mặc định http://localhost:3000</p><p>npm run dev</p>|
| :- |

*Phụ lục A.2: Lệnh cài đặt và chạy giao diện web*
## <a name="_toc246366737"></a>**A.3. Cài đặt và chạy dịch vụ trí tuệ nhân tạo hội thoại (chatbot)**

|<p>cd chatbot</p><p>python -m venv venv</p><p>source venv/bin/activate</p><p>pip install -r requirements.txt</p><p> </p><p># Khai báo API key của OpenAI và (tuỳ chọn) địa chỉ Redis</p><p>export CHATBOT\_OPENAI\_API\_KEY=sk-xxxxxxxxxxxxxxxx</p><p>export CHATBOT\_REDIS\_URL=redis://localhost:6379/0</p><p> </p><p># Chạy dịch vụ (chạy từ thư mục gốc dự án để import đúng package)</p><p>cd ..</p><p>python -m chatbot.main</p><p># hoặc: uvicorn chatbot.main:app --reload --port 8001</p>|
| :- |

*Phụ lục A.3: Lệnh cài đặt và chạy dịch vụ chatbot AI (mặc định http://localhost:8001)*
## <a name="_toc246366738"></a>**A.4. Khởi tạo dữ liệu mẫu**
Cơ sở dữ liệu khởi tạo ở trạng thái rỗng. Trên môi trường phát triển, chạy `flask --app run:app db upgrade` rồi `python seed_dev.py` từ thư mục `spa-booking-api`. Mọi API quản trị yêu cầu JWT admin lấy từ `POST /api/auth/login`; API tạo dịch vụ nhận mảng `durations`, còn API tạo nhân viên yêu cầu `username` và `password`. Xem `RUNNING.md` và `docs/REST_API_Specification.md` để biết cấu hình hiện tại. Endpoint tạo dữ liệu mẫu công khai đã bị vô hiệu hóa.

*Phụ lục A.4: Khởi tạo dữ liệu mẫu bằng migration và script phát triển.*
## <a name="_toc246366739"></a>**A.5. Chạy kiểm thử tự động**

Từ thư mục gốc dự án, chạy `venv/bin/python -m pytest -q -p no:asyncio -p scripts.pytest_asyncio_compat chatbot/tests`. Từ `spa-booking-api`, chạy `PYTHONPATH=.. ../venv/bin/python -m pytest -q -p no:asyncio -p scripts.pytest_asyncio_compat tests`. Từ `spa-booking-frontend`, chạy `npm test -- --runInBand` và Playwright. Các kịch bản HTTP và trình duyệt thật của Task 12 yêu cầu cấu hình tách biệt ghi trong `docs/progress/task-12.md`.

*Phụ lục A.5: Lệnh chạy kiểm thử tự động hiện tại.*
## <a name="_toc246366740"></a>**PHỤ LỤC B. Một số đoạn mã nguồn tiêu biểu**
Các đoạn mã dưới đây được trích từ mã nguồn thật của dự án (đã lược bớt một số đoạn không thiết yếu) nhằm minh họa cách cài đặt các nghiệp vụ quan trọng.
## <a name="_toc246366741"></a>**B.1. Tính khung giờ còn trống — SlotService.get\_available\_slots (trích, spa-booking-api/app/services/slot\_service.py)**

|<p>while current\_time + timedelta(minutes=duration) <= close\_time:</p><p>`    `end\_time = current\_time + timedelta(minutes=duration)</p><p>`    `st, et = current\_time.time(), end\_time.time()</p><p> </p><p>`    `available\_capacity = TherapistService.count\_available\_capacity(</p><p>`        `shop\_id, date\_obj, st, et</p><p>`    `)</p><p> </p><p>`    `slot = {</p><p>`        `'startTime': current\_time.strftime('%H:%M'),</p><p>`        `'endTime': end\_time.strftime('%H:%M'),</p><p>`        `'availableCapacity': available\_capacity,</p><p>`    `}</p><p>`    `if available\_capacity >= number\_of\_people:</p><p>`        `slots.append(slot)</p><p> </p><p>`    `current\_time += timedelta(minutes=SlotService.SLOT\_INTERVAL)</p>|
| :- |

*Phụ lục B.1: Vòng lặp tính khung giờ trống theo bước 15 phút, dựa trên số nhân viên đang trong ca*
## <a name="_toc246366742"></a>**B.2. Tạo lịch hẹn và phân công nhân viên — BookingService.create (trích, spa-booking-api/app/services/booking\_service.py)**

|<p>eligibility = CustomerService.check\_eligibility(phone\_number)</p><p>if not eligibility['isEligible']:</p><p>`    `raise BusinessRuleViolation('CUSTOMER\_BLOCKED', 'Customer on NG List')</p><p> </p><p>if number\_of\_people == 1 and therapist\_preference\_type == 'specific':</p><p>`    `therapist = db.session.query(Therapist).filter(</p><p>`        `Therapist.id == therapist\_id, Therapist.shop\_id == shop\_id,</p><p>`        `Therapist.status == 'active'</p><p>`    `).with\_for\_update(skip\_locked=True).first()</p><p> </p><p>`    `if not therapist or not BookingService.\_is\_therapist\_free(</p><p>`        `therapist.id, booking\_date, start\_time, end\_time</p><p>`    `):</p><p>`        `raise BusinessRuleViolation('SLOT\_UNAVAILABLE',</p><p>`            `'Requested therapist is no longer available at this time')</p><p>`    `assigned\_therapist = therapist</p><p> </p><p>elif number\_of\_people == 1 and therapist\_preference\_type == 'gender':</p><p>`    `therapist = BookingService.\_lock\_available\_therapist\_by\_gender(</p><p>`        `shop\_id, booking\_date, start\_time, end\_time, therapist\_preference\_value)</p><p> </p><p>else:</p><p>`    `# nhóm từ 2 người: không cho chỉ định nhân viên cụ thể,</p><p>`    `# hệ thống tự phân công ngẫu nhiên/ít tải nhất trong số nhân viên còn trống</p>|
| :- |

*Phụ lục B.2: Kiểm tra NG List và phân công nhân viên theo loại yêu cầu (cụ thể / theo giới tính / nhóm), dùng row-level lock (with\_for\_update) để tránh trùng lịch*
## <a name="_toc246366743"></a>**B.3. Thực thi hành động của chatbot AI — ToolOrchestrator (trích, chatbot/conversation/tool\_orchestrator.py)**

|<p>async def propose\_write\_action(self, state, plan):</p><p>`    `"""Đề xuất một hành động ghi dữ liệu (vd: tạo lịch hẹn) và lưu ở trạng thái chờ."""</p><p>`    `tool = self.tool\_registry.get\_tool(plan.tool\_name)</p><p>`    `if not tool or not tool.is\_write:</p><p>`        `raise ValueError(f"Tool '{plan.tool\_name}' is not a write tool")</p><p> </p><p>`    `validated\_args = tool.RequestModel(\*\*plan.tool\_args).model\_dump()</p><p>`    `state.pending\_action = PendingAction(</p><p>`        `tool\_name=plan.tool\_name, arguments=validated\_args,</p><p>`        `status='pending', timestamp=datetime.now(),</p><p>`    `)</p><p> </p><p>async def execute\_pending\_action(self, state):</p><p>`    `"""Chỉ thực thi sau khi khách hàng xác nhận; hết hạn sau 5 phút."""</p><p>`    `if datetime.now() - state.pending\_action.timestamp > timedelta(minutes=5):</p><p>`        `state.pending\_action = None</p><p>`        `raise ValueError('Pending action expired.')</p><p>`    `tool = self.tool\_registry.get(state.pending\_action.tool\_name)</p><p>`    `result = await tool.execute(tool.RequestModel(\*\*state.pending\_action.arguments))</p><p>`    `state.pending\_action = None</p><p>`    `return result.model\_dump()</p>|
| :- |

*Phụ lục B.3: Cơ chế “đề xuất rồi xác nhận” giúp chatbot không tự ý tạo lịch hẹn khi chưa được khách hàng đồng ý*
## <a name="_toc246366744"></a>**PHỤ LỤC C. Danh sách API chính**

|**Endpoint**|**Chức năng**|
| :- | :- |
|GET /api/shops|Danh sách chi nhánh|
|GET /api/shops/{id}/courses|Danh sách dịch vụ của chi nhánh|
|GET /api/shops/{id}/available-slots|Tra cứu khung giờ trống (có thể kèm danh sách nhân viên)|
|GET /api/shops/{id}/available-therapists|Danh sách nhân viên còn trống theo khung giờ|
|POST /api/booking-eligibility-checks|Kiểm tra khách hàng có bị hạn chế (NG List) hay không|
|POST /api/bookings|Tạo lịch hẹn mới|
|GET /api/bookings|Tra cứu lịch hẹn theo số điện thoại|
|GET /api/bookings/{id}|Chi tiết một lịch hẹn|
|PATCH /api/bookings/{id}|Chỉnh sửa lịch hẹn (khi còn ở trạng thái Booked)|
|PATCH /api/bookings/{id}/cancel|Hủy lịch hẹn|
|PATCH /api/bookings/{id}/checkin|Check-in khách hàng|
|PATCH /api/bookings/{id}/checkout|Check-out, hoàn tất dịch vụ|
|POST /api/auth/login|Đăng nhập quản trị viên / nhân viên (trả JWT)|
|POST /api/admin/shops|Tạo chi nhánh mới (yêu cầu JWT)|
|POST /api/admin/shops/{id}/courses|Tạo dịch vụ mới cho chi nhánh (yêu cầu JWT)|
|POST /api/admin/shops/{id}/therapists|Thêm nhân viên mới (yêu cầu JWT)|
|GET /api/admin/bookings|Xem toàn bộ lịch hẹn (yêu cầu JWT)|

***Lưu ý:** Danh sách đầy đủ hơn 40 endpoint được mô tả chi tiết trong docs/REST\_API\_Specification.md của dự án; có thể trích thêm vào phụ lục nếu Khoa yêu cầu đặc tả API đầy đủ.*
## <a name="_toc246366745"></a>**PHỤ LỤC D. Ví dụ minh họa luồng hội thoại đặt lịch qua chatbot AI**
***Lưu ý:** Đoạn hội thoại dưới đây là ví dụ minh họa cho luồng xử lý (không phải log thực tế trích xuất từ hệ thống) — nên thay bằng một đoạn hội thoại thật chụp lại khi chạy thử hệ thống.*

|<p>Khách hàng: Chào shop, chiều mai mình muốn đặt massage vai gáy cho 1 người.</p><p>Trợ lý AI:  Dạ anh/chị muốn đặt tại chi nhánh nào ạ, và khoảng mấy giờ chiều mai?</p><p>Khách hàng: Chi nhánh Quận 1, khoảng 3 giờ chiều.</p><p>Trợ lý AI:  Dạ, chi nhánh Quận 1 lúc 15:00 ngày mai còn trống. Anh/chị có muốn</p><p>`            `chọn nhân viên cụ thể không, hay để shop sắp xếp ạ?</p><p>Khách hàng: Để shop sắp xếp giúp mình.</p><p>Trợ lý AI:  Dạ, xác nhận giúp mình: Massage vai gáy, 1 người, 15:00 ngày mai,</p><p>`            `chi nhánh Quận 1. Mình tiến hành đặt lịch nhé?</p><p>Khách hàng: Ok, đặt giúp mình.</p><p>Trợ lý AI:  Dạ đã đặt lịch thành công, mã lịch hẹn là BK202612050007.</p><p>`            `Hẹn gặp anh/chị lúc 15:00 ngày mai ạ!</p>|
| :- |

*Phụ lục D.1: Ví dụ minh họa luồng đặt lịch qua chatbot AI*
2

[ref1]: Aspose.Words.396207f1-bfe1-4f21-8134-477e6a572cc3.001.png
