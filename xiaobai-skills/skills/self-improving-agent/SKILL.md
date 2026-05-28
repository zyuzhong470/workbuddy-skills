---
name: self-improving-agent
description: Repo-local meta-skill for improving Xiaobai Skills over time. Use after significant project changes, user feedback, install failures, promotion experiments, or repeated workflow friction to update AGENTS.md, capture project-specific gotchas, or propose new repo-local skills. Do not use globally or after every small task.
---

# Self-Improving Agent

This is a repo-local skill for Xiaobai Skills. It helps the project learn from
real work without turning every task into expensive reflection.

Use it only when one of these happens:

- A user reports an install or curation failure.
- A promotion experiment teaches something reusable.
- The recommended starter stack changes.
- The agent repeatedly searches for the same repo knowledge.
- A workflow repeats enough to deserve a repo-local skill.
- A release reveals missing docs, checks, or restore steps.

Do not use it after every small edit.

## Step 1: Diagnose The Learning

Ask:

1. Did the repo structure or command flow change?
2. Did the user correct a behavior that should persist?
3. Did an install command fail in a way future agents should know?
4. Did a starter-stack decision prove good or bad?
5. Did a repeated workflow emerge?

If the answer is no, make no changes.

## Step 2: Choose The Right Artifact

- Update `AGENTS.md` for short repo rules, commands, gotchas, or decision
  history.
- Update `README.md` for user-facing install or positioning changes.
- Update `ROADMAP.md` for future work.
- Update `docs/promotion-kit.md` for launch and marketing learnings.
- Create `skills/<name>/SKILL.md` only for repeatable multi-step workflows.

Prefer one concise update over several files.

## Step 3: Update AGENTS.md Safely

When editing `AGENTS.md`:

- Keep entries short and repo-specific.
- Add dated decision notes only when they explain future behavior.
- Remove or revise stale notes instead of appending contradictions.
- Keep the file readable for every future session.
- Never add secrets, payment details, tokens, or private user data.

## Step 4: Create Repo-Local Skills Sparingly

Create a new skill only when the workflow is:

- repeated
- multi-step
- specific enough to benefit from written procedure
- useful for future maintainers

Use:

```text
skills/<skill-name>/SKILL.md
```

The skill must include:

- clear `name`
- clear `description`
- trigger conditions
- steps
- output contract

## Step 5: Validate

Before finishing:

1. Re-read changed files.
2. Check for contradictions with existing docs.
3. Keep project-level instructions conservative.
4. If code or scripts changed, run the relevant validation.
5. Summarize the learning in the final response.

## Anti-Patterns

- Turning one-off preferences into permanent rules.
- Creating global skills for Xiaobai-specific workflows.
- Recording private sponsorship/payment data in repo docs.
- Enabling broad self-reflection on every task.
- Creating verbose AGENTS.md notes that cost more than they save.

