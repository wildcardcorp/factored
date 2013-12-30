# convenience Makefile to run tests and QA tools
# options: zc.buildout options
# src: source path
# minimum_coverage: minimun test coverage allowed
# pep8_ignores: ignore listed PEP 8 errors and warnings
# max_complexity: maximum McCabe complexity allowed
# css_ignores: skip file names matching find pattern (use ! -name PATTERN)
# js_ignores: skip file names matching find pattern (use ! -name PATTERN)

SHELL = /bin/sh

options = -N -q -t 3
src = factored
minimum_coverage = 60
pep8_ignores = E501
max_complexity = 12

qa:
# QA runs only if an environment variable named QA is present
ifneq "$(QA)" ""
	@echo Validating Python files
	bin/flake8 --ignore=$(pep8_ignores) --max-complexity=$(max_complexity) $(src)

	@echo Validating minimun test coverage
	bin/coverage.sh $(minimum_coverage)
else
	@echo 'No QA environment variable present; skipping'
endif

install:
	mkdir -p buildout-cache/downloads
	python bootstrap.py
	bin/buildout $(options)

tests:
	bin/test

