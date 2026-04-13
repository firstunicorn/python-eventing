# Pytest conftest cannot be package directory

**[Rule](#rule)** • **[Solution](#solution)** • **[Pattern](#pattern)**

## Rule

Pytest requires `tests/conftest.py` as a **module file**, NOT a package directory. Never create `tests/conftest/` directory alongside `tests/conftest.py`.

## Critical error

```python
ImportError while loading conftest 'tests/conftest.py'.
_pytest.pathlib.ImportPathMismatchError: (
    'tests.conftest',
    '/path/to/tests/conftest',
    PosixPath('/path/to/tests/conftest.py')
)
```

**Cause**: Both `tests/conftest.py` file AND `tests/conftest/` directory exist.

## Solution

When splitting large conftest.py (> 100 lines):

**Use different directory name**:
```
tests/
├── conftest.py              # Required pytest module (< 100 lines)
└── conftest_modules/        # NOT conftest/ - different name
    ├── __init__.py
    ├── cleanup_hooks.py
    ├── container_fixtures.py
    └── database_fixtures.py
```

**Import from renamed directory**:
```python
# tests/conftest.py
"""Pytest configuration."""

from tests.conftest_modules.cleanup_hooks import *  # noqa: F403
from tests.conftest_modules.container_fixtures import *  # noqa: F403
from tests.conftest_modules.database_fixtures import *  # noqa: F403
```

## Pattern

**Step 1**: Create new directory with DIFFERENT name
```bash
mkdir tests/conftest_modules
```

**Step 2**: Move fixture modules to new directory
```bash
mv fixture_code_1.py tests/conftest_modules/
mv fixture_code_2.py tests/conftest_modules/
```

**Step 3**: Create thin conftest.py that imports
```python
# tests/conftest.py (< 20 lines)
from tests.conftest_modules.cleanup_hooks import *
from tests.conftest_modules.container_fixtures import *
```

**Step 4**: Configure linter ignores for F401
```ini
# setup.cfg
per-file-ignores =
    tests/conftest.py:F401
    tests/conftest_modules/__init__.py:F401
```

## Prevention

**Never use these names alongside conftest.py**:
- `tests/conftest/` - Conflicts with conftest.py
- `tests/conftest_fixtures/` - Too similar, risky

**Safe naming patterns**:
- `tests/conftest_modules/` ✓
- `tests/fixtures/` ✓
- `tests/shared_fixtures/` ✓
- `tests/test_helpers/` ✓

**Verification after split**:
```bash
# Check pytest can collect
pytest --collect-only -q

# Check no path mismatch
python -c "import tests.conftest; print('OK')"

# Verify git state clean
git ls-tree -r HEAD | grep tests/conftest
# Should show ONLY:
# tests/conftest.py
# tests/conftest_modules/...
```

## Error symptoms

- All tests fail to import
- `ImportPathMismatchError` mentioning conftest
- Error shows both file path and directory path
- CI fails but local might work (caching)

## Git tracking issues

Even after deleting directory locally:
```bash
rm -rf tests/conftest/
```

**Must explicitly remove from git**:
```bash
git rm -r tests/conftest/
git commit -m "Remove old conftest directory"
```

Otherwise git keeps tracking deleted directory, CI fails.
