"""
Convert all regulatory_downloads/ files (HTML + PDF + TXT) to Markdown.
Output: regulatory_md/ preserving folder structure.
"""

import re
import html2text
from pathlib import Path
from pypdf import PdfReader

SRC = Path(__file__).parent / "regulatory_downloads"
DEST = Path(__file__).parent / "regulatory_md"

# html2text config
h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = True
h2t.ignore_tables = False
h2t.body_width = 0          # no line wrapping
h2t.unicode_snob = True
h2t.mark_code = True


def clean_md(text: str) -> str:
    """Remove excessive blank lines and leading/trailing whitespace."""
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    return text.strip() + '\n'


def html_to_md(src: Path, dest: Path):
    raw = src.read_text(encoding="utf-8", errors="ignore")
    md = h2t.handle(raw)
    md = clean_md(md)
    dest.write_text(md, encoding="utf-8")
    return len(md)


def pdf_to_md(src: Path, dest: Path):
    reader = PdfReader(str(src))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"<!-- Page {i} -->\n\n{text.strip()}")
    md = clean_md("\n\n---\n\n".join(parts))
    dest.write_text(md, encoding="utf-8")
    return len(md)


def txt_to_md(src: Path, dest: Path):
    text = src.read_text(encoding="utf-8", errors="ignore").strip()
    md = f"{text}\n"
    dest.write_text(md, encoding="utf-8")
    return len(md)


def convert_all():
    ok, failed = [], []

    files = sorted(f for f in SRC.rglob("*") if f.is_file() and f.name != "download_manifest.json")

    for src in files:
        rel = src.relative_to(SRC)
        dest = DEST / rel.with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            ext = src.suffix.lower()
            if ext == ".html":
                size = html_to_md(src, dest)
                status = "html→md"
            elif ext == ".pdf":
                size = pdf_to_md(src, dest)
                status = "pdf→md"
            elif ext in (".txt", ".md"):
                size = txt_to_md(src, dest)
                status = "txt→md"
            else:
                print(f"  [SKIP] {rel}")
                continue

            kb = size // 1024
            print(f"  [OK]   {rel} → {dest.name} ({kb} KB)")
            ok.append(str(rel))
        except Exception as e:
            print(f"  [FAIL] {rel} — {e}")
            failed.append((str(rel), str(e)))

    print(f"\n{'='*60}")
    print(f"Done — Converted: {len(ok)}  |  Failed: {len(failed)}")
    print(f"Output: {DEST}  ({sum(f.stat().st_size for f in DEST.rglob('*.md')) // 1024} KB total)")
    if failed:
        print("\nFailed:")
        for f, e in failed:
            print(f"  - {f}: {e}")


if __name__ == "__main__":
    print(f"Converting {SRC} → {DEST}\n")
    convert_all()
