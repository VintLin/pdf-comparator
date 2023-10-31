import os
import sys
sys.setrecursionlimit(5000)
from cx_Freeze import setup, Executable
from typing import List, Tuple, Dict
from pathlib import Path
from setuptools import find_packages

# Setup file based on https://github.com/pypa/sampleproject/blob/master/setup.py
root_path = Path(__file__).parent.absolute()

def get_long_description() -> str:
    path_to_readme = root_path / "README.md"
    return path_to_readme.read_text()

def get_project_info() -> Dict[str, str]:
    project_info: Dict[str, str] = {}
    project_info_path = root_path / "pdfcomparator" / "__version__.py"
    exec(project_info_path.read_text(), project_info)
    return project_info

project_info = get_project_info()

# options
options = {
    "build_exe": {
        "include_files": [
            (os.path.join("libs", "msvcp140.dll"), "msvcp140.dll"),
            (os.path.join("libs", "vcomp140.dll"), "vcomp140.dll"),
        ],
    }
}

setup(
    name=project_info["__title__"].lower(),
    version=project_info["__version__"],
    description=project_info["__description__"],
    url=project_info["__url__"],
    author=project_info["__author__"],
    author_email=project_info["__author_email__"],
    license=project_info["__license__"],
    python_requires=">=3.8",
    # Pypi metadata
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    project_urls={
        "Source": "https://github.com/VintLin/pdf-comparator",
        "Changelog": "https://github.com/VintLin/pdf-comparator/releases",
        # "Documentation": "https://github.com/VintLin/pdf-comparator/documentation",
    },
    options=options,
    executables=[
            Executable(os.path.join("pdfcomparator", "__main__.py"), target_name="pdfcomparator.exe"),
        ],
)