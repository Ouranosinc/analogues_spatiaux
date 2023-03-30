# utils.py
import dask
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
import xarray as xr
from xclim import analog as xa
from .constants import quality_thresholds, num_realizations

from xarray import __version__ as xa_ver
from xclim import __version__ as xc_ver
from pandas import __version__ as pd_ver
from geopandas import __version__ as gp_ver
from joblib import __version__ as jl_ver

from pathlib import Path
import json

def check_version(config):
    """ returns true if the current config version is the most up to date.
    """
    ### VERSIONS:
    # check versions to delete or not the cache:
    ver_new = {"xa":xa_ver,"xc":xc_ver,"pd":pd_ver,"gp":gp_ver,"jl":jl_ver}
    if "versions" in config:
        ver_old = config["versions"]
        if any([((k not in ver_old) or (ver_old[k] != ver_new[k])) for k in ver_new]):
            return False
        return True
    else: # versions not in config, assume it is not up to date.
        return False 
        

def open_thredds(url):
    """Open netCDF files on thredds and decode the string variables."""
    ds = xr.open_dataset(url, decode_timedelta=False)
    with xr.set_options(keep_attrs=True):
        for c in ds.variables.keys():
            if ds[c].dtype == 'S64':
                ds[c] = ds[c].str.decode('latin1')
    return ds

from xclim.core.utils import uses_dask

def is_computed(df):
    # returns true if df is computed, false if not.
    return not uses_dask(df) # no longer a dask array.

def inplace_compute(*df):
    """ Given the input dataframes df, computes them and updates them in place. similar to sim = dask.compute(sim), 
        but allows to do partial computations and allocations. """
    df_comp = dask.compute(*df)
    for i,dfi in enumerate(df):
        if hasattr(dfi,"update"):
            dfi.update(df_comp[i])
        else: # DataArray, not Dataset
            dfi.data = df_comp[i].data
    
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
