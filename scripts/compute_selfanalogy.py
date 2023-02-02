"""
Self analogy
------------
Compute the best analogs, with the target period the same as the reference one.
Used to compare the "best analog" methods and double-adjustment methods.
The analysis of these results was done in a very messy notebook. I can share it upon request.
"""
from dask.distributed import Client
import logging
from pathlib import Path
import numpy as np
import sys
import xarray as xr
import xclim as xc
from xclim import analog as xa
from config import load_config, CONFIG
logger = logging.getLogger("workflow")


def stack_drop_nans(ds, mask, *, new_dim='site'):
    """Stack dimensions into a single axis and drops indexes where the mask is false."""
    mask_1d = mask.stack({new_dim: mask.dims})
    out = ds.stack({new_dim: mask.dims}).where(mask_1d, drop=True).reset_index(new_dim)
    for dim in mask.dims:
        out[dim].attrs.update(ds[dim].attrs)
    return out


def haversine_distance(lon1, lat1, lon2, lat2):
    """Distance between lat/lon points, in units of earth's radius."""
    lon1, lat1, lon2, lat2 = map(np.deg2rad, [lon1, lat1, lon2, lat2])
    return 2 * np.arcsin(np.sqrt(
        np.sin((lat2 - lat1) / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2)**2
    ))


def get_best_closestN(score, lon, lat, tgt_lon, tgt_lat, N=10):
    isort = np.argsort(score)
    score[isort][:N]
    lon = lon[isort][:N]
    lat = lat[isort][:N]
    dist = haversine_distance(lon, lat, tgt_lon, tgt_lat)
    i = dist.argmin()
    if np.isnan(score[i]):
        return np.nan, np.nan, np.nan
    return score[i], lon[i], lat[i]


def get_best_closestP(score, lon, lat, tgt_lon, tgt_lat, distrib, P=1):
    isort = np.argsort(score)
    score = score[isort]
    lon = lon[isort]
    lat = lat[isort]

    perc = np.interp(score, distrib, np.arange(distrib.size))
    perc_min = np.nanmin(perc)
    if np.isnan(perc_min) or perc_min == 20.0:
        return np.nan, np.nan, np.nan

    mask = perc < (perc_min + P)
    score = score[mask]
    lon = lon[mask]
    lat = lat[mask]

    dist = haversine_distance(lon, lat, tgt_lon, tgt_lat)
    i = dist.argmin()
    return score[i], lon[i], lat[i]


def get_best_closestPp(score, lon, lat, tgt_lon, tgt_lat, distrib, P=1):
    isort = np.argsort(score)
    score = score[isort]
    lon = lon[isort]
    lat = lat[isort]

    sc = score[:10]
    perc = np.interp(score, distrib, np.arange(distrib.size))
    perc_min = np.nanmin(perc)
    if np.isnan(perc_min) or perc_min == 20.0:
        return np.nan, np.nan, np.nan

    mask = perc < (perc_min + P)
    score = score[mask]
    lon = lon[mask]
    lat = lat[mask]

    dist = haversine_distance(lon, lat, tgt_lon, tgt_lat)
    logger.info(f"{perc_min}, {mask.sum()}, {sc}, {distrib}")
    print(f"{perc_min}, {mask.sum()}, {sc}, {distrib}")

    i = dist.argmin()
    return score[i], lon[i], lat[i]


