# utils.py
import dask
from dask.diagnostics import ProgressBar
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
import xarray as xr
from xclim import analog as xa
from .constants import quality_thresholds, num_realizations


def open_thredds(url):
    """Open netCDF files on thredds and decode the string variables."""
    ds = xr.open_dataset(url, decode_timedelta=False)
    with xr.set_options(keep_attrs=True):
        for c in ds.variables.keys():
            if ds[c].dtype == 'S64':
                ds[c] = ds[c].str.decode('latin1')
    return ds


def stack_drop_nans(ds, mask):
    """Stack dimensions into a single axis 'site' and drops indexes where the mask is false."""
    mask_1d = mask.stack(site=mask.dims).reset_index('site').drop_vars(mask.coords.keys())
    out = ds.stack(site=mask.dims).reset_index('site').where(mask_1d, drop=True)
    for dim in mask.dims:
        out[dim].attrs.update(ds[dim].attrs)
    return out.assign_coords(site=np.arange(out['site'].size))


def get_score_percentile(score, indices, benchmark):
    """Compare scores with the reference distribution for an indicator combination.
    Returns the interpolated percentiles.
    """
    dist = benchmark.sel(indices='_'.join(sorted(indices)))
    if isinstance(score, xr.DataArray):
        return xr.apply_ufunc(
            np.interp,
            score, dist, dist.percentiles,
            input_core_dims=[[], ['percentiles'], ['percentiles']],
            output_dtypes=[score.dtype],
            dask='parallelized',
        )
    perc = np.interp(score, dist, benchmark.percentiles)
    return perc


def get_quality_flag(score=None, indices=None, benchmark=None, percentile=None):
    """Compute the percentiles of scores compared to the reference distribution
    and return the quality flag as defined above.
    """
    if percentile is None:
        percentile = get_score_percentile(score, indices, benchmark)
    q = np.searchsorted(quality_thresholds, percentile)
    if isinstance(score, xr.DataArray):
        return score.copy(data=q).rename('quality_flag')
    return q


def get_unusable_indices(cities, dref, dsim, iloc, ssp, tgt_period):
    """Return a set of indices that are not usable for this combination of city, scenario and target period.

    This simply tests that the standard deviation is null over any realization on the reference period or the target period,
    or over the reference.
    """
    city = cities.iloc[iloc]
    ref = (dref.sel(lat=city.geometry.y, lon=city.geometry.x).std('time') == 0)
    sim = dsim.isel(location=iloc, realization=slice(0, num_realizations)).sel(ssp=ssp)
    simh = (sim.sel(time=slice('1991', '2020')).std('time') == 0).any('realization')
    simf = (sim.sel(time=tgt_period).std('time') == 0).any('realization')
    with ProgressBar():
        simh, simf, ref = dask.compute(simh, simf, ref)
    return set(
        [name for name, var in simh.data_vars.items() if var]
    ).union(
        [name for name, var in simf.data_vars.items() if var]
    ).union(
        [name for name, var in ref.data_vars.items() if var]
    )


def get_distances(lon, lat, geom):
    df = gpd.GeoDataFrame(geometry=[Point(lo, la) for lo, la in zip(lon, lat)], crs=4326)
    return df.to_crs(epsg=8858).distance(geom).values


def dec2sexa(num, secfmt='02.0f'):
    """Get a sexadecimal sting from a float."""
    deg = int(num)
    minu = int((num - deg) * 60)
    sec = (num - deg - (minu / 60)) * 3600
    if f"{sec:{secfmt}}" == '60':
        deg = deg + 1
        minu = 0
        sec = 0
    return f"{deg}°{minu:02.0f}′{sec:{secfmt}}″"


def n_combinations(n, k):
    return np.math.factorial(n) / (np.math.factorial(k) * np.math.factorial(n - k))


def _zech_aslan(inputs):
    return xa.zech_aslan(inputs[0], inputs[1])
