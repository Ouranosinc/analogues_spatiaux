# Development of Climate Analogs for Major Canadian Cities
Project 706400 of Ouranos for the CCCS.

This repo contains a shareable version of most code used to generate the input data used
in the prototype dashboard, as well as the dashboard itself.

The code has changed a lot during the project and it may happen that the public data was
generated with an older version of what is here. For the same reason, the environment
file given here reflects the state of my conda environment at the moment of creating this
repo and some packages may have different versions than when the data was generated.

Link to Pavics site: https://pavics.ouranos.ca/analogues_spatiaux/Dashboard
Link to CCDP staging: https://app-spatial-analogs-staging.climatedata.ca/analogs/Dashboard
## Structure

### Configuration
Importing an idea from the internal scenario codebase of Ouranos (xscen), a lot of 
customizable parameters for each script actually lie in configuration files (`config.yml` and `paths.yml`).
The goal was to uncouple the algorithms from the parameters allowing for the building of
"generic" workflows which can be customized without touching the python script.

The configuration reader is in `config.py`.

### Population density map and masks
As the first task done for this project and its run-and-forget aspect, the code for this
part is not well organized. It lives in `Masques.ipynb`, a notebook one should NOT try to
run in its entirety. See the header of the notebook for more info.

This notebook also transforms the list of cities (the excel sheet) into a geojson and then
into a netCDF. 

### CMIP6 data
The first part of the `Simulations CMIP6.ipynb` notebook generates the ESM catalogs
needed by `extract_cmip6.py` to actually download and extract the data.

The PCA+KKZ is further done in another section of `Simulations CMIP6.ipynb`. Once the list
of realization is generated, it needs to be added to `config.yml`.

### Bias-adjustment / indices
Daily bias-adjustment is done with `bias_adjust_daily.py`. Then `calc_indices.py` can
compute the climate indices. `bias_adjust_annual.py` does the second bias-adjustment, if
needed. `calc_indices.py` is also the one to compute the indices on the reference data.
The climate indices are defined in `analog.yml`, with french translations in `analog.fr.json`.

One can use `fig_indices_comp.py` to plot all indices, in order to visually inspect them
compared to the reference ones. It also splits the Zarr files into netCDFs, which is what
it stored on PAVICS.

### Approximate distributions and self-analogy
`analog_quantiles.py` performs the Monte-Carlo analysis to approximate the dissimilarity
score distributions, which it saves into a netCDF file.

`compute_selfanalogy.py` computes the best analogs for each index, using the 1991-2020
target period. Results were analyzed in another notebook, not present in this repo.

### Notebook and dashboard
The final products are `Dashboard.ipynb` and `Step_by_step.ipynb`. They are both
independent from the rest of the code in this repo, and rely on data available through PAVICS.

The visualization are different between the two versions. First of all, plotting with
matplotlib ("Step_by_step") and holoviews/bokeh ("Dashboard") assurely gives different
results, but the Dashboard has been subject to some more iterations. The analog finding
code, however, should be identical.

A lot more explanations are given in the step by step notebook.
