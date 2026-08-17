#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


STRICT_FINAL_FORBIDDEN_TERMS = [
    "示例候选人",
    "某 AI 应用团队",
    "某内容增长团队",
    "138-0000-0000",
    "candidate@example.com",
    "example.com",
]

PLACEHOLDER_ASSET_HASHES = {
    "AC7A49EA49557314B7EF631290B1F9B5195206F3A2F905D05591DDC293C4FD78",
    "C988D2FE51095E5D68C40A603363CD17CBCC05A609C3A414192851E04D23442C",
}


class ImageSourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        source = dict(attrs).get("src")
        if source:
            self.sources.append(source)


def run(command: list[str]) -> tuple[int, str, str]:
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return 127, "", str(exc)
    return process.returncode, process.stdout, process.stderr


def find_chrome(explicit: str | None) -> str | None:
    if explicit:
        path = Path(explicit).expanduser()
        return str(path.resolve()) if path.is_file() else None

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def find_tool(name: str) -> str | None:
    system_tool = shutil.which(name)
    if system_tool:
        return system_tool

    codex_dependencies = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies"
    candidates = [
        codex_dependencies / "native" / "poppler" / "Library" / "bin" / f"{name}.exe",
        codex_dependencies / "native" / "poppler" / "bin" / name,
        codex_dependencies / "bin" / name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


@lru_cache(maxsize=1)
def find_pdf_python() -> str | None:
    codex_python = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "python"
        / ("python.exe" if sys.platform == "win32" else "bin/python")
    )
    candidates = [Path(sys.executable), codex_python]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        code, _, _ = run([str(candidate), "-c", "import pdfplumber, pypdf"])
        if code == 0:
            return str(candidate)
    return None


def inspect_fonts_with_python(pdf: Path) -> tuple[int, str, str]:
    python = find_pdf_python()
    if not python:
        return 127, "", "Neither pdffonts nor a Python PDF inspection runtime is available."
    script = """
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pdfplumber
with pdfplumber.open(sys.argv[1]) as document:
    fonts = sorted({
        str(char.get("fontname", ""))
        for page in document.pages
        for char in page.chars
        if char.get("fontname")
    })
print("\\n".join(fonts))
"""
    return run([python, "-c", script, str(pdf)])


def extract_text_with_python(pdf: Path) -> tuple[int, str, str]:
    python = find_pdf_python()
    if not python:
        return 127, "", "Neither pdftotext nor a Python PDF extraction runtime is available."
    script = """
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pypdf import PdfReader
reader = PdfReader(sys.argv[1])
print("\\n".join((page.extract_text() or "") for page in reader.pages))
"""
    return run([python, "-c", script, str(pdf)])


def add_check(checks: list[dict], name: str, passed: bool, evidence: str, required: bool = True) -> None:
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "required": bool(required),
            "evidence": evidence.strip(),
        }
    )


def export_pdf(html: Path, pdf: Path, chrome: str) -> tuple[bool, str]:
    pdf.parent.mkdir(parents=True, exist_ok=True)
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf}",
        html.resolve().as_uri(),
    ]
    code, stdout, stderr = run(command)
    if code != 0:
        return False, (stderr or stdout or "Chrome export failed")
    if not pdf.exists() or pdf.stat().st_size == 0:
        return False, "Chrome returned success but did not create a non-empty PDF."
    return True, f"Created {pdf} ({pdf.stat().st_size} bytes)"


