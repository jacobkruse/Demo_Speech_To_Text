---
name: transcribe-vietnamese
description: Phiên âm (speech-to-text) file âm thanh tiếng Việt thành văn bản bằng Whisper Large-v3 chạy trên GPU cục bộ. Dùng skill này bất cứ khi nào người dùng muốn chuyển giọng nói thành văn bản, phiên âm, gỡ băng ghi âm, lấy nội dung từ file âm thanh (mp3, wav, m4a, flac, ogg), làm phụ đề, hoặc tóm tắt/xử lý nội dung một file audio — kể cả khi họ không dùng từ "phiên âm" (ví dụ "file ghi âm cuộc họp này nói gì", "lấy text từ audio này", "transcribe this recording").
---

# Phiên âm tiếng Việt với Whisper Large-v3

Project này (thư mục gốc repo, nơi có `transcriber.py`) đã có sẵn mọi thứ: venv riêng
tại `.venv\`, model whisper-large-v3 (tự tải về cache HF lần chạy đầu), chạy GPU nếu có.
Không cần cài đặt gì thêm — chỉ cần gọi đúng lệnh dưới đây từ thư mục gốc của project.

## Lệnh chạy

```powershell
& ".venv\Scripts\python.exe" "transcriber.py" "<đường_dẫn_file_âm_thanh>" --output "<file_kết_quả.txt>"
```

- Đường dẫn chứa khoảng trắng phải đặt trong dấu nháy kép.
- Luôn dùng `--output` rồi đọc file kết quả bằng tool Read — đáng tin cậy hơn parse stdout,
  nhất là với audio dài.
- stdout chỉ chứa văn bản phiên âm; các dòng trạng thái (thiết bị, thời gian xử lý)
  nằm ở stderr.
- Nếu venv chưa tồn tại (máy mới clone repo): làm theo mục "Cài đặt" trong README.md trước,
  chú ý phần lưu ý GPU trong CLAUDE.md.

## Đọc chính tả: nói trực tiếp vào micro

Khi người dùng muốn **nói** thay vì đưa file có sẵn ("ghi âm giúp tôi", "tôi đọc rồi
bạn ghi lại", "dictate"), dùng `dictate.py` — ghi âm từ micro rồi phiên âm.

Hướng dẫn người dùng tự chạy bằng tiền tố `!` trong ô nhập của Claude Code; văn bản in ra
sẽ vào thẳng hội thoại để Claude đọc. Tiền tố `!` chạy trong bash (Git Bash) nên đường dẫn
phải dùng gạch chéo xuôi `/`, KHÔNG dùng `\` (bash nuốt mất dấu `\`):

```
!.venv/Scripts/python dictate.py
```

Dừng ghi: người dùng **ngừng nói ~2s** (tự dừng) hoặc **bấm Ctrl+C** để dừng ngay (vẫn phiên
âm phần đã ghi). KHÔNG dùng phím gõ (ENTER...) để dừng được khi chạy qua `!` vì tiến trình
không có stdin tương tác (sẽ EOF); Ctrl+C dùng được vì là tín hiệu. Người dùng nói, ngừng nói,
văn bản tiếng Việt hiện ra; Claude đọc và xử lý tiếp. Biến thể:

- `!.venv/Scripts/python dictate.py --silence 3` — nói chậm/ngắt nhiều thì nới thời lặng để
  khỏi bị cắt giữa câu (mặc định 2.0s).
- `!.venv/Scripts/python dictate.py --seconds 15` — ghi cố định 15 giây.
- `!.venv/Scripts/python dictate.py -o ghichu.txt` — đồng thời lưu kết quả ra file.

Nếu người dùng than "bắt không hết câu": họ ngắt giữa câu lâu hơn thời lặng nên bị dừng sớm —
khuyên dùng `--silence 3` (hoặc cao hơn), hoặc bấm Ctrl+C khi nói xong.

Lưu ý: KHÔNG tự chạy `dictate.py` qua Bash/PowerShell hộ người dùng để "đọc thay" — nó cần
giọng nói thật từ micro của họ. Nếu cần Claude tự kích hoạt ghi âm (hiếm), chỉ nhánh
`--seconds N` mới hợp lý.

## Lưu ý khi chạy

- **Timeout**: đặt timeout tối thiểu 300000ms (5 phút). Mỗi lần gọi phải load model từ cache
  đĩa (~30–60s), sau đó phiên âm rất nhanh trên GPU (~40s audio xử lý trong ~3s).
  Nếu cache Hugging Face trống, lần chạy đầu sẽ tải model ~3GB — có thể mất hơn 10 phút.
- **Audio dài**: hỗ trợ sẵn, file dài hơn 30 giây được tự cắt chunk xử lý theo batch.
  Không cần chia nhỏ file trước.
- **Định dạng hỗ trợ**: wav, mp3, flac, ogg, m4a (decode bằng librosa/soundfile, không cần
  ffmpeg). Với file **video** (mp4, mkv...) hoặc định dạng không đọc được: trích audio ra wav
  trước bằng ffmpeg nếu máy có (`ffmpeg -i video.mp4 -vn -ac 1 -ar 16000 audio.wav`),
  nếu không có ffmpeg thì báo người dùng cung cấp file âm thanh.
- **Ngôn ngữ**: model được ép `language="vietnamese"`. Nếu người dùng muốn phiên âm ngôn ngữ
  khác, nói rõ là skill này hiện cấu hình cho tiếng Việt (có thể sửa `transcriber.py`
  nếu họ yêu cầu).

## Xử lý lỗi thường gặp

- `FileNotFoundError` / librosa không đọc được file → kiểm tra đường dẫn tồn tại,
  đúng định dạng âm thanh; nếu là video thì trích audio như trên.
- `torch.cuda.OutOfMemoryError` → GPU đang bị process khác chiếm VRAM; đề nghị người dùng
  đóng ứng dụng đang dùng GPU rồi chạy lại.
- Lỗi mạng khi tải model → cache trống và máy không kết nối được huggingface.co;
  báo người dùng kiểm tra mạng.

## Sau khi có kết quả

Đọc file .txt kết quả và trả lời theo đúng yêu cầu gốc của người dùng: nếu họ chỉ cần
văn bản thì đưa văn bản; nếu họ nhờ tóm tắt/dịch/làm phụ đề thì tiếp tục xử lý văn bản đó.
Whisper không thêm dấu câu hoàn hảo — có thể chỉnh nhẹ chính tả/dấu câu khi người dùng
yêu cầu bản "sạch", nhưng đừng tự ý sửa nội dung.
