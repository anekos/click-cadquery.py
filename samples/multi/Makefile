.PHONY: add_library
add_library:
	uv pip install -e ../../

.PHONY: build
build: build-box build-cylinder

.PHONY: build-box
build-box:
	uv run main.py build

.PHONY: build-cylinder
build-cylinder:
	uv run main.py cylinder
