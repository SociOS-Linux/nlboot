.PHONY: validate test

validate: test
	@echo "OK: validate"

test:
	python3 -m pip install --user pytest >/dev/null
	PYTHONPATH=src python3 -m pytest -q
