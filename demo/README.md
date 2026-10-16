# StockPilot narrated presentation

- [Narrated MP4](StockPilot-Capstone-Narrated.mp4)
- [PowerPoint with editable text, shapes and speaker notes](../docs/presentation/StockPilot-Capstone.pptx)
- [Matching PDF](../docs/presentation/StockPilot-Capstone.pdf)
- [Full narration transcript](NARRATION.md)
- [Chapter timestamps](CHAPTERS.md)
- [English captions](StockPilot-Capstone.srt)
- [Live demonstration runbook](RUNBOOK.md)

The recording is an original illustrated technical walkthrough, with **Kokoro neural synthetic English narration** using the generic `af_heart` voice. It covers the product, stack, data model, three stock workflows, background reporting, concurrency, delivery, Kubernetes, security, observability, GitOps and Terraform. The presentation uses native editable PowerPoint text and shapes; the PDF is rendered from the same scene definitions. The voice does not imitate an identified person.

This is **not a live browser, Docker, Kubernetes or AWS recording**. Chromium startup and local socket creation are denied in the current execution environment. Application and platform claims are tied to source files, while successful checks are recorded in [the evidence register](../docs/evidence.md). The recording shows only the presentation.

To regenerate with installed Python dependencies:

```bash
python -m pip install python-pptx Pillow
python docs/presentation/build_presentation.py
```

Video generation additionally needs FFmpeg and either Kokoro ONNX or espeak-ng. Set `STOCKPILOT_TTS_MODEL` and `STOCKPILOT_TTS_VOICES` to local Kokoro model/voice files to select a neural generic voice. No voice cloning or external narration service is used.

```bash
python -m pip install kokoro-onnx
export STOCKPILOT_TTS_MODEL=/path/to/kokoro-v1.0.int8.onnx
export STOCKPILOT_TTS_VOICES=/path/to/voices-v1.0.bin
python docs/presentation/build_presentation.py --video
```

The script currently uses Noto Sans fonts from `/usr/share/fonts/google-noto`; adjust `FONT_DIR` on another operating system. Intermediate audio and video segments are ignored under `.render/`.

Speech implementation: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (MIT), [Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M) (Apache 2.0). The StockPilot application, slide layouts, diagrams and narration are original.
