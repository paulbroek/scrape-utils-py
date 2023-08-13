PYTHON=python

PACKAGE=scrape_utils
PYDIR :=./$(PACKAGE)
PYSRC := $(shell find $(PYDIR) -type f -name '*.py')
DIST=./dist

TESTS_DIR=./tests

all: clean

wheel: clean $(PYSRC)
	python setup.py bdist_wheel --universal
	echo ./base ../notion-utils-api/base ../notion-utils-api/api ../notion-utils-api/tests | xargs -n 1 cp dist/*.whl

clean:
	rm -f $(DIST)/*
	rm -rf build/*
	find ./ -name "*.whl" -type f -delete
# 	find ./base -name "*.whl" -type f -delete
