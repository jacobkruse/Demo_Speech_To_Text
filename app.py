"""Web UI demo phiên âm tiếng Việt với Whisper Large-v3 (Gradio)."""

import time

import gradio as gr
import librosa

from transcriber import MODEL_ID, get_device_info, transcribe


def run_transcribe(audio_path: str | None, progress=gr.Progress()):
    if not audio_path:
        return "", "⚠️ Vui lòng tải lên file âm thanh hoặc ghi âm trước."

    duration = librosa.get_duration(path=audio_path)
    progress(0.1, desc="Đang load model (lần đầu sẽ mất vài phút để tải ~3GB)...")

    start = time.perf_counter()
    text = transcribe(audio_path)
    elapsed = time.perf_counter() - start

    info = (
        f"✅ Xong — audio dài {duration:.1f}s, "
        f"xử lý hết {elapsed:.1f}s trên {get_device_info()}"
    )
    return text, info


with gr.Blocks(title="Demo Whisper Large-v3 — Phiên âm tiếng Việt") as demo:
    gr.Markdown(
        f"""
        # 🎙️ Demo phiên âm tiếng Việt — Whisper Large-v3
        Model: [`{MODEL_ID}`](https://huggingface.co/{MODEL_ID}) ·
        Hỗ trợ audio dài (tự động cắt chunk 30s) ·
        Thiết bị: **{get_device_info()}**
        """
    )

    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                sources=["upload", "microphone"],
                type="filepath",
                label="Tải file âm thanh (mp3/wav/m4a...) hoặc ghi âm trực tiếp",
            )
            transcribe_btn = gr.Button("📝 Phiên âm", variant="primary")
        with gr.Column():
            output_text = gr.Textbox(
                label="Văn bản tiếng Việt",
                lines=12,
            )
            status = gr.Markdown()

    transcribe_btn.click(
        fn=run_transcribe,
        inputs=audio_input,
        outputs=[output_text, status],
    )

if __name__ == "__main__":
    demo.launch()
