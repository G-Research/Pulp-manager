.DEFAULT_GOAL:=all

ROOT_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
PKG_NAME := hashi_vault_client

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
l lint:
	@echo "# pylint"
	@pylint-3 --rcfile="$(ROOT_DIR)/pylint.rc" --ignore-patterns=".*_test.py" $(PKG_NAME) || :
	@echo "# pep8"
	@pep8 --ignore=E501 --filename="*.py" --exclude="*_test.py" $(PKG_NAME) || :

.PHONY : t test
t test:
	@python setup.py test
# @python $(PKG_NAME)/*_test.py

.PHONY : c cover
c cover:
	@coverage erase
	@coverage run --source=$(PKG_NAME) $(PKG_NAME)/*_test.py
	@coverage report
	@coverage html

venv: export PIP_CONFIG_FILE=$(PWD)/pip.conf
venv: requirements.txt
	@virtualenv venv
	@. venv/bin/activate; \
	pip install -r requirements.txt; \
	pip install -e .
# @python setup.py develop

.PHONY : bdist
bdist:
	@python setup.py sdist bdist_wheel

.PHONY : clean
clean:
	rm -rf venv
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	rm -rf htmlcov
	find -iname "*.pyc" -delete
	find -iname "*.pyo" -delete
