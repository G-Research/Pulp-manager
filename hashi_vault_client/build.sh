#!/bin/bash
set -e -E -u -C -o pipefail; shopt -s failglob;

make lint

echo "running tests..."
python3.6 setup.py test

echo "creating wheel..."
python3.6 setup.py bdist_wheel --universal
