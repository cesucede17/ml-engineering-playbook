# Guide — Creating a Machine Learning project

**Author:** CSUELA · **Date:** 2026-10-07

> **What it's for:** setting up an ML project from scratch with the same structure, the same
> rules, and the same Claude skills across the whole team.
> **How to use it:** no need to follow it by hand. In an empty folder, open Claude Code and ask
> it to read and follow `ml-engineering-playbook/NEW_ML_PROJECT_PROMPT.md`. This guide is the
> reference Claude (and the team) uses for structure and best practices.
> **Requirement:** the personal pipeline (`general-pipeline`) must already be installed, once
> per person. The prompt checks this and stops with a message if it's missing.

---

## 1. Before starting: the questions

Claude does **not** write training or deployment code without having these answers. Have them
ready (or tell it to assume defaults and record that in `docs/decisions.md`):

| Question | Options | What it changes |
|---|---|---|
| Project profile? | **Study + report** · **Re-runnable** · **Production** · **EU-funded deliverable** (combinable) | How much discipline is required (the `mle-workflow` skill, §2.1) and what `mle-reviewer` checks |
| How are results organized? | **By version**, `model VNN` (recommended) · by pipeline stage | Where each version's model, report, and delivery end up (§3) |
| Problem type? | **Tabular** (pandas + scikit-learn) · **Deep learning** (PyTorch) | Libraries, training structure, whether a GPU is needed |
| Approximate data size? | < 1 GB · 1-50 GB · > 50 GB | pandas vs. batch processing; whether data fits in the project folder or needs external storage |
| Is there MLflow? | No (the version registry is enough) · yes, there's already a server · local MLflow | Where experiments also get logged (§4.4) |

By default, if no one says otherwise: **Study + report, by version, tabular, < 1 GB, no MLflow**
(the `ml_registry` version log stores parameters, metrics, and fingerprints for every version).

### The four profiles, in one sentence each

- **Study + report:** the output is a document delivered once. Example: an energy-savings study
  for an industrial plant.
- **Re-runnable:** the same code gets re-run when new data arrives. Example: a consumption model
  recalculated every month.
- **Production:** another system calls the model without a human reviewing each result. Example:
  a prediction consumed by a web application.
- **EU-funded deliverable:** the figures end up in a European project's deliverable; stacks on
  top of the underlying profile.

Study → Re-runnable → Production are cumulative: each one includes the essentials of the
previous.

---

## 2. Installing the skills

### 2.1 The personal ML pieces: `mle-workflow` and `mle-reviewer`

Installed **once per person** in `~/.claude` (the prompt copies them from `components/` if you
don't have them, and if you have different versions it shows the diff and asks):

| Piece | Where it lives | What it does |
|---|---|---|
| Skill **`mle-workflow`** | `~/.claude/skills/mle-workflow/` | The discipline matching the project's profile: data contract, baseline, validation before accepting a version, error analysis, and traceability. |
| Agent **`mle-reviewer`** | `~/.claude/agents/mle-reviewer.md` | A **read-only** reviewer run at **milestones** (§4.2): looks for data leakage, comparisons with no baseline, misleading metrics, and non-reproducible results. |

`ml-pipeline-workflow` (from the catalog, §2.2) says **how the pipeline is organized**;
`mle-workflow` says **how to work** so the numbers stay trustworthy.

### 2.2 The project's own skills: the catalog

**Not installed by hand.** The `NEW_ML_PROJECT_PROMPT.md` prompt does it via `tools/kit.py`,
which picks skills from `SKILLS_CATALOG.json` based on the project's requirements (options like
`api`, `llm`, `gitlab`, `office`...), writes `.claude/settings.json` and
`.claude/pipeline-skills.json`, installs the plugins **at project scope**, and **verifies** that
every skill, agent, and command exists and is active. The project's phase → skills table lives
in its `CLAUDE.md` and is validated with `task skills`.

To preview what would happen without creating anything yet, in a test folder:

```bash
python <ml-engineering-playbook>/tools/kit.py select --type ml --options api,gitlab,monitoring
python <ml-engineering-playbook>/tools/kit.py table
```

