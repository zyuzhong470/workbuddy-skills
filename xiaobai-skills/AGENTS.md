# Xiaobai Skills Agent Notes

This repository builds and publishes `xiaobai-skills`, a beginner-friendly
starter pack and curator for Codex/agent skills.

## Codebase Map

- `SKILL.md`: the main Xiaobai skill loaded by Codex.
- `agents/openai.yaml`: UI metadata for Codex skill listing.
- `scripts/install-xiaobai-skills.ps1`: Windows installer and curator script.
- `docs/`: design notes, promotion kit, and sponsor docs.
- `assets/`: public assets such as the WeChat Pay QR code.
- `skills/self-improving-agent/`: repo-local skill for project reflection.
- `README.md`: public-facing GitHub project page.
- `ROADMAP.md`: planned work.

## Local Norms

- Keep public repository docs mostly ASCII/English unless a file is explicitly
  meant to be Chinese; this avoids encoding issues in Windows PowerShell output.
- Prefer conservative defaults: install useful skills, but move broad or risky
  alternatives to backup rather than global.
- Do not enable `superpowers` globally unless the user explicitly asks; it is a
  backup framework due to possible compute/context overhead.
- Treat WeChat Pay information as public sponsorship material only; never commit
  private payment credentials or personal secrets.

## Guardrails

- Never delete installed user skills during curation unless the user explicitly
  asks for deletion. Move to backup instead.
- Do not re-enable all backup workflow frameworks at once.
- Do not make claims about guaranteed star growth, sponsorship income, or viral
  performance.
- Do not add fake stars, vote-buying instructions, or spammy promotion tactics.

## Patterns & Gotchas

- Git and GitHub CLI may be installed but unavailable in the current PowerShell
  PATH. Use full paths if needed:
  - `C:\Program Files\Git\cmd\git.exe`
  - `C:\Program Files\GitHub CLI\gh.exe`
- GitHub Sponsors may not support receiving funds in every region; this project
  currently uses a custom WeChat Pay sponsor page.
- If adding Chinese text, verify the committed file displays correctly in
  GitHub, not only in the local terminal.

## Repo-Local Skills

| Skill | Purpose | Trigger |
| --- | --- | --- |
| [self-improving-agent](skills/self-improving-agent/SKILL.md) | Capture project-specific learnings and improve repo instructions | Significant project change, install failure, repeated workflow, or user correction |

## Self-Correction Protocol

Use the repo-local `self-improving-agent` skill after meaningful project changes
or feedback. Do not invoke it after every small edit.

