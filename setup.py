from setuptools import setup, Extension
import pybind11

# Windows-specific C++ flag
cpp_args = ['/std:c++17']

ext_modules = [
    Extension(
        "quiz_engine",
        ["backend_cpp/engine.cpp"],
        include_dirs=[pybind11.get_include()],
        language='c++',
        extra_compile_args=cpp_args,
    ),
]

setup(
    name="quiz_engine",
    version="1.0",
    ext_modules=ext_modules,
)