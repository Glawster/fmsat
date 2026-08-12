"""Setuptools compatibility entry point for FMSAT."""

from pathlib import Path
from setuptools import setup


setup(
    name="fmsat",
    version="0.1.0",
    description="Football Manager Squad Assessment Tool",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Andy Wilson",
    author_email="murky_oblong0s@icloud.com",
    python_requires=">=3.12",
    packages=[
        "fmsat",
        "fmsat.app",
        "fmsat.config",
        "fmsat.core",
        "fmsat.core.images",
        "fmsat.core.ocr",
        "fmsat.core.parser",
        "fmsat.core.validation",
        "fmsat.database",
    ],
    package_dir={"fmsat": "."},
    package_data={"fmsat": ["config/*.yaml", "config/roleProfiles/*.yaml"]},
    include_package_data=True,
    install_requires=[
        "numpy>=1.26",
        "opencv-python>=4.8",
        "organiseMyProjects",
        "paddleocr>=2.7",
        "PySide6>=6.6",
        "PyYAML>=6.0",
        "SQLAlchemy>=2.0",
    ],
    extras_require={
        "compression": ["lz4>=4.3", "zstandard>=0.22"],
        "bundles": ["UnityPy>=1.10"],
        "dev": ["black>=24.0", "pytest>=8.0", "ruff>=0.6"],
    },
    entry_points={"console_scripts": ["fmsat=fmsat.main:main"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: X11 Applications :: Qt",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
)
