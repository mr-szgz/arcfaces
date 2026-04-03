from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

_MENU_KEY = r"Software\Classes\Directory\shell\Arcfaces"


def _find_project_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file() and (parent / "arcfaces").is_dir():
            return parent
    return start


def _resolve_project_root() -> Path:
    if getattr(sys, "frozen", False):
        start = Path(sys.executable).resolve().parent
    else:
        start = Path(__file__).resolve().parent
    return _find_project_root(start)


def _resolve_python(project_root: Path) -> Path | None:
    override = os.environ.get("ARCFACES_PYTHON")
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = project_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python.resolve()

    if not getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    fallback = shutil.which("python")
    if fallback:
        return Path(fallback).resolve()

    return None


def _resolve_launcher_path(project_root: Path) -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    candidate = project_root / "dist" / "run-arcfaces.exe"
    if candidate.exists():
        return candidate.resolve()

    return None


def _install_context_menu(project_root: Path) -> int:
    if os.name != "nt":
        print("Context-menu install is only supported on Windows.", file=sys.stderr)
        return 1

    launcher = _resolve_launcher_path(project_root)
    if not launcher:
        print("run-arcfaces.exe not found. Build it first, then re-run --install.", file=sys.stderr)
        return 1

    try:
        import winreg
    except Exception as exc:
        print(f"Unable to load winreg: {exc}", file=sys.stderr)
        return 1

    command_value = f"\"{launcher}\" \"%1\""
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _MENU_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Run Arcfaces")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(launcher))
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, f"{_MENU_KEY}\\command", 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command_value)

    print(f"Installed context menu: {launcher}")
    return 0


def _delete_registry_tree(root, subkey: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_registry_tree(root, f"{subkey}\\{child}")
    except FileNotFoundError:
        return

    winreg.DeleteKey(root, subkey)


def _uninstall_context_menu() -> int:
    if os.name != "nt":
        print("Context-menu uninstall is only supported on Windows.", file=sys.stderr)
        return 1

    try:
        import winreg
    except Exception as exc:
        print(f"Unable to load winreg: {exc}", file=sys.stderr)
        return 1

    _delete_registry_tree(winreg.HKEY_CURRENT_USER, _MENU_KEY)
    print("Removed Arcfaces context menu entry.")
    return 0


def _format_registry_command(launcher: Path) -> str:
    return f"\"{launcher}\" \"%1\""


def _info(project_root: Path) -> int:
    launcher = _resolve_launcher_path(project_root)
    python_exe = _resolve_python(project_root)

    print("Arcfaces launcher info:")
    print(f" - project_root: {project_root}")
    print(f" - launcher_exe: {launcher or '(not built)'}")
    print(f" - python: {python_exe or '(not found)'}")

    if os.name != "nt":
        if launcher:
            print(f" - registry_command_preview: {_format_registry_command(launcher)}")
        return 0

    try:
        import winreg
    except Exception as exc:
        print(f" - registry: unable to load winreg ({exc})")
        if launcher:
            print(f" - registry_command_preview: {_format_registry_command(launcher)}")
        return 0

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _MENU_KEY, 0, winreg.KEY_READ) as key:
            display, _ = winreg.QueryValueEx(key, "")
            icon, _ = winreg.QueryValueEx(key, "Icon")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{_MENU_KEY}\\command", 0, winreg.KEY_READ) as key:
            command, _ = winreg.QueryValueEx(key, "")
        print(" - registry_status: installed")
        print(f" - registry_display: {display}")
        print(f" - registry_icon: {icon}")
        print(f" - registry_command: {command}")
    except FileNotFoundError:
        print(" - registry_status: not installed")
        if launcher:
            print(f" - registry_command_preview: {_format_registry_command(launcher)}")
    return 0


def _coerce_args(args: list[str]) -> list[str]:
    if not args:
        return args
    has_recognize = any(arg.lower() in {"--recognize", "-recognize"} for arg in args)
    if not has_recognize and not args[0].startswith("-"):
        return ["--recognize", args[0], *args[1:]]
    return args


def _run_arcfaces(project_root: Path, forward_args: list[str]) -> int:
    python_exe = _resolve_python(project_root)
    if not python_exe:
        print("Unable to locate a Python interpreter for Arcfaces.", file=sys.stderr)
        return 1

    cmd = [str(python_exe), "-m", "arcfaces", *forward_args]
    env = os.environ.copy()
    env["ARCFACES_PROG"] = "run-arcfaces"
    result = subprocess.run(cmd, cwd=str(project_root), env=env)
    return int(result.returncode)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run-arcfaces")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install a File Explorer context-menu entry (Windows only).",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the File Explorer context-menu entry (Windows only).",
    )
    parser.add_argument(
        "--info",
        "-Info",
        "-i",
        action="store_true",
        help="Show resolved paths and registry status without installing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args, remainder = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    project_root = _resolve_project_root()

    if args.install:
        return _install_context_menu(project_root)
    if args.uninstall:
        return _uninstall_context_menu()
    if args.info:
        return _info(project_root)

    if not remainder:
        parser.print_usage(sys.stderr)
        return 2

    forward_args = _coerce_args(remainder)
    return _run_arcfaces(project_root, forward_args)


if __name__ == "__main__":
    raise SystemExit(main())
