"""Ghi âm từ micro rồi phiên âm tiếng Việt — đọc chính tả cho Claude Code.

Chạy script này bằng tiền tố `!` trong ô nhập của Claude Code; văn bản phiên âm
in ra sẽ xuất hiện ngay trong hội thoại để Claude ghi nhận. Tiền tố `!` chạy trong
bash nên đường dẫn dùng gạch chéo xuôi `/`.

Dừng ghi: ngừng nói ~2s sẽ TỰ DỪNG, hoặc bấm Ctrl+C để dừng ngay (vẫn phiên âm phần
đã ghi). Không dùng phím gõ (ENTER...) để dừng được khi chạy qua `!` vì tiến trình không
có stdin tương tác (sẽ EOF); Ctrl+C dùng được vì là tín hiệu, không phải phím đọc stdin.

Cách dùng:
    !.venv/Scripts/python dictate.py                  # nói; im lặng ~2s (hoặc Ctrl+C) là dừng
    !.venv/Scripts/python dictate.py --silence 3       # nói chậm/ngắt nhiều: nới thời lặng
    !.venv/Scripts/python dictate.py --seconds 15      # ghi cố định 15 giây
    !.venv/Scripts/python dictate.py -o ghichu.txt     # đồng thời lưu ra file
"""

import argparse
import queue
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

from transcriber import SAMPLING_RATE, get_device_info, get_pipeline

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Ghi ở đúng 16kHz mono mà Whisper cần, nên không phải resample lại
MIN_SAMPLES = int(SAMPLING_RATE * 0.3)  # dưới 0.3s coi như không nói gì
BLOCK_SEC = 0.1  # độ dài mỗi khối xử lý mức âm lượng
ONSET_BLOCKS = 3  # cần bấy nhiêu khối to LIÊN TIẾP mới tính là bắt đầu có giọng
MIN_VOICED_SEC = 0.4  # tổng thời lượng có tiếng nói tối thiểu để đáng phiên âm


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block.astype(np.float64) ** 2))) if block.size else 0.0


