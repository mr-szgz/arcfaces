# Arcfaces CLI

Analyze images and folders of images using arcface to organize and create visomaster compatible target face embeddings.

## Install

1. `pip install https://github.com/mr-szgz/arcfaces/releases/download/v0.1.1/arcfaces-0.1.1-py3-none-any.whl`
2. download [run_arcfaces.exe](https://github.com/mr-szgz/arcfaces/releases/download/v0.1.1/run-arcfaces.exe) from release
3. `run_arcfaces.exe --install` will install "**Run Arcfaces**" into File Explorer for Folders -> Go Right-Click a Folder

## Usage

```sh
python -m arcfaces "M:/media/dump/photos"
```

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
