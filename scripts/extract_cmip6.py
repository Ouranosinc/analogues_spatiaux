"""
Download CMIP6
--------------
Given a catalog, downloads and extracts all available dataset, extracting the target cities
through bilinear interpolation.
"""
import dask
from dask.diagnostics import ProgressBar
import intake
import logging
from pathlib import Path
import xarray as xr
from xclim.core.calendar import get_calendar, convert_calendar
from xesmf import Regridder
import numpy as np
from config import load_config, CONFIG
dask.config.set(**{'array.slicing.split_large_chunks': False})
logger = logging.getLogger("workflow")


def cleanup(ds):
    dsc = ds.drop_vars(set(ds.coords) - {'time', 'lat', 'lon'})
    dsc = dsc.expand_dims(realization=["{institution_id}_{source_id}".format(**ds.attrs)], ssp=[ds.attrs['experiment_id']])
    if get_calendar(ds.time) == '360_day':
        logger.warning(f"Interpolating nan on {ds.attrs['source_id']} - 360 day calendar.")
        dsc = convert_calendar(dsc, 'noleap', align_on='random', missing=np.NaN)
        dsc = dsc.interpolate_na('time')
    else:
        dsc = convert_calendar(dsc, 'noleap')
    return dsc


load_config('config.yml', 'paths.yml', verbose=(__name__ == '__main__'))


if __name__ == '__main__':

    wdir = Path(CONFIG['project']['workdir'])
    odir = Path(CONFIG['biasadjust']['simulations_raw'])
    dask.config.set(**CONFIG['dask'])
    logger.info('Opening and reading conf.')

    cities = xr.open_dataset(wdir / 'geo' / 'cities.nc')
    ds_cities = xr.Dataset(coords={'lon': cities.lon, 'lat': cities.lat})

    # Set of sims
    sims = CONFIG['extraction']['simulations']
    sim_parts = [
        dict(zip(['institution_id', 'source_id', 'member_id'], sim.split('_')))
        for sim in sims
    ]

    logger.info('Reading data catalog.')
    catalog = intake.open_esm_datastore(CONFIG['extraction']['catalog_url'])

    # iterate over sim to get datasets
    subcats = {}
    logger.info('Iterating over sims to get sub catalogs.')
    for sim, parts in zip(sims, sim_parts):
        sc = catalog.search(
            experiment_id=['historical', 'ssp245', 'ssp585'],
            table_id='day',
            variable_id=['tasmax', 'tasmin', 'pr'],
            **parts
        )
        ks = sc.keys()
        if len(ks) > 3:
            for gl in ['gn', 'gr1', 'gr2']:
                sc2 = sc.search(grid_label=gl)
                if len(sc2.keys()) == 3:
                    sc = sc2
                    break
            else:
                raise ValueError(f'Didnt find one grid label for {sim}')
        sc.esmcat.aggregation_control.groupby_attrs = ['experiment_id']
        subcats[sim] = sc

    # Iterate over sims to extract the data
    for sim in sims:
        out_paths = {exp_id: odir / f"day_{sim}_{exp_id}_1950-2100.zarr"
                     for exp_id in subcats[sim].df.experiment_id.unique()
                     if exp_id != 'historical'}

        if all(pth.is_dir() for pth in out_paths.values()):
            logger.info(f'Already computed {sim}.')
            continue
        elif any(pth.is_dir() for pth in out_paths.values()):
            raise ValueError(f'Part of {sim} already computed?')

        logger.info(f'Opening dataset for {sim}.')
        dsdict = subcats[sim].to_dataset_dict(xarray_open_kwargs={'drop_variables': ['time_bnds', 'height'], 'use_cftime': True})
        print()
        outs = {}
        for exp_id, ds in dsdict.items():
            logger.info(f'Regridding : {exp_id}')
            reg = Regridder(ds, ds_cities, 'bilinear', locstream_out=True, unmapped_to_nan=True)
            outs[exp_id] = reg(ds, keep_attrs=True)

        hist = outs.pop('historical')

        res = {}
        for exp_id, fut in outs.items():
            logger.info(f'Concat and save to file : {exp_id}.')
            ds = xr.concat([hist.sel(time=slice('1950', '2014')), fut.sel(time=slice('2015', '2100'))], 'time')
            assert xr.infer_freq(ds.time) == 'D'
            ds.attrs.update(fut.attrs)

            ds['time'] = ds.time.dt.floor('D')
            ds = ds.chunk({'time': -1}).squeeze()
            res[exp_id] = ds.to_zarr(odir / f"day_{sim}_{exp_id}_1950-2100.zarr", compute=False)

        logger.info('Computing.')
        with ProgressBar():
            dask.compute(res)

    if Path(CONFIG['biasadjust']['simulations']).is_dir():
        exit()

    logger.info('Reopening all realizations and cleaning metadata.')
    dss = {'ssp245': [], 'ssp585': []}
    geo = xr.open_dataset(Path(CONFIG['project']['workdir']) / 'geo' / 'cities.nc')

    for pth in odir.glob('day*.zarr'):
        if pth == Path(CONFIG['biasadjust']['simulations']):
            continue
        logger.info(f'Opening : {pth.stem}')
        ds = cleanup(xr.open_zarr(pth))
        dss[ds.ssp.item()].append(ds)

    logger.info('Concatening everything to a single dataset, sorting by KKZ order.')
    ds245 = xr.concat(dss['ssp245'], 'realization')
    ds585 = xr.concat(dss['ssp585'], 'realization')
    ds = xr.concat([ds245, ds585], 'ssp')

    reals = ['_'.join(sim.split('_')[:2]) for sim in sims]
    ds = ds.assign(real_order=(('realization',), [reals.index(real) for real in ds.realization]))
    ds = ds.sortby('real_order').drop_vars('real_order')

    ds.pr.attrs.pop('original_units')
    ds.pr.attrs.pop('original_name')
    ds.tasmin.attrs.pop('original_name')
    ds.tasmax.attrs.pop('original_name')
    ds.attrs = {
        'conventions': 'CF-1.9',
        'title': 'Daily CMIP6 data interpolated over canadian cities',
        'comment': 'One member per institution/model pair, chosen by PCA+KKZ, downloaded from S3 (AWS) storage, regridded bilinearly to the 65 canadian cities.',
        'author': 'Pascal Bourgault <bourgault.pascal@ouranos.ca>'
    }

    logger.info('Saving to disk.')
    with ProgressBar():
        ds.to_zarr(CONFIG['biasadjust']['simulations'])
