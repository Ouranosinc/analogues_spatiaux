#!/usr/bin/env python
# coding: utf-8

# # update_create_config
# - creates `config.json`, or updates it, if necessary.
# - Also, removes old `/cache`, `benchmark.obj`, `density.obj`, if config isn't recent enough
# 

# In[4]:


from xarray import __version__ as xa_ver
from xclim import __version__ as xc_ver
from pandas import __version__ as pd_ver
from geopandas import __version__ as gp_ver
from joblib import __version__ as jl_ver

from pathlib import Path
import json

from joblib import Memory

config_path = Path('config.json')
if not config_path.is_file():
    config = {}
else:
    with open(config_path,encoding='utf-8') as config_file:
        config = json.load(config_file)
    

### GLOBAL OPTS:
# Projection
biasadjust = 'single' # only changes the dsim url at the moment.
# Random city on load
init_rand_city = True
# dask threading:
dask_schedule = 'single-threaded'

config["options"] = dict(init_rand_city=init_rand_city,biasadjust=biasadjust, dask_schedule=dask_schedule)

### CSS:
template_css = """
/*

  FONTS

*/

@font-face {
  font-family: 'CDCSans';
  src: url('./fonts/CerebriSans-Light.eot');
  src: url('./fonts/CerebriSans-Light.ttf');
  font-weight: 300;
}

@font-face {
  font-family: 'CDCSans';
  src: url('./fonts/CerebriSans-Book.eot');
  src: url('./fonts/CerebriSans-Book.ttf');
  font-weight: 400;
}

@font-face {
  font-family: 'CDCSans';
  src: url('./fonts/CerebriSans-SemiBold.eot');
  src: url('./fonts/CerebriSans-SemiBold.ttf');
  font-weight: 600;
}

/*

  VARIABLES
  from climatedata.ca
  
*/

:root {
  --blue: #3869f6;
  --indigo: #6610f2;
  --purple: #6f42c1;
  --pink: #e83e8c;
  --red: #e50e40;
  --orange: #fd7e14;
  --yellow: #ffc107;
  --green: #28a745;
  --teal: #20c997;
  --cyan: #17a2b8;
  --slate1: #657092;
  --slate2: #797f86;
  --blue-medium: #3869f6;
  --blue-light1: #a9b5e4;
  --blue-light2: #cbd3f4;
  --purple-dark: #2c345f;
  --purple-light: #a4bbff;
  --purple-light2: #d6d6ea;
  --white: #fff;
  --gray: #6c757d;
  --gray-dark: #343a40;
  --primary: #3869f6;
  --secondary: #e50e40;
  --success: #28a745;
  --info: #657092;
  --warning: #ffc107;
  --danger: #e50e40;
  --light: #f6f6f6;
  --dark: #060d12;
  --gray-100: #f2f2f2;
  --gray-200: #eef0f5;
  --font-family-sans-serif: "CDCSans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
  --font-family-monospace: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

/*

  TAGS
  
*/

html body {
  font-family: var(--font-family-sans-serif);
  font-weight: 300;
  color: #212529;
  -webkit-font-smoothing: antialiased;
}

body h1,
body h2,
body h3,
body h4,
body h5,
body h6 {
  color: var(--primary);
}

body h3 {
  font-size: 1.25rem;
  
}


/*

  TEMPLATE
  
*/

#container #header {
  position: relative !important; 
  background-color: var(--primary) !important;
  box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.3) !important;
  z-index: 5 !important;
}

#container #content {
  position: relative;
  z-index: 1;
}

#container #sidebar {
  background-color: var(--gray-100);
  padding-left: 0px;
  padding-right: 0px;
}

#sidebar .nav .bk-root {
  border-bottom: 1px solid #ddd;
  padding-bottom: 0rem;
  margin-bottom: 0rem;
  height: 100%;
  width: 100%;
}

#sidebar [id^="flex-item"]{
  margin-bottom: 1.5rem;
}

#sidebar .nav {
  height: 100%;
  width: 100%;
  margin: 0
}

#sidebar label {
  display: block;
  margin-bottom: 0.5rem;
}

#pn-Modal {
  z-index: 1001;
}
/* 
   Fix for scrollbar being on top of modal... 
   put it on the left...
*/

#sidebar::-webkit-scrollbar {
  display: none;
}

#sidebar {
  direction:rtl;
}

#sidebar>ul {
  direction:ltr;
  width:100%;
}

#sidebar .flex-sidebar>div>.bk {
  width: 100%;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
/*

  COMPONENTS
  
*/

table.link-table {
  width: 500px;
}

table.link-table td {
  text-align: left;
  padding: 0.5rem;
}

table.link-table tr {
  background-color: white;
  
}

#container .bk-root {
  font-family: var(--font-family-sans-serif);
}

/* buttons */


.bk-root .bk-btn {
  padding: 6px 0;
  border-radius: 25px;
  box-shadow: none;
  transition: 0.25s;
  display: flex;
  justify-content:center;
  align-items:center;
}

#sidebar .bk-root .bk-btn {
  border-color: var(--primary);
  
}

#sidebar .bk-root .bk-btn:active, #sidebar .bk-root .bk-btn.bk-active {
  box-shadow: none;
}

#sidebar .bk-root .bk-btn-default.bk-active {
  background-color: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

/* select */

.bk-root .bk-input {
  padding: 0;
}
.bk-root .bk.card {
  margin-left: 10px;
}

#sidebar .bk-root select:not([multiple]).bk-input,
#sidebar .bk-root select:not([size]).bk-input {
  border-radius: 0;
  border-color: var(--primary);
  transition: 0.25s;
  padding: 5px 10px;
  width: 280px;
}

#sidebar .bk-root .card select.bk-input,
#sidebar .bk-root .card select.bk-input {
  width: 260px !important;
}

.bk-root select:not([multiple]).bk-input:hover,
.bk-root select:not([size]).bk-input:hover {
  box-shadow: 0 0.125rem 0.75rem rgba(0, 0, 0, 0.1);
}

/* autocomplete */

#sidebar .bk-root .choices__inner {
  border-radius: 0;
  background: #fff;
  border-color: var(--primary);
  transition: 0.25s;
}

#sidebar .bk-root .choices__inner:hover {
  box-shadow: 0 0.125rem 0.75rem rgba(0, 0, 0, 0.1);
}

#sidebar .bk-root .choices__list--multiple .choices__item {
  border-radius: 0;
  background-color: var(--slate1);
}


/* spinner */

.bk-root .bk-input-group > .bk-spin-wrapper {
  transition: 0.25s;
}

.bk-root .bk-input {
  border-radius: 0;
  background: #fff;
  border-color: var(--primary);
}

.bk-root .bk-input-group > .bk-spin-wrapper:hover {
  box-shadow: 0 0.125rem 0.75rem rgba(0, 0, 0, 0.1);
}

/* progress */

progress.success:not([value])::before {
  background-color: var(--primary);
}

progress::-webkit-progress-value {
  background-color: var(--primary);
}

/* modal close button */
.pn-modalclose {
  font-size: 2rem;
  color: var(--dark);
}
.pn-modalclose:hover {
  cursor:pointer;
  color: var(--primary);
}

.pn-modal-content {
  box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.3) !important;
  z-index: 5 !important;
}

span.quality-word {
  font-size: 1rem;
  font-weight: bold;
}

span.quality-word.Excellent {
  color: var(--green);
}

span.quality-word.Good {
  color: var(--blue-light1);
}

span.quality-word.Average {
  color: var(--yellow);
}

span.quality-word.Poor {
  color: var(--orange);
}

span[class^='rank-word-'], span[class*=' rank-word-'] {
  font-size: 1rem;
  font-weight: bold;
}

.tg-excellent button {
    background-color: var(--green) !important;
}
.tg-good button {
    background-color: var(--blue-light1) !important;
}
.tg-average button {
    background-color: var(--yellow) !important;
}
.tg-poor button {
    background-color: var(--orange) !important;
}
.tgx button {
    border-radius: 30px !important;
}
.tgx .bk-btn-default.bk-active {
    border-color: #00f !important;
}
td {
    text-align: right;
} 
tr:nth-child(even) {
    background-color: #EEE;
}"""

config["css"] = template_css.replace('\n','\\n')

### URLS:
dref = 'https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/dodsC/birdhouse/ouranos/spatial-analogs/era5-land.ncml'
dsim = f'https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/dodsC/birdhouse/ouranos/spatial-analogs/cmip6_{biasadjust}.ncml'
places = ("https://pavics.ouranos.ca/geoserver/public/ows?" +
     "service=wfs&version=2.0.0&request=GetFeature" +
    "&typeName=public:ne_10m_populated_places&bbox=22,-170,83,-48" +
    "&propertyname=NAME,ADM0_A3,ADM1NAME,the_geom&outputFormat=application/json")
masks = 'https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/dodsC/birdhouse/ouranos/spatial-analogs/masks.nc'
benchmark = 'https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/dodsC/birdhouse/ouranos/spatial-analogs/benchmarks.nc'

config["url"] = dict(dref=dref,dsim=dsim,places=places,masks=masks,benchmark=benchmark)

with open(config_path,'w',encoding='utf-8') as config_file:
    json.dump(config,config_file, ensure_ascii=False, indent=4)


# In[ ]:




