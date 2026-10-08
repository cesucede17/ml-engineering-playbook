# Prompt: create a Machine Learning project

**Author:** CSUELA · **Date:** 2026-10-07

> **How to use this (human):** create an empty folder for the project, open Claude Code inside
> it, and type:
>
> ```text
> Read <PATH>\ml-engineering-playbook\NEW_ML_PROJECT_PROMPT.md and follow it to create the project in this folder.
> ```
>
> (`<PATH>` is wherever you have the `ml-engineering-playbook` folder). You need the personal
> pipeline (`general-pipeline/`) installed once, beforehand. Claude will explain what it's going
> to create, ask you some questions, install and verify the skills, propose a design, and build
> the structure. You just answer and approve.
>
> Everything below is addressed to Claude.

---

## Instructions for Claude

You're going to create a new **Machine Learning** project in the current working directory.
`GUIDE` is the folder containing this file (`ml-engineering-playbook`). In it you'll find:

- `PROJECT_GUIDE_ML.md`: the structure and best-practices reference;
- `SKILLS_CATALOG.json` and `tools/kit.py`: the project's skills;
- `components/`: the `mle-workflow` skill, the `mle-reviewer` agent, and the tools
  (`new_ml_project.py`, `ml_registry.py`, `migrate.py`, `compare_excel.py`). Don't modify these.

Follow the phases **in order**. Each phase has a **gate**: don't move to the next one until it's
met and you've shown the evidence (command output) to the human.

### Rules for the whole process

- **Language and tone.** Reply in the profile's `language` (phase 0); so should the project's
  documentation and comments. Speak plainly and explain each technical term the first time it
  comes up, at the profile's `level`:
  - **low:** an everyday analogy and an example; short sentences; one step at a time;
  - **medium:** 1-2 sentences with an example;
  - **high:** only the unusual bits, in one sentence.
  Use generic examples ("an industrial plant," "a factory's monthly energy use") unless the human
  gives you their own.
- **One question at a time.** If you have the `AskUserQuestion` tool, use it (at most 4 options,
  the recommended one first and labeled "(recommended)"; the tool adds "Other" on its own). For
  picking several things at once, use `multiSelect: true`. Without that tool, write numbered
  options and wait.
- **Nothing is installed or created without approval.** There are three explicit approvals: the
  interview summary (phase 2), copying `mle-workflow` and `mle-reviewer` if a different version
  already existed (phase 3), and the design (phase 6).
- Read `GUIDE/PROJECT_GUIDE_ML.md` **before** phase 1.
- The project's skills are chosen **only** via `GUIDE/tools/kit.py` from
  `GUIDE/SKILLS_CATALOG.json`. Don't install or enable plugins by hand, and don't add skills
  outside the catalog; if a new one is needed, propose it as a catalog change (it goes through
  `skill-scanner` first).
- Don't activate `security-guidance` and don't `git push`. Don't read or display the content of
  any `.env`.
- **guardian is never bypassed.** The personal pipeline installed a watchdog (guardian) that can
  block one of your actions. If it does:
  1. stop and show the message;
  2. explain in one or two plain sentences, at the human's level, why that step is needed;
  3. if it's genuinely needed, ask the human to **manually** create the unlock file in the folder
     the message names (valid for 2 hours);
  4. once they confirm it's done, repeat the exact same action.
  Don't try to work around it — not with a script, not with an equivalent command. You never
  create that file yourself or write its name into a command. Two cases you'll definitely run
  into:
  - **`data/raw/` is protected**: the human copies the original data in by hand; you never write
    there (not even a `.gitkeep`: `data/` is already outside git);
  - **quality gates** (`.pre-commit-config.yaml`, the `[tool.ruff]`, `[tool.pytest]`,
    `[tool.mypy]` sections of `pyproject.toml`...) can be created, but not changed afterward:
    write them complete and correct the first time.
- Nothing is accepted without running it and seeing the output. If something fails, use
  `systematic-debugging` and fix the root cause — don't hide it or skip it.
- Don't write training code against real data until the skeleton is verified (phase 8).
- If the folder isn't empty, stop and ask before touching anything. If what they actually want
  is to reorganize an existing project, that's not creating one: follow guide §3.4 (`migrate.py`).
- If the human also wants a web app to serve the model, that's a separate project (the
  `platform-engineering-playbook` kit): note it as a next step.

### How commands are written

- `PY` is the profile's Python launcher (`python` key: `python`, `python3`, or `py`).
- Write paths with `/` and in quotes, Windows included.
- `TOOLS` is `GUIDE/components/tools`.

---

### Phase 0 — Check the personal pipeline and the environment

