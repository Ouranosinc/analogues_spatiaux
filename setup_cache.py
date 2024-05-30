# .py file for warming up the dashboard cache
import logging

import panel as pn

from core import utils

logger = logging.getLogger('analogs-setup')
logger.setLevel(logging.INFO)

logger.info("Cache warming is starting")

utils.check_version_delete_cache()

logger.info("Loading: config")
config = pn.state.as_cached('config',utils.load_config)

logger.info("Loading: datavars")
datavars = pn.state.as_cached('datavars',utils.load_datavars)

logger.info("Loading: cities")
cities = pn.state.as_cached('cities',utils.load_cities)

logger.info("Loading: places")
places = pn.state.as_cached('places',utils.load_places)

logger.info("Loading: dref")
dref = pn.state.as_cached('dref',utils.load_dref)

logger.info("Loading: dsim")
dsim = pn.state.as_cached('dsim',utils.load_dsim)

logger.info("Loading: density")
density = pn.state.as_cached('density',utils.load_density)

logger.info("Loading: benchmark")
benchmark = pn.state.as_cached('benchmark',utils.load_benchmark)

logger.info("Cache warming done. Setup finished.")
