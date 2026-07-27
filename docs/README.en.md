# Order Paper OCR

[中文](../README.md) · **English** · [Français](README.fr.md)

Order Paper OCR is a Windows desktop application that corrects delivery-note photos, groups pages by order, reads product rows, independently verifies box-count markings, supports manual review, and exports a two-column Excel file containing only product code and box count.

The interface switches live between Chinese, English and French. Select the globe language icon in the toolbar or change Language in Settings. Recognized product codes, order numbers and evidence are never rewritten by the UI language switch.

## Recognition pipeline

- EXIF orientation, four-way rotation scoring, page detection and perspective correction
- color-preserving denoising, shadow correction and contrast enhancement
- local RapidOCR/ONNX text and position hints
- OpenAI Responses API image input with strict Pydantic structured outputs
- whole-page extraction plus independent row verification using page, row and enlarged column crops
- Python-only final box-count rule calculation
- SQLite recovery, SHA-256 duplicate detection and API result caching

## Box-count rule

The final value never comes from the total quantity column.

1. A clearly associated non-negative handwritten box override has highest priority.
2. Otherwise, a printed box count inside a clearly closed circle is kept.
3. Otherwise, a confirmed absence of a closed circle produces zero.
4. An uncertain circle blocks automatic export and requires manual review.

Dots, ticks, short strokes, slashes, brackets and open arcs are not closed circles.

## Install and start

Use 64-bit Python 3.11 on Windows 10/11.

1. Run `install.bat`.
2. Run `start.bat`, or use the packaged `dist\订单纸单识别器.exe`.
3. On first launch, enter `OPENAI_API_KEY` in Settings. The key is stored in Windows Credential Manager.

For development:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

## Privacy and limitations

Images are sent only to the configured OpenAI vision API. The application contains no advertising, analytics or tracking SDKs. Do not commit `.env`, API keys, real delivery-note photos, audit logs or Excel exports.

Accuracy is not guaranteed to be 100%. Blurry images, character conflicts such as O/0, I/l/1 and S/5, uncertain circles, missing pages and ambiguous handwriting require manual confirmation.

See [GitHub upload instructions](GITHUB_UPLOAD.md), [contribution rules](../CONTRIBUTING.md), and the [security policy](../SECURITY.md).

