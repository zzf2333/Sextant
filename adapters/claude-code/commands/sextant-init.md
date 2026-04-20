# /sextant-init

> Bootstrap Sextant knowledge system in an existing project.

Scans the current project to detect tech stack and module structure, then generates
the four core knowledge files. Designed for first-time setup — use `--force` to
overwrite existing knowledge files (trace files are never touched).

## Usage

```
/sextant-init          # detect and prompt before writing
/sextant-init --force  # overwrite existing knowledge files silently
```

## Workflow

### Step 1: Pre-flight check

1a. **Existing file check** (skip if `--force` provided):

Check for these files:
- `.sextant/SEXTANT.md`
- `.sextant/PROJECT_EVOLUTION_LOG.md`
- `.sextant/hook-registry.json`
- Any `modules/*/EVOLUTION.md`

If any exist:
```
The following knowledge files already exist:
  - .sextant/SEXTANT.md
  - modules/core/EVOLUTION.md

Use --force to overwrite, or remove them manually and run again.
```
Stop.

1b. If `--force` is active, print: `Note: --force active — existing knowledge files will be overwritten.`

---

### Step 2: Tech stack detection

> Use Bash tool to check file existence and read manifest content.
> Detection is deterministic first (exact string match), LLM reasoning only as fallback.

**2a. Language & Runtime detection**

Check in order — use ALL matches (polyglot projects enumerate all):

| Signal file | Language | Runtime |
|---|---|---|
| `package.json` exists | JavaScript or TypeScript | Read `"engines": {"node": "..."}` if present |
| `pyproject.toml` or `setup.py` exists | Python | Read `requires-python` in pyproject.toml |
| `go.mod` exists | Go | Read first line `go X.Y` |
| `Cargo.toml` exists | Rust | Read `edition = "..."` in [package] |
| `pom.xml` or `build.gradle` exists | Java | Presence only — no XML parsing |
| `Gemfile` exists | Ruby | Check `.ruby-version` or `ruby` line in Gemfile |
| `.csproj` or `.fsproj` exists | C# or F# | Presence only — no XML parsing |

If no signal found: Language = "Not detected", Runtime = "Not detected"

**TypeScript upgrade:**
If Language includes JavaScript, check for `tsconfig.json` existence or `"typescript"` in `package.json` devDependencies.
If found → upgrade Language entry to `TypeScript`.

**2b. Framework detection (deterministic first, LLM fallback)**

**Deterministic pass:** Use Bash to check manifest files for exact dependency keys.

**Node.js** (`package.json` dependencies + devDependencies):
- `"next"` key → Next.js
- `"react"` key (without Next.js) → React
- `"vue"` key → Vue.js
- `"@angular/core"` key → Angular
- `"express"` key → Express
- `"fastify"` key → Fastify
- `"@nestjs/core"` key → NestJS

**Python** (`pyproject.toml` or `requirements.txt`):
- `django` → Django
- `flask` → Flask
- `fastapi` → FastAPI

**Go** (`go.mod` require block):
- `github.com/gin-gonic/gin` → Gin
- `github.com/labstack/echo` → Echo
- `github.com/gofiber/fiber` → Fiber

**Rust** (`Cargo.toml` [dependencies]):
- `actix-web` → Actix-web
- `axum` → Axum
- `rocket` → Rocket

**Java/C#:** Presence only — framework listed as "Unknown (see dependencies)". No parsing.

**LLM fallback:** Only if multiple frameworks are detected for the same language (ambiguous), use LLM reasoning to determine the primary framework based on manifest content.

If multiple frameworks detected across languages: list all, comma-separated.
If no framework detected: leave as template placeholder.

**2c. Test runner detection**

Branch by detected language:

**Node.js** — read `"test":` script value in `package.json`:
- Contains `jest` → Jest
- Contains `vitest` → Vitest
- Contains `mocha` → Mocha
- `"@playwright/test"` in dependencies → Playwright (add alongside unit runner)
- If no test script: leave as placeholder

**Python** — check in order:
- `pytest` in dependencies (pyproject.toml or requirements.txt) → pytest
- `pytest.ini` or `conftest.py` exists → pytest
- Fallback → unittest (built-in, no dep needed)

**Go:** Built-in → `go test`

**Rust:** Built-in → `cargo test`

**Java:** Check `pom.xml` or `build.gradle` for `junit` → JUnit; `testng` → TestNG

**2d. Build tool detection**

**Node.js** — read `"build":` script value in `package.json`:
- Contains `vite` → Vite
- Contains `webpack` → webpack
- Contains `turbo` → Turborepo
- Contains `tsup` → tsup
- Contains only `tsc` → TypeScript compiler
- No build script → "Not applicable"

