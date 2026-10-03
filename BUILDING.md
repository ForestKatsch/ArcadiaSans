# Building Arcadia Sans

Fonts are built straight from `src/ArcadiaSans.glyphspackage`. Glyphs.app isn't needed, only Python 3.9 or later.

```bash
make          # builds everything into build/
make clean    # removes build/ and venv/
```

The first run creates `venv/` with the pinned versions from `requirements.txt`. `make` produces:

- `build/exports/ttf/`, `build/exports/otf/`: static instances
- `build/exports/variable/`: the variable font
- `build/exports/webfonts/`: WOFF and WOFF2 of the variable font
- `build/release-vX.YYY.zip`: all of the above, for GitHub releases

## How it works

`build.py` converts the Glyphs source to UFO masters with glyphsLib, then runs fontmake. glyphsLib can't apply corner and cap components the way Glyphs does, so `smart_components.py` does that first, along with the other outline changes Glyphs makes on export (decomposing mirrored components). Its rules were checked against UFOs exported from Glyphs 4. Outlines match except for a few 1-unit rounding differences.

Builds set `SOURCE_DATE_EPOCH=0`, so the same source and dependency versions produce identical files.
