.PHONY: add_library
add_library:
	uv pip install -e ../../

.PHONY: build
build: build-box

.PHONY: build-box
build-box:
	uv run main.py build --partition '30(3),*'

.PHONY: preview
preview:
	uv run main.py partition --partition '30(3),*'
