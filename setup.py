from setuptools import setup, find_packages

setup(
    name='wfs_geocoder', 
    version='0.3', 
    packages=['wfs_geocoder'], 
    install_requires=[
        'OWSLib',
    ]
)