def record_until_silence(silence_hang: float, max_duration: float,
                         start_timeout: float) -> np.ndarray:
    """Ghi âm, dừng khi im lặng đủ lâu hoặc khi người dùng bấm Ctrl+C.

    - Hiệu chỉnh nền ồn trong ~0.4s đầu để đặt ngưỡng giọng nói.
    - Chỉ tính "có giọng" khi đủ ONSET_BLOCKS khối to liên tiếp (chống ồn nền giật cục
      khiến Whisper "ảo giác" trên đoạn không có lời).
    - Chờ tới khi nghe thấy giọng (tối đa start_timeout giây).
    - Dừng khi: im lặng liên tục silence_hang giây, HOẶC bấm Ctrl+C (dừng ngay, vẫn
      phiên âm phần đã ghi), HOẶC chạm max_duration (chốt an toàn).
    - Nếu tổng thời lượng có tiếng nói < MIN_VOICED_SEC thì coi như không nghe rõ giọng
      và trả về rỗng (không phiên âm để tránh ra câu rác).
    """
    print("🎙️  Đang ghi âm... cứ NÓI; im lặng ~{:g}s sẽ tự dừng, "
          "hoặc bấm Ctrl+C để dừng ngay.".format(silence_hang), file=sys.stderr)
    q: queue.Queue = queue.Queue()
    blocksize = int(SAMPLING_RATE * BLOCK_SEC)

    def callback(indata, _frames, _time, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    frames: list[np.ndarray] = []
    calib: list[float] = []
    threshold: float | None = None
    speech_started = False
    consec_voiced = 0        # số khối to liên tiếp (để xác nhận bắt đầu có giọng)
    voiced_blocks = 0        # tổng số khối có tiếng nói (để kiểm tra cuối)
    silence_run = 0.0
    waited = 0.0
    elapsed = 0.0

    with sd.InputStream(samplerate=SAMPLING_RATE, channels=1, dtype="float32",
                        blocksize=blocksize, callback=callback):
        try:
            while True:
                try:
                    block = q.get(timeout=0.2)
                except queue.Empty:
                    continue
                frames.append(block)
                dur = len(block) / SAMPLING_RATE
                elapsed += dur
                level = _rms(block)

                if threshold is None:  # đang hiệu chỉnh nền ồn
                    calib.append(level)
                    if len(calib) >= 4:
                        noise = sum(calib) / len(calib)
                        # ngưỡng kẹp trong [0.012, 0.05] để tránh quá nhạy/quá điếc
                        threshold = max(min(noise * 3.5, 0.05), 0.012)
                    continue

                voiced = level > threshold
                if voiced:
                    voiced_blocks += 1

                if not speech_started:
                    waited += dur
                    # cần đủ khối to LIÊN TIẾP mới tính là có giọng (ồn nền giật
                    # cục một khối sẽ bị reset, không kích hoạt nhầm)
                    consec_voiced = consec_voiced + 1 if voiced else 0
                    if consec_voiced >= ONSET_BLOCKS:
                        speech_started = True
                    elif waited >= start_timeout:
                        print("⚠️  Không nghe thấy giọng nói trong {:g}s.".format(start_timeout),
                              file=sys.stderr)
                        return np.zeros(0, np.float32)  # bỏ đoạn ồn nền, không phiên âm
                else:
                    if voiced:
                        silence_run = 0.0
                    else:
                        silence_run += dur
                        if silence_run >= silence_hang:
                            break

                if elapsed >= max_duration:
                    print("⏱️  Đạt giới hạn {:g}s, dừng ghi.".format(max_duration),
                          file=sys.stderr)
                    break
        except KeyboardInterrupt:
            print("\n⏹️  Dừng ghi (Ctrl+C).", file=sys.stderr)

    while not q.empty():  # vét nốt buffer còn lại
        frames.append(q.get())

    # Chống "ảo giác": nếu hầu như không có tiếng nói thì đừng phiên âm
    if voiced_blocks * BLOCK_SEC < MIN_VOICED_SEC:
        print("⚠️  Không nghe rõ giọng (gần như im lặng) — bỏ qua, "
              "hãy nói rõ hơn rồi thử lại.", file=sys.stderr)
        return np.zeros(0, np.float32)

    return np.concatenate(frames).flatten() if frames else np.zeros(0, np.float32)


def record_seconds(seconds: float) -> np.ndarray:
    """Ghi âm cố định N giây."""
    print(f"🎙️  Đang ghi âm {seconds:g}s... NÓI đi.", file=sys.stderr)
    audio = sd.rec(int(seconds * SAMPLING_RATE), samplerate=SAMPLING_RATE,
                   channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ghi âm micro rồi phiên âm tiếng Việt"
    )
    parser.add_argument("--seconds", type=float,
                        help="Ghi cố định N giây thay vì tự dừng khi im lặng")
    parser.add_argument("--silence", type=float, default=2.0,
                        help="Số giây im lặng để tự dừng (mặc định 2.0)")
    parser.add_argument("--max", type=float, default=120.0,
                        help="Giới hạn thời gian ghi tối đa (mặc định 120s)")
    parser.add_argument("--start-timeout", type=float, default=15.0,
                        help="Chờ tối đa bấy nhiêu giây để nghe thấy giọng (mặc định 15)")
    parser.add_argument("-o", "--output",
                        help="Ghi văn bản kết quả ra file .txt (UTF-8)")
    args = parser.parse_args()

    print(f"Thiết bị: {get_device_info()}", file=sys.stderr)
    if args.seconds:
        audio = record_seconds(args.seconds)
    else:
        audio = record_until_silence(args.silence, args.max, args.start_timeout)

    if audio.size < MIN_SAMPLES:
        print("⚠️  Không ghi được âm thanh (quá ngắn hoặc sai micro mặc định).",
              file=sys.stderr)
        sys.exit(1)

    print(f"Đã ghi {audio.size / SAMPLING_RATE:.1f}s. Đang phiên âm...", file=sys.stderr)
    pipe = get_pipeline()
    result = pipe(
        {"array": audio, "sampling_rate": SAMPLING_RATE},
        generate_kwargs={"language": "vietnamese", "task": "transcribe"},
    )
    text = result["text"].strip()

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Đã ghi kết quả vào: {args.output}", file=sys.stderr)

    print(text)


if __name__ == "__main__":
    main()
