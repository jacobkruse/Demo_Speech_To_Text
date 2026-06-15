# Ngữ cảnh project — DemoWhisper_Large

Demo phiên âm (speech-to-text) tiếng Việt bằng `openai/whisper-large-v3` (HF Transformers),
có web UI Gradio, CLI, và đọc chính tả từ micro. Xem README.md cho hướng dẫn cài đặt/chạy.

## Trạng thái hiện tại (cập nhật 2026-06-16)

**Đã xong và đã kiểm chứng** (Windows 11, RTX 5070 Ti 16GB, Python 3.14):

- `transcriber.py` — load model + `transcribe()`, ép `language="vietnamese"`, audio dài >30s
  xử lý qua chunk. CLI: `python transcriber.py <audio> [--output out.txt]`.
  stdout chỉ chứa văn bản kết quả, trạng thái in ra stderr.
- `app.py` — web UI Gradio (upload + ghi âm micro), chạy OK tại http://127.0.0.1:7860.
- `dictate.py` — ghi âm từ micro rồi phiên âm (đọc chính tả). Tự dừng khi im lặng ~2s
  hoặc bấm Ctrl+C; có `--seconds`, `--silence`, `--output`. Đã test đọc tiếng Việt OK.
- `test_e2e.py` — smoke test (audio TTS tiếng Anh vì Windows không có giọng TTS tiếng Việt;
  `test_audio.wav` bị gitignore, tái tạo bằng PowerShell:
  `Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SetOutputToWaveFile("test_audio.wav"); $s.Speak("Hello, this is a test. " * 6); $s.Dispose()`).
- Skill Codex `transcribe-vietnamese` tại `.agents/skills/` — đồng bộ với bản Claude Code ở
  `.claude/skills/`. Đã chạy thử OK (phiên âm file + đọc chính tả).

**Việc còn lại (đều tùy chọn):**

1. Dùng skill ở mọi project: copy `.agents/skills/transcribe-vietnamese/` sang vị trí skill
   global của Codex và đổi lệnh trong SKILL.md sang đường dẫn tuyệt đối của repo.
2. Chạy eval + tối ưu `description` cho việc tự kích hoạt (đã chọn hướng "test nhanh").

## Cách dùng nhanh

- Phiên âm file: `& ".venv\Scripts\python.exe" transcriber.py "audio.mp3" --output kq.txt`
- Đọc chính tả: chạy `.venv\Scripts\python dictate.py -o ghichu.txt` trong terminal, nói →
  ngừng ~2s (hoặc Ctrl+C) → đọc `ghichu.txt`.
- Web UI: `& ".venv\Scripts\python.exe" app.py` → http://127.0.0.1:7860

## Bẫy kỹ thuật đã gặp (tránh mất thời gian lại)

- **torch trên Windows/PyPI là bản CPU.** Phải cài từ index PyTorch. `requirements.txt` pin
  `torch==2.12.0+cu130` cho RTX 50-series (Blackwell cần CUDA ≥ 12.8). GPU đời cũ hơn có thể
  dùng cu126/cu128; không GPU thì bỏ pin và dòng `--extra-index-url` để dùng bản CPU.
  Python 3.14 cần torch ≥ 2.9 (wheel cp314).
- **transformers v5** (5.11.0): dùng `dtype=` chứ không phải `torch_dtype=` trong
  `from_pretrained`; các tham số `low_cpu_mem_usage`/`use_safetensors` đã bỏ.
- **gradio 6**: `gr.Textbox` không còn `show_copy_button`.
- **Console Windows mặc định cp1252** không in được tiếng Việt → code có
  `sys.stdout.reconfigure(encoding="utf-8")`; chạy script khác in tiếng Việt thì đặt
  `$env:PYTHONUTF8 = "1"`.
- **`dictate.py` không dùng "bấm ENTER để dừng":** khi chạy không có stdin tương tác,
  `input()` ném EOFError. Vì vậy dừng theo im lặng (VAD đơn giản theo RMS) hoặc Ctrl+C
  (là tín hiệu, không phải phím đọc stdin). Nếu chạy qua một shell wrapper (vd tiền tố `!`
  của Claude Code) thì đường dẫn dùng gạch chéo xuôi `/` vì wrapper chạy trong bash.
- Audio decode bằng librosa/soundfile (không cần ffmpeg) cho wav/mp3/flac/ogg/m4a;
  file video thì phải trích audio bằng ffmpeg trước. Ghi âm dùng `sounddevice`.

## Repo

- Remote: https://github.com/jacobkruse/Demo_Speech_To_Text.git (branch `main`)
- Model cache Hugging Face ở `%USERPROFILE%\.cache\huggingface` (~3GB, tải lần đầu).
