# Prioritize user intent over technical details in commit messages

**[Intent](#intent)** • **[Pattern](#pattern)** • **[Example](#example)** • **[Why](#why)**

## Critical rule

**Focus on what user problem solving, not what code changed.**

Commit scope must reflect PRIMARY user intent, not implementation details.

## Required format

When user makes changes with multiple concerns AND you don't know initial issue:

```
1. Review git diff (silently)
2. Ask: "What was the PRIMARY problem you were solving?"
   A) [User-facing issue 1] (rating: X/100)
   B) [User-facing issue 2] (rating: Y/100)
   C) [Technical detail] (rating: Z/100)
   D) All equally important
   
   Recommendation: [Highest rated option and why]
3. Wait for user answer
4. Generate scope options based on their stated PRIMARY intent
```

## Intent

Technical changes are means to an end. The commit message should describe the END (user's goal), not the MEANS (code changes).

## Pattern

**Wrong approach:**
- Count lines changed
- Lead with most technically interesting change
- Suggest scope before checking context OR asking user
- Treat secondary fixes as primary
- Don't rate options when asking

**Correct approach:**
1. Identify all changes
2. Check context for initial issue
3. If unclear, ASK user which problem was primary WITH RATED OPTIONS
4. Wait for explicit answer
5. Scope reflects their stated intent
6. Commit body: primary issues first, secondary fixes last

## Example

**Changes made:**
- 4 import corrections (`eventing.*` → `messaging.*`)
- Installation section rewrite (10 lines)
- CDC description update (8 lines)

**Wrong (technical focus):**
```
Scope: docs(imports)
Body: Fixed 4 import paths...
```

**Correct (user intent focus):**
```
Ask first:
"What was the PRIMARY problem you were solving?
A) Unclear installation instructions (rating: 85/100)
B) Incorrect CDC description (rating: 85/100) 
C) Wrong import paths (rating: 30/100)

Recommendation: A and B - user-facing onboarding blockers"

Then scope based on their answer:
Scope: docs(integration-guide): fix unclear installation and incorrect CDC description

Body:
## Starting point
Integration guide had two critical issues:
1. Unclear installation instructions
2. Incorrect CDC publishing description

## Changes
### Installation section
...

### CDC publishing section
...

### Secondary fixes
- Corrected import paths from eventing.* to messaging.*
```

## Why this matters

**User intent reveals:**
- What was broken
- Why they cared enough to fix it
- What problem is now solved
- Priority of changes

**Technical details reveal:**
- How it was fixed
- But not WHY or for WHOM

## When to apply

- Multi-concern commits where initial issue is unclear from context
- Documentation fixes
- Refactoring with side fixes
- Any commit where you're tempted to count lines to pick scope

**Always check context first before asking user.**

## Lesson learned from

Integration guide commit where AI initially suggested `docs(imports)` scope because 4 import corrections seemed significant, but user's PRIMARY intent was fixing "unclear installation + incorrect CDC description". 

**Mistake:** Didn't check context or ask user first. Led with technical detail count.

**Correct approach:** Should have asked with rated options:
- A) Unclear installation (85/100)
- B) Incorrect CDC (85/100)
- C) Wrong imports (30/100)

This would have immediately revealed user priorities. Import fixes were secondary cleanup discovered while addressing primary issues.
