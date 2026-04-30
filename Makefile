.PHONY: validate test rust-check rust-test rust-run-fixture

validate: test
	@echo "OK: validate"

test:
	python3 -m pip install --user pytest cryptography >/dev/null
	PYTHONPATH=src python3 -m pytest -q

rust-check:
	cd rust/nlboot-client && cargo check

rust-test:
	cd rust/nlboot-client && cargo test

rust-run-fixture:
	cd rust/nlboot-client && cargo run -- plan \
	  --manifest ../../examples/signed_boot_manifest.recovery.json \
	  --token ../../examples/enrollment_token.recovery.json \
	  --trusted-keys ../../examples/trusted_keys.recovery.json \
	  --require-fips \
	  --now 2026-04-26T14:35:00Z
