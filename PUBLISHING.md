# Publishing mac-mail-backup to PyPI

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **Email Verification**: Verify your email address
3. **2FA**: Enable two-factor authentication (required for new projects)
4. **API Token**: Create a token at https://pypi.org/manage/account/token/
   - Scope: "Entire account" for first upload, then you can create project-specific tokens

## Step 1: Install Build Tools

```bash
pip install build twine
```

## Step 2: Build the Package

```bash
cd "/Users/abhi.yenpure/Mail Backup/mac-mail-backup"
python -m build
```

This creates two files in `dist/`:
- `mac_mail_backup-1.0.0.tar.gz` (source distribution)
- `mac_mail_backup-1.0.0-py3-none-any.whl` (wheel)

## Step 3: (Optional) Test on TestPyPI First

TestPyPI is a separate instance for testing. Recommended for first-time publishers.

### 3a. Create TestPyPI Account
- Register at https://test.pypi.org/account/register/
- Create API token at https://test.pypi.org/manage/account/token/

### 3b. Upload to TestPyPI
```bash
twine upload --repository testpypi dist/*
```

When prompted:
- Username: `__token__`
- Password: Your TestPyPI API token (including the `pypi-` prefix)

### 3c. Test Installation from TestPyPI
```bash
pip install --index-url https://test.pypi.org/simple/ mac-mail-backup
mac-mail-backup --version
mac-mail-backup --list
```

## Step 4: Upload to PyPI (Production)

```bash
twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: Your PyPI API token (including the `pypi-` prefix)

## Step 5: Verify Installation

```bash
pip install mac-mail-backup
mac-mail-backup --version
```

## Alternative: Configure Token in File

To avoid entering credentials each time, create `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

Then upload with:
```bash
twine upload dist/*                    # PyPI
twine upload --repository testpypi dist/*  # TestPyPI
```

## Updating the Package

For future releases:

1. Update version in `src/mac_mail_backup/__init__.py` and `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit and tag:
   ```bash
   git add .
   git commit -m "Release v1.1.0"
   git tag v1.1.0
   git push origin main --tags
   ```
4. Clean old builds and rebuild:
   ```bash
   rm -rf dist/ build/ *.egg-info
   python -m build
   twine upload dist/*
   ```

## Useful Links

- **PyPI Project Page** (after upload): https://pypi.org/project/mac-mail-backup/
- **GitHub Repository**: https://github.com/ayenpure/mac-mail-backup
- **PyPI Help**: https://packaging.python.org/tutorials/packaging-projects/
