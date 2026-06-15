---
description: Ghi âm tiếng Việt từ micro rồi phiên âm thành văn bản (đọc chính tả)
---

Người dùng muốn đọc chính tả tiếng Việt bằng micro. Làm tuần tự:

1. In ngay một dòng cho người dùng: "🎙️ Bắt đầu ghi âm — HÃY NÓI NGAY BÂY GIỜ. Nói xong
   ngừng ~2 giây là tự dừng (hoặc đợi tới lúc đó)." Đây là tín hiệu để họ nói, vì khi chạy
   qua công cụ thì họ không thấy thông báo realtime của script.

2. Chạy NGAY (đừng hỏi lại) từ thư mục gốc project, đặt timeout >= 300000ms:

   `.venv\Scripts\python.exe dictate.py --output dictation_out.txt --start-timeout 20`

   Script ghi âm trước rồi mới phiên âm; recording bắt đầu gần như tức thì khi tiến trình
   chạy nên người dùng cần nói sớm (có ~20s để bắt đầu trước khi script bỏ cuộc).

3. Đọc file `dictation_out.txt` để lấy văn bản kết quả.
   - Nếu file rỗng / không tồn tại, hoặc script báo "Không nghe rõ giọng" / "Không nghe thấy
     giọng nói": báo người dùng nói to và rõ hơn, bắt đầu nói sớm hơn, rồi chạy lại `/noi`.
   - Nếu người dùng nói "bắt không hết câu": gợi ý họ ngắt nghỉ ít hơn, hoặc lần sau dùng
     `!.venv/Scripts/python dictate.py --silence 3` để nới thời gian im lặng.

4. Trình bày văn bản đã phiên âm. Nếu câu nói của người dùng kèm một yêu cầu (vd "tóm tắt
   lại", "dịch sang tiếng Anh", "sửa code..."), thì tiếp tục thực hiện yêu cầu đó dựa trên
   văn bản vừa phiên âm.