**Python:**
- `poetry.lock` exists → Poetry
- `Pipfile.lock` exists → Pipenv
- `hatch` in deps → Hatch
- Default → setuptools

**Go:** Built-in → `go build`

**Rust:** Built-in → `cargo build`

**Java:** `pom.xml` → Maven; `build.gradle` → Gradle

**2e. Lint & format detection**

**Node.js:**
- `.eslintrc.*` exists or `"eslint"` in package.json → ESLint
- `.prettierrc.*` exists or `"prettier"` in package.json → Prettier
- Both → "ESLint + Prettier"

**Python:**
- `ruff` in deps → Ruff
- `black` in deps → Black
- `flake8` in deps → Flake8

**Go:** `.golangci.yml` exists → golangci-lint; default → `go fmt`

**Rust:** Built-in → `cargo fmt` + `cargo clippy`

---

### Step 3: Module detection

> Step 3a is terminal: if any conventional path matches, skip Step 3b entirely.

**3a. Conventional paths (check in order, stop at first match):**

| Path | Strategy |
|---|---|
| `apps/` exists | Each immediate subdirectory is a module |
| `packages/` exists | Each immediate subdirectory is a module |
| `services/` exists | Each immediate subdirectory is a module |
| `modules/` exists | Each immediate subdirectory is a module |
| `src/` exists AND contains subdirectories with source files | Each immediate subdirectory under src/ is a module |

If a conventional path matches: collect modules from that path. **Go to Step 3c. Do not run Step 3b.**

**3b. Fallback: top-level source scan (only if Step 3a found nothing)**

Scan top-level directories. Exclude standard dirs:
- `node_modules`, `vendor`, `.venv`, `venv`, `env`, `target`, `dist`, `build`
- `.git`, `.sextant`, `.next`, `.nuxt`, `out`, `coverage`, `.cache`, `.turbo`
- `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.tox`, `tmp`, `temp`

For each remaining top-level directory:
- If it contains at least 3 source files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rs`, `.java`) → module candidate

Note: `src/` alone (as a directory containing files, not subdirectories) → single module named after the project, not a sub-module list.

**3c. Module naming**

- Use directory name as module name (lowercase)
- Nested modules (e.g., `apps/web`): slug = `apps-web`
- Single-directory project: module name = project name (infer from package.json `"name"`, pyproject.toml project name, go.mod module path, or directory name)

**3d. No modules case**

If no modules detected after Steps 3a + 3b:
- Create **no** `modules/` directory
- Generate only the three global knowledge files (`.sextant/SEXTANT.md`, `.sextant/PROJECT_EVOLUTION_LOG.md`, `.sextant/hook-registry.json`)
- Print: `No modules detected. Creating global knowledge files only.`

---

### Step 4: verify_commands detection

> Branch by detected runtime. Output as YAML array.

**Node.js / TypeScript:**
- Check which package manager: `pnpm-lock.yaml` → pnpm; `yarn.lock` → yarn; default → npm
- Has `"test"` script → `<pm> test`
- Has `"typecheck"` or `"type-check"` script → `<pm> run typecheck`
- Has `"lint"` script → `<pm> run lint`
- `tsconfig.json` exists and no `typecheck` script → `npx tsc --noEmit`

**Python:**
- pytest detected → `python -m pytest`
- `ruff` detected → `ruff check .`
- `mypy` in deps → `python -m mypy .`

**Go:**
- `go test ./...`
- `.golangci.yml` exists → `golangci-lint run`

**Rust:**
- `cargo test`
- `cargo clippy`

**Java:**
- Maven → `mvn test`
- Gradle → `gradle test`

If no commands detected: output as commented placeholder block.

---

### Step 5: Display detection summary

Print:

```
── Sextant Initialization ─────────────────────────────────

Detected tech stack:
  Language:       TypeScript
  Runtime:        Node.js 20
  Framework:      Next.js 14
  Test runner:    Vitest
  Lint / format:  ESLint + Prettier
  Build tool:     Vite

Detected modules (3):
  - apps/web
  - packages/ui
  - packages/core

Verification commands:
  - pnpm test
  - npx tsc --noEmit
  - pnpm run lint

Files to create:
  ✓ .sextant/SEXTANT.md
  ✓ .sextant/PROJECT_EVOLUTION_LOG.md
  ✓ .sextant/hook-registry.json
  ✓ modules/apps-web/EVOLUTION.md
  ✓ modules/packages-ui/EVOLUTION.md
  ✓ modules/packages-core/EVOLUTION.md

