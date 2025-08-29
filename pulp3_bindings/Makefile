.DEFAULT_GOAL:=all

ROOT_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
PKG_NAME := pulp3_bindings

.PHONY : all
all:
	@printf "%s\n" "Usage: make <target>"
	@printf "\n%s\n" "Targets:"
	@printf "    %-22s%s\n" \
	"t|test"      	"Run tests" \
	"l|lint"        "Run lint" \
	"c|cover"       "Run coverage" \
	"venv"          "Create virtualenv" \
	"bdist"         "Create wheel file" \
	"clean"         "Clean workspace" \
	"h|help"        "Print this help"

.PHONY : h help
h help: all

.PHONY : l lint
l lint: venv
	@echo "# pylint"; \
	./venv/bin/pylint --rcfile ./pylint.rc  pulp3/

.PHONY : t test
t test: venv
	@./venv/bin/pytest -v
# @python $(PKG_NAME)/*_test.py

.PHONY : c cover
c cover: venv
	@. venv/bin/activate; \
	coverage erase; \
	coverage run --source=. -m pytest -v && coverage report --fail-under=90; \
	coverage report; \
	coverage html

.PHONY : venv
venv: export PIP_CONFIG_FILE=$(PWD)/pip.conf
venv: requirements.txt
	@python3 -m venv venv
	@. venv/bin/activate; \
	pip install --upgrade pip; \
	pip install -r requirements.txt
# @python setup.py develop

.PHONY : bdist
bdist: venv
	@. venv/bin/activate; \
	python3 setup.py bdist_wheel --universal

.PHONY : clean
clean:
	rm -rf venv
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	rm -rf htmlcov
	find -iname "*.pyc" -delete
	find -iname "*.pyo" -delete
