from __future__ import annotations

import argparse
import sys

from .arcfaces import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arcfaces")
    parser.add_argument(
        "--recognize",
        "-Recognize",
        dest="recognize",
        metavar="PATH",
        help="Path to an image or a folder of images.",
    )
    parser.add_argument(
        "--save-size",
        "-SaveSize",
        dest="save_size",
        type=int,
        choices=(256, 512, 1024),
        metavar="SIZE",
        help="Resize-crop face images to SIZE (256, 512, or 1024).",
    )
    parser.add_argument(
        "--top",
        "-Top",
        dest="top",
        nargs="?",
        const=".",
        metavar="PATH",
        help="Print the most popular identity folder path for an arcfaces/ directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.recognize and args.top is None:
        parser.print_usage(sys.stderr)
        return 2
    from .arcfaces import recognize_command, top_identity

    if args.recognize:
        rc = recognize_command(args.recognize, save_size=args.save_size)
        if rc != 0:
            return rc
        if args.top is None:
            return 0
        top_path = args.recognize if args.top == "." else args.top
        return top_identity(top_path)

    top_path = args.top
    return top_identity(top_path)

__all__ = ["__version__", "main"]
