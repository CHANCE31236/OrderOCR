# Uploading this project to GitHub

The clean source package excludes `.venv`, `build`, `dist`, cache files, logs, Excel exports, customer images and `.env`.

## Create the repository

1. Create an empty GitHub repository. Do not add a README or `.gitignore` on GitHub because this package already contains them.
2. Open PowerShell in the clean `OrderOCR-GitHub` folder.
3. Run:

   ```powershell
   git init
   git branch -M main
   python scripts/check_no_secrets.py
   git add .
   git status
   git commit -m "Initial OrderOCR release"
   git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
   git push -u origin main
   ```

Review `git status` before committing. `.env`, real order photos, exports and local databases must never appear.

## Create a Windows release

After CI passes, create and push a version tag:

```powershell
git tag v1.1.0
git push origin v1.1.0
```

The `Windows release` workflow tests the project, builds the one-file executable, runs the packaged RapidOCR self-test and attaches `OrderOCR-Windows-x64.zip` to the tagged GitHub Release.

## Choose a license

No open-source license is included because choosing one grants legal reuse rights. Before inviting outside contributors, choose a license appropriate for the owner’s intentions and add it as `LICENSE`.

