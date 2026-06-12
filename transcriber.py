"""Module phiên âm tiếng Việt dùng openai/whisper-large-v3.

Model được load lazy (lần gọi đầu tiên) và cache lại cho các lần sau.
Audio được đọc bằng librosa rồi đưa vào pipeline dưới dạng numpy array
để không phụ thuộc vào ffmpeg.
"""

import librosa
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

MODEL_ID = "openai/whisper-large-v3"
SAMPLING_RATE = 16_000  # Whisper yêu cầu 16kHz

_pipe = None


def get_device_info() -> str:
    if torch.cuda.is_available():
        return f"GPU: {torch.cuda.get_device_name(0)}"
    return "CPU (không tìm thấy GPU — sẽ chạy chậm)"


def get_pipeline():
    """Load model lần đầu và trả về pipeline ASR đã cache."""
    global _pipe
    if _pipe is None:
        use_cuda = torch.cuda.is_available()
        device = "cuda:0" if use_cuda else "cpu"
        dtype = torch.float16 if use_cuda else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_ID, dtype=dtype)
        model.to(device)

        processor = AutoProcessor.from_pretrained(MODEL_ID)

        _pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            # Audio dài hơn 30s được cắt thành các chunk 30s xử lý song song
            chunk_length_s=30,
            batch_size=8,
            device=device,
        )
    return _pipe


def transcribe(audio_path: str) -> str:
    """Phiên âm một file âm thanh tiếng Việt thành văn bản."""
    audio, _ = librosa.load(audio_path, sr=SAMPLING_RATE, mono=True)

    pipe = get_pipeline()
    result = pipe(
        {"array": audio, "sampling_rate": SAMPLING_RATE},
        generate_kwargs={"language": "vietnamese", "task": "transcribe"},
    )
    return result["text"].strip()


if __name__ == "__main__":
    import argparse
    import sys
    import time
    from pathlib import Path

    # Console Windows mặc định dùng codepage cũ (cp1252) không in được tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Phiên âm file âm thanh tiếng Việt bằng Whisper Large-v3"
    )
    parser.add_argument("audio", help="Đường dẫn file âm thanh (mp3/wav/m4a/flac/ogg...)")
    parser.add_argument(
        "-o", "--output",
        help="Ghi văn bản kết quả ra file .txt (UTF-8), ngoài việc in ra console",
    )
    args = parser.parse_args()

    # Trạng thái in ra stderr để stdout chỉ chứa văn bản kết quả —
    # tiện cho script/agent khác gọi và lấy kết quả trực tiếp
    print(f"Thiết bị: {get_device_info()}", file=sys.stderr)
    print("Đang load model (lần đầu sẽ tải ~3GB)...", file=sys.stderr)
    start = time.perf_counter()
    text = transcribe(args.audio)
    elapsed = time.perf_counter() - start
    print(f"Xong sau {elapsed:.1f}s", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Đã ghi kết quả vào: {args.output}", file=sys.stderr)

    print(text)
