import os

import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setuptools.setup(
    name="aj-micro-utils",
    version=os.environ.get("TAG_VERSION"),
    author="Atom Juice",
    author_email="developers@atomjuice.com",
    description="Contains the various bits used across services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/atomjuice/aj_token",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=install_requires,
    include_package_data=True
)
