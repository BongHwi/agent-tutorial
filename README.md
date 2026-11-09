# AI Coding Agent Tutorial (Codex · DeepSeek Harness)

A self-paced, remote, 4-week hands-on course for physics students.
The goal is not "how to make AI write code" but **how to use AI as a research/development partner that you design, manage and verify**.

**Language:** the course text is English. Prompts are given in English and Japanese; you may write or adapt your own prompts in Japanese (or English). Observations in your submission can also be in Japanese. Keep the rules explicit (file-name format, "dry-run", "wait for my approval") whichever language you use.

## Concepts
| Concept | One line | Where you meet it |
|---|---|---|
| Model | The LLM that generates text. It cannot act on its own | everywhere |
| Harness | The program that wraps a model with tools, permissions and a loop to make an "agent" (Codex CLI, DeepSeek Harness) | M1, M5 |
| Tool | An action the agent really performs (read/write files, run commands) | observe in M1 |
| Skill | A reusable bundle of instructions/tools for a recurring task | week 4 |
| Session | One conversation. After it ends the agent remembers nothing | M2 |
| Context | What the agent can see at once (conversation, files). It is limited | M6+ |
| Permission | What the agent is allowed to do (sandbox, approvals) | M3 |
| Verification | Checking the result by an **independent method**, not by the agent's word | every mission |

## 4-week overview
| Week | Content | Missions |
|---|---|---|
| 1 | File missions: environment, renaming, restructuring with undo | M0, M1, M2 |
| 2 | Permission experiment, working via scripts, DeepSeek Harness (DSH) | M3, M4, M5 |
| 3 | Detector timing analysis: delegate analysis and verify it | M6, M7, M8 |
| 4 | Writing Skills: turn your way of working into a reusable Skill | M9, M10, M11 |

This package is **week 1 (M0–M2)**.

## Layout
```
agent-tutorial/
  README.md          this file
  missions/          M0.md, M1.md, M2.md  (go in order)
  tools/             check_env.py, make_messy_folder.py, check_mission.py
```
Put it at `~/agent-tutorial`. Create all work **only inside `~/agent-lab/`**.

## How to proceed
1. Do M0 → M1 → M2 in order, following `missions/`.
2. Try the given prompt as is; if the result is poor, improve the prompt. How you changed it is part of your submission.
3. When the "Done when" criteria are met, collect the "Submit" items and submit.

## How to submit (one GitHub repo per student)
Each student uses **their own GitHub repo** for all missions.

1. Once (in M0): create a **private** GitHub repo `agent-tutorial-<student number>` and invite the instructor account **`BongHwi`** as a collaborator (repo Settings → Collaborators → Add people).
   ```bash
   cd ~/agent-lab
   git clone https://github.com/<your GitHub ID>/agent-tutorial-<student number>.git submission
   ```
   The submission repo lives in `~/agent-lab/submission`. It is a **separate git repository** from the mission folders (`m1`, `m2`); do not mix them.
2. For each mission write one file `submission/M<n>.md` with the "Submit" items (command output in code blocks). Copy artifacts (`moves.csv`, `undo.py`, ...) into `submission/M<n>/`. Do not upload `.mission.json` or the whole data folder.
3. Commit and push:
   ```bash
   cd ~/agent-lab/submission
   git add -A && git commit -m "M<n> submission" && git push
   ```
4. The last commit before the deadline is graded. History is also read, so never rewrite it (no force push).

Grading = **verification tool passes + observation notes**. 5–10 lines of notes are enough, but they must be concrete: what the agent did, what you corrected.
Create a GitHub account in M0 if you have none, and never upload personal data or keys.

## Safety rules (must follow)
1. Always run the agent inside `~/agent-lab/<work folder>`. Never from `~` or `/`.
2. Start Codex with `--cd <folder> --sandbox workspace-write`. Do not use options such as `--dangerously-bypass-approvals-and-sandbox`.
3. Before any task, `git init` + commit so you can restore the starting state.
4. Read and understand a command before approving it. If you don't understand, don't approve; ask for an explanation.
5. No deletion (`rm`, overwriting). Move things into e.g. `_duplicates/` instead.
6. Never put passwords, API keys or personal data in prompts or files.
7. When the agent says "done", check with the verification tool and `git status` yourself.
