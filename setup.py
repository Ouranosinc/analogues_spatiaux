# .py file for setting up ./core as a python package with pip.
from setuptools import setup, find_packages
requirements = [
  "pandas==1.3.5",
	"panel==0.14.4",
	"bokeh==2.4.3",
	"clisops",
	"dask",
	"geopandas",
	"intake",
	"joblib",
	"jupyter",
	"matplotlib",
	"numpy",
	"param",
	"PyYAML",
	"Shapely",
	"xarray",
	"xclim",
	"xesmf",
	"pyogrio"]
setup(
    name='AnaloguesCore',
    version='1.0.2',
    author='Sarah Gammon',
    author_email='gammon.sarah@ouranos.ca',
    description='Core module for spatial analogues dashboard app',
    packages=find_packages(include=['core', 'core.*']), 
    install_requires=requirements,
)