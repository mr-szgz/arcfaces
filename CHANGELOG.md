# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `--open-output-dir` (arcfaces): open the output directory after a run.
- Added `LICENSE` (GPLv3). This means the project is now under the GNU General Public License v3, requiring source availability and GPL-compatible derivatives; we chose this to align with visomaster-fusion so the projects can cohabitate in the future.

## [0.1.1] - 2026-04-03

### Changed
- Release workflow now builds a Windows executable and publishes it with release assets.
- Development tooling updated for PyInstaller builds and README generation.
- Removed obsolete readme-update skill tooling.

## [0.1.0] - 2026-04-03

### Added
- `--install` (run-arcfaces): install the File Explorer context-menu entry.
- `--uninstall` (run-arcfaces): remove the File Explorer context-menu entry.
- `--info` / `-i` / `-Info` (run-arcfaces): show resolved paths and registry command.
- `--version` / `-v` / `-Version` (arcfaces): print version and exit.
- Positional `PATH` argument (arcfaces): allows `arcfaces <path>` without flags.
- Comma-separated `--save-faces` values (arcfaces): accept multiple sizes in one run.