───────────────────────────────────────────────────────────
```

---

### Step 6: User confirmation

**If `--force` is NOT active:**

```
Proceed with initialization? [y/n]
```

- `y` / `Y` → continue to Step 7
- `n` / `N` → print `Initialization aborted. No files created.` and stop (zero side effects)
- Any other input → print `Invalid input. Initialization aborted.` and stop

**If `--force` IS active:** skip confirmation, proceed immediately.

---

### Step 7: Generate knowledge files

**7.0. Create `.sextant/` directory**

If `.sextant/` does not already exist:
```bash
mkdir -p <project_root>/.sextant
```

**7a. Generate `.sextant/SEXTANT.md`**

Use the SEXTANT.md template structure. Auto-fill detected values:
- `Language:` → detected Language (or "Not detected")
- `Runtime:` → detected Runtime (or "Not detected")
- `Framework:` → detected Framework (or leave as comment)
- `Test runner:` → detected Test runner (or leave as comment)
- `Lint / format:` → detected Lint/format tools (or leave as comment)

Leave as template comment placeholders:
- `Data store`
- `Default Preferences`
- `Explicit Non-Goals`
- `Known Constraints`

Auto-fill `verify_commands`: uncomment and fill if commands detected; leave commented if none.

Write to `<project_root>/.sextant/SEXTANT.md`.

**7b. Generate `.sextant/PROJECT_EVOLUTION_LOG.md`**

Copy the PROJECT_EVOLUTION_LOG template as-is (no auto-fill).

Write to `<project_root>/.sextant/PROJECT_EVOLUTION_LOG.md`.

**7c. Generate `.sextant/hook-registry.json`**

```json
{
    "$schema": "https://sextant.dev/schemas/hook-registry/v1",
    "version": "1",
    "hooks": [],
    "_instructions": [
        "Add hooks only after real failures or near-misses — not speculatively.",
        "Each hook must have a 'created_from_lesson' that references an actual incident.",
        "trigger values: pre-commit | pre-push | pre-build | on-stage-gate",
        "check_type values: regex | file-exists | shell",
        "For check_type 'shell': pattern_or_command is a shell command; exit 0 = pass, non-zero = fail"
    ]
}
```

Write to `<project_root>/.sextant/hook-registry.json`.

**7d. Generate `modules/*/EVOLUTION.md` for each detected module**

(Skip entirely if Step 3d applied — no modules detected.)

For each module:
- `Module:` → module name
- `Last updated:` → current date (YYYY-MM-DD)
- `Module Purpose:` → `<!-- TODO: Describe the purpose of this module -->`
- All other fields (Key Evolution Events, Deprecated Paths, Open Design Questions) → template placeholder

Create `<project_root>/modules/<module_slug>/` directory if absent.
Write `<project_root>/modules/<module_slug>/EVOLUTION.md`.

---

### Step 8: Final summary

```
── Initialization complete ────────────────────────────────

Created:
  ✓ .sextant/SEXTANT.md
  ✓ .sextant/PROJECT_EVOLUTION_LOG.md
  ✓ .sextant/hook-registry.json
  ✓ modules/apps-web/EVOLUTION.md
  ✓ modules/packages-ui/EVOLUTION.md
  ✓ modules/packages-core/EVOLUTION.md

Next steps:
  1. Review .sextant/SEXTANT.md and fill in the placeholders:
     - Default Preferences
     - Explicit Non-Goals
     - Known Constraints

  2. Edit each modules/*/EVOLUTION.md and replace the TODO
     in "Module Purpose" with a one-paragraph description.

  3. Run /sextant "<task description>" to start your first task.

───────────────────────────────────────────────────────────
```

---

## Error Handling

**Missing manifest files:**
```
No project manifest detected. This command requires at least one of:
  - package.json (Node.js / TypeScript)
  - pyproject.toml or setup.py (Python)
  - go.mod (Go)
  - Cargo.toml (Rust)
  - pom.xml / build.gradle (Java)
  - Gemfile (Ruby)
  - *.csproj / *.fsproj (C# / F#)

Ensure you are in a valid project directory.
```
Stop.

**File write errors:**
If any file write fails, print the error and stop. Do NOT leave partial state — no files should remain if initialization fails mid-way.

---

## Notes

- This command is idempotent with `--force`. Re-running regenerates all knowledge files from current project state.
- Detection is best-effort. If the result is incorrect, edit `.sextant/SEXTANT.md` — it is just a markdown file.
- `.sextant/traces/` is never created by this command. It is created on first task execution via `/sextant <description>`.
- For non-standard project structures, initialize with this command then adjust the generated files manually.
