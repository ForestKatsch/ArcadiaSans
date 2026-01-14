.PHONY: all clean ttf otf variable webfonts release

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

# Generate designspace file
$(UFO_DIR)/Arcadia.designspace: src/ArcadiaSans.glyphspackage $(VENV) $(UFO_DIR)
	@echo "Generating designspace..."
	@venv/bin/python3 -c "from glyphsLib import GSFont, to_designspace; \
		font = GSFont('src/ArcadiaSans.glyphspackage'); \
		ds = to_designspace(font); \
		ds.write('$(UFO_DIR)/Arcadia.designspace')" 2>&1 | grep -v "Non-existent glyph" || true

# Build TTF (all instances)
ttf: $(UFO_DIR)/Arcadia.designspace
	@echo "Building TTF instances..."
	@mkdir -p $(EXPORT_DIR)/ttf
	venv/bin/fontmake -m $(UFO_DIR)/Arcadia.designspace -i -o ttf \
		--output-dir $(EXPORT_DIR)/ttf --no-production-names \
		--overlaps-backend pathops

# Build OTF (all instances)
otf: $(UFO_DIR)/Arcadia.designspace
	@echo "Building OTF instances..."
	@mkdir -p $(EXPORT_DIR)/otf
	venv/bin/fontmake -m $(UFO_DIR)/Arcadia.designspace -i -o otf \
		--output-dir $(EXPORT_DIR)/otf --no-production-names \
		--overlaps-backend pathops

# Build variable font
variable: $(UFO_DIR)/Arcadia.designspace
	@echo "Building variable..."
	@mkdir -p $(EXPORT_DIR)/variable
	venv/bin/fontmake -m $(UFO_DIR)/Arcadia.designspace -o variable \
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

# Release - build all formats and zip
release: all
	@echo "Creating release zip..."
	@MAJOR=$$(grep 'versionMajor' src/ArcadiaSans.glyphspackage/fontinfo.plist | sed 's/[^0-9]//g'); \
	MINOR=$$(grep 'versionMinor' src/ArcadiaSans.glyphspackage/fontinfo.plist | sed 's/[^0-9]//g'); \
	VERSION="v$$MAJOR.$$(printf '%03d' $$MINOR)"; \
	echo "  Version: $$VERSION"; \
	cd $(EXPORT_DIR) && zip -r ../release-$$VERSION.zip . -x "*.DS_Store"; \
	echo "✓ Created build/release-$$VERSION.zip"

# Clean
clean:
	rm -rf build venv
