"""Fix script for pydocstyle D405 'See also' capitalization and other automated fixes."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent  # .cursor/ -> eventing/
SRC = ROOT / "src" / "messaging"
print(f"SRC dir: {SRC}")
assert SRC.exists(), f"SRC dir {SRC} does not exist!"

# Fix 1: D405 "See also" -> "See Also"
print("\n=== Fixing D405: 'See also' -> 'See Also' ===")
fixed_d405 = 0
for py_file in SRC.rglob("*.py"):
    content = py_file.read_text(encoding="utf-8")
    if "See also" in content:
        content = content.replace("See also", "See Also")
        py_file.write_text(content, encoding="utf-8")
        fixed_d405 += 1
        print(f"  Fixed: {py_file.relative_to(ROOT)}")
print(f"Fixed {fixed_d405} files\n")

# Fix 2: D102 - add missing docstring to SequentialDispatchBackend.invoke
print("=== Fixing D102: SequentialDispatchBackend.invoke ===")
backends = SRC / "core" / "contracts" / "bus" / "backends.py"
content = backends.read_text(encoding="utf-8")
content = content.replace(
    '    async def invoke(\n        self,\n        event: BaseEvent,\n        handlers: list[RegisteredHandler],\n        invoke_one: Callable[[RegisteredHandler], Awaitable[None]],\n    ) -> None:\n        _ = event',
    '    async def invoke(\n        self,\n        event: BaseEvent,\n        handlers: list[RegisteredHandler],\n        invoke_one: Callable[[RegisteredHandler], Awaitable[None]],\n    ) -> None:\n        """Run the provided handlers for one event."""\n        _ = event',
)
backends.write_text(content, encoding="utf-8")
print("  Fixed backends.py\n")

# Fix 3: W391 - trailing blank line at end of file
print("=== Fixing W391: trailing blank line ===")
repo_file = SRC / "infrastructure" / "outbox" / "outbox_repository.py"
content = repo_file.read_text(encoding="utf-8")
content = content.rstrip() + "\n"
repo_file.write_text(content, encoding="utf-8")
print("  Fixed outbox_repository.py\n")

print("All automated fixes applied.")
