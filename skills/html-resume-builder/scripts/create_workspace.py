#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SUPPORTED_TEMPLATES = ("basic-a4",)


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy a supported resume template into an editable workspace.")
    parser.add_argument(
        "--template",
        choices=SUPPORTED_TEMPLATES,
        default="basic-a4",
        help="Supported template. The default is the only currently admitted template.",
    )
    parser.add_argument("--output", required=True, help="Destination directory for the editable resume workspace.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory.")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    templates_root = (skill_root / "assets" / "templates").resolve()
    source = (templates_root / args.template).resolve()
    destination = Path(args.output).expanduser().resolve()

    if not source.is_dir() or not (source / "resume.html").is_file():
        raise SystemExit(f"Template is incomplete: {source}")
    if destination == templates_root or templates_root in destination.parents:
        raise SystemExit("Output must be outside the bundled template library.")

    if destination.exists():
        if not args.force:
            raise SystemExit(f"Output already exists: {destination}. Use --force to replace it.")
        if not destination.is_dir() or destination.is_symlink():
            raise SystemExit(f"Refusing to replace a non-directory or symlink: {destination}")
        shutil.rmtree(destination)

    shutil.copytree(source, destination)
    print(f"Created resume workspace: {destination}")
    print(f"Template: {args.template}")
    print(f"Editable HTML: {destination / 'resume.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
