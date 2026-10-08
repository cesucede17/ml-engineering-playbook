# ML Engineering Playbook

A kit for creating Machine Learning projects **with a single prompt**: Claude Code asks what the
project needs, installs and verifies the right skills, builds a **version-based** structure, and
checks that the pipelines actually run before the first commit.

This folder is **self-contained**: share it as-is, and it only needs the companion
[personal pipeline guide](../platform-engineering-playbook/README-personal-pipeline.md) installed once.

## Prerequisite: the personal pipeline

This guide requires the **personal pipeline** to be installed once per person (the guardian
watchdog, the startup summary, the journal and tasks). The prompt checks this by reading
`~/.claude/pipeline_profile.json`; if it's missing, it stops and tells you how to install it.
That profile also provides your experience level (how much Claude explains) and your language.

## What structure it creates

**Version-based** (the recommended layout): each model version lives entirely in its own
`model_vNN/` folder (model, traceability, rationale, report, presentation, and delivery).

- Only the **last 2** versions are kept visible; older ones move to `obsolete/`.
- **No `final/` folders**: the current version is simply whichever `VERSIONS.md` says it is.
- Scripts write to **`tmp/`**; a version is deliberately "released" once validated.
- Every version is logged with **`ml_registry`** (parameters, metrics, and data fingerprints).
- At **milestones** (closing a version, a report, or a deliverable with model figures), the
  **`mle-reviewer`** agent runs — it only observes and flags, you decide.

The alternative **pipeline-stage layout** is still available: it's picked during the interview.
Details in `PROJECT_GUIDE_ML.md` §3.

## How to create a project

1. Create an empty folder for the project and open Claude Code inside it.
2. Type:

   ```text
   Read <PATH>/ml-engineering-playbook/NEW_ML_PROJECT_PROMPT.md and follow it to create the project in this folder.
   ```

3. Answer the questions, type `/reload-plugins` when Claude asks you to, and approve the design.

| Phase | What happens | How it's checked |
|---|---|---|
| 0. Profile and environment | Checks the personal pipeline is installed and what tools you have | Profile read + tool → version table |
| 1. Context brief | Explains briefly what will be created and why | You say "let's start" |
| 2. Interview | Project profile, team, data type/size, MLflow, metric, and requirements | You approve the summary |
| 3. ML components | Copies `mle-workflow` and `mle-reviewer` into your `~/.claude` (if you already have different versions, shows the diffs and asks) | File → outcome table |
| 4. Scaffold | `new_ml_project.py` creates the folders, the version registry, and the git repo | Folder tree |
| 5. Skills | `kit.py` selects, installs, and verifies the project's skills | `kit.py check` passes + skills loaded in session |
| 6. Design | `brainstorming` on the adapted guide structure | You approve the spec |
| 7. Skeleton | Plan + skeleton with TDD, CI, pre-commit, `task skills` | — |
| 8. Verification | End-to-end pipelines (see phase 8 of the prompt) | Output of every command |
| 9. Wrap-up | Review, first commit (no push), report | Final report |

## Contents

```
ml-engineering-playbook/
├── README.md                     This file
├── NEW_ML_PROJECT_PROMPT.md      THE prompt: what gets asked of Claude
├── PROJECT_GUIDE_ML.md           Reference: structure and best practices
├── SKILLS_CATALOG.json           Single source of truth for skills: plugin, phase, and when each installs
├── tools/kit.py                  Selects, installs, and checks skills (plain Python, no dependencies)
├── vendored_skills/              Third-party skills, with LICENSE and .upstream-commit
├── components/                   GENERATED, do not hand-edit:
│   ├── skill_mle_workflow/       The mle-workflow skill (domain-neutral version)
│   ├── agent_mle_reviewer.md     The mle-reviewer agent (domain-neutral version)
│   ├── LICENSE-ECC               License of the source material for the two pieces above
│   └── tools/                    new_ml_project, ml_registry, migrate, and compare_excel
└── VERSION                       Date and version of the sources components/ was generated from
```

Vendored skills included: `find-bugs`, `security-audit`, `security-review`, `skill-scanner`
(Apache-2.0, from [getsentry/skills](https://github.com/getsentry/skills), redistributed as-is
with their original license and attribution — not authored by me).

## Options the kit understands

| Option | Meaning |
|---|---|
| `python` | Python codebase (implicit in ML) |
| `api` | Exposes an HTTP API (in ML: the model is served via API) |
| `db` | Relational database with migrations |
| `llm` | Uses LLMs (Claude's API or others), RAG, or prompts |
| `finetuning` | LLM fine-tuning |
| `airflow` | Orchestration with Airflow |
| `big_data` | Large datasets (> 50 GB), Spark |
| `monitoring` | Production monitoring (metrics, traces, SLOs, drift) |
| `k8s` | Kubernetes deployment |
| `iac` | Infrastructure as code (Terraform) |
| `gitlab` | Repository and CI on GitLab |
| `github` | Repository and CI on GitHub |
| `office` | Reads or writes Excel, Word, PowerPoint, or PDF |
| `personal_data` | Processes personal or sensitive data |

## How pipeline skills are kept working

- **One source of truth:** `SKILLS_CATALOG.json` states which skill, agent, or command is used,
  which plugin it comes from, in which phase, and for which requirements. No one picks skills by hand.
- **Reproducible selection:** `kit.py select` generates `.claude/settings.json` (version-controlled,
  so cloning the repo gives everyone the same plugins) and `.claude/pipeline-skills.json` (the
  project's manifest).
- **Project-scoped install:** `kit.py install` registers marketplaces and installs with `--scope project`.
- **Real verification:** `kit.py check` confirms via `claude plugin list` that every plugin is
  installed for that folder in the right state, that every skill/agent/command exists inside its
  plugin, that local skills carry a license and provenance, and that the skills table in
  `CLAUDE.md` matches the manifest.
- **Inside the project:** the kit ships as `scripts/verify_skills.py` and is checked with `task skills`.

### Adding requirements later

```bash
python <PATH>/ml-engineering-playbook/tools/kit.py select --type ml --options <all, old and new>
python <PATH>/ml-engineering-playbook/tools/kit.py install
python <PATH>/ml-engineering-playbook/tools/kit.py table --write CLAUDE.md
python <PATH>/ml-engineering-playbook/tools/kit.py check
```

and `/reload-plugins` in Claude Code.

## Reorganizing an existing project

It isn't recreated from scratch: it's reorganized with `components/tools/migrate.py`, which first
simulates, then moves files and verifies with checksums that nothing was lost (and rolls back if
anything fails). Always after a backup. Steps in `PROJECT_GUIDE_ML.md` §3.4.

## What if there's also a web app serving the model?

That's a separate project, using the `platform-engineering-playbook` kit.

## Maintaining the kit

- **Adding or changing a skill:** edit `SKILLS_CATALOG.json`. A new third-party skill goes through
  `skill-scanner` first and is stored in `vendored_skills/` with `LICENSE` and `.upstream-commit`.
- **Updating a vendored skill:** re-copy it from the source repo, run `skill-scanner`, and update
  `.upstream-commit`.
- `tools/kit.py` is identical in `ml-engineering-playbook` and `platform-engineering-playbook`: if
  changed in one, copy it to the other.
- `components/` is generated by the packager from the original sources: if `mle-workflow`,
  `mle-reviewer`, or a tool is improved, it's regenerated, not hand-edited here.
