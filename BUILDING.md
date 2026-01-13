# Building Arcadia Sans

This document describes how to build font files from the Glyphs source.

## Prerequisites

- Python 3.9 or later
- Glyphs.app (for UFO export)

## Build Process

1. **Export UFO files from Glyphs:**
   - Open `src/ArcadiaSans.glyphspackage` in Glyphs.app
   - File → Export → UFO
   - Export to `build/ufo/`
   - This handles corner components correctly

2. **Build fonts:**
   ```bash
   make              # Build everything
   ```

The Makefile automatically:
- Creates Python virtual environment (if needed)
- Installs dependencies (if needed)
- Generates designspace for variable fonts
- Builds fonts with reproducible timestamps

You can also build specific formats:

```bash
make ttf          # Static TTF instances
make otf          # Static OTF instances
make variable     # Variable font
make webfonts     # WOFF/WOFF2
```

## Cleaning

```bash
make clean        # Remove build/ and venv/
```

## Reproducible Builds

Builds use `SOURCE_DATE_EPOCH=0` for reproducible timestamps and `--no-production-names` to ensure consistent output across different environments.