1. **Profile.** Read `~/.claude/pipeline_profile.json` with the file-reading tool (not a shell
   command).
   - **If it doesn't exist, stop here.** Explain, at the "low" level, that the personal pipeline
     comes first: it's installed once and sets up the watchdog, the startup summary, the journal,
     and tasks. Tell them the sentence: `Read <PATH>/general-pipeline/INSTALL_PROMPT.md and follow
     it`, and to retype this guide's sentence once done. Create nothing.
   - If it exists, keep `level`, `language`, `python` (this is `PY`), `roots`, and
     `protected_segments`. If `format` is greater than 1, warn that the personal pipeline is
     newer than this guide, and continue.
   - If the current folder isn't inside any of the `roots`, flag it: the startup summary won't
     recognize it as a project. Let the human decide whether to continue here or move it.
2. **Environment.** Check (without installing anything) that these exist: `git`, `PY` (≥ 3.10),
   `uv`, `claude`, `task` (go-task), `pre-commit`, and `gitleaks`; plus `docker` if the model will
   be served via API.

**Gate 0:** profile read (level, language, and `PY`) + a tool → version / MISSING table. If
something essential is missing, say how to install it and wait. Anything that only affects later
steps gets noted and you move on.

---

### Phase 1 — Context brief: what's being created and why (short)

Explain it in your own words, at the human's `level`, in a few lines:

1. **What you're going to do:** some questions about the project, installing two personal ML
   pieces for them (once) and the project's skills, creating the folders, designing the rest
   together, and checking that everything works before the first commit.
2. **The version-based structure** (the recommended one), with an example: each model version
   lives entirely in its own folder (`model V1`, `model V2`...) with the model, the report, and
   the delivery; only the last 2 are visible and the rest move to `obsolete/`; there are no
   `final/` folders; whatever scripts generate goes to `tmp/` until a version is accepted.
   **Why:** this way an outdated version is never opened by mistake, and it's always clear what
   was delivered with each one.
3. **The two personal ML pieces:** `mle-workflow` (the discipline that keeps the numbers
   trustworthy, based on the project's profile) and `mle-reviewer` (a reviewer that only observes,
   run before closing a version, a report, or a deliverable).
4. End with "Shall we start?" and wait for the answer.

---

### Phase 2 — Interview: what the project needs

One question at a time. If the human doesn't know, suggest the recommended option and say so:
everything gets written into `docs/decisions.md` and can be changed.

1. **Name** of the project and the Python package, **what's being predicted**, **what for**, and
   **who uses the result** (free text).
2. **Project profile** (`multiSelect: true`; explain all four per guide §1): Study + report
   (recommended if unsure) · Re-runnable · Production · EU-funded deliverable. Study, Re-runnable,
   and Production are cumulative: if two are chosen, the most demanding one applies; EU-funded
   deliverable stacks on top. Build the `--profile` text from the answer, e.g.
   `"Re-runnable + EU-funded deliverable"`.
3. **Organization:** by version, `model VNN` (recommended) · by pipeline stage (guide §3.2; for
   projects with no versioned deliverables, like a model that retrains itself in production).
4. **Data type:** tabular, pandas + scikit-learn (recommended) · deep learning, PyTorch (images,
   text, signals).
5. **Approximate data size** and where it lives: < 1 GB (recommended) · 1-50 GB · > 50 GB.
6. **MLflow:** no, the `ml_registry` version log is enough (recommended) · yes, there's already an
   MLflow server (ask for its address) · local MLflow in `mlruns/`. Explain that `ml_registry` is
   always used: it stores parameters, metrics, and fingerprints for every version, no server
   needed.
7. **Primary metric** and the minimum acceptable threshold (even if provisional).
8. **Requirements → catalog options**, as `multiSelect` questions of up to 4 options each
   (`python` always applies; with a Production profile, recommend `api` and `monitoring`):

| Question | Option |
|---|---|
| Will the model be served via an API? | `api` |
| Reads or writes a relational database? | `db` |
| Uses LLMs, RAG, or prompts? LLM fine-tuning? | `llm`, `finetuning` |
| Orchestration with Airflow? | `airflow` |
| Data > 50 GB (Spark)? | `big_data` |
| Production monitoring (drift, metrics)? | `monitoring` |
| Kubernetes? Terraform? | `k8s`, `iac` |
| Repository on GitLab or GitHub? | `gitlab` or `github` |
| Excel, Word, PowerPoint, or PDF as input or output? | `office` |
| Personal or sensitive data? | `personal_data` |

**Gate 2:** summary (name, profile, organization, type, size, MLflow, metric, and options), the
exact `new_ml_project.py` command, and the `kit.py select` command you're about to run. Wait for
the human's "yes."

---

### Phase 3 — Install `mle-workflow` and `mle-reviewer` (once per person)

These are personal: they go into `~/.claude`, not the project.

