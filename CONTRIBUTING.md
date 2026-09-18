# Contributing

Issues and pull requests are welcome. Keep changes narrow, explain which workflow contract changes, and add a regression test for observable behavior.

## Before opening a pull request

1. Run the unit suite and context-budget validator.
2. Do not commit credentials, private media, personal paths, generated projects, model weights, browsers, or toolchain binaries.
3. Document new network destinations, subprocesses, writable paths, dependencies, and human-approval changes.
4. Preserve fail-closed behavior: missing or malformed approval, hash, schema, or validation evidence must not become success.
5. Bind test evidence to the final commit. Do not reuse a passing result from code that changed afterward.

Changes to approval gates, handoffs, command construction, credential handling, path resolution, dependency bootstrapping, or release promotion receive security-sensitive review.

By contributing, you agree that your contribution is licensed under Apache-2.0.
