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

# CỐ Ý không import torch/transformers/librosa ở đây. Chúng nặng (vài giây) và
# chỉ cần khi phiên âm. Import sớm sẽ khiến prompt "Đang ghi âm" hiện chậm. Phần
# transcribe nạp chúng lazy ở main, ngay sau khi đã ghi xong (chạy nền lúc đang nói).
SAMPLING_RATE = 16000  # 16kHz mono là định dạng Whisper cần

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Ghi ở tần số gốc của thiết bị (vd 48kHz) rồi resample về 16kHz cho Whisper.
# Lý do: nhiều mic trên Windows (WASAPI) chỉ chấp nhận tần số gốc, không nhận
# thẳng 16kHz; ghi sai host API/tần số là nguyên nhân "không thu được tiếng".
MIN_SAMPLES = int(SAMPLING_RATE * 0.3)  # dưới 0.3s coi như không nói gì
BLOCK_SEC = 0.1  # độ dài mỗi khối xử lý mức âm lượng
ONSET_BLOCKS = 3  # cần bấy nhiêu khối to LIÊN TIẾP mới tính là bắt đầu có giọng
MIN_VOICED_SEC = 0.4  # tổng thời lượng có tiếng nói tối thiểu để đáng phiên âm


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block.astype(np.float64) ** 2))) if block.size else 0.0


def default_input_device() -> int:
    """Chọn mic mặc định của WASAPI (giống thiết bị trình duyệt/web app dùng).

    sounddevice mặc định chọn host API MME, trên máy này lại trỏ vào endpoint
    Realtek không thu được tiếng. WASAPI là host API mà Windows/trình duyệt dùng.
    """
    for h in sd.query_hostapis():
        if "wasapi" in h["name"].lower() and h["default_input_device"] >= 0:
            return h["default_input_device"]
    return sd.default.device[0]


def device_samplerate(device: int) -> int:
    """Tần số lấy mẫu gốc của thiết bị (WASAPI bắt buộc dùng đúng tần số này)."""
    return int(sd.query_devices(device)["default_samplerate"])


def record_until_silence(silence_hang: float, max_duration: float,
                         start_timeout: float, device: int, rec_sr: int) -> np.ndarray:
    """Ghi âm, dừng khi im lặng đủ lâu hoặc khi người dùng bấm Ctrl+C.

    Ghi ở tần số gốc rec_sr của thiết bị; phần resample về 16kHz làm ở main.

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
    blocksize = int(rec_sr * BLOCK_SEC)

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

    with sd.InputStream(samplerate=rec_sr, channels=1, dtype="float32", device=device,
                        blocksize=blocksize, callback=callback):
        try:
            while True:
                try:
                    block = q.get(timeout=0.2)
                except queue.Empty:
                    continue
                frames.append(block)
                dur = len(block) / rec_sr
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


def list_input_devices() -> None:
    """In các thiết bị thu (micro) kèm chỉ số để chọn bằng --device."""
    default_in = sd.default.device[0]
    print("Các micro (input) khả dụng:", file=sys.stderr)
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            mark = " (mặc định)" if i == default_in else ""
            name = dev["name"].splitlines()[0]  # vài tên có xuống dòng
            print(f"  [{i}] {name}{mark}", file=sys.stderr)


def resolve_device(spec: str) -> int:
    """Đổi --device (chỉ số hoặc một phần tên) thành chỉ số thiết bị."""
    if spec.strip().lstrip("-").isdigit():
        return int(spec)
    spec_low = spec.lower()
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and spec_low in dev["name"].lower():
            return i
    raise SystemExit(f"Không tìm thấy micro khớp '{spec}'. "
                     f"Chạy --list-devices để xem danh sách.")


def record_seconds(seconds: float, device: int, rec_sr: int) -> np.ndarray:
    """Ghi âm cố định N giây ở tần số gốc rec_sr."""
    print(f"🎙️  Đang ghi âm {seconds:g}s... NÓI đi.", file=sys.stderr)
    audio = sd.rec(int(seconds * rec_sr), samplerate=rec_sr,
                   channels=1, dtype="float32", device=device)
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
    parser.add_argument("--device",
                        help="Chọn micro theo chỉ số hoặc một phần tên (vd 20 hoặc AirPods)")
    parser.add_argument("--list-devices", action="store_true",
                        help="Liệt kê các micro khả dụng rồi thoát")
    args = parser.parse_args()

    if args.list_devices:
        list_input_devices()
        return

    # Chọn mic: --device nếu có, không thì mic mặc định của WASAPI (như web app)
    device = resolve_device(args.device) if args.device else default_input_device()
    rec_sr = device_samplerate(device)
    print(f"Micro: [{device}] {sd.query_devices(device)['name'].splitlines()[0]} "
          f"@ {rec_sr} Hz", file=sys.stderr)

    # Ghi âm NGAY (chưa đụng tới torch/transformers nên prompt hiện gần như tức thì)
    if args.seconds:
        audio = record_seconds(args.seconds, device, rec_sr)
    else:
        audio = record_until_silence(args.silence, args.max, args.start_timeout,
                                     device, rec_sr)

    if audio.size == 0:  # các hàm ghi âm đã in lý do (không nghe giọng / im lặng)
        sys.exit(1)

    # Giờ mới nạp thư viện nặng (đã ghi xong; không bắt người dùng chờ lúc đầu)
    print("Đang nạp model & phiên âm...", file=sys.stderr)
    import librosa
    from transcriber import get_device_info, get_pipeline

    # Resample về 16kHz cho Whisper (đã ghi ở tần số gốc của thiết bị)
    if rec_sr != SAMPLING_RATE:
        audio = librosa.resample(audio, orig_sr=rec_sr, target_sr=SAMPLING_RATE)

    if audio.size < MIN_SAMPLES:
        print("⚠️  Không ghi được âm thanh (quá ngắn hoặc sai micro mặc định).",
              file=sys.stderr)
        sys.exit(1)

    print(f"Đã ghi {audio.size / SAMPLING_RATE:.1f}s ({get_device_info()}).",
          file=sys.stderr)
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
