import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

meta = {}
with open(os.path.join(here, "digital_document_checker", "__meta__.py"), encoding="utf-8") as fh:
    exec(fh.read(), meta)

with open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = fh.read()


def _read_requirements(path):
    full = os.path.join(here, path)
    if not os.path.isfile(full):
        return []
    with open(full, encoding="utf-8") as fh:
        return [
            line.strip()
            for line in fh
            if line.strip() and not line.startswith("#")
        ]


setup(
    name=meta["__title__"],
    version=meta["__version__"],
    description=meta["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=meta["__url__"],
    author=meta["__author__"],
    author_email=meta["__author_email__"],
    license=meta["__license__"],
    python_requires=">=3.9",
    packages=find_packages(include=["digital_document_checker*"]),
    include_package_data=True,
    package_data={"digital_document_checker": ["data/*.json"]},
    install_requires=_read_requirements("requirements.txt"),
    extras_require={
        "qr": ["pyzbar>=0.1.9", "Pillow>=9.0"],
        "pdf": ["PyMuPDF>=1.23"],
        "full": ["pyzbar>=0.1.9", "Pillow>=9.0", "PyMuPDF>=1.23"],
        "dev": ["pytest>=7.0", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "digital-document-checker = digital_document_checker.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Security :: Cryptography",
    ],
)