An ML project **always** carries `ml-pipeline-workflow` (the central one), the `data-scientist`,
`ml-engineer`, and `mlops-engineer` agents, `data-quality-frameworks`, the Python ones
(`python-project-structure`, `uv-package-manager`, `python-testing-patterns`...),
`property-based-testing`, the `superpowers` process skills, and the review/security ones. The
rest depends on the chosen options.

---

## 3. The structure

### 3.1 By version (the recommended one)

The idea: **each model version lives entirely in its own folder**, with everything produced
alongside it. To know what shipped with V3, just open `model V3/`.

```
<project>/
├── README.md                     Map: what's in each folder and which version is current
├── VERSIONS.md                   Version history. Generated by ml_registry (never hand-edited)
├── CLAUDE.md                     Project rules for Claude (template in §6)
├── pyproject.toml                Dependencies via uv (uv.lock version-controlled)
├── .gitignore                    data/, tmp/, binaries (xlsx, pptx, joblib, pt...), .env
├── .env.example                  Environment variables, no real values
│
├── data/                         NEVER in git (origin and date documented elsewhere)
│   ├── raw/                      Data exactly as it arrived. Read-only (guardian protects it)
│   └── processed/                Clean and validated, generated by code
│
├── src/
│   ├── ml_registry.py            Version registry (copied in by new_ml_project.py)
│   └── <package>/                The code, split by stage: preparation, training,
│                                 validation (and deployment, if the profile is Production)
├── configs/                      Parameters, paths, and validation THRESHOLDS (yaml)
├── tests/                        unit/, integration/, and fixtures/ (small synthetic data)
│
├── model V1/                     EVERYTHING for that version: model, traceability notes,
├── model V2/                     rationale, report, presentation, and client delivery
│
├── registry/                     Each version's record: <VNN>.json, <VNN>.params.yaml, current.txt
├── reports/                      Only project-wide documents (not version-specific)
├── experiments/                  Exploratory trials
├── notebooks/                    (optional) Exploration only, numbered: 01_eda.ipynb...
├── docs/
│   ├── decisions.md              Answers from §1 and key decisions
│   ├── superpowers/specs/        Designs (YYYY-MM-DD-<topic>-design.md)
│   ├── superpowers/plans/        Implementation plans
│   └── journal/                  End-of-day summaries
├── tmp/                          Script and test output. Outside git
└── obsolete/                     Superseded material, old versions included
```

`python <ml-engineering-playbook>/components/tools/new_ml_project.py <path> --profile "<profile>"`
creates this base (with `model V1/`, `registry/`, `VERSIONS.md`, a README, `.gitignore`, and
`git init`). The prompt adds the rest afterward (code, configs, tests, CI).

**Version rules:**

1. **One folder per version**, always named the same way: `model V1`, `model V2`... Inside goes
   **everything** for that version: the model, the traceability notes (where every figure comes
   from), the rationale, the report, the presentation, and the delivery.
2. **Only the last 2 versions visible** at the root. When a third one is born, the oldest visible
   one moves to `obsolete/`. This way no one opens an outdated version by mistake.
3. **No `final/` folders**, or any other cross-cutting ones. "Final" stops being final the moment
   the next version lands; `VERSIONS.md` says which one is current.
4. **Scripts write to `tmp/`**, never on top of an already-released `model VNN/`. A version is
   **released** deliberately: once validated (and reviewed at the milestone, §4.2), its results
   are copied from `tmp/` into `model VNN/` and logged. From then on it's never touched.
5. **Every version is logged with `ml_registry`** (§3.3), storing parameters, metrics, and
   fingerprints of the data and results.
6. **git tracks only code and text.** Data, models, Excel files, presentations, and `tmp/` stay
   out.

> **Fingerprint (SHA-256):** a code computed from a file's content that changes if a single byte
> changes. Used to tell whether a data spreadsheet is exactly the one used in the previous
> version, without opening it.

### 3.2 By pipeline stage (alternative)

For projects with no versioned deliverables (e.g. a production model that retrains itself),
results are organized by stage instead:

