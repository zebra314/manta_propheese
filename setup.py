from setuptools import setup, find_packages

setup(
    name="manta_propheese",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires="==3.10.*",
)