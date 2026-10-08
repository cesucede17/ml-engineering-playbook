# Third-party notices

The skills under this folder are **not authored by me**. They are vendored (copied as-is) from
upstream open-source repositories, each pinned to a specific commit (see each skill's
`.upstream-commit` file) and kept under its original license.

| Skill | Upstream | License |
|---|---|---|
| `find-bugs` | [getsentry/skills](https://github.com/getsentry/skills) | Apache-2.0 |
| `security-audit` | [getsentry/skills](https://github.com/getsentry/skills) | Apache-2.0 |
| `security-review` | [getsentry/skills](https://github.com/getsentry/skills) | Apache-2.0 |
| `skill-scanner` | [getsentry/skills](https://github.com/getsentry/skills) | Apache-2.0 |

Each skill's own `LICENSE` file is the authoritative license text. `MIT License` in this repo's
root `LICENSE` file covers only my own content (the guide text, the `kit.py` tool, and the
`components/` templates) — it does not relicense these vendored skills.

To update a vendored skill: re-copy it from the source repository, run `skill-scanner` on it, and
update its `.upstream-commit`.
