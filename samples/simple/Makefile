.PHONY: add_library
add_library:
	uv pip install -e ../../

.PHONY: build
build: build-box

.PHONY: build-box
build-box:
	uv run main.py build
