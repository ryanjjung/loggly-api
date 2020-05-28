from setuptools import setup

setup(
    name='loggly-api',
    version='0.3.0',
    description="A Python library to work with Loggly's APIs",
    url='https://github.com/ryanjjung/loggly-api',
    author='Ryan Jung',
    author_email='ryanjjung@gmail.com',
    license='Apache License 2.0',
    install_requires='requests',
    packages=['loggly'])

