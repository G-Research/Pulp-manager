.DEFAULT_GOAL:=all

ROOT_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
PKG_NAME := pulp_manager

.PHONY : all
all:
	@printf "%s\n" "Usage: make <target>"
	@printf "\n%s\n" "Targets:"
	@printf "    %-22s%s\n" \
	"t|test"      	"Run all tests" \
	"l|lint"        "Run lint" \
	"c|cover"       "Run coverage for all tests" \
	"venv"          "Create virtualenv" \
	"bdist"         "Create wheel file" \
	"clean"         "Clean workspace" \
	"h|help"        "Print this help"
	"run-pulp3"     "Start Pulp 3 locally with Docker Compose"


.PHONY : h help
h help: all

.PHONY : l lint
l lint: venv
	@echo "# pylint"; \
	./venv/bin/pylint --rcfile ./pylint.rc  pulp_manager/

.PHONY : t test
t test: venv
	@./venv/bin/pytest -v

.PHONY : c cover
c cover: venv
	@. venv/bin/activate; \
	coverage erase; \
	coverage run --source=. --omit=pulp_manager/tests/unit/mock_repository.py -m pytest -v && coverage report --fail-under=90; \
	coverage html

venv: requirements.txt
	@python3 -m venv venv
	@. venv/bin/activate; \
	pip install --upgrade pip; \
	pip install -r requirements.txt

run-pulp-manager: setup-network
	@echo "Starting local Docker Compose environment..."
	docker compose -f dockercompose-local.yml up --build

.PHONY : run-pulp3
run-pulp3: setup-network
	@echo "Starting Pulp 3 locally with Docker Compose..."
	docker compose -f ./dockercompose-pulp3.yml up --build

setup-network:
	@echo "Creating or verifying network..."
	docker network inspect pulp-net >/dev/null 2>&1 || \
	docker network create pulp-net
	@echo "Network setup completed."