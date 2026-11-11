# Contributing

Thank you for improving OrderOCR.

## Local development

1. Install a 64-bit Python between 3.11 and 3.13 (CI runs 3.11).
2. Run `install.bat` or create `.venv` manually.
3. Install development dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
   ```

4. Run tests:

   ```powershell
   $env:QT_QPA_PLATFORM='offscreen'
   .\.venv\Scripts\python.exe -m pytest -q
   ```

## Pull requests

- Keep API keys, `.env`, customer images, generated Excel files and audit logs out of commits.
- Add tests for behavior changes.
- Preserve product-code characters and leading zeros.
- Never weaken the rule that the “quantity” column is not a box count.
- UI text must be added to all three dictionaries in `src/ui/i18n.py`.
- Run `python scripts/check_no_secrets.py` before opening a pull request.

## Licensing

OrderOCR is released under the MIT license (see [LICENSE](LICENSE)). By
contributing you agree that your contribution is licensed under the same terms.

