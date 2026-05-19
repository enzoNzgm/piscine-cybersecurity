.PHONY: all prepare install run run-silent clean help

PYTHON := $(shell command -v python3 2>/dev/null || echo python)
REQ := requirements.txt

all: prepare

prepare:
	@if [ -f "stockholm" ]; then \
		chmod +x stockholm; \
		echo "stockholm is ready to run"; \
	else \
		echo "Warning: stockholm script not found in current directory"; \
	fi

install: $(REQ)
	@echo "Installing Python dependencies (may require sudo/virtualenv)..."
	@$(PYTHON) -m pip install -r $(REQ)

run: stockholm
	./stockholm

run-silent: stockholm
	./stockholm -s

help:
	@echo "Usage: make [target]"
	@echo "  all         - Prepare the stockholm script (make executable)"
	@echo "  install     - Install Python dependencies from requirements.txt"
	@echo "  run         - Run ./stockholm"
	@echo "  run-silent  - Run ./stockholm -s (no output)"
	@echo "  help        - Show this message"