```
<project>/
├── data/raw/  data/processed/  data/features/
├── src/<package>/
│   ├── data_preparation/         ingestion → validation → cleaning → features
│   ├── model_training/           training (sklearn or PyTorch)
│   ├── model_validation/         metrics, comparison with the production model, report
│   ├── model_deployment/         packaging, serving (API/batch), model registry
│   └── common/                   logging, config loading, seeds, utilities
├── models/<VNN>/                 Each version's artifacts. NEVER in git
├── reports/validation/           Generated validation reports
├── configs/  tests/  experiments/  notebooks/  docs/
├── registry/  VERSIONS.md        The version log works the same way
├── tmp/                          Test runs. Outside git
└── obsolete/                     Superseded material
```

Created with the same tool, then `model V1/` is replaced with `models/`. Rules 4, 5, and 6 from
§3.1 still apply.

### 3.3 The tools

Found in `ml-engineering-playbook/components/tools/`, using only Python's standard library.

| Tool | What for | Usage |
|---|---|---|
| `new_ml_project.py` | Create a new project's base (empty folder) | `python new_ml_project.py <path> --profile "Re-runnable"` |
| `ml_registry.py` | Log each version and compare them. Copied into `src/` | see below |
| `migrate.py` | Reorganize an existing project without losing anything | §3.4 |
| `compare_excel.py` | Check that two spreadsheets match, cell by cell | `python compare_excel.py A.xlsx B.xlsx [--tolerance 1e-9] [--ignore <sheets>]` |

**`ml_registry`**, from code:

```python
from ml_registry import version

with version("V2", project=".", description="Adds outdoor temperature") as v:
    v.parameters(alpha=0.1, window=24)
    v.data("data/raw/consumption_2026.xlsx")
    # ... train and validate ...
    v.metrics(r2=0.81, mae=12.4)
    v.result("model V2/model.joblib", "model V2/report.docx")
```

On exiting the block it writes `registry/V2.json` and `registry/V2.params.yaml`, warns if a data
file at the same path has changed since the previous version, and regenerates `VERSIONS.md`. If
the code inside fails, nothing is logged.

From the terminal (`python src/ml_registry.py ...`):

| Command | What it does |
|---|---|
| `verify V2` | Recomputes fingerprints: OK / CHANGED / MISSING |
| `compare V1 V2` | Which parameters, metrics, and data changed |
| `register V1 --description … --data … --result … --param k=v --metric k=v [--date YYYY-MM-DD]` | Logs an old version after the fact |
| `current V2` | Marks the current version |
| `regenerate` | Rebuilds `VERSIONS.md` |

### 3.4 Reorganizing an existing project

Moving an old project into this structure uses `migrate.py`, **never** manual moves:

