from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [l.strip() for l in fh if l.strip() and not l.startswith("#")]

setup(
    name="venomsan",
    version="2.0.0",
    author="Pentester",
    description="Advanced Web Application Penetration Testing Framework - SQLi, XSS, LFI, RCE, CSRF, PrivEsc, Buffer Overflow",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/camorro5/camorro.git",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={"console_scripts": ["venomsan=venomsan.main:app"]},
)
