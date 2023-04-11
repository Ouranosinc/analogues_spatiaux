"""
Calculate climate indices
-------------------------
From the "virtual" xclim module, compute all needed indices, into a single zarr.
"""
import dask
from dask.diagnostics import ProgressBar
import logging
import numpy as np
from pathlib import Path
import sys
import xarray as xr
import xclim as xc
from config import CONFIG, load_config
logger = logging.getLogger('workflow')


load_config('config.yml', 'paths.yml', verbose=True)


if __name__ == '__main__':
    dataset = sys.argv[-1]
    dask.config.set(**CONFIG['dask'])
    xc.set_options(metadata_locales=['fr'], cf_compliance='log')
    cities = xr.open_dataset('geo/cities.nc')

    indices = xc.build_indicator_module_from_yaml('analog')
    logger.info(f'Loaded module. Opening dataset {dataset}.')
    if dataset == 'ref':
        ds = xr.open_zarr(CONFIG['biasadjust']['reference_raw'])
    elif dataset == 'sim':
        ds = xr.open_zarr(CONFIG['biasadjust']['output'])
    else:
        raise ValueError(f'Must give valid dataset. Got {dataset}.')

    ds = ds.assign(tas=xc.atmos.tg(ds=ds))

    out = xr.Dataset(attrs=CONFIG['indicators'][f'attrs_{dataset}'])
    for name, ind in indices.iter_indicators():
        logger.info(f'Creating indicator {name}.')
        daout = ind(ds=ds)
        out = out.assign({daout.name: daout})

    if dataset == 'ref':
        out.attrs['history'] = xc.core.formatting.update_history("Computed annual indices on daily ERA5-Land reference data.", ds)
        out = out.chunk({'time': (10, 10, 10, 10), 'lon': (576, 576, 514), 'lat': (224, 224, 224)})
    elif dataset == 'sim':
        out.attrs['history'] = xc.core.formatting.update_history("Computed annual indices on daily bias-adjusted CMIP6 data.", ds)
        out = out.chunk({'time': -1})
        out.realization.encoding = {}  # not sure why, but numcodecs whines otherwise
        out.ssp.encoding = {}

    logger.info('Computing and writing to disk.')
    with ProgressBar():
        if dataset == 'ref':
            out.to_zarr(CONFIG['biasadjust']['reference_indices'])
        elif dataset == 'sim':
            out.to_zarr(CONFIG['biasadjust']['output_indices_single'])

    logger.info("Spitting netCDFs")
    if dataset == 'ref':
        filetmpl = "era5-land_{name}_1951-2100.nc"
    elif dataset == 'sim':
        filetmpl = "cmip6_{name}_1951-2100.nc"
    encoding = {'time': {'dtype': 'int32'}}
    outpath = Path(CONFIG['indicators'][f'{dataset}_netcdf'])
    outpath.mkdir(exist_ok=True, parents=True)
    for name, var in out.data_vars.items():
        enc = encoding.copy()
        enc[name] = {'dtype': 'float32'}
        if 'is_dayofyear' in var.attrs:
            var.attrs['is_dayofyear'] = np.int32(var.attrs['is_dayofyear'])
        if 'location' in var.dims:
            var = var.assign_coords(city=cities.city).to_dataset()
            enc['location'] = {'dtype': 'int32'}
        var.attrs.update(out.attrs)
        var.to_netcdf(outpath / filetmpl.format(name=name), encoding=enc)
