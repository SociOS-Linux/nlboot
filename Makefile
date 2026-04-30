.PHONY: validate test rust-check rust-test rust-run-fixture rust-fetch-fixture rust-execute-dry-run-fixture

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

rust-fetch-fixture:
	rm -rf /tmp/nlboot-fixture-plan.json /tmp/nlboot-cache /tmp/nlboot-evidence
	cd rust/nlboot-client && cargo run -- plan \
	  --manifest ../../examples/signed_boot_manifest.recovery.json \
	  --token ../../examples/enrollment_token.recovery.json \
	  --trusted-keys ../../examples/trusted_keys.recovery.json \
	  --require-fips \
	  --now 2026-04-26T14:35:00Z \
	  --out /tmp/nlboot-fixture-plan.json
	cd rust/nlboot-client && cargo run -- fetch \
	  --plan /tmp/nlboot-fixture-plan.json \
	  --artifact-map ../../examples/artifact_map.recovery.json \
	  --cache /tmp/nlboot-cache \
	  --evidence /tmp/nlboot-evidence
	test -f /tmp/nlboot-evidence/artifact-cache-record.json

rust-execute-dry-run-fixture: rust-fetch-fixture
	cd rust/nlboot-client && cargo run -- execute \
	  --plan /tmp/nlboot-fixture-plan.json \
	  --cache /tmp/nlboot-cache \
	  --adapter linux-kexec \
	  --load-only \
	  --dry-run \
	  --evidence /tmp/nlboot-evidence \
	  --i-understand-this-mutates-host
	test -f /tmp/nlboot-evidence/pre-exec-proof.json
