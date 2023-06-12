# utils.py
import dask
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
import xarray as xr
from xclim import analog as xa
from .constants import quality_thresholds, num_realizations, version_path

from xarray import __version__ as xa_ver
from xclim import __version__ as xc_ver
from pandas import __version__ as pd_ver
from geopandas import __version__ as gp_ver
from joblib import __version__ as jl_ver

from pathlib import Path
import json

def color_convert_alpha(s):
    ''' returns the same color s = '#rrggbb' when placed over a white background, but
        maximizes the alpha value, to allow blending.
    '''
    s = s[1:]
    colrgb = tuple([int(s[i:i+2],16) for i in range(0,len(s),2)])

    alpha = (255 - min(colrgb)) / 255
    cnew = [int((ci - min(colrgb)) / alpha) for ci in colrgb]
    chex = '#%02x%02x%02x' % tuple(cnew)
    return chex, alpha

def check_version():
    """ returns true if the current versionfile is correct.
    """
    ### VERSIONS:
    # check versions to delete or not the cache:
    ver_new = {"xa":xa_ver,"xc":xc_ver,"pd":pd_ver,"gp":gp_ver,"jl":jl_ver}
    ver_old = {}
    if version_path.is_file():
        with open(version_path,'r',encoding='utf-8') as version_file:
            ver_old = json.load(version_file)
    if any([((k not in ver_old) or (ver_old[k] != ver_new[k])) for k in ver_new]):
        return False
    else:
        return True 
    
def update_versions():
    # versionfile:
    ver_new = {"xa":xa_ver,"xc":xc_ver,"pd":pd_ver,"gp":gp_ver,"jl":jl_ver}
    with open(version_path,'w',encoding='utf-8') as version_file:
        json.dump(ver_new,version_file, ensure_ascii=False, indent=4)

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

def getmask(density,density_factor,tg_density,minpts,maxpts,mindensity):
    tg_density = max(tg_density,mindensity)
    
    with np.errstate(divide='ignore'):
        dsabs = np.abs(np.log10(density/tg_density))
    dsabs_1d = dsabs.stack({'site':('lat','lon')})
    dsabs_1d = dsabs_1d.sortby(dsabs_1d)
    
    ds_minpt = dsabs_1d.isel(site=minpts).item() > dsabs
    ds_maxpt = dsabs_1d.isel(site=maxpts).item() > dsabs
    
    ds_lower = density > max((tg_density / density_factor),mindensity)
    ds_upper = density < max((tg_density * density_factor),mindensity)
    
    mask  = (ds_lower & ds_upper) # all points that are in the range
    mask &= ds_maxpt # stop at 10000 closest points.
    mask |= ds_minpt # add closest 500 pts, if not already there.
    
    return mask
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
            score, dist, benchmark.percentiles,
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