if __name__ == '__main__':
    load_config('config.yml', 'paths.yml', verbose=True)
    c = Client(
        n_workers=16,
        threads_per_worker=1,
        local_directory=CONFIG['dask']['temporary_directory'],
        dashboard_address=8786
    )
    logger.info('Dask client running on 8786')

    if len(sys.argv) >= 3:
        adj = sys.argv[-2]
        method = sys.argv[-1]
    else:
        adj = CONFIG['selfanalogy']['adj']
        method = CONFIG['selfanalogy']['method']
    logger.info(f'Starting self-analogy computation for {adj} adjustment with method {method}.')

    # Fichiers
    dref = xr.open_zarr(
        CONFIG['biasadjust']['reference_indices'], decode_timedelta=False
    ).chunk({'time': -1}).sel(time=slice('1991', '2020'))

    dsim = xr.open_zarr(
        CONFIG['biasadjust'][f'output_indices_{adj}'], decode_timedelta=False
    ).isel(realization=slice(None, 12))
    dsim = xc.core.calendar.convert_calendar(dsim, 'default')

    cities = xr.open_dataset('geo/cities.nc')
    masks = xr.open_zarr(CONFIG['project']['masks'])

    density = masks.dens_adj.sel(year=2020, drop=True).where(
        masks.roi & dref.isel(time=0).notnull().to_array().all('variable')
    ).load()

    logger.info('Files are open, generating output.')
    sim = dsim.sel(time=slice('1991', '2020')).to_array('indices', 'thearray')
    sim = sim.drop_vars(['lat', 'lon']).load().to_dataset()
    mask = (density > 10)
    dens1d = stack_drop_nans(density, mask)
    ref = stack_drop_nans(dref, mask).to_array('indices', 'thearray').load()
    ref = ref.chunk({'indices': 10}).to_dataset().assign(lon=ref.lon, lat=ref.lat)

    benchmark = xr.open_dataset(
        CONFIG['analog_quantiles']['output']
    ).benchmark.sel(indices=ref.indices)
    scores = []
    lons = []
    lats = []
    for i in range(cities.location.size):
        city = cities.isel(location=i, drop=True)
        if city.density < 1000:
            ref_i = ref.where(
                (dens1d > max(10, city.density / 4)) & (dens1d < max(city.density, 10) * 4) & (ref.lat > 40),
                drop=True
            )
        else:
            ref_i = ref.where(
                (dens1d > city.density / 8) & (dens1d < (city.density * 8)),
                drop=True
            )
        diss = xa.spatial_analogs(sim.isel(location=i, drop=True), ref_i, dist_dim='time', method='zech_aslan')
        if method == 'min':
            indx = diss.fillna(100).argmin('site')
            score = diss.min('site')
            lon = xc.indices.run_length.lazy_indexing(ref_i.lon, indx).where(score.notnull()).where(diss.notnull().any('site')).drop_vars(['lon', 'lat'])
            lat = xc.indices.run_length.lazy_indexing(ref_i.lon, indx + 0).where(score.notnull()).where(diss.notnull().any('site')).drop_vars(['lon', 'lat'])
        elif method == 'closestN':
            score, lon, lat = xr.apply_ufunc(
                get_best_closestN,
                diss, ref_i.lon, ref_i.lat, city.lon, city.lat,
                input_core_dims=[['site'], ['site'], ['site'], [], []],
                output_core_dims=[[], [], []],
                dask='parallelized',
                vectorize=True,
                output_dtypes=[diss.dtype, ref_i.lon.dtype, ref_i.lat.dtype],
            )
        elif method == 'closestP':
            score, lon, lat = xr.apply_ufunc(
                get_best_closestP,
                diss, ref_i.lon, ref_i.lat, city.lon, city.lat, benchmark,
                input_core_dims=[['site'], ['site'], ['site'], [], [], ['percentiles']],
                output_core_dims=[[], [], []],
                dask='parallelized',
                vectorize=True,
                output_dtypes=[diss.dtype, ref_i.lon.dtype, ref_i.lat.dtype],
            )

        scores.append(score)
        lons.append(lon)
        lats.append(lat)

    out = xr.merge([
        xr.concat(scores, cities.location).rename('score'),
        xr.concat(lons, cities.location).rename('lon'),
        xr.concat(lats, cities.location).rename('lat')
    ])

    logger.info('Computing all.')
    out.to_netcdf(Path(CONFIG['project']['datadir']) / f"self_analog_{adj}_{method}.nc")
