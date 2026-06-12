# Demo Whisper Large-v3 — Phiên âm tiếng Việt

Project demo dùng model [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)
(thư viện 🤗 Transformers) để chuyển giọng nói tiếng Việt thành văn bản, với giao diện web Gradio.

## Tính năng

- 🎙️ Upload file âm thanh (mp3, wav, m4a, flac...) hoặc **ghi âm trực tiếp từ micro**
- 🇻🇳 Phiên âm tiếng Việt (ép `language="vietnamese"` để model không đoán nhầm ngôn ngữ)
- ⏱️ Hỗ trợ **audio dài hơn 30 giây** — tự động cắt thành chunk 30s và xử lý theo batch
- ⚡ Tự phát hiện GPU: chạy CUDA + float16 nếu có, fallback CPU + float32 nếu không

## Cấu trúc

| File | Vai trò |
|---|---|
| `transcriber.py` | Load model + hàm `transcribe()`. Chạy được độc lập như CLI. |
| `app.py` | Giao diện web Gradio, gọi vào `transcriber.py`. |
| `requirements.txt` | Dependencies (PyTorch build CUDA 13.0 cho GPU RTX 50-series). |

## Cài đặt

```powershell
# Trong thư mục project (đã có sẵn .venv)
.venv\Scripts\python -m pip install -r requirements.txt
```

> **Lưu ý GPU:** `requirements.txt` pin `torch==2.12.0+cu130` từ index PyTorch vì RTX 5070 Ti
> (kiến trúc Blackwell) cần PyTorch build với CUDA ≥ 12.8, trong khi bản torch mặc định trên
> PyPI cho Windows là bản **CPU**. Nếu không pin, pip sẽ cài nhầm bản CPU.

## Chạy demo

### Web UI (Gradio)

```powershell
.venv\Scripts\python app.py
```

Mở trình duyệt tại địa chỉ hiện ra (mặc định http://127.0.0.1:7860), upload file hoặc ghi âm,
bấm **Phiên âm**.

### Dòng lệnh

```powershell
.venv\Scripts\python transcriber.py duong_dan\file_am_thanh.mp3
```

## Lưu ý

- **Lần chạy đầu tiên** sẽ tải model ~3GB từ Hugging Face về cache
  (`%USERPROFILE%\.cache\huggingface`), mất vài phút tùy mạng. Các lần sau load từ cache.
- Model chiếm khoảng **6–10GB VRAM** ở float16 (RTX 5070 Ti 16GB là thoải mái).
- Nếu cần nhanh hơn nữa với chất lượng gần tương đương, đổi `MODEL_ID` trong
  `transcriber.py` thành `openai/whisper-large-v3-turbo` (nhẹ và nhanh hơn ~2 lần).
- Audio được decode bằng `librosa`/`soundfile` nên **không cần cài ffmpeg** cho các định dạng
  phổ biến (wav, mp3, flac, ogg). Nếu gặp định dạng lạ không đọc được, cài thêm
  [ffmpeg](https://ffmpeg.org/download.html) và thêm vào PATH.
