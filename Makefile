.PHONY: all clean ttf otf variable webfonts

# Paths
UFO_DIR = build/ufo
VENV = venv/bin/activate
EXPORT_DIR = build/exports

# Reproducible builds
export SOURCE_DATE_EPOCH = 0

# Targets
all: ttf otf variable webfonts

# Create virtual environment
$(VENV): pyproject.toml
	@echo "Creating virtual environment..."
	python3 -m venv venv
	venv/bin/pip install -q -e .
	@echo "✓ Virtual environment ready!"

# Check for manually exported UFO files
$(UFO_DIR):
	@if [ ! -d "$(UFO_DIR)" ] || [ -z "$$(ls -A $(UFO_DIR)/*.ufo 2>/dev/null)" ]; then \
		echo "Error: No UFO files found in $(UFO_DIR)/"; \
		echo ""; \
		echo "Please export UFO files from Glyphs:"; \
		echo "  1. Open src/ArcadiaSans.glyphspackage in Glyphs.app"; \
		echo "  2. File → Export → UFO"; \
		echo "  3. Export to $(UFO_DIR)/"; \
		echo ""; \
		exit 1; \
	fi

# Build TTF
ttf: $(VENV) $(UFO_DIR)
	@echo "Building TTF..."
	@mkdir -p $(EXPORT_DIR)/ttf
	venv/bin/fontmake -u $(UFO_DIR)/*.ufo -o ttf \
		--output-dir $(EXPORT_DIR)/ttf --no-production-names \
		--overlaps-backend pathops

# Build OTF
otf: $(VENV) $(UFO_DIR)
	@echo "Building OTF..."
	@mkdir -p $(EXPORT_DIR)/otf
	venv/bin/fontmake -u $(UFO_DIR)/*.ufo -o otf \
		--output-dir $(EXPORT_DIR)/otf --no-production-names \
		--overlaps-backend pathops

# Build variable font
variable: $(VENV) $(UFO_DIR)
	@echo "Generating designspace..."
	@venv/bin/python3 -c "from glyphsLib import GSFont, to_designspace; \
		font = GSFont('src/ArcadiaSans.glyphspackage'); \
		ds = to_designspace(font); \
		ds.write('$(UFO_DIR)/Arcadia.designspace')" 2>&1 | grep -v "Non-existent glyph" || true
	@echo "Building variable..."
	@mkdir -p $(EXPORT_DIR)/variable
	venv/bin/fontmake -m $(UFO_DIR)/*.designspace -o variable \
		--output-dir $(EXPORT_DIR)/variable --no-production-names \
		--overlaps-backend pathops

# Build webfonts
webfonts: variable
	@echo "Building webfonts..."
	@mkdir -p $(EXPORT_DIR)/webfonts
	@for ttf in $(EXPORT_DIR)/variable/*.ttf; do \
		base=$$(basename $$ttf .ttf); \
		echo "  $$base => woff2"; \
		venv/bin/fonttools ttLib.woff2 compress -o $(EXPORT_DIR)/webfonts/$$base.woff2 $$ttf; \
		echo "  $$base => woff"; \
		venv/bin/python3 -c "from fontTools.ttLib import TTFont; f=TTFont('$$ttf'); f.flavor='woff'; f.save('$(EXPORT_DIR)/webfonts/$$base.woff')"; \
	done

# Clean
clean:
	rm -rf build venv
