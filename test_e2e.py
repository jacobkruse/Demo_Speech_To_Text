"""Test end-to-end: load model, phiên âm file audio dài >30s trên GPU.

Dùng audio TTS tiếng Anh (Windows không có giọng TTS tiếng Việt để sinh
sample) nên override language="english" — pipeline giống hệt bản tiếng Việt,
chỉ khác giá trị tham số language.
"""

import sys
import time

import librosa

sys.stdout.reconfigure(encoding="utf-8")

from transcriber import SAMPLING_RATE, get_device_info, get_pipeline

AUDIO = "test_audio.wav"

duration = librosa.get_duration(path=AUDIO)
print(f"Audio: {AUDIO} ({duration:.1f}s)")
print(f"Thiết bị: {get_device_info()}")

print("Đang load model...")
t0 = time.perf_counter()
pipe = get_pipeline()
print(f"Load model xong sau {time.perf_counter() - t0:.1f}s")

audio, _ = librosa.load(AUDIO, sr=SAMPLING_RATE, mono=True)
t0 = time.perf_counter()
result = pipe(
    {"array": audio, "sampling_rate": SAMPLING_RATE},
    generate_kwargs={"language": "english", "task": "transcribe"},
)
elapsed = time.perf_counter() - t0

print(f"\nPhiên âm {duration:.1f}s audio hết {elapsed:.1f}s")
print(f"Kết quả:\n{result['text'].strip()}")
