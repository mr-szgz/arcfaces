---
name: update-readme
description: Use only as part of a release process to render README.md in the project root from the README.template.md using the generate_readme.py script.
---

# Update README (Release Only)

Use this skill **only** when a release process is happening.

## Workflow

1. Run the script `./.agents/skills/update-readme/scripts/generate_readme.py`.
2. Ensure it renders `./.agents/skills/update-readme/references/README.template.md` into the project-root `README.md`.
3. Do not run this script outside a release process.


