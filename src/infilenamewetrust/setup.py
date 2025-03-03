from setuptools import setup, Extension
from Cython.Build import cythonize

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