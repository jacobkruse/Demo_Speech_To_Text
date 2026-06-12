# Ngữ cảnh project — DemoWhisper_Large

Demo phiên âm (speech-to-text) tiếng Việt bằng `openai/whisper-large-v3` (HF Transformers),
có web UI Gradio và CLI. Xem README.md cho hướng dẫn cài đặt/chạy đầy đủ.

## Trạng thái hiện tại (cập nhật 2026-06-12)

**Đã xong và đã kiểm chứng** (trên máy gốc: Windows 11, RTX 5070 Ti 16GB, Python 3.14):

- `transcriber.py` — load model + `transcribe()`, ép `language="vietnamese"`, audio dài >30s
  xử lý qua chunk. CLI: `python transcriber.py <audio> [--output out.txt]`.
  stdout chỉ chứa văn bản kết quả, trạng thái in ra stderr.
- `app.py` — web UI Gradio (upload + ghi âm micro), đã chạy OK tại http://127.0.0.1:7860.
- Test end-to-end pass: phiên âm 39.5s audio mất 2.7s trên GPU.
- `test_e2e.py` — smoke test (dùng audio TTS tiếng Anh vì Windows không có giọng TTS tiếng Việt;
  file `test_audio.wav` bị gitignore, tái tạo bằng PowerShell:
  `Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SetOutputToWaveFile("test_audio.wav"); $s.Speak("Hello, this is a test. " * 6); $s.Dispose()`).

**Đang làm dở: biến project thành skill cho Claude Code**

- Draft skill nằm tại `.claude/skills/transcribe-vietnamese/SKILL.md` (project skill,
  tự nạp khi mở Claude Code trong repo này; dùng đường dẫn tương đối nên chạy được trên máy khác
  sau khi setup venv).
- Các bước còn lại:
  1. Trên máy mới: tạo venv + cài requirements (xem lưu ý GPU bên dưới), chạy `test_e2e.py` xác nhận.
  2. Test nhanh skill: nhờ Claude Code phiên âm một file audio, xem skill có tự kích hoạt và chạy đúng.
  3. (Tùy chọn) Nếu muốn dùng skill ở mọi project: copy sang `~\.claude\skills\` và đổi các lệnh
     trong SKILL.md sang đường dẫn tuyệt đối của repo trên máy đó.
  4. (Tùy chọn) Dùng skill-creator (`/skill-creator`) để chạy eval và tối ưu description cho việc
     tự kích hoạt (đã chọn hướng "test nhanh" thay vì eval đầy đủ).

## Bẫy kỹ thuật đã gặp (tránh mất thời gian lại)

- **torch trên Windows/PyPI là bản CPU.** Phải cài từ index PyTorch. `requirements.txt` đang pin
  `torch==2.12.0+cu130` cho RTX 50-series (Blackwell cần CUDA ≥ 12.8). Máy khác GPU đời cũ hơn
  có thể dùng cu126/cu128; không GPU thì bỏ pin và dòng `--extra-index-url` để dùng bản CPU.
  Python 3.14 cần torch ≥ 2.9 (wheel cp314).
- **transformers v5** (đang dùng 5.11.0): dùng `dtype=` chứ không phải `torch_dtype=` trong
  `from_pretrained`; các tham số `low_cpu_mem_usage`/`use_safetensors` đã bỏ.
- **gradio 6**: `gr.Textbox` không còn `show_copy_button`.
- **Console Windows mặc định cp1252** không in được tiếng Việt → code đã có
  `sys.stdout.reconfigure(encoding="utf-8")`; khi chạy script khác in tiếng Việt,
  đặt `$env:PYTHONUTF8 = "1"`.
- Audio decode bằng librosa/soundfile (không cần ffmpeg) cho wav/mp3/flac/ogg/m4a;
  file video thì phải trích audio bằng ffmpeg trước.

## Repo

- Remote: https://github.com/jacobkruse/Demo_Speech_To_Text.git (branch `main`)
- Model cache Hugging Face nằm ở `%USERPROFILE%\.cache\huggingface` (~3GB, tải lần đầu).
