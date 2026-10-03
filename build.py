#!/usr/bin/env python3
"""Build Arcadia Sans into build/. See BUILDING.md."""

import logging
import os
import shutil
import zipfile
from pathlib import Path

from fontmake.font_project import CFFOptimization, FontProject
from fontTools.pens.roundingPen import RoundingPointPen
from fontTools.ttLib import TTFont
from glyphsLib import GSFont, to_designspace
from glyphsLib.glyphdata import get_glyph

from smart_components import prepare_for_export

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
EXPORTS = BUILD / "exports"

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")  # Reproducible timestamps.


def masters(font):
    """Convert the Glyphs source to a designspace, matching Glyphs.app's UFO export."""
    prepare_for_export(font)
    ds = to_designspace(font, minimal=True)
    for source in ds.sources:
        ufo = source.font
        # Corners are already applied, and Glyphs doesn't erase open corners.
        del ufo.lib["com.github.googlei18n.ufo2ft.filters"]
        # Glyphs doesn't attach marks to spacing accents (dieresis, macron, ...).
        categories = ufo.lib.get("public.openTypeCategories", {})
        for name in list(categories):
            if (get_glyph(name).category, get_glyph(name).subCategory) == ("Mark", "Spacing"):
                del categories[name]
        for glyph in ufo:
            contours = list(glyph.contours)
            glyph.clearContours()
            for contour in contours:
                contour.drawPoints(RoundingPointPen(glyph.getPointPen()))
    return ds


def main():
    # glyphsLib warns about every feature referencing an unexported glyph; it's just noise here.
    logging.getLogger("glyphsLib").addFilter(lambda r: "Non-existent glyph" not in r.getMessage())

    font = GSFont(ROOT / "src/ArcadiaSans.glyphspackage")
    ds = masters(font)
    shutil.rmtree(BUILD, ignore_errors=True)

    for fmt in ["ttf", "otf", "variable"]:
        print(f"Building {fmt}...")
        FontProject().run_from_designspace(
            ds,
            output=[fmt],
            interpolate=fmt != "variable",
            output_dir=EXPORTS / fmt,
            use_production_names=False,
            overlaps_backend="pathops",
            optimize_cff=CFFOptimization.SUBROUTINIZE,
        )

    print("Building webfonts...")
    (EXPORTS / "webfonts").mkdir()
    for ttf in (EXPORTS / "variable").glob("*.ttf"):
        for flavor in ["woff2", "woff"]:
            webfont = TTFont(ttf)
            webfont.flavor = flavor
            webfont.save(EXPORTS / "webfonts" / f"{ttf.stem}.{flavor}")

    zip_path = BUILD / f"release-v{font.versionMajor}.{font.versionMinor:03d}.zip"
    print(f"Creating {zip_path.relative_to(ROOT)}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(EXPORTS.rglob("*.*")):
            # A fixed timestamp keeps the zip reproducible.
            zf.writestr(zipfile.ZipInfo(str(path.relative_to(EXPORTS))), path.read_bytes(), zipfile.ZIP_DEFLATED)


if __name__ == "__main__":
    main()
