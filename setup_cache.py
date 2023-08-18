# .py file for warming up the dashboard cache
import panel as pn
import core
import xclim
from core import utils

utils.check_version_delete_cache()

config = pn.state.as_cached('config',utils.load_config)
datavars = pn.state.as_cached('datavars',utils.load_datavars)
cities = pn.state.as_cached('cities',utils.load_cities)
places = pn.state.as_cached('places',utils.load_places)
dref = pn.state.as_cached('dref',utils.load_dref)
dsim = pn.state.as_cached('dsim',utils.load_dsim)
density = pn.state.as_cached('density',utils.load_density)
benchmark = pn.state.as_cached('benchmark',utils.load_benchmark)