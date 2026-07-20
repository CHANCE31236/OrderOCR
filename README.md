# OrderOCR

OrderOCR is a Windows desktop application that turns photographed delivery notes into reviewed Excel files. It corrects document images, groups pages by order, extracts product rows, independently verifies box-count markings, supports manual review, and exports only product codes and final box counts.

The interface can switch instantly between English, Chinese, and French from the globe icon or Settings. English is the default language. Localized strings remain in the source only to support this feature; repository documentation, build output, commit messages, and release notes are written in English.

## Features

- EXIF orientation handling, four-way rotation scoring, document detection, and perspective correction
- Color-preserving denoising, shadow correction, and contrast enhancement
- Local RapidOCR/ONNX text and position hints
- OpenAI Responses API image input with strict Pydantic structured output validation
- Whole-page extraction plus independent row verification using page, row, and enlarged column crops
- Python-only final box-count calculation
- Manual review with confidence indicators and row image previews
- SQLite recovery, SHA-256 duplicate detection, and API result caching
- Excel export and JSON audit records
- Live English, Chinese, and French interface switching

## Box-count rule

The final box count never comes from the total quantity column.

1. A clearly associated non-negative handwritten box override has highest priority.
2. Otherwise, a printed box count inside a clearly closed circle is kept.
3. Otherwise, a confirmed absence of a closed circle produces zero.
4. An uncertain circle blocks automatic export and requires manual review.

Dots, ticks, short strokes, slashes, brackets, and open arcs are not closed circles.

## Requirements

- Windows 10 or Windows 11
- 64-bit Python 3.11 (Python 3.12 and 3.13 are also supported)
- Network access to the OpenAI API
- An OpenAI API key with access to a vision-capable model that supports structured outputs

## Install and run

1. Run `install.bat`.
2. Run `start.bat`.
3. On first launch, enter `OPENAI_API_KEY` in Settings.

The API key is stored in Windows Credential Manager. It is not written to ordinary settings files, logs, or source code.

You can also copy `.env.example` to `.env` and enter the key there. The `.env` file is ignored by Git.

## Typical workflow

1. Import or drag in JPG, JPEG, PNG, BMP, TIFF, or WebP files.
2. Start recognition.
3. Review page grouping, missing-page warnings, and extracted product rows.
4. Inspect red and yellow rows and confirm uncertain values.
5. Export one Excel file per order.

The spreadsheet contains only two columns: `Product code` and `Box count`. Product codes are stored as text to preserve leading zeros.

## Build a Windows executable

Run `build.bat`. The script installs development dependencies, runs the test suite, builds a one-file executable, copies runtime resources, and creates an English desktop shortcut.

Output:

```text
dist\OrderOCR.exe
```

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --self-test
```

## Privacy

Images are sent only to the configured OpenAI vision API. The application contains no advertising, analytics, or tracking SDKs. Do not commit `.env`, API keys, real delivery-note photos, audit logs, or Excel exports.

## Limitations

Recognition is not guaranteed to be 100% accurate. Blurry images, damaged page edges, character conflicts such as O/0, I/l/1 and S/5, uncertain circles, missing pages, and ambiguous handwriting require manual confirmation.

## Repository

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [GitHub upload and release notes](docs/GITHUB_UPLOAD.md)

CI runs secret scanning, automated tests, and the source self-test on Windows. Version tags matching `v*` build `OrderOCR.exe` and publish a GitHub Release.

No open-source license has been selected. All rights remain with the repository owner unless a license is added later.
