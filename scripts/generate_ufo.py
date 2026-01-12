#!/usr/bin/env python3
"""Generate UFO files from Glyphs source with decomposed components."""

import os
import sys
from glyphsLib import GSFont, to_ufos

def main():
    if len(sys.argv) != 3:
        print("Usage: generate_ufo.py <glyphs_source> <output_dir>")
        sys.exit(1)

    glyphs_source = sys.argv[1]
    output_dir = sys.argv[2]

    # Load Glyphs font
    font = GSFont(glyphs_source)

    # Convert to UFOs
    ufos = to_ufos(font, propagate_anchors=False)

    # Decompose all components and remove corner glyphs
    for ufo in ufos:
        # Decompose components
        for glyph in ufo:
            if glyph.components:
                pen = glyph.getPointPen()
                for component in list(glyph.components):
                    component_glyph = ufo[component.baseGlyph]
                    component.drawPoints(pen)
                glyph.clearComponents()

        # Remove corner component glyphs (they're now decomposed into other glyphs)
        corner_glyphs = [g.name for g in ufo if '_corner' in g.name]
        for glyph_name in corner_glyphs:
            del ufo[glyph_name]

        filename = f"{ufo.info.familyName.replace(' ', '')}-{ufo.info.styleName}.ufo"
        ufo.save(os.path.join(output_dir, filename), overwrite=True)

if __name__ == "__main__":
    main()
