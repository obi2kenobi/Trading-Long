# CLAUDE.md — Standard Working Rules

These rules are binding for every development session. No exceptions.

---

## 1. Process Rules

### Read before acting
Understand the current state of the repo before touching anything. Read relevant files, check git status, understand the context.

### One problem at a time
No jumping ahead, no parallel work on multiple things. Step by step. Complete one task before starting the next.

### Repeat the request in your own words
Before executing, confirm understanding by rephrasing the request. Wait for explicit approval before proceeding.

### If something is unclear, ask — never guess
One extra question is always better than one wrong assumption. Never invent requirements, business logic, or expected behavior.

### Validate logic before moving on
The user owns the domain knowledge. Get explicit confirmation that the result is correct before proceeding to the next step.

### Input and output examples before writing code
Require concrete examples of what goes in and what should come out before implementing any logic.

---

## 2. Code Rules

### Only what is asked
No additions, no spontaneous "improvements", no unrequested initiatives. If it wasn't asked for, don't do it.

### Zero waste
No superfluous code, no unnecessary files, no over-engineering. The simplest solution that works is the right one.

### Short functions
If a function exceeds 30-40 lines, it must be broken down. Each function does one thing.

### One file, one responsibility
No monolithic files. Every file has a single, clear purpose.

### No dead code
Don't leave commented-out code, unused imports, or placeholder functions. If it's not used, delete it.

### Respect existing patterns
Follow the conventions already present in the codebase: naming, structure, formatting, architecture. Consistency over personal preference.

---

## 3. Communication Rules

### Respond in the user's language
If the user writes in Italian, respond in Italian. If in English, respond in English. Match the language of the conversation.

### Be direct and concise
No filler, no unnecessary preambles. State what you're doing and why, then do it.

### Report problems immediately
If something doesn't work, is ambiguous, or seems wrong — say it immediately. Don't try to silently work around issues.

### Show, don't tell
When explaining a change, show the relevant code. When reporting a result, show the output.

---

## 4. Git Rules

### Commit after every working step
So we can always roll back to a point that works. Each commit represents a stable, functional state.

### Commit messages format
Use clear, descriptive messages. Format: `<type>: <short description>`

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

Example: `feat: add export functionality for usage reports`

### Never force push
Never use `--force` on shared branches unless explicitly asked.

### Review changes before committing
Always check `git diff` before committing to ensure only intended changes are included.

---

## 5. Error Handling

### Read the error completely
Before attempting a fix, read the full error message and stack trace. Understand the root cause.

### Fix the cause, not the symptom
Don't add workarounds. Find and fix the actual problem.

### One fix at a time
When debugging, change one thing at a time and verify the result before making the next change.

---

## 6. Project-Specific Notes

<!-- Add project-specific instructions below this line -->
<!-- Examples: -->
<!-- - Tech stack: React Native + TypeScript -->
<!-- - Test command: npm test -->
<!-- - Build command: npm run build -->
<!-- - Linter: eslint with project config -->
<!-- - Deployment: describe process -->
