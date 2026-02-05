# v0.5.0 Release Instructions

This document contains instructions for completing the v0.5.0 release of ai-lib-python.

---

## Prerequisites

- GitHub access to push to `hiddenpath/ai-lib-python`
- PyPI access to upload packages
- PyPI API token configured
- Python 3.10+
- Git configured

---

## Step 1: Push to GitHub

The commit is ready but requires authentication to push.

### Option A: Push using GitHub CLI (if configured)

```bash
gh auth login
git push origin main
git push origin v0.5.0
```

### Option B: Push using Personal Access Token

```bash
# Create a token at: https://github.com/settings/tokens
# Use the token with git:
git remote set-url origin https://YOUR_TOKEN@github.com/hiddenpath/ai-lib-python.git
git push origin main
git push origin v0.5.0
```

### Option C: Push using SSH (if SSH keys configured)

```bash
git remote set-url origin git@github.com:hiddenpath/ai-lib-python.git
git push origin main
git push origin v0.5.0
```

### Verify

```bash
gh release view v0.5.0  # If using GitHub CLI
# Or visit: https://github.com/hiddenpath/ai-lib-python/releases
```

---

## Step 2: Publish to PyPI

### 2.1 Configure PyPI API Token

```bash
# Install twine
pip install --upgrade twine

# Create PyPI token at: https://pypi.org/manage/account/token/
# Add to ~/.pypirc:

[pypi]
username = __token__
password = your-pypi-token-here
```

### 2.2 Build the Package

Navigate to the project directory:

```bash
cd /home/alex/pyapp/ai-lib-python
```

Check that pyproject.toml is configured correctly:

```bash
# Verify version is 0.5.0
grep "version = 0.5.0" pyproject.toml
grep "__version__ = 0.5.0" src/ai_lib_python/__init__.py
```

Build the distribution packages:

```bash
# Install build dependencies if needed
pip install --upgrade build

# Build source and wheel
python -m build
```

This will create:
- `dist/ai-lib-python-0.5.0.tar.gz` (source distribution)
- `dist/ai_lib_python-0.5.0-py3-none-any.whl` (wheel)

### 2.3 Verify the Package

```bash
# Check distribution
twine check dist/*

# Test install (optional)
pip install dist/ai_lib_python-0.5.0.tar.gz
```

### 2.4 Upload to PyPI

```bash
# Upload to PyPI (production)
twine upload dist/*
```

Or for TestPyPI first:

```bash
# Configure TestPyPI
# https://test.pypi.org/manage/account/token/

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ ai-lib-python==0.5.0
```

### 2.5 Verify PyPI Publication

```bash
# Check package on PyPI
pip install ai-lib-python==0.5.0

# Verify version
python -c "import ai_lib_python; print(ai_lib_python.__version__)"
# Should print: 0.5.0
```

Or visit: https://pypi.org/project/ai-lib-python/

---

## Step 3: Create GitHub Release (Recommended)

After pushing to GitHub, create a formal release:

### Option A: Using GitHub CLI

```bash
# The tag should already exist (v0.5.0)
gh release create v0.5.0 \
  --title "v0.5.0 - Beta Release with Guardrails" \
  --notes-file RELEASE_NOTES_V0.5.0.md \
  --generate-notes
```

### Option B: Manual on GitHub

1. Visit: https://github.com/hiddenpath/ai-lib-python/releases/new
2. Select tag: `v0.5.0`
3. Title: `v0.5.0 - Beta Release with Guardrails`
4. Description: Copy content from `RELEASE_NOTES_V0.5.0.md`
5. Publish

---

## Step 4: Update Documentation Site (Optional)

The docs are configured with mkdocs. To build and deploy:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build documentation
mkdocs build

# Preview locally
mkdocs serve

# Deploy to GitHub Pages (if configured)
mkdocs gh-deploy
```

---

## Step 5: Announcements

### Internal

- Update team on release completion
- Add release notes to internal tracking

### Public

- GitHub release (Step 3)
- PyPI publish (Step 2)
- Update README if needed
- Blog post or social media (optional)

---

## Verification Checklist

Before considering the release complete:

- [ ] Git pushed to `origin/main`
- [ ] Tag v0.5.0 pushed to `origin`
- [ ] GitHub release created
- [ ] Package built successfully
- [ ] Package uploaded to PyPI
- [ ] PyPI package installable: `pip install ai-lib-python==0.5.0`
- [ ] Version correct: `ai_lib_python.__version__ == '0.5.0'`
- [ ] Tests pass (run in venv with fresh install)
- [ ] Documentation builds successfully

---

## Rollback Plan (if needed)

If issues are discovered after release:

1. **PyPI**: Cannot delete published packages (PyPI policy)
   - Upload a new version (0.5.1) with fixes
   - Mark v0.5.0 as "yanked" if critical

2. **GitHub**: Keep tag, add notes to release
   - Update release description with known issues
   - Link to fixed version

3. **Code**: Tag new version and push fixes

---

## Files Summary

New files added in v0.5.0:

**Source Code**:
- `src/ai_lib_python/guardrails/` - New guardrails module
- `tests/integration/` - Integration test suite

**Examples**:
- `examples/guardrails_production.py`
- `examples/concurrent_production.py`
- `examples/multi_provider_production.py`

**Documentation**:
- `docs/index.md`
- `docs/guardrails.md`
- `docs/api/client.md`
- `docs/api/guardrails.md`
- `docs/api/types.md`
- `mkdocs.yml`

**Reports**:
- `CODE_REVIEW_REPORT_V0.5.0.md`
- `TYPE_CHECKING_GUIDE.md`
- `ROUTING_MANAGER_REFACTORING_ASSESSMENT.md`
- `RELEASE_NOTES_V0.5.0.md`

**Modified**:
- `pyproject.toml` - Version 0.4.0 → 0.5.0, Beta status
- `src/ai_lib_python/__init__.py` - Version 0.4.0 → 0.5.0
- `CHANGELOG.md` - v0.5.0 entry added

---

## Support

If you encounter issues:

- **Git auth**: GitHub personal access tokens: https://github.com/settings/tokens
- **PyPI auth**: PyPI API tokens: https://pypi.org/manage/account/token/
- **Build issues**: Check `python -m build` output
- **Upload issues**: Check twine logs: `twine upload --verbose dist/*`

---

## Next Steps After Release

1. Monitor for issues and feedback
2. Begin planning v0.6.0
3. Consider implementing routing/manager refactoring (P2 assessed)
4. Add more guardrail patterns based on user needs
5. Extend integration test coverage as needed

---

**End of Release Instructions**
