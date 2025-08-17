.PHONY: publish
publish:
	uv build
	uv publish --publish-url https://test.pypi.org/legacy/ --token "$(TOKEN)"
