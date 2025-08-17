
.PHONY: build
build:
	echo 'build'.

.PHONY: publish-test
publish-test: build
	uv publish --publish-url https://test.pypi.org/legacy/ --token "$(TOKEN)"

.PHONY: publish-prod
publish-prod: build
	uv publish --token "$(TOKEN)"
