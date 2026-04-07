**[Context window](#context-window)** • **[Pre-commit verification](#pre-commit)** • **[Anti-pattern](#anti-pattern)** • **[Correct workflow](#workflow)**

# Pre-commit verification workflow

## Critical rule

**NEVER write a commit message without:**
1. **Reviewing your ENTIRE context window/conversation**
2. **Running `git status`**
3. **Deep-reviewing the full diff**

## Context window audit (for AI agents)

### Why context matters

AI agents work in long conversations with large context windows:
- **Context size:** 100K-1M+ tokens (hundreds of messages)
- **Time span:** Work done 50-100 messages ago is still uncommitted
- **Accumulation:** Each small change adds up to major uncommitted work
- **Recency bias:** Recent work overshadows earlier changes in agent's immediate attention

**Problem:** Easy to remember the last 5 messages but forget the 50 messages before that.

**Universal examples of forgotten work:**

**Scenario A: Feature development**
- Implemented JWT authentication (messages 20-25)
- Created test fixtures for auth (message 28)
- Updated .env.example with JWT_SECRET (message 30)
- Added auth documentation (message 35)
- Created API examples (message 38)
- Recent: Fixed docstring (message 42) ← Only this remembered!

**Scenario B: Bug fix investigation**
- Investigated null user bug (messages 15-20)
- Added validator layer (message 22)
- Updated route handlers (message 25)
- Added edge case tests (message 28)
- Updated error messages (message 30)
- Recent: Fixed import (message 32) ← Only this remembered!

**Scenario C: Refactoring**
- Extracted service layer (messages 10-15)
- Updated 8 handler files with new imports (messages 16-20)
- Reorganized test structure (message 22)
- Updated 5 __init__.py files (message 24)
- Fixed circular imports (message 26)
- Recent: Added docstring (message 28) ← Only this remembered!

### How to audit your context window

**Step 1: Scroll to session start**
- Find where work on current task began
- Note the initial goal or user request
- Identify scope: "fix linters", "refactor tests", "update architecture"

**Step 2: Review every tool call and result**
- What files did you edit? (StrReplace, Write tools)
- What files did you create? (Write, EditNotebook)
- What files did you move? (Shell commands with mv/rename)
- What files did you delete? (Delete, Shell commands)
- What configs did you modify? (pyproject.toml, .env, docker-compose.yml)

**Step 3: Build mental checklist**
- Tests: which files modified?
- Source: which modules changed?
- Configs: which settings updated?
- Docs: which files created/modified?
- Fixtures: which reorganized?

**Step 4: Cross-reference with git status**
- Every file in git status should appear in your context window review
- Every change in your mental checklist should appear in git status
- Mismatches indicate forgotten work or unrelated changes

## Why this matters

AI agents often work on multiple related changes across a session:
- Fixing linter errors in source files
- Updating test files to match
- Modifying configuration (pyproject.toml, .env)
- Adding documentation
- Creating new test fixtures
- Refactoring modules into sub-folders

**Problem:** Easy to forget earlier changes and commit only the most recent edits, creating fragmented, incomplete commits.

## Required workflow

### Step 0: Context window audit (AI agents only)

Before checking git status, review your ENTIRE conversation:

```
ACTION: Scroll through full context window
GOAL: Build complete mental picture of ALL work done

CHECKLIST:
- [ ] Found session start / initial task goal
- [ ] Noted every file edited (search for StrReplace, Write calls)
- [ ] Noted every file created (Write, new directories)
- [ ] Noted every config modified (pyproject.toml, .env, etc.)
- [ ] Noted every test file touched
- [ ] Noted every doc file created
- [ ] Built mental checklist of expected changes
```

**Time investment:** 2-3 minutes to scroll through 100+ messages
**Payoff:** Comprehensive commits that represent actual work scope

### Step 1: Verify ALL changes

```bash
git status                    # See every modified/deleted/untracked file
git diff --stat               # Understand full scope with line counts
git diff --cached             # Check what's already staged
```

**Cross-reference with context window:**
- Every file in `git status` should match work you noted in context review
- Every change in your mental checklist should appear in `git status`
- Missing files? Review context window more carefully
- Extra files? Check if they're related or metadata (.cursor/, .specstory/)

### Step 2: Check for commonly forgotten items

Review your context window and git status for:
- [ ] Test files modified 50+ messages ago
- [ ] Configuration files (pyproject.toml, setup.cfg, .env, docker-compose.yml)
- [ ] Documentation files (docs/, README.md, memories/)
- [ ] New directories (test fixtures split into folders)
- [ ] Renamed/moved files (refactored modules)
- [ ] Dependency locks (uv.lock, poetry.lock, package-lock.json)
- [ ] Type annotations added to resolve Mypy errors
- [ ] Linter suppressions (# noqa, # type: ignore, # pylint: disable)
- [ ] Timeout adjustments in async tests
- [ ] Import statement changes

### Step 3: Group related changes
Stage ALL logically related work together:
```bash
# ✅ GOOD: Complete commit
git add tests/ pyproject.toml docs/ docker-compose.yml
git commit -m "refactor(tests): split files and fix all linters"
```

### Step 4: Exclude only metadata
```bash
# Exclude .cursor/, .specstory/, or user-explicitly-requested files
# But include EVERYTHING else related to the task
```

## Anti-pattern examples (universal)

### Example 1: Feature development

**Session work (50 messages):**
1. Implemented JWT authentication module (messages 20-25)
2. Created test suite for auth (messages 26-28)
3. Updated .env.example with new secrets (message 30)
4. Added authentication documentation (messages 32-35)
5. Created API usage examples (message 38)
6. Fixed small docstring typo (message 42) ← recent, salient in memory

**Wrong approach:**
```bash
# ❌ Only commits recent docstring fix
git add src/auth/jwt_handler.py
git commit -m "docs(auth): fix typo in JWT docstring"
```

**Result:** 
- Forgot: tests/auth/, docs/auth-guide.md, .env.example, examples/
- Incomplete: Feature appears to be just a docstring fix
- Later: Create awkward "feat(auth): add JWT authentication" commit with missing context

### Example 2: Bug fix investigation

**Session work (40 messages):**
1. Debugged null user crashes (messages 10-15)
2. Added validation layer (messages 16-18)
3. Updated route handlers with validators (messages 20-22)
4. Added comprehensive edge case tests (messages 24-28)
5. Updated error messages (message 30)
6. Fixed import statement (message 32) ← recent, salient in memory

**Wrong approach:**
```bash
# ❌ Only commits recent import fix
git add src/api/routes.py
git commit -m "fix(api): correct import path"
```

**Result:**
- Forgot: src/api/validators.py, tests/api/test_edge_cases.py, error messages
- Incomplete: Bug fix appears to be just an import path correction
- Later: Have to explain why "import fix" actually includes validator and tests

### Example 3: Dependency upgrade

**Session work (35 messages):**
1. Upgraded SQLAlchemy to 2.0 (message 5)
2. Updated all model imports (messages 7-12)
3. Migrated to new Session API (messages 14-18)
4. Created alembic migration (message 20)
5. Updated 12 test files with new patterns (messages 22-28)
6. Fixed lint warning in one file (message 30) ← recent, salient in memory

**Wrong approach:**
```bash
# ❌ Only commits recent lint fix
git add tests/integration/test_db.py
git commit -m "chore(tests): fix lint warning"
```

**Result:**
- Forgot: pyproject.toml, poetry.lock, src/models/*, alembic/versions/*, 11 other test files
- Incomplete: Appears to be a trivial lint fix, not major upgrade
- Later: Discover uncommitted breaking changes from SQLAlchemy 2.0 migration

## Correct approach (universal examples)

### Example 1: Feature development (JWT authentication)

**Step 0: Context window audit**
```
[Scroll through 50 messages]
Goal: Add JWT authentication
Changes noted:
- Messages 20-25: Implemented JWTHandler class (src/auth/jwt_handler.py)
- Message 26: Created auth fixtures (tests/auth/conftest.py)
- Messages 27-28: Added test suite (tests/auth/test_jwt_handler.py)
- Message 30: Updated .env.example with JWT_SECRET
- Messages 32-35: Wrote auth documentation (docs/auth-guide.md)
- Message 38: Created API examples (examples/auth_flow.py)
- Message 42: Fixed docstring typo
```

**Step 1: Verify with git status**
```bash
git status
# Shows:
# M .env.example
# A docs/auth-guide.md
# A examples/auth_flow.py
# A src/auth/jwt_handler.py
# A tests/auth/conftest.py
# A tests/auth/test_jwt_handler.py

# Cross-reference: ✅ All 6 files match context notes
```

**Step 2: Commit complete feature**
```bash
git add src/auth/ tests/auth/ docs/auth-guide.md examples/auth_flow.py .env.example
git commit -m "feat(auth): add JWT authentication with RS256"
```

### Example 2: Bug fix (null user validation)

**Step 0: Context window audit**
```
[Scroll through 40 messages]
Goal: Fix null user crashes
Changes noted:
- Messages 16-18: Created ValidationLayer (src/api/validators.py)
- Messages 20-22: Updated routes with validation (src/api/routes.py, src/api/user_routes.py)
- Messages 24-28: Added edge case tests (tests/api/test_edge_cases.py)
- Message 30: Updated error messages (src/api/errors.py)
- Message 32: Fixed import statement
```

**Step 1: Verify with git status**
```bash
git status
# Shows:
# M src/api/errors.py
# M src/api/routes.py
# M src/api/user_routes.py
# A src/api/validators.py
# A tests/api/test_edge_cases.py

# Cross-reference: ✅ All 5 files match context notes
```

**Step 2: Commit complete fix**
```bash
git add src/api/ tests/api/
git commit -m "fix(api): handle null user with validation layer"
```

### Example 3: Dependency upgrade (SQLAlchemy 2.0)

**Step 0: Context window audit**
```
[Scroll through 35 messages]
Goal: Upgrade SQLAlchemy to 2.0
Changes noted:
- Message 5: Updated pyproject.toml (SQLAlchemy 1.4 → 2.0)
- Messages 7-12: Updated model imports (src/models/*)
- Messages 14-18: Migrated to new Session API (src/db/session.py, src/api/*.py)
- Message 20: Created migration (alembic/versions/upgrade_sqlalchemy.py)
- Messages 22-28: Updated test patterns (tests/*)
- Message 30: Fixed lint warning
```

**Step 1: Verify with git status**
```bash
git status
# Shows:
# M alembic/versions/upgrade_sqlalchemy.py
# M poetry.lock
# M pyproject.toml
# M src/api/routes.py
# M src/api/user_routes.py
# M src/db/session.py
# M src/models/user.py
# M src/models/base.py
# M tests/ (12 files)

# Cross-reference: ✅ All 18 files match context notes
```

**Step 2: Commit complete upgrade**
```bash
git add pyproject.toml poetry.lock src/ alembic/ tests/
git commit -m "chore(deps): upgrade SQLAlchemy to 2.0"
```

**Universal pattern:**
1. Context window audit → Build complete mental picture
2. Git status → Verify all files present
3. Cross-reference → Ensure nothing forgotten
4. Commit → ALL related work together

## Key insight for AI agents

**Context window is your source of truth for work scope.**

When user says "fix and commit", they mean:
1. Fix the immediate issue (docstrings, linter errors, test failures)
2. **Review your ENTIRE context window to see ALL work done**
3. **Commit ALL related work from the full session**

Don't assume "recent edits only" - your context window contains the complete picture.

**Your advantage:** Unlike humans, you have perfect recall of your entire context window. Use it!

**Your challenge:** Recency bias makes recent work feel more salient. Combat this by actively scrolling back through the full conversation.

## Mental model

Think of commits as **chapters**, not **sentences**:
- **Chapter (✅ correct):** "Split test files and fix all linter issues" (25 files, complete story)
- **Sentence (❌ wrong):** "Fix docstrings" (5 files, incomplete fragment)

Your context window tells you which chapter you're writing.

## Exception: user explicitly requests partial commit

Only commit partial changes when user specifically says:
- "Commit just the docstring fixes"
- "Commit only the test refactoring"
- "Stage these 3 files only"

Otherwise, default to comprehensive commits.
