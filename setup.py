# import versioneer # https://github.com/python-versioneer/python-versioneer/blob/master/INSTALL.md
from typing import Final, List

from setuptools import find_packages, setup

requires: Final[List[str]] = [
    "yapic.json",
    "redis",
    "sqlmodel",
    "fastapi",
    "asyncpg",
    "psycopg2",
    "requests",
    "python-dotenv",
    "sqlalchemy-utils",
    "uvloop",
]

# requires: Final[List[str]] = []

setup(
    name="scrape_utils",
    version="0.0.8",
    description="Scrape utility package: filters, caching, proxies, ..",
    url="git@github.com:paulbroek/scrape-utils-py.git",
    author="Paul Broek",
    author_email="pcbroek@paulbroek.nl",
    license="unlicense",
    install_requires=requires,
    include_package_data=True,
    packages=find_packages(),
    python_requires=">=3.9",
    zip_safe=False,
)
