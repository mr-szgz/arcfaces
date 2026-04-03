from __future__ import annotations

import argparse
import os
import sys
from datetime import date

from .arcfaces import __version__


def _build_parser() -> argparse.ArgumentParser:
    prog_name = os.environ.get("ARCFACES_PROG") or "arcfaces"
    parser = argparse.ArgumentParser(prog=prog_name)
    parser.add_argument(
        "--version",
        "-Version",
        "-v",
        action="version",
        version=_banner(),
        help="Show the Arcfaces version and exit.",
    )
    parser.add_argument(
        "--recognize",
        "-Recognize",
        dest="recognize",
        metavar="PATH",
        help="Path to an image or a folder of images.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to an image or a folder of images (positional).",
    )
    parser.add_argument(
        "--save-faces",
        "-SaveFaces",
        dest="save_faces",
        default="512",
        metavar="SIZES",
        help="Resize-crop face images to SIZES (comma-separated). Example: --save-faces 256,512,1024.",
    )
    parser.add_argument(
        "--save-top",
        "-SaveTop",
        dest="top",
        nargs="?",
        const=1,
        type=int,
        metavar="N",
        default=1,
        help="Move the top identity folders into the source directory (default N=1).",
    )
    parser.add_argument(
        "--threshold",
        "-Threshold",
        dest="threshold",
        type=float,
        default=0.5,
        metavar="SIM",
        help="Face similarity threshold for clustering (default: 0.5).",
    )
    parser.add_argument(
        "--merge-faces",
        "-MergeFaces",
        dest="merge_faces",
        metavar="PATH",
        help="Path to an identity folder of face JSONs to merge into a single embedding.",
    )
    parser.add_argument(
        "--name",
        "-Name",
        dest="merge_name",
        metavar="NAME",
        help="Optional embedding name override for --merge-faces.",
    )
    return parser


def _banner() -> str:
    year = date.today().year
    return f"Arcfaces CLI {__version__}\nCopyright (c) {year}"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    print(_banner(), flush=True)
    if args.merge_faces:
        from .embeddings import write_visomaster_embedding_for_folder

        write_visomaster_embedding_for_folder(
            args.merge_faces, name_override=args.merge_name
        )
        return 0
    if not args.recognize and args.path:
        args.recognize = args.path
    if not args.recognize and args.top is None:
        parser.print_usage(sys.stderr)
        return 2
    save_faces_text = str(args.save_faces)
    size_tokens = [token.strip() for token in save_faces_text.split(",") if token.strip()]
    if not size_tokens:
        print("Save faces sizes must be one or more integers.", file=sys.stderr)
        return 2
    save_faces_sizes: list[int] = []
    for token in size_tokens:
        try:
            size_value = int(token)
        except ValueError:
            print(f"Invalid size value: {token}", file=sys.stderr)
            return 2
        if size_value <= 0:
            print(f"Invalid size value: {token}", file=sys.stderr)
            return 2
        save_faces_sizes.append(size_value)
    top_path = "."
    top_count = args.top
    from .arcfaces import recognize_command, top_identity

    if args.recognize:
        rc = recognize_command(
            args.recognize,
            save_faces=save_faces_sizes,
            threshold=args.threshold,
        )
        if rc != 0:
            return rc
        if top_path is None:
            return 0
        top_path = args.recognize if top_path == "." else top_path
        return top_identity(top_path, count=top_count)

    return top_identity(top_path or ".", count=top_count)


__all__ = ["__version__", "main"]
