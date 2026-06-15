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
- Skill Claude Code `transcribe-vietnamese` tại `.claude/skills/` — đã chạy thử OK (tự kích
  hoạt, phiên âm file + đọc chính tả). Bản song song cho Codex ở `AGENTS.md` + `.agents/skills/`.

**Việc còn lại (đều tùy chọn):**

1. Dùng skill ở mọi project: copy `.claude/skills/transcribe-vietnamese/` sang `~\.claude\skills\`
   và đổi lệnh trong SKILL.md sang đường dẫn tuyệt đối của repo.
2. Dùng skill-creator (`/skill-creator`) chạy eval + tối ưu `description` cho việc tự kích hoạt
   (đã chọn hướng "test nhanh" thay vì eval đầy đủ).

## Cách dùng nhanh

- Phiên âm file: `& ".venv\Scripts\python.exe" transcriber.py "audio.mp3" --output kq.txt`
- Đọc chính tả (trong Claude Code): gõ `!.venv/Scripts/python dictate.py` → nói → ngừng ~2s
  (hoặc Ctrl+C) → text vào thẳng hội thoại.
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
- **Tiền tố `!` của Claude Code chạy trong bash (Git Bash):** đường dẫn phải dùng gạch chéo
  xuôi `/` (bash nuốt mất `\`), và tiến trình KHÔNG có stdin tương tác (input()→EOFError).
  Vì vậy `dictate.py` không dùng "bấm ENTER để dừng" mà dừng theo im lặng (VAD đơn giản theo
  RMS) hoặc Ctrl+C (là tín hiệu, không phải phím đọc stdin).
- Audio decode bằng librosa/soundfile (không cần ffmpeg) cho wav/mp3/flac/ogg/m4a;
  file video thì phải trích audio bằng ffmpeg trước. Ghi âm dùng `sounddevice`.
- **Ghi âm micro (dictate.py):** `sounddevice` mặc định chọn host API **MME**, trên máy này
  trỏ vào endpoint Realtek **không thu được tiếng** (RMS ~0.002). Web app (trình duyệt) chạy
  được vì dùng **WASAPI** ở **tần số gốc 48kHz**. Vì vậy dictate.py chọn default input của
  WASAPI rồi ghi ở 48kHz và resample về 16kHz (WASAPI không nhận thẳng 16kHz: lỗi -9997).
  Đã test thu được giọng OK. Có `--list-devices` / `--device` nếu cần đổi mic.

## Repo

- Remote: https://github.com/jacobkruse/Demo_Speech_To_Text.git (branch `main`)
- Model cache Hugging Face ở `%USERPROFILE%\.cache\huggingface` (~3GB, tải lần đầu).