1. A full **backup** of the project in a separate folder (e.g. the projects folder's `tmp/`)
   before anything else.
2. A plan (`plan.json`) with the moves and the folders left untouched:

   ```json
   {"moves": [{"from": "results/v3", "to": "model V3"}],
    "untouchable": ["model V4"],
    "add_only": ["model V3"]}
   ```

   - **untouchable:** nothing moves into or out of these (e.g. the current version);
   - **add_only:** something can be added inside, but existing content isn't changed.
3. `python migrate.py --project <path> --plan plan.json` **simulates** and shows the plan. It's
   reviewed with the human.
4. With `--apply`: fingerprint inventory before → move → fingerprint inventory after → verify
   nothing was lost or duplicated. If anything fails, it's rolled back. **Close Excel and File
   Explorer on that folder first** — an open file can't be moved.
5. If code paths change, the current version is rebuilt into `tmp/` and compared against the
   released one (`compare_excel.py`). Only accepted if they match.
6. Old versions are logged after the fact with `ml_registry.py register`.

---

## 4. Best practices (mandatory)

### 4.1 The standard ones

1. **Modularity.** Each stage is a module with an entry point (`python -m <package>.<stage>`)
   and can be tested on its own, without running the previous ones (use `tests/fixtures/`).
2. **Idempotency.** Re-running a stage with the same inputs gives the same outputs and breaks
   nothing: it writes to `tmp/` (or overwrites atomically), never appends to what's already
   there. `data/raw/` is never modified: data errors are fixed in code.
3. **Reproducibility.** Seeds fixed in config; dependencies locked in `uv.lock`; every version
   logged with its parameters, the git commit, and the data fingerprints.
4. **Data and model versioning.** Data and models stay out of git. `ml_registry` tracks which
   data and which results belong to each version (MLflow's and DVC's ideas, without the
   servers). If the team already has **MLflow**, experiments are also logged there (`mlruns/`
   outside git if local); if they already use **DVC**, that's kept.
5. **Validation before accepting a version** (and before any deployment). The validation stage
   compares against the thresholds in `configs/` and against the current version. If it doesn't
   pass, the version isn't released and nothing is deployed. No exceptions.
6. **Traceability.** Every stage logs parameters, metrics, input/output data size, and duration
   (structured logging). No stray `print` calls. Every figure in a report traces back to which
   file, which version, and which script produced it (traceability notes in `model VNN/`).
7. **Data validation.** Preparation checks schema, types, nulls, ranges, duplicates, and dates
   (timezone and format) before continuing. If it fails, it stops.
8. **No data leakage.** Train/val/test splits decided before building features; for time series,
   split by time, never randomly.
9. **Notebooks for exploration only.** What works in a notebook moves into `src/` with tests.
10. **Secrets.** Never in code or git. Local `.env` + version-controlled `.env.example`.
11. **Baseline first.** Before any complex model, a trivial baseline (mean, majority class, last
    known value) and a simple one (linear/logistic regression). Every new model is compared
    against them.
12. **Business-aligned metric.** The validation metric is chosen up front, with whoever will use
    the result, and written into `docs/decisions.md`. For imbalanced classes, never accuracy
    alone.
13. **Configuration, not constants.** Hyperparameters, paths, and thresholds in `configs/`,
    validated on load. No magic numbers in code.
14. **Code quality like any other software.** `ruff` (format and lint), types with
    `mypy`/`pyright`, pre-commit with `gitleaks` and large-file blocking (avoids accidentally
    committing datasets or models). Quality rules are written correctly from the start:
    afterward, guardian doesn't let Claude change them just to make a check "pass."
15. **Git.** Short branches per change, Conventional Commits (`feat(data): …`,
    `fix(training): …`), review before merging into `main`, and a tag per released version
    (`model-V2`).
16. **CI.** On every push: lint, types, unit tests, and the full pipeline against
    `tests/fixtures/` (minutes, not hours). Real training never runs in CI.
17. **Model card.** Every released version carries a `MODEL_CARD.md` in its folder: what it's
    for and what it isn't, training data, per-segment metrics, known limitations and biases.
18. **Production monitoring** (Production profile). Log inputs and predictions (no personal
    data), watch for data drift and performance drift once ground truth arrives, and define
    **when retraining happens**.
19. **Reversible deployment** (Production profile). The previous version stays registered and
    can be rolled back to within minutes.
20. **Personal data (GDPR).** Minimization, pseudonymization where possible, and a defined
    retention period.

### 4.2 Milestones: `mle-reviewer`

A **milestone** is a moment with no easy way back:

- releasing a model version;
- closing a report with model figures;
- closing a deliverable with model figures.

Before every milestone, Claude runs the **`mle-reviewer`** agent (read-only), shows its findings,
and **the human decides**. The reviewer fixes nothing: it flags things like a model compared
with no baseline, or a feature using information from the future (data leakage).

---

## 5. The Claude working pipeline

**Typical** phases and skills. Each project's exact table is generated by the kit into its
`CLAUDE.md`.

| Phase | What's produced | Skills |
|---|---|---|
| Bootstrap | Structure, `pyproject.toml`, `CLAUDE.md`, `docs/decisions.md`, CI | `ml-pipeline-workflow`, `/ml-pipeline`, `python-project-structure`, `uv-package-manager`, `gitlab-ci-patterns` / `github-actions-templates` |
| Design | Spec in `docs/superpowers/specs/` | `brainstorming`, `mle-workflow` (prediction contract) |
| Plan | Plan in `docs/superpowers/plans/` | `writing-plans`, `using-git-worktrees` |
| Data | Preparation + tests + data validation; EDA in a notebook | `data-quality-frameworks`, `mle-workflow`, `property-based-testing`, `test-driven-development`, `data-scientist` and `data-engineer` agents |
| Training | Training, baseline first, output to `tmp/` | `ml-pipeline-workflow`, `mle-workflow`, `ml-engineer` agent, `test-driven-development` |
| Validation | Metrics against thresholds and the current version; error analysis | `mle-workflow`, `verification-before-completion` |
| Milestone | Review before releasing the version, the report, or the deliverable | **`mle-reviewer`** agent |
| Release | `model VNN/` with everything + `ml_registry` + `current` | `verification-before-completion` |
| Review | Reviewed diff | `/code-review`, `/review-pr`, `find-bugs`, `requesting-code-review` |
| Security | Dependencies and config reviewed | `security-review`, `/audit`, `supply-chain-risk-auditor`, `secrets-management` |
| Deployment | (Production) served model + checklist | `deployment-pipeline-design`, `/config-validate`, `mlops-engineer` agent |
| Documentation | README, `CLAUDE.md` up to date, model card | `claude-md-improver` (+ `docx` with the `office` option) |

---

## 6. Project `CLAUDE.md` template

```markdown
# <Project>

<One sentence: what it predicts, for whom, with what data.>

## Starting decisions
- Profile: <Study + report | Re-runnable | Production | + EU-funded deliverable> (mle-workflow skill)
- Organization: <by version (model VNN) | by stage (models/VNN)>
- Type: <tabular (pandas + scikit-learn) | deep learning (PyTorch)>
- Data: <approx. size>, source: <...>. Detail in docs/decisions.md
- Registry: ml_registry (registry/ and VERSIONS.md). MLflow: <no | server ... | local in mlruns/>

## Pipeline
<The phase → skills table is written by `kit.py table --write CLAUDE.md` between the skills:start / skills:end markers.>
Use `ml-pipeline-workflow` for the pipeline's structure and `mle-workflow` for the discipline.

## Versions
- Each version lives entirely in `model VNN/` (model, traceability, rationale, report, deck, delivery).
- Only the last 2 versions visible; older ones move to obsolete/. No final/ folders.
- Scripts write to tmp/, never on top of an already-released model VNN/.
- Every version is logged with src/ml_registry.py; the current one is in VERSIONS.md.
- To reorganize folders: migrate.py (simulate, show, apply) after a backup.

## Milestones
Before releasing a version, closing a report with model figures, or a deliverable with model
figures, run the mle-reviewer agent and show its findings. The human decides.

## Rules
- Every stage is independently testable; tests in tests/unit/<stage>/.
- Re-running a stage must be safe (idempotent). data/raw/ is read-only.
- Nothing is released or deployed without validation passing against configs/'s thresholds.
- Before writing training or deployment code, check the starting decisions.
- Data, models, binaries, tmp/, and .env never in git. Never read or display .env's content.
- Documentation and comments in <language>.

## Commands
- `uv sync` — install
- `uv run pytest -q` — tests
- `uv run python -m <package>.<stage>` — run one stage
- `task pipeline` — every stage in order (output to tmp/)
- `python src/ml_registry.py compare V1 V2` — compare versions
- `task skills` — verify the project's skills are installed and active
```

---

## 7. Starting a project

Use `ml-engineering-playbook/NEW_ML_PROJECT_PROMPT.md`: in an empty folder, open Claude Code and
type `Read <path>\ml-engineering-playbook\NEW_ML_PROJECT_PROMPT.md and follow it to create the
project in this folder.` Claude checks that you have the personal pipeline, interviews you,
installs `mle-workflow` and `mle-reviewer`, creates the base with `new_ml_project.py`, installs
and verifies the project's skills, designs the rest with you, and checks that the pipeline runs
end-to-end before the first commit.

---

## 8. "Well-built project" checklist

- [ ] `mle-workflow` and `mle-reviewer` available in the session
- [ ] `.claude/settings.json` and `.claude/pipeline-skills.json` in the repo; `task skills` is OK
- [ ] `CLAUDE.md` with the starting decisions, the version rules, and the milestone rule
- [ ] `docs/decisions.md` with profile, organization, problem type, data size, and MLflow
- [ ] `README.md` with the folder map; `VERSIONS.md` generated by `ml_registry`
- [ ] `uv run pytest -q` green
- [ ] `git status` clean, with no data, models, binaries, or `.env` in the history
- [ ] Validation thresholds in `configs/` (even if provisional)
- [ ] `task pipeline` runs every stage against the fixtures, twice with the same result, and
      writes only to `tmp/`
- [ ] With an impossible threshold, validation fails and nothing is released or deployed
