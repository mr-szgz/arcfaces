---
name: generate-readme
description: Generate project README.md
---

# Generate README

## Overview

This skill is self-contained. Use scripts instead of ad-hoc steps.

- `scripts/` holds the runnable tooling.
- `assets/` holds the README template.
- `references/` holds usage docs.

## Paths

- Skill root = folder containing this `SKILL.md`.
- Use relative paths for all skill files: `scripts/`, `assets/`, `references/`.
- Project root must be passed explicitly with `--project-prefix`.

## Inputs

- `tag` (required): release tag to target (e.g., `v0.3.1`). Never assume `latest`.
- `owner` + `repo` (required for asset lookup). Prefer reading from git remote; if missing, ask.

## Outputs

- Project root `README.md` rendered from the template.
- Optional GitHub release description replaced with the full README (user-confirmed).

## Script-First Operations

Use the scripts for all release asset discovery and README rendering. Do not manually craft URLs.

- `python scripts/check_requirements.py --project-prefix "<path>" [--python "<python_exe>"]`
  Checks this skill's `requirements.txt` against a target project environment and prints a single-line warning with an install command when packages are missing.
- `python scripts/fetch_release_assets.py <owner> <repo> <tag>`
  Prints `asset_name<TAB>download_url` for the tag's release assets. Use this output to select the `.whl` and `run_arcfaces.exe` URLs.
- `python scripts/generate_readme.py --version <tag>`
  Renders the template into `README.md` using the selected asset URLs and changelog content.

## References

- Template: `assets/README.template.md`

## Workflow

1. Collect `tag`, `owner`, and `repo` (ask if missing).
2. Run `fetch_release_assets.py` and capture the `.whl` and `run_arcfaces.exe` URLs.
3. Run `generate_readme.py --version <tag>` and ensure it renders the template into the project root `README.md`.
4. Prompt: `Update GitHub release description with README.md? (Y/n)`.
5. If confirmed, run `gh release edit <tag> --notes-file README.md`. If declined, skip.

## Hard Rules

- Never infer `latest`.
- Always derive asset URLs from the release assets list for the specified tag.
- Keep all changes inside this skill directory except for the final `README.md`.
