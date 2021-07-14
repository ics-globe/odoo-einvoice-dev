#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup
from os.path import join, dirname


exec(
    open(join(dirname(__file__), "odoo", "release.py"), "rb").read()
)  # Load release variables
lib_name = "odoo"

setup(
    name="odoo",
    version=version,
    description=description,
    long_description=long_desc,
    url=url,
    author=author,
    author_email=author_email,
    classifiers=[c for c in classifiers.split("\n") if c],
    license=license,
    scripts=["setup/odoo"],
    packages=find_packages(),
    package_dir={"%s" % lib_name: "odoo"},
    include_package_data=True,
    install_requires=[
        "babel >= 1.0",
        "decorator",
        "docutils",
        "feedparser",
        "gevent",
        "html2text",
        "idna",
        "Jinja2",
        "lxml",  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        "libsass",
        "mako",
        "mock",
        "ofxparse",
        "passlib",
        "pillow",  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        "polib",
        "psutil",  # windows binary code.google.com/p/psutil/downloads/list
        "psycopg2 >= 2.2",
        "pydot",
        "pypdf2",
        "pyserial",
        "python-dateutil",
        "python-stdnum",
        "pytz",
        "pyusb >= 1.0.0b1",
        "qrcode",
        "reportlab",  # windows binary pypi.python.org/pypi/reportlab
        "requests",
        "zeep",
        "vobject",
        "werkzeug",
        "xlsxwriter",
        "xlwt",
    ],
    python_requires=">=3.6",
    extras_require={"ldap": ["python-ldap"], "SSL": ["pyopenssl"],},
    tests_require=["freezegun",],
)
