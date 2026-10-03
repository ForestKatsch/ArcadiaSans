.PHONY: all clean

all: venv/.installed
	venv/bin/python build.py

venv/.installed: requirements.txt
	python3 -m venv venv
	venv/bin/pip install -q -r requirements.txt
	touch $@

clean:
	rm -rf build venv
