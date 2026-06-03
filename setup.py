"""
Setup file for hw_tester package.
Uses pyproject.toml for configuration.
"""
from setuptools import setup, find_packages

setup(
    name="hw-tester",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "PySide6",
        "pyserial",
        "pyyaml",
        "pandas",
        "openpyxl",
        "python-docx",
    ],
    entry_points={
        "console_scripts": [
            "hw-tester=hw_tester.app:main",
        ],
    },
)
