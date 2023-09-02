PYTHON=python

PACKAGE=scrape_utils
PYDIR :=./$(PACKAGE)
PYSRC := $(shell find $(PYDIR) -type f -name '*.py')
DIST=./dist

TESTS_DIR=./tests

all: clean

wheel: clean $(PYSRC)
	# build wheel while suppressing output
	python setup.py bdist_wheel --universal > /dev/null 2>&1
	# copy wheel files to docker build directories
	echo 	../notion-utils-api/base \
			../notion-utils-api/api \
			../notion-utils-api/tests \
			../misc-scraping/misc_scraping/scrape_youtube/base \
			../misc-scraping/misc_scraping/scrape_youtube/tests \
			../misc-scraping/misc_scraping/scrape_goodreads/base \
			../misc-scraping/misc_scraping/scrape_goodreads/tests \
			| xargs -n 1 cp $(DIST)/*.whl

clean:
	rm -f $(DIST)/*
	rm -rf build/*
	find	../notion-utils-api/base \
			../notion-utils-api/api \
			../notion-utils-api/tests \
			../misc-scraping/misc_scraping/scrape_youtube/base \
			../misc-scraping/misc_scraping/scrape_youtube/tests \
			../misc-scraping/misc_scraping/scrape_goodreads/base \
			../misc-scraping/misc_scraping/scrape_goodreads/tests \
			-name "$(PACKAGE)*.whl" -type f -delete

# 	find ./ -name "*.whl" -type f -delete
# 	find ./base -name "*.whl" -type f -delete