| From | To |
|---|---|
| `GUIDE/components/skill_mle_workflow/SKILL.md` | `~/.claude/skills/mle-workflow/SKILL.md` |
| `GUIDE/components/LICENSE-ECC` | `~/.claude/skills/mle-workflow/LICENSE-ECC` |
| `GUIDE/components/agent_mle_reviewer.md` | `~/.claude/agents/mle-reviewer.md` |

For each file:

1. **If the destination doesn't exist:** copy it (create the folder if missing).
2. **If it exists and is identical:** do nothing.
3. **If it exists and differs:** show the diff (with Python's `difflib`, or by reading both
   files) and explain in one sentence where that might come from: an older version of this
   guide, or a version the human has customized. Ask:
   - "Replace with the guide's version" (recommended if theirs is older than the date in
     `GUIDE/VERSION` and hasn't been touched): first save theirs alongside it, suffixed
     `.previous` (`SKILL.md.previous`, `mle-reviewer.md.previous`), then copy the new one;
   - "Keep mine" (recommended if they've customized it).

Copy using the file-writing tools or Python's `shutil.copy2`. **Only** these three paths — don't
touch anything else in `~/.claude`.

Then check that `mle-workflow` appears in your skills list and `mle-reviewer` in your agents
list. If they don't appear yet, that's fine: they'll be there next time Claude Code opens (they're
used at milestones, later on). Tell the human.

**Gate 3:** file → copied / already there / replaced (with `.previous` backup) / kept theirs
table.

---

### Phase 4 — Create the project base

```bash
PY "TOOLS/new_ml_project.py" "." --profile "<profile>"
```

Creates `data/raw/`, `data/processed/`, `src/` (with `ml_registry.py`), `model V1/`, `registry/`,
`reports/`, `experiments/`, `docs/journal/`, `tmp/`, and `obsolete/`, plus `README.md`,
`.gitignore`, `VERSIONS.md`, and the git repository (`main` branch). If it says the folder isn't
empty, stop and ask.

- **By stage** (question 3): replaces `model V1/` with `models/` and adds the guide §3.2
  structure (`data/features/`, the stages inside `src/<package>/`, `reports/validation/`).
- `.gitignore` excludes `*.csv`, `*.parquet`... Add exceptions at the end for synthetic test data
  (e.g. `!tests/fixtures/**`), which does belong in git.

**Gate 4:** tree (2 levels) and error-free output from `PY src/ml_registry.py regenerate`.

---

### Phase 5 — Install and verify the project's skills

From the project folder:

```bash
PY "GUIDE/tools/kit.py" select --type ml --options <opt1,opt2,...>
PY "GUIDE/tools/kit.py" install
```

`select` writes `.claude/pipeline-skills.json` (manifest: which skills this project uses and in
which phase), `.claude/settings.json` (the project's marketplaces and plugins; version-controlled
for the team), and copies local skills into `.claude/skills/`. `install` registers any missing
marketplaces and installs the plugins with `--scope project`.

Then:

1. Create a provisional `CLAUDE.md` with the project title and run
   `PY "GUIDE/tools/kit.py" table --write CLAUDE.md`.
2. Run `PY "GUIDE/tools/kit.py" check`. It must end in `OK` with exit code 0. If there are
   failures, run `install` again and diagnose what remains.
3. Ask the human to type **`/reload-plugins`** and wait for confirmation.
4. Verify **inside the session** that your available-skills list includes at least:
   `ml-pipeline-workflow`, `data-quality-frameworks`, `brainstorming`, `writing-plans`,
   `test-driven-development`, and `verification-before-completion`. If any is missing, stop and
   diagnose: don't continue without them.

**Gate 5:** `check` output is `OK` + confirmation that the skills are loaded in the session.

---

### Phase 6 — Design

Use the **`brainstorming`** skill, supported by **`ml-pipeline-workflow`** (structure) and
**`mle-workflow`** (discipline per the project profile), to close with the human on the rest of
the guide §3 structure, adapted to their answers: `src/<package>/` modules per stage, configs
with thresholds, how a version is released (from `tmp/` to `model VNN/` + `ml_registry`), the
prediction contract and the `mle-workflow` baseline, MLflow if chosen, CI, and `task` commands.
Write the spec in `docs/superpowers/specs/YYYY-MM-DD-initial-structure-design.md` and
`docs/decisions.md` with phase 2's answers.

**Gate 6:** the human approves the spec in writing.

---

### Phase 7 — Plan and skeleton

1. With `writing-plans`, write the plan in `docs/superpowers/plans/` as small, verifiable tasks.
2. Execute the plan with TDD (`test-driven-development`), using the manifest's **bootstrap**
   phase skills (`ml-pipeline-workflow`, `python-project-structure`, `uv-package-manager`,
   `gitlab-ci-patterns` or `github-actions-templates`).
3. The skeleton must include, at minimum:
   - An extended `README.md` (the one from `new_ml_project.py` is the base: keep its folder map).
   - A complete `CLAUDE.md` from the guide §6 template, with the "Versions" and "Milestones"
     sections. The skills section **is not hand-written**: it's regenerated with
     `kit.py table --write CLAUDE.md`.
   - `pyproject.toml` with uv, `.gitattributes`, `.editorconfig`, `.env.example`, and
     `.pre-commit-config.yaml` (ruff, gitleaks, large-file blocking), written complete the first
     time.
   - `configs/` for data, training, and validation (with **thresholds**), validated on load.
   - `Taskfile.yml` with `setup`, `test`, `lint`, `typecheck`, `ci`, **`pipeline`** (every stage in
     order, output to `tmp/`), and **`skills`** (`PY scripts/verify_skills.py check`).
   - Copy `GUIDE/tools/kit.py` to `scripts/verify_skills.py` (its `check` and `table` subcommands
     work without the guide folder).
   - The CI file (`.gitlab-ci.yml` or `.github/workflows/ci.yml`): lint, types, tests, and the
     pipeline against fixtures.
   - In every `src/<package>/` stage, a **real, minimal** entry point: preparation → training →
     validation (→ deployment only with a Production profile) must run end-to-end on a tiny
     synthetic dataset in `tests/fixtures/`, with data-schema validation, a **baseline** model,
     comparison against the thresholds, and logging of parameters and metrics (structured logs,
     and MLflow if chosen).
   - **Releasing** a version as a separate, explicit step (e.g. `task release -- V1`): it only
     copies what validation approved into `model VNN/`, logs it with `ml_registry`, and refuses if
     that version's folder already has content. Test it against a temp folder, never the real
     project.
   - A `MODEL_CARD.md` template in `docs/` (copied into `model VNN/` on release).
   - With `api`: a minimal service that loads the validated model, `/health` and `/ready`, and a
     multi-stage Dockerfile without a root user.

---

### Phase 8 — Verify the pipelines work

Run each check and show its output. **All** that apply must pass:

| Check | When |
|---|---|
| `task skills` is `OK` | always |
| `task ci` (lint + types + tests) is green | always |
| `pre-commit run --all-files` is green | always |
| The CI file is valid YAML and its stages call the same `task` commands | always |
| `task pipeline` runs every stage end-to-end on the fixtures | always |
| **Writes only to `tmp/`:** after `task pipeline`, `model V1/` is still empty | version-based |
| **Idempotency:** running `task pipeline` twice → same output (compare fingerprints) | always |
| **Validation gate:** with an impossible threshold, validation fails and nothing is released or deployed (automated test) | always |
| **Data validation:** a fixture with a broken schema makes preparation fail (automated test) | always |
| **Release:** in a temp folder, releasing logs the version (`registry/<V>.json`, `VERSIONS.md`), and releasing the same version again is refused (automated test) | always |
| Parameters and metrics logged at every stage (logs, and MLflow if chosen) | always |
| `docker build` + start + `/health` and `/ready` respond 200, and a test prediction works | with `api` |

If something can't be run on this machine (e.g. no Docker), say so clearly and note it as
pending — don't mark it as passed.

**Gate 8:** every applicable row green, with its output.

---

### Phase 9 — Wrap-up

1. Review the full diff with `requesting-code-review` (or `/code-review`) and fix what comes up.
2. First commit `chore: initial structure` on `main` (phase 4 already created the repo). No push.
3. Final report to the human:
   - Project tree (2 levels).
   - Skills-per-phase table (the one in `CLAUDE.md`), plus `mle-workflow` and `mle-reviewer`.
   - Result of every phase-8 check.
   - Pending items (what couldn't be verified, and why).
   - Next step: manually copy the original data into `data/raw/` and design the preparation step
     against real data (`brainstorming` + `data-quality-frameworks` + `mle-workflow`).
   - Reminder about **milestones**: before releasing a version, closing a report, or a
     deliverable with model figures, `mle-reviewer` is run.
   - Reminder for the team: whoever clones the repo opens Claude Code, accepts the project's
     plugins, runs `/reload-plugins` and `task skills`.

---

### Changing requirements later

```bash
PY "GUIDE/tools/kit.py" select --type ml --options <all options, old and new>
PY "GUIDE/tools/kit.py" install
PY "GUIDE/tools/kit.py" table --write CLAUDE.md
PY "GUIDE/tools/kit.py" check
```

then `/reload-plugins`. `select` doesn't disable plugins that were already enabled: if an option
is removed, the human reviews `.claude/settings.json` by hand (guardian doesn't let Claude edit
it).