def check_pdfinfo(pdf: Path, checks: list[dict], *, require_tools: bool) -> None:
    tool = find_tool("pdfinfo")
    if not tool:
        add_check(
            checks,
            "pdfinfo available",
            False,
            "pdfinfo not found; install Poppler for this check.",
            required=require_tools,
        )
        return

    code, stdout, stderr = run([tool, str(pdf)])
    if code != 0:
        add_check(checks, "pdfinfo runs", False, stderr or stdout)
        return

    pages_match = re.search(r"^Pages:\s+(\d+)", stdout, re.M)
    pages_ok = bool(pages_match and pages_match.group(1) == "1")
    add_check(checks, "one page", pages_ok, pages_match.group(0) if pages_match else stdout)

    size_match = re.search(r"^Page size:\s+(.+)$", stdout, re.M)
    size_text = size_match.group(1) if size_match else ""
    dimensions = re.search(r"([0-9.]+)\s+x\s+([0-9.]+)\s+pts", size_text)
    width = float(dimensions.group(1)) if dimensions else 0
    height = float(dimensions.group(2)) if dimensions else 0
    size_ok = 590 <= width <= 600 and 837 <= height <= 847
    add_check(checks, "A4 portrait", size_ok, size_text or "Page size not found.")


def check_fonts(pdf: Path, checks: list[dict], expected_font: str, *, require_tools: bool) -> None:
    tool = find_tool("pdffonts")
    code, stdout, stderr = run([tool, str(pdf)]) if tool else inspect_fonts_with_python(pdf)
    if code != 0:
        add_check(checks, "font inspection runs", False, stderr or stdout, required=require_tools)
        return

    if expected_font:
        passed = expected_font in stdout
        add_check(checks, f"expected font contains {expected_font}", passed, stdout)
    else:
        add_check(
            checks,
            "fonts listed",
            bool(stdout.strip()),
            stdout or "No fonts found.",
            required=require_tools,
        )


def check_text(
    pdf: Path,
    html: Path,
    checks: list[dict],
    forbidden_terms: list[str],
    *,
    require_tools: bool,
) -> None:
    tool = find_tool("pdftotext")
    if tool:
        code, stdout, stderr = run([tool, "-layout", str(pdf), "-"])
    else:
        code, stdout, stderr = extract_text_with_python(pdf)

    text = stdout if code == 0 else ""
    add_check(
        checks,
        "PDF text extraction",
        code == 0 and bool(text.strip()),
        f"Extracted {len(text)} characters." if code == 0 else (stderr or stdout),
        required=require_tools,
    )

    html_text = html.read_text(encoding="utf-8", errors="ignore")
    haystack = f"{text}\n{html_text}"
    hits = [term for term in forbidden_terms if term and term in haystack]
    add_check(
        checks,
        "forbidden terms absent",
        not hits,
        "No forbidden terms found." if not hits else "Found: " + ", ".join(sorted(set(hits))),
    )


def check_assets(html: Path, checks: list[dict], *, reject_placeholders: bool) -> None:
    parser = ImageSourceParser()
    parser.feed(html.read_text(encoding="utf-8", errors="ignore"))

    local_assets: list[Path] = []
    for source in parser.sources:
        parsed = urlparse(source)
        if parsed.scheme or parsed.netloc:
            continue
        asset_path = (html.parent / unquote(parsed.path)).resolve()
        if asset_path not in local_assets:
            local_assets.append(asset_path)

    missing = [str(path) for path in local_assets if not path.is_file() or path.stat().st_size == 0]
    add_check(
        checks,
        "local image assets available",
        not missing,
        "All referenced local images are available." if not missing else "Missing: " + ", ".join(missing),
    )

    if reject_placeholders:
        placeholders = []
        for path in local_assets:
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest().upper() in PLACEHOLDER_ASSET_HASHES:
                placeholders.append(str(path))
        add_check(
            checks,
            "placeholder image assets absent",
            not placeholders,
            "No bundled placeholder images found."
            if not placeholders
            else "Replace bundled placeholders: " + ", ".join(placeholders),
        )


