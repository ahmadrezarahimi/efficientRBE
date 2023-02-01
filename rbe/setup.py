from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='rbe',
   version='1.0',
   description='Efficient registration-based encryption (RBE)',
   license="GPL",
   long_description=long_description,
   author="Noemi Glaeser <nglaeser@umd.edu>, Ahmadreza Rahimi <ahmadreza.rahimi@mpi-sp.org>",
   url="https://github.com/ahmadrezarahimi/efficientRBE",
   packages=['rbe'],  #same as name
   install_requires=[
        'python>=3',
        'pyparsing==2.4.0',
        'petrelic==0.1.5',
       ], #external packages as dependencies
)