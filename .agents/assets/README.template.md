# Arcfaces CLI

Analyze images and folders of images using arcface to organize and create visomaster compatible target face embeddings.

## Install

1. `pip install {{ github_whl_release_url }}`
2. download [run_arcfaces.exe]({{ github_exe_release_url }}) from release
3. `run_arcfaces.exe --install`

## Usage

scan and save results into 

```sh
$ arcfaces "M:/media/path/photos" # saves results into ./arcfaces (eg. M:/media/path/photos/arcfaces)
```

```sh
$ arcfaces --help # or uv run python -m arcfaces -h

{{cli_help_output}}
```

{{ changelog_content }}
