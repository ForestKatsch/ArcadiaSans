.PHONY: all clean ttf otf variable webfonts check-ufo

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

# Check for UFO sources
check-ufo:
	@test -d $(UFO_DIR) || (echo "Error: $(UFO_DIR) not found" && \
		echo "Export your Glyphs source to $(UFO_DIR)/" && exit 1)
	@test -n "$$(ls -A $(UFO_DIR)/*.ufo 2>/dev/null)" || \
		(echo "Error: No UFO files in $(UFO_DIR)/" && exit 1)

# Build TTF
ttf: $(VENV) check-ufo
	@echo "Building TTF..."
	@mkdir -p $(EXPORT_DIR)/ttf
	venv/bin/fontmake -u $(UFO_DIR)/*.ufo -o ttf \
		--output-dir $(EXPORT_DIR)/ttf --no-production-names \
		--overlaps-backend pathops

# Build OTF
otf: $(VENV) check-ufo
	@echo "Building OTF..."
	@mkdir -p $(EXPORT_DIR)/otf
	venv/bin/fontmake -u $(UFO_DIR)/*.ufo -o otf \
		--output-dir $(EXPORT_DIR)/otf --no-production-names \
		--overlaps-backend pathops

# Build variable font
variable: $(VENV) check-ufo
	@echo "Building variable..."
	@mkdir -p $(EXPORT_DIR)/variable
	@if [ -n "$$(ls $(UFO_DIR)/*.designspace 2>/dev/null)" ]; then \
		venv/bin/fontmake -m $(UFO_DIR)/*.designspace -o variable \
			--output-dir $(EXPORT_DIR)/variable --no-production-names \
			--overlaps-backend pathops; \
	else \
		echo "Error: No .designspace file found in $(UFO_DIR)/"; \
		echo "Export from Glyphs with multiple masters to build variable fonts"; \
		exit 1; \
	fi

# Build webfonts
webfonts: variable
	@echo "Building webfonts..."
	@mkdir -p $(EXPORT_DIR)/webfonts
	@for ttf in $(EXPORT_DIR)/variable/*.ttf; do \
		base=$$(basename $$ttf .ttf); \
		venv/bin/fonttools ttLib.woff2 compress -o $(EXPORT_DIR)/webfonts/$$base.woff2 $$ttf; \
		venv/bin/fonttools ttLib.woff2 compress --flavor woff -o $(EXPORT_DIR)/webfonts/$$base.woff $$ttf; \
	done

# Clean
clean:
	rm -rf build venv
