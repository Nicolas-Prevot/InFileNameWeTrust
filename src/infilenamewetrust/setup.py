from setuptools import setup, Extension
from Cython.Build import cythonize
import sys

extensions = [
    Extension(
        name="cython_fastencode",
        sources=["cython_fastencode.pyx"],
        language="c"
    )
]

setup(
    name="cython_fastencode",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"}
    ),
)
# python setup.py build_ext --inplace