Use the GitHub issue body or repo-local `AGENT_TASKS/*.md` file as the source of truth.

Before editing:
1. Read the issue or task packet.
2. Inspect the live repository.
3. Identify existing validation commands.
4. Keep the PR bounded.

When implementing:
- Prefer existing repository patterns.
- Add tests, fixtures, or validators with implementation changes.
- Keep generated files only if repository conventions require them.
- Do not modify unrelated workflows or policy files.
- For boot/recovery/host-control behavior, implement dry-run and evidence paths before real behavior.
- Preserve the separation between portable core and platform adapters.

When opening the PR:
- Link the issue or task packet.
- Include validation evidence.
- List known gaps.
- State non-goals preserved.
- Do not mark ready if validation did not run.

NLBoot validation commands:
```bash
make validate
make rust-check
make rust-test
make rust-run-fixture
make rust-fetch-fixture
make rust-execute-dry-run-fixture
make rust-exec-dry-run-fixture
make rust-apple-m2-dry-run-fixture
```