def render_screenshot(pdf: Path, screenshot_prefix: Path, checks: list[dict], *, require_tools: bool) -> None:
    tool = find_tool("pdftoppm")
    if not tool:
        add_check(
            checks,
            "screenshot rendered",
            False,
            "pdftoppm not found; install Poppler for screenshot rendering.",
            required=require_tools,
        )
        return

    screenshot_prefix.parent.mkdir(parents=True, exist_ok=True)
    code, stdout, stderr = run([tool, "-jpeg", "-r", "180", str(pdf), str(screenshot_prefix)])
    rendered = screenshot_prefix.parent / f"{screenshot_prefix.name}-1.jpg"
    passed = code == 0 and rendered.exists() and rendered.stat().st_size > 0
    add_check(
        checks,
        "screenshot rendered",
        passed,
        f"{rendered} ({rendered.stat().st_size} bytes)" if passed else (stderr or stdout),
    )


def read_ppm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    index = 0

    def token() -> bytes:
        nonlocal index
        while index < len(data) and data[index:index + 1].isspace():
            index += 1
        if index < len(data) and data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] not in (b"\n", b"\r"):
                index += 1
            return token()
        start = index
        while index < len(data) and not data[index:index + 1].isspace():
            index += 1
        return data[start:index]

    magic = token()
    if magic != b"P6":
        raise ValueError(f"Unsupported PPM format: {magic!r}")
    width = int(token())
    height = int(token())
    max_value = int(token())
    if max_value != 255:
        raise ValueError(f"Unsupported PPM max value: {max_value}")
    while index < len(data) and data[index:index + 1].isspace():
        index += 1
    pixels = data[index:]
    expected = width * height * 3
    if len(pixels) < expected:
        raise ValueError(f"PPM pixel data is incomplete: expected {expected}, got {len(pixels)}")
    return width, height, pixels[:expected]


def bottom_whitespace_ratio(
    width: int,
    height: int,
    pixels: bytes,
    *,
    left_ratio: float,
    right_ratio: float,
    white_threshold: int = 245,
) -> tuple[float, int | None]:
    x0 = max(0, min(width - 1, int(width * left_ratio)))
    x1 = max(x0 + 1, min(width, int(width * right_ratio)))
    row_width = x1 - x0
    min_ink_pixels = max(10, int(row_width * 0.0025))

    for y in range(height - 1, -1, -1):
        row_start = (y * width + x0) * 3
        ink_pixels = 0
        for x in range(row_width):
            offset = row_start + x * 3
            r, g, b = pixels[offset], pixels[offset + 1], pixels[offset + 2]
            if r < white_threshold or g < white_threshold or b < white_threshold:
                ink_pixels += 1
                if ink_pixels >= min_ink_pixels:
                    return (height - 1 - y) / height, y
    return 1.0, None


