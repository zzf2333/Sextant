.PHONY: test test-structure test-bootstrap test-install test-json test-release test-cli

# Run all tests
test:
	@bash tests/run-all.sh

# Run individual suites
test-structure:
	@bash tests/test-structure.sh

test-bootstrap:
	@bash tests/test-bootstrap.sh

test-install:
	@bash tests/test-install.sh

test-json:
	@bash tests/test-json.sh

test-release:
	@bash tests/test-release.sh

test-cli:
	@bash tests/test-cli.sh
