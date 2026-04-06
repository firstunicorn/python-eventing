# Commit message writing

**[Core principles](#core-principles)** • **[Structure](#structure)** • **[Style](#style)** • **[Examples](#examples)**

---

## Core principles

1. **Sentence case throughout** - capitalize only the first word (and proper names like Kafka, EventBus)
2. **Organic narrative** - write naturally, avoid "user did X" phrasing
3. **Start with context** - explain the starting point, not just what changed
4. **Technical detail** - file paths, function names, specific changes
5. **Journey over changelog** - explain the thought process and decisions

---

## Structure

### Standard format

```
type(scope): brief subject in sentence case

## Starting point
What was the situation? What prompted this work?

## Investigation (if applicable)
What did you explore? What options did you consider?

## Changes
What changed and why. Technical specifics.

## Result
What works now? What remains unchanged?
```

### Type prefixes

- `feat` - new feature
- `fix` - bug fix
- `refactor` - restructuring without behavior change
- `docs` - documentation
- `test` - tests
- `chore` - maintenance

Add `!` for breaking: `feat!` or `refactor!`

---

## Style rules

### Sentence case (always)

```markdown
✅ Good:
## Investigation: what do external libraries provide?

❌ Avoid:
## Investigation: What Do External Libraries Provide?
```

### Organic narrative

```markdown
✅ Good:
While reviewing the codebase, we noticed the EventBus had tests but
wasn't wired into main.py. This raised a question: should we integrate
it or is it redundant?

❌ Avoid:
User discovered EventBus was not integrated. User asked if it should
be integrated. Decision was made to integrate.
```

### Technical specificity

```markdown
✅ Good:
- Imported build_event_bus from messaging.core.contracts
- Added EventBus initialization in lifespan() with empty handler list
- Exposed via app.state.event_bus

❌ Avoid:
- Added imports
- Initialized EventBus
- Made it available
```

---

## Examples

### Feature commit

```
feat(eventbus): integrate in-process domain event dispatcher into production

## Starting point: tests without integration

While reviewing the eventing system architecture, we noticed the EventBus
had comprehensive test coverage (tests/unit/core/test_event_bus.py) but was
never wired into the production application (main.py).

## Investigation: what do external libraries provide?

Before integrating, we needed to understand what existing libraries offer
for in-process event dispatch.

### Kafka and Kafka Streams
- ❌ No in-process event dispatch
- Kafka Streams Processor is for external topic processing

[... more investigation ...]

## Integration work

### 1. Wired into application (src/messaging/main.py)
- Import build_event_bus and HandlerRegistration
- Initialize EventBus in lifespan()
- Expose via app.state.event_bus

[... more details ...]

## Result

EventBus now available for:
- Multiple handlers per event
- Lifecycle hooks for observability
- Testing isolation

Direct outbox approach remains primary pattern.
```

### Bug fix commit

```
fix(testing): correct outbox recovery metrics assertion

## Problem

test_metrics_accuracy_mixed_results was asserting wrong expectation.
After failure events marked as failed, test expected total - success_count
unpublished events.

## Root cause

get_unpublished() filters by published=False AND failed=False, returning
0 after events marked failed (not total - success_count).

## Solution

Changed assertion from total - success_count to 0 to match actual
get_unpublished() behavior.
```

---

## Critical mistakes to avoid

1. ❌ **Title Case** - use sentence case
2. ❌ **"User did X"** - write naturally
3. ❌ **No context** - always explain starting point
4. ❌ **Vague changes** - be technically specific
5. ❌ **Changelog style** - explain the journey

---

## Implementation checklist

- [ ] Subject line: sentence case, type(scope): description
- [ ] Starts with context/starting point
- [ ] Natural narrative (no "user" language)
- [ ] Technical specifics (paths, names)
- [ ] Design decisions explained
- [ ] Philosophy/rationale included
- [ ] Breaking changes marked if applicable