def check_bottom_whitespace(
    pdf: Path,
    checks: list[dict],
    *,
    max_ratio: float,
    main_content_right_ratio: float,
    require_tools: bool,
) -> None:
    tool = find_tool("pdftoppm")
    if not tool:
        add_check(
            checks,
            "main content bottom whitespace <= limit",
            False,
            "pdftoppm not found; install Poppler to measure bottom whitespace.",
            required=require_tools,
        )
        return

    with tempfile.TemporaryDirectory(prefix="resume-bottom-whitespace-") as temp_dir:
        prefix = Path(temp_dir) / "page"
        code, stdout, stderr = run([tool, "-r", "120", "-singlefile", str(pdf), str(prefix)])
        ppm = prefix.with_suffix(".ppm")
        if code != 0 or not ppm.exists():
            add_check(checks, "main content bottom whitespace <= limit", False, stderr or stdout)
            return

        try:
            width, height, pixels = read_ppm(ppm)
            full_ratio, full_row = bottom_whitespace_ratio(
                width,
                height,
                pixels,
                left_ratio=0.02,
                right_ratio=0.98,
            )
            main_ratio, main_row = bottom_whitespace_ratio(
                width,
                height,
                pixels,
                left_ratio=0.03,
                right_ratio=main_content_right_ratio,
            )
        except Exception as exc:
            add_check(checks, "main content bottom whitespace <= limit", False, str(exc))
            return

    passed = main_ratio <= max_ratio
    add_check(
        checks,
        "main content bottom whitespace <= limit",
        passed,
        (
            f"main={main_ratio:.1%}, full={full_ratio:.1%}, limit={max_ratio:.1%}, "
            f"main_last_row={main_row}, full_last_row={full_row}"
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an HTML resume to PDF and run basic QA checks.")
    parser.add_argument("html", help="Path to resume.html.")
    parser.add_argument("--pdf", help="Output PDF path. Defaults to HTML stem with .pdf.")
    parser.add_argument("--screenshot", help="Screenshot prefix for pdftoppm. Defaults beside the PDF.")
    parser.add_argument("--chrome", help="Path to Chrome/Chromium.")
    parser.add_argument(
        "--expected-font",
        default="",
        help="Optional font substring expected in pdffonts output. By default, only require a readable font list.",
    )
    parser.add_argument("--forbid-term", action="append", default=[], help="Additional forbidden term to scan.")
    parser.add_argument(
        "--strict-final",
        action="store_true",
        help="Require the full toolchain and reject bundled demo/template leftovers.",
    )
    parser.add_argument(
        "--max-bottom-whitespace",
        type=float,
        default=0.15,
        help="Maximum allowed bottom whitespace ratio in the main content area.",
    )
    parser.add_argument(
        "--main-content-right-ratio",
        type=float,
        default=0.86,
        help="Right boundary ratio for main content whitespace measurement; excludes far-right QR/footer by default.",
    )
    args = parser.parse_args()

    if not 0 <= args.max_bottom_whitespace <= 1:
        parser.error("--max-bottom-whitespace must be between 0 and 1.")
    if not 0.03 < args.main_content_right_ratio <= 1:
        parser.error("--main-content-right-ratio must be greater than 0.03 and at most 1.")

    html = Path(args.html).expanduser().resolve()
    if not html.is_file():
        raise SystemExit(f"HTML not found: {html}")

    pdf = Path(args.pdf).expanduser().resolve() if args.pdf else html.with_suffix(".pdf")
    if pdf == html:
        parser.error("PDF output must not overwrite the input HTML file.")
    if pdf.suffix.lower() != ".pdf":
        parser.error("PDF output must use a .pdf extension.")
    screenshot_prefix = (
        Path(args.screenshot).expanduser().resolve()
        if args.screenshot
        else pdf.with_suffix("")
    )

    checks: list[dict] = []
    if pdf.exists():
        pdf.unlink()
    chrome = find_chrome(args.chrome)
    if not chrome:
        add_check(checks, "Chrome available", False, "Chrome/Chromium was not found.")
    else:
        add_check(checks, "Chrome available", True, chrome)
        ok, evidence = export_pdf(html, pdf, chrome)
        add_check(checks, "PDF exported", ok, evidence)

    if pdf.exists() and pdf.stat().st_size > 0:
        check_pdfinfo(pdf, checks, require_tools=args.strict_final)
        check_fonts(pdf, checks, args.expected_font, require_tools=args.strict_final)
        forbidden_terms = list(args.forbid_term)
        if args.strict_final:
            forbidden_terms += STRICT_FINAL_FORBIDDEN_TERMS
        check_text(pdf, html, checks, forbidden_terms, require_tools=args.strict_final)
        check_assets(html, checks, reject_placeholders=args.strict_final)
        render_screenshot(pdf, screenshot_prefix, checks, require_tools=args.strict_final)
        check_bottom_whitespace(
            pdf,
            checks,
            max_ratio=args.max_bottom_whitespace,
            main_content_right_ratio=args.main_content_right_ratio,
            require_tools=args.strict_final,
        )

    failed_required = [check for check in checks if check["required"] and not check["passed"]]
    summary = {
        "html": str(html),
        "pdf": str(pdf),
        "screenshot_prefix": str(screenshot_prefix),
        "ok": not failed_required,
        "checks": checks,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
