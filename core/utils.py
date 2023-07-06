# utils.py

from .constants import quality_thresholds, num_realizations, version_path, datavar_path, cities_file, benchmark_path, density_path, cache_path

from pathlib import Path
import json

def load_config():
    global config
    if 'config' not in globals():
        config_path = 'config.json';
        with open(config_path,encoding='utf-8') as config_file:
            config = json.load(config_file)
    return config

def load_dsim():
    global dsim, config
    import xclim as xc
    config = load_config()
    if 'dsim' not in globals():
        dsim = open_thredds(config["url"]["dsim"])
        dsim = xc.core.calendar.convert_calendar(dsim, 'default')
    return dsim

def load_dref():
    global dref, config
    config = load_config()
    if 'dref' not in globals():
        dref = open_thredds(
            config["url"]["dref"]
        ).chunk({'time': -1}).sel(time=slice('1991', '2020'))
    return dref

def load_datavars():
    global datavars
    if 'datavars' not in globals():
        if not datavar_path.is_file():
            # obtain from dsim
            datavars = update_datavars()
        else:
            with open(datavar_path) as fp:
                datavars = json.load(fp)
    return datavars

def update_datavars():
    global dsim
    if 'dsim' not in globals():
        dsim = load_dsim()
    datavars = {k:{"en":v.long_name,"fr":v.long_name_fr} for k, v in dsim.data_vars.items()}
    with open(datavar_path,'w',encoding='utf-8') as fp:
        json.dump(datavars,fp, ensure_ascii=False, indent=4)
    return datavars

def load_places():
    global places
    import geopandas as gpd
    import urllib
    from packaging import version
    
    config = load_config()
    if 'places' not in globals():
        # workaround for #2796 in geopandas:
        with urllib.request.urlopen(url=config["url"]["places"]) as req:
            if version.parse(gpd.__version__) >= version.parse("0.13.0"):
                #(for Trevor's sensibilities)
                places = gpd.read_file(filename=req, engine='pyogrio')
            else:
                places = gpd.read_file(filename=req)
        places['lat'] = places.geometry.y
        places['lon'] = places.geometry.x
        places = places.to_xarray()
    return places

def load_cities():
    global cities
    import geopandas as gpd
    if 'cities' not in globals():
        cities = gpd.read_file(cities_file)
    return cities

def load_benchmark():
    global benchmark, config
    import pickle
    if 'benchmark' not in globals():
        if not benchmark_path.is_file():
            config = load_config()
            benchmark = open_thredds(config["url"]["benchmark"]).benchmark.load()
            with open(benchmark_path, 'wb') as obj_handler:
                pickle.dump(benchmark, obj_handler)
        else:
            with open(benchmark_path, 'rb') as obj_handler:
                benchmark = pickle.load(obj_handler)
    return benchmark

def load_density():
    global density, config
    import pickle
    config = load_config()
    if 'density' not in globals():
        if not density_path.is_file():
            masks = open_thredds(config["url"]["masks"])
            dref = load_dref()
            density = masks.dens_adj.sel(year=2020).where(
                masks.roi & dref.isel(time=0).notnull().to_array().all('variable')
            ).load()

            with open(density_path, 'wb') as obj_handler:
                pickle.dump(density, obj_handler)
        # load pickled data
        else:
            with open(density_path, 'rb') as obj_handler:
                density = pickle.load(obj_handler)
    return density

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

def check_pip_version(pkgs):
    '''returns a dictionary of packages {pkg_name:version}, as returned by pip list.'''
    # thanks Trevor! this speeds it up immensely.
    import importlib
    return {k:importlib.metadata.version(k) for k in pkgs}

def get_old_version():
    """ returns true if the current versionfile is correct.
    """
    ver_old = {}
    if version_path.is_file():
        with open(version_path,'r',encoding='utf-8') as version_file:
            ver_old = json.load(version_file)
    return ver_old
   
def compare_versions(ver_new, ver_old):
    '''returns true if and only if ver_new[k] == ver_old[k] for all k in union(ver_new,ver_old)'''
    for k in set().union(ver_new.keys(),ver_old.keys()):
        if ((k not in ver_new) or 
            (k not in ver_old) or
            (ver_new[k] != ver_old[k])):
            return False
    return True
        
def update_versions(ver_new):
    # versionfile:
    with open(version_path,'w',encoding='utf-8') as version_file:
        json.dump(ver_new,version_file, ensure_ascii=False, indent=4)

def check_version_delete_cache():
    print('checking package versions...')
    curr = check_pip_version(['xarray','xclim','pandas','geopandas','joblib'])
    old = get_old_version()
    if not compare_versions(curr,old):
        print("Old versions detected. Removing cached files.")
        try:
            os.remove(benchmark_path)
        except:
            pass
        try:
            os.remove(density_path)
        except:
            pass
        try:
            os.rmdir(cache_path)
        except:
            pass
        # add marker for next time, so persistence is possible:
        update_versions(curr)

def open_thredds(url): 
    """Open netCDF files on thredds and decode the string variables."""
    import xarray as xr
    ds = xr.open_dataset(url, decode_timedelta=False)
    with xr.set_options(keep_attrs=True):
        for c in ds.variables.keys():
            if ds[c].dtype == 'S64':
                ds[c] = ds[c].str.decode('latin1')
    return ds

def is_computed(df):
    # returns true if df is computed, false if not.
    from xclim.core.utils import uses_dask
    return not uses_dask(df) # no longer a dask array.

def inplace_compute(*df):
    """ Given the input dataframes df, computes them and updates them in place. similar to sim = dask.compute(sim), 
        but allows to do partial computations and allocations. """
    import dask

    df_comp = dask.compute(*df)
    for i,dfi in enumerate(df):
        if hasattr(dfi,"update"):
            dfi.update(df_comp[i])
        else: # DataArray, not Dataset
            dfi.data = df_comp[i].data

def getmask(density,density_factor,tg_density,minpts,maxpts,mindensity):
    import numpy as np

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
    import numpy as np

    mask_1d = mask.stack(site=mask.dims).reset_index('site').drop_vars(mask.coords.keys())
    out = ds.stack(site=mask.dims).reset_index('site').where(mask_1d, drop=True)
    for dim in mask.dims:
        out[dim].attrs.update(ds[dim].attrs)
    return out.assign_coords(site=np.arange(out['site'].size))


def get_score_percentile(score, indices, benchmark):
    """Compare scores with the reference distribution for an indicator combination.
    Returns the interpolated percentiles.
    """
    import numpy as np
    import xarray as xr
    import dask

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
    import numpy as np
    import xarray as xr
    
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
    ''' much more efficient than factorials: '''
    from math import comb
    return math.comb(n,k)


def _zech_aslan(inputs):
    from xclim import analog as xa
    return xa.zech_aslan(inputs[0], inputs[1])
