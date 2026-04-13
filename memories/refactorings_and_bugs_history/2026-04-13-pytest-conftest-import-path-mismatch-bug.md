# Pytest conftest import path mismatch bug

**[Bug](#bug)** • **[Root cause](#root-cause)** • **[Fix](#fix)** • **[Prevention](#prevention)**

## Bug

All pytest tests failed to run in CI with:

```python
ImportError while loading conftest '/home/runner/.../tests/conftest.py'.
_pytest.pathlib.ImportPathMismatchError: (
    'tests.conftest',
    '/home/runner/.../tests/conftest',
    PosixPath('/home/runner/.../tests/conftest.py')
)
```

## Root cause

**Both `tests/conftest.py` file AND `tests/conftest/` directory existed simultaneously**.

### How it happened

1. Original `tests/conftest.py` file exceeded 100-line limit
2. Split into modular sub-folder: `tests/conftest/` with multiple files
3. BUT forgot to delete original `tests/conftest.py` file
4. Git tracked BOTH the file and the directory

### Why pytest fails

Pytest requires `conftest.py` as a **module file**, not a **package directory**:

- `tests/conftest.py` (file) → Valid pytest conftest module ✓
- `tests/conftest/` (directory with `__init__.py`) → Python package, NOT conftest module ✗

When both exist:
1. Python imports `tests.conftest` as package (directory with `__init__.py`)
2. Pytest expects `tests/conftest` to be module (file)
3. Import path mismatch error occurs

### Git tracking both

Even after file system deletion:
```bash
$ git ls-tree -r HEAD | grep tests/conftest
tests/conftest.py                    # Old file
tests/conftest/__init__.py           # New directory
tests/conftest/cleanup_hooks.py
# ... more files in directory
```

Git still tracked old file, causing CI to fail even when local tests passed.

## Fix

### Step 1: Rename directory to avoid conflict

```bash
mv tests/conftest tests/conftest_modules
```

**Why**: This completely eliminates naming conflict. Pytest sees only `conftest.py` file.

### Step 2: Create new conftest.py that imports from renamed directory

**File**: `tests/conftest.py`
```python
"""Pytest configuration for integration and unit tests.

This file imports fixtures from modular conftest sub-modules
to comply with the 100-line limit while maintaining pytest's
expected conftest.py structure.
"""

# Import all fixtures from split modules
from tests.conftest_modules.cleanup_hooks import *  # noqa: F403
from tests.conftest_modules.config import *  # noqa: F403
from tests.conftest_modules.container_fixtures import *  # noqa: F403
from tests.conftest_modules.database_fixtures import *  # noqa: F403
from tests.conftest_modules.http_client_fixtures import *  # noqa: F403
```

### Step 3: Explicitly delete old directory from git

```bash
git rm -r tests/conftest/
git commit -m "fix(tests): complete removal of old tests/conftest/ directory"
```

**Why**: Previous commit moved directory but didn't explicitly remove from git index.

### Step 4: Configure flake8 to ignore F401 in conftest files

**File**: `setup.cfg`
```ini
per-file-ignores =
    # Pytest conftest: F401 (star imports of fixtures used by pytest discovery)
    tests/conftest.py:F401
    tests\conftest.py:F401
    tests/conftest_modules/__init__.py:F401
    tests\conftest_modules\__init__.py:F401
```

**Why**: Pytest fixtures are auto-discovered at runtime, so imports appear unused to static analysis.

## Prevention

**Rule**: Never create a directory with the same name as a required pytest module file.

**Pattern for splitting conftest.py**:
```
tests/
├── conftest.py              # Required pytest module (< 100 lines)
└── conftest_modules/        # Split implementation (NOT conftest/)
    ├── __init__.py
    ├── cleanup_hooks.py
    ├── container_fixtures.py
    └── database_fixtures.py
```

**Checklist when splitting conftest.py**:
- [ ] New directory has different name (e.g., `conftest_modules/`, not `conftest/`)
- [ ] New `conftest.py` file created with star imports
- [ ] Old directory explicitly removed from git: `git rm -r tests/conftest/`
- [ ] Pytest collection works: `pytest --collect-only -q`
- [ ] F401 ignored in `setup.cfg` for conftest files

## Lessons learned

1. **Pytest conftest.py is special**: Cannot be replaced with package directory
2. **File system != git repository**: Deleting locally doesn't remove from git
3. **CI more strict than local**: Local Python might handle ambiguity, CI enforces strict path matching
4. **Name carefully**: When splitting, use suffix like `_modules`, `_fixtures`, `_helpers`
5. **Verify git state**: Always check `git ls-tree` after file reorganization

## Related issues

- All 192+ tests failed to import
- 4 commits required to fully resolve
- Issue affected all three Python versions in CI matrix (3.10, 3.11, 3.12)

## Timeline

1. Initial split: `tests/conftest.py` → `tests/conftest/` (BAD)
2. First attempt: Renamed to `tests/conftest_modules/`, created new `conftest.py`
3. CI still failed: Old `tests/conftest/` still in git
4. Final fix: `git rm -r tests/conftest/` + configure flake8 F401
5. Result: All tests can import, pytest collection works
