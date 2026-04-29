# Sextant Quickstart

Get from install to your first completed task in about 5 minutes.

---

## 1. Install the adapter (< 1 minute)

```sh
git clone https://github.com/zzf2333/Sextant
cd Sextant
./adapters/claude-code/install.sh --project --path /path/to/your-project
```

Expected output:

```
Installing Sextant Claude Code adapter (project)

Agents → /your/project/.claude/agents
  ✓  sextant-spec.md
  ✓  sextant-planner.md
  ✓  sextant-builder.md
  ✓  sextant-reviewer.md
  ✓  sextant-rca.md

Commands → /your/project/.claude/commands
  ✓  sextant.md
  ✓  sextant-spec.md
  ...

  ✓  Knowledge files initialized
  ✓  CLAUDE.md: snippet appended

Installation complete
Project is ready.

  Start with:
    /sextant "what you want to build"
```

---

## 2. Open your project in Claude Code

Open Claude Code in your project directory (or in the IDE extension for your project).

---

## 3. Start your first task

Type:

```
/sextant "add input validation to the registration form"
```

Sextant will:

1. Classify the task (usually L1 for a normal feature)
2. Create a trace directory (`.sextant/traces/2026-XX-XX-add-input-validation/`)
3. Write a structured spec using the spec subagent
4. Auto-review the spec with the reviewer subagent
5. If spec is approved, write an implementation plan
6. Auto-review the plan
7. Show you the plan and pause:

```
── Plan approved ────────────────────────────────────
Review the plan above, then run /sextant to build.
─────────────────────────────────────────────────────
```

---

## 4. Approve and build

Review the plan (it shows the recommended implementation approach, engineering
footprint, and reviewer feedback). If it looks right:

```
/sextant
```

Sextant builds — invoking the builder subagent to make the actual code changes.
It then pauses:

```
── Build complete ───────────────────────────────────
Run /sextant to verify, review, and record this task.
─────────────────────────────────────────────────────
```

---

## 5. Verify and close

```
/sextant
```

Sextant:
1. Runs your project's verification commands (detected or from `.sextant/SEXTANT.md`)
2. Runs the reviewer on the build diff using a Clean Context Packet
3. If everything passes, runs a fast-close analysis for knowledge writebacks
4. Closes the task trace

Final output:

```
── Task complete ─────────────────────────────────────
Task:  2026-04-19-add-input-validation
Level: L1  |  Writebacks: 0
Trace: .sextant/traces/2026-04-19-add-input-validation/

Knowledge updated. The next /sextant will load these changes as context.
──────────────────────────────────────────────────────
```

---

## Dogfood evidence

Sextant v0.1.0 was cut as a Dogfood Gate tooling release with an explicit maintainer
override. Keep filling `docs/dogfood.md` from real traces only. The active evidence
target is 10 real tasks, 80% closed-loop completion, 50% non-empty reviewer deletion
proposal rate, 60% verify first-pass rate, and no more than 20% active bypasses.

Reviewer stages use Clean Context Packets: project facts, formal artifacts, and the
review rubric are allowed; generation transcript, hidden reasoning, author
self-justification, and negotiation history are excluded.

---

## That's it

Three `/sextant` invocations. Spec, plan, build, verify, record — all ran. Every gate
checked. Reviewer ran three times (spec, plan, build). Knowledge loop closed.

---

## Next steps

### Fill in your `.sextant/SEXTANT.md`

Open `.sextant/SEXTANT.md` in your project and fill in the tech stack and preferences:

```markdown
## Current Tech Stack
- Language: TypeScript 5.x
- Runtime: Node.js 20
- Test runner: Vitest
```

This makes every future task spec and plan more accurate.

### Pin your verify commands

In `.sextant/SEXTANT.md`, add a verification section:

```yaml
verify_commands:
  - npm test
  - npx tsc --noEmit
  - npm run lint
```

Without this, Sextant auto-detects from `package.json` — but pinning it is more reliable.

### Enable hooks (optional)

Add session guardrails to `~/.claude/settings.json` or your project's `.claude/settings.json`.
See `adapters/claude-code/hooks/README.md` for the three enforcement levels (advisory,
team, strict).

### Check status any time

```
/sextant-status
```

Shows the current task, stage, pending gate, and recommended next action. Useful when
resuming work after a break.

---

## Troubleshooting

**"No active task" when running `/sextant` with no args**
→ Start a new task: `/sextant "task description"`

**Gate check failed: review-spec.md not found**
→ Run `/sextant-spec` first — it creates the spec and runs the reviewer automatically.

**Verify failed — no verify commands detected**
→ Add `verify_commands:` to your `.sextant/SEXTANT.md`, or confirm commands when prompted.

**Lost track of where a task is**
→ Run `/sextant-status` — it shows stage, blockers, and the recommended next command.

**Want to restart a rejected spec**
→ Run `/sextant-spec <task_id>` to re-run the spec subagent on the existing trace,
   or `/sextant "<revised description>"` to start fresh.
