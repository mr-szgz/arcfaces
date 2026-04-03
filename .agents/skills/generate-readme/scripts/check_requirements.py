#!/usr/bin/env python3
"""
Check Requirements Helper

This helper is generic and safe. It never installs packages or modifies
environments. It only reports what it finds.

Purpose:
Use this when you need a lightweight signal that the target project can run
this skill without installing anything.

Usage:
    python scripts/check_requirements.py --project-prefix "<project root>"
    python scripts/check_requirements.py --project-prefix "<project root>" --python "<python exe>"

Behavior:
- Searches common virtualenv folders under the target project root.
- Reports the first discovered python binary (if any).
- If --python is provided, runs "python -m pip show" for each entry in this
  skill's requirements.txt.
- When packages are missing, prints a single warning line that includes an
  install command.

Output contract:
When missing packages are detected, expect a line like:
    warning_missing_requirements: jinja2, requests | install: "<python exe> -m pip install -r "<skill_root>/requirements.txt""

Treat that line as advisory only. Do not install anything unless the user
explicitly asks.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_requirements() -> list[str]:
    req_path = _skill_root() / "requirements.txt"
    if not req_path.exists():
        return []
    reqs = []
    for raw in req_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        reqs.append(line)
    return reqs


def _req_name(req_line: str) -> str:
    # Very small parser: strip extras and version markers.
    name = req_line
    for sep in ["==", ">=", "<=", "~=", "!="]:
        if sep in name:
            name = name.split(sep, 1)[0]
    if ";" in name:
        name = name.split(";", 1)[0]
    if "[" in name:
        name = name.split("[", 1)[0]
    return name.strip()


def _find_venv_candidates(project_root: Path) -> list[Path]:
    names = [".venv", "venv", "env", ".env", ".venv3", "venv3"]
    candidates = []
    for name in names:
        p = project_root / name
        if p.exists() and p.is_dir():
            candidates.append(p)
    return candidates


def _python_path_for_venv(venv_path: Path) -> Path | None:
    win = venv_path / "Scripts" / "python.exe"
    if win.exists():
        return win
    posix = venv_path / "bin" / "python"
    if posix.exists():
        return posix
    return None


def _check_requirements(python_exe: str) -> dict:
    reqs = _read_requirements()
    if not reqs:
        return {"checked": False, "reason": "requirements.txt not found or empty"}

    missing = []
    for req in reqs:
        name = _req_name(req)
        if not name:
            continue
        try:
            proc = subprocess.run(
                [python_exe, "-m", "pip", "show", name],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if proc.returncode != 0:
                missing.append(name)
        except Exception as exc:
            return {"checked": False, "reason": str(exc)}

    return {"checked": True, "missing": missing}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect project virtual env and python binary without modifying anything."
    )
    parser.add_argument(
        "--project-prefix",
        required=True,
        help="Path to the target project root",
    )
    parser.add_argument(
        "--python",
        dest="python_exe",
        help="Python executable used to check skill requirements (optional)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    project_root = Path(args.project_prefix).expanduser().resolve()
    venvs = _find_venv_candidates(project_root)
    venv_entries = []
    for v in venvs:
        py = _python_path_for_venv(v)
        venv_entries.append(
            {
                "venv_path": str(v),
                "python_path": str(py) if py else "",
            }
        )

    selected = None
    for entry in venv_entries:
        if entry["python_path"]:
            selected = entry
            break

    req_check = None
    if args.python_exe:
        req_check = _check_requirements(args.python_exe)
        if req_check.get("checked") and req_check.get("missing"):
            req_path = _skill_root() / "requirements.txt"
            req_check["install_command"] = (
                f"\"{args.python_exe}\" -m pip install -r \"{req_path}\""
            )

    payload = {
        "project_root": str(project_root),
        "venvs": venv_entries,
        "selected_venv": selected["venv_path"] if selected else "",
        "selected_python": selected["python_path"] if selected else "",
        "requirements_check": req_check,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"project_root: {payload['project_root']}")
    print(f"selected_venv: {payload['selected_venv']}")
    print(f"selected_python: {payload['selected_python']}")
    if venv_entries:
        print("venvs:")
        for entry in venv_entries:
            print(f"  venv_path: {entry['venv_path']}")
            print(f"  python_path: {entry['python_path']}")
    else:
        print("venvs: none found")

    if req_check is not None:
        if req_check.get("checked"):
            missing = req_check.get("missing", [])
            print(f"requirements_checked: true")
            print(f"requirements_missing: {', '.join(missing) if missing else 'none'}")
            if missing:
                print(
                    "warning_missing_requirements: "
                    f"{', '.join(missing)} | install: {req_check.get('install_command','')}"
                )
        else:
            print(f"requirements_checked: false")
            print(f"requirements_reason: {req_check.get('reason', 'unknown')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
