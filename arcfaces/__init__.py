from __future__ import annotations

import argparse
import os
import sys

from .arcfaces import __version__


def _build_parser() -> argparse.ArgumentParser:
    prog_name = os.environ.get("ARCFACES_PROG") or "arcfaces"
    parser = argparse.ArgumentParser(prog=prog_name)
    parser.add_argument(
        "--version",
        "-Version",
        "-v",
        action="version",
        version=__version__,
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
        "--save-faces",
        "-SaveFaces",
        dest="save_faces",
        type=int,
        default=512,
        choices=(256, 512, 1024),
        metavar="SIZE",
        help="Resize-crop face images to SIZE (256, 512, or 1024). Default: 512.",
    )
    parser.add_argument(
        "--save-top",
        "-SaveTop",
        dest="top",
        nargs="?",
        const=1,
        type=int,
        metavar="N",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.recognize and args.top is None:
        parser.print_usage(sys.stderr)
        return 2
    top_path = None
    top_count = 1
    if args.top is not None:
        top_path = "."
        top_count = args.top
    from .arcfaces import recognize_command, top_identity

    if args.recognize:
        rc = recognize_command(
            args.recognize,
            save_faces=args.save_faces,
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
