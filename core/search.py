# search.py
from .constants import (
    num_bestanalogs, 
    per_bestanalogs, 
    best_analog_mode, 
    num_realizations, 
    max_na,
    quality_terms_en, 
    quality_terms_fr, 
    analog_modes, 
    max_real,
    cache_path,
    minpts,
    maxpts,
    min_density)

from .utils import (
    get_quality_flag,
    get_score_percentile,
    n_combinations,
    stack_drop_nans,
    _zech_aslan,
    inplace_compute,
    is_computed,
    getmask,
    load_dsim,
    load_dref,
    load_cities,
    is_valid,
    get_valid
)

from .compress import (
    simplify_args,
    _to_short,
    _to_float
)

import logging
from joblib import Memory
mem = Memory(cache_path, verbose=0, bytes_limit=1e9, compress=9)
logger = logging.getLogger('analogs')
    
@mem.cache(ignore=["cities","dref","dsim"])
def get_unusable_indices(iloc, ssp, tgt_period, max_na = max_na, dsim=None,dref=None,cities=None):
    """Return a set of indices that are not usable for this combination of city, scenario and target period.

    This simply tests that the standard deviation is null over any realization on the reference period or the target period,
    or over the reference.
    
    To speed up the check, it uses cached variables.
    
    If dsim and dref are not given, loads them into global variables.
    """
    import dask
    from dask.diagnostics import ProgressBar
    
    with ProgressBar():
        if dsim is None:
            dsim = load_dsim()
        if dref is None:
            dref = load_dref()
        if cities is None:
            cities = load_cities()
        city = cities.iloc[iloc]
        ref = dref.sel(lat=city.geometry.y, lon=city.geometry.x)
        sim = dsim.isel(location=city.location, realization=slice(0, num_realizations)).sel(ssp=ssp)
        simh = sim.sel(time=slice('1991', '2020'))
        simf = sim.sel(time=tgt_period)

        def check(ds):
            ds_check = (ds.std('time') == 0) | is_valid(ds,max_na)
            if 'realization' in ds.dims:
                return ds_check.any('realization')
            return ds_check
    
        simh, simf, ref = dask.compute(simh, simf, ref)
        ds_ls = [simh,simf,ref]
        var = set()
        for ds in ds_ls:
            var.union([name for name in ds.data_vars if check(ds[[name]])])
        return var


def analogs( dsim,
             dref,
             density,
             benchmark,
             city,cities,places,
             climate_indices,
             density_factor,max_density,
             tgt_period,periods,
             ssp,ssp_list,
             best_analog_mode=best_analog_mode, analog_modes=analog_modes,
             num_realizations=num_realizations, max_real=max_real,
             minpts=minpts,maxpts=maxpts,mindensity=min_density, max_na = max_na):
    """ This function handles computation of the analogs search function"""
    import numpy as np
    sim = dsim[climate_indices].isel(location=city.location).sel(ssp=ssp).isel(realization=slice(0, num_realizations))
    
    all_indices = [x.name for k,x in dsim.data_vars.items()]
    
    arg_repr, full_args = simplify_args(best_analog_mode,analog_modes,
                                                       city, cities,  
                                                       climate_indices, all_indices,
                                                       density_factor, max_density,
                                                       tgt_period, periods,      
                                                       ssp,ssp_list,
                                                       num_realizations,max_real,
                                                       max_na)
    
    analogDF = None
    
    mask = getmask(density,density_factor,city.density,minpts,maxpts,mindensity)
    ref = stack_drop_nans(dref[climate_indices], mask).chunk({'site': 100})
    #in_cache = _analogs_search.check_call_in_cache(sim,
    #                               ref,
    #                               benchmark,
    #                               density,
    #                               cities,
    #                               full_args,
    #                               arg_repr)
    
    analogs_raw = _analogs_search(sim,
                                   ref,
                                   benchmark,
                                   density,
                                   cities,
                                   full_args,
                                   arg_repr)
    
   
    analogDF = _compute_analog_vars(analogs_raw,climate_indices,benchmark,density,sim,city, cities,places,num_realizations)
    
    
    
    if is_computed(ref):
        ref_cities = ref # ref is already computed, just use it.
    else:
        pts = analogDF[['site','lon','lat']].set_index('site')
        pts = pts[~pts.index.duplicated(keep='first')].to_xarray()
        
        ref_cities = dref[climate_indices].sel(lon=pts.lon,lat=pts.lat)
        
    return analogDF,sim,ref_cities

def _compute_analog_vars(analogs_raw, climate_indices, benchmark, density, sim, city, cities, places,num_realizations):
    """ This function computes additional variables for each analog in analogs, based on given inputs.
        These additional variables are lookups, may produce large variables, but are fast to compute.
        Thus, they are not cached with _analogs_search."""
    analogDF = []
    from clisops.core.subset import distance
    from shapely.geometry import Point
    import geopandas as gpd
    import numpy as np
    analogs = np.frombuffer(analogs_raw,'<u2').reshape((num_realizations,5))
    
    for ireal in range(0,num_realizations):
        # unpack analog array:
        analog = analogs[ireal,...]
        
        # handle (0,0,0,0,0)
        if ~np.any(analog):
            continue
        # convert output to floats:
        site,zscore,score,ilat,ilon = _to_float(*analog)
            
        d = density.isel(lat=ilat,lon=ilon)
        
        lat = d.lat.item()
        lon = d.lon.item()
        densityPt = d.item()
        geometry = Point(lon, lat)
        dists = distance(places,lat=lat,lon=lon) # works whenever xarray has (lat,lon).
        near_ind = dists.argmin().item()
        near_city = places.isel(index=near_ind)
        near_dist = distance(near_city,lat=city.lat_raw,lon=city.lon_raw).item() / 1000.
        #geocrs = gpd.GeoDataFrame({'geometry':[geometry]}, crs='EPSG:4326').to_crs(epsg=8858)
        #distances = places.distance(geocrs.geometry.iloc[0])
        #near_city = places.iloc[distances.argmin()].copy()
        #near_dist = geocrs.distance(cities.loc[[city.name]].to_crs(epsg=8858).geometry.iloc[0]).iloc[0] / 1000

        if near_city.ADM0_A3 in ['USA', 'CAN']:
            near_city['fullname'] = f"{near_city['NAME'].item()}, {near_city['ADM1NAME'].item()}"
        else:
            near_city['fullname'] = f"{near_city['NAME'].item()}, {near_city['ADM0_A3'].item()}"
        
        percentile = get_score_percentile(score, climate_indices, benchmark)
        qflag = get_quality_flag(percentile=percentile)
        quality_en = quality_terms_en[qflag]
        quality_fr = quality_terms_fr[qflag]
        analogDict = dict(ireal = ireal,
                          site  = site,
                          zscore= zscore,
                          score = score,
                          ilat  = ilat,
                          ilon  = ilon,
                          lat   = lat,
                          lon   = lon,
                          simulation = sim.isel(realization=ireal).realization.item(), 
                          near   = near_city['fullname'].item(),
                          near_dist   = near_dist,
                          density     = densityPt, 
                          geometry    = geometry, 
                          percentile  = percentile  , 
                          qflag       = qflag       , 
                          quality_en  = quality_en,
                          quality_fr  = quality_fr
                         )
        analogDF.append(analogDict)
    analogDF = gpd.GeoDataFrame.from_records(analogDF).sort_values('zscore').reset_index(drop=True).set_crs(epsg=4326)
    analogDF['rank'] = analogDF.index + 1
    return analogDF


@mem.cache(ignore=["sim","ref","benchmark","cities","full_args","density"])               
def _analogs_search( sim,
                     ref,
                     benchmark,
                     density,
                     cities,
                     full_args,
                     a): # compressed arguments for caching efficiency.
    """ This function computes the analogs search. 
        It isn't meant to be called directly, as you should use the wrapper, analogs, to compute extra variables efficiently
    """
    import numpy as np
    from clisops.core.subset import distance
    from xclim import analog as xa
    import dask
    from types import SimpleNamespace
    import warnings
    # change this value to invalidate the website cache on the next commit:
    invalidate_cache = 1;
    
    ns = SimpleNamespace(**full_args) # call variables passed to simplify_args with ns.[varname]
    # Compute the Zech-Aslan dissimiarity
    # We also keep the simulated and reference timeseries in memory for the graphs.
    # percentiles are computed for the `closestPer` method.
    
    sim = sim.drop_vars(['lon', 'lat']).sel(time=ns.tgt_period)
    ilat_ref = density.indexes["lat"]
    ilon_ref = density.indexes["lon"]
    inplace_compute(sim, ref)
    
    analogs = np.zeros((ns.num_realizations,5),dtype='<u2')
    # compute realization per realization, drop NaNs instead of return NaNs, if maxna >= 1:
    
    sim_mean = sim.mean('realization')
    for ireal,real in enumerate(sim.realization):
        sim_tgt = sim.sel(realization=real)
        try:
            sim_tgt = get_valid(sim_tgt,ns.max_na)
        except ValueError as err:
            warnings.warn(f'Too many NaN values for {real.item()}, {ns.city.city}, {ns.tgt_period}, {ns.climate_indices}')
            continue
        
        diss = xa.spatial_analogs(sim_tgt,ref,dist_dim='time',method='zech_aslan')
        perc = get_score_percentile(diss,ns.climate_indices,benchmark)
        zscore = xa.spatial_analogs(sim_mean,sim_tgt,dist_dim='time',method='seuclidean')
        (diss,perc,zscore) = dask.compute(diss,perc,zscore)
        perc_min = perc.min()
        
        if perc_min.isnull().item():
            warnings.warn(f'Could not compute percentile analogue score for {real.item()}, {ns.city.city}, {ns.tgt_period}, {ns.climate_indices}')
            continue
            
        if ns.best_analog_mode == 'min':
            i = diss.argmin().item()
        elif ns.best_analog_mode == 'closestPer':
            diss = diss.where(perc < (perc_min + per_bestanalogs), drop=True)
            diss = diss.sortby(diss)
            dists = distance(diss, lat=ns.city.lat_raw,lon=ns.city.lon_raw)
            i = dists.argmin()
        elif ns.best_analog_mode == 'closestDens':
            diss = diss.where(perc < (perc_min + per_bestanalogs), drop=True)
            diss = diss.sortby(diss)
            dens_dist = np.abs(density.sel(lat=diss.lat,lon=diss.lon) - ns.city.density)
            i = dens_dist.argmin()

        score = diss.isel(site=i)
        site = score.site.item()
        
        lat = score.lat.item()
        ilat = ilat_ref.get_loc(lat,method='nearest')
        lon = score.lon.item()
        ilon = ilon_ref.get_loc(lon,method='nearest')
        
        analogs[ireal,:] = np.around(_to_short(site,zscore.item(),score.item(),ilat,ilon))
        
    return np.array(analogs,dtype='<u2').tobytes()


def montecarlo_distribution(ds, mask, maxindicators=5, couples=200000, workers=4,skipna=False,maxna = 0):
    """
    Estimate the score distributions with a Monte-Carlo method.

    Random couples of points are taken for each possible indicator combination and
    their Zech-Aslan dissimilarity score is computed. The quantiles of the approximated
    distributed are returned.

    Data will be loaded first, so the masked ds should fit in memory!

    Parameters
    ----------
    ds: xr.Dataset
      The "reference" dataset with all indicators, over spatial dimensions and the reference period.
    mask: xr.DataArray
      Boolean array with the same spatial dimensions as `ds`, indicating which points (sites)
      should be included in the computation.
    maxindicators: int
      The maximum number of indicators that can be use to search for analogs.
    couples: int
      The number of couples to test for each indicator combination.
    workers: int
      The number of Multi-processing workers to use.
    skipna: bool
      if True, NaN values are skipped instead of outputting a dissimilarity of NaN
    Returns
    -------
    cdf, xr.DataArray
      The quantized distributions, the indicator combinations are along `indices`,
      with the names joined by underscores in alphabetical order.
    """
    import xarray as xr
    from multiprocessing import Pool
    from itertools import combinations
    import pandas as pd
    import numpy as np
    import dask
    logger.info(f'Loading data where mask is True.')
    ds = stack_drop_nans(ds, mask).drop_vars(['lat', 'lon'])
    ds = ds.to_array('indices').transpose('site', 'time', 'indices')
    #ds = ds.load()

    # Sort to ensure alphabetical order and thus consistent index in the final df.
    allindices = list(sorted(ds.indices.values))
    NperI = [n_combinations(len(allindices), i) for i in range(1, maxindicators + 1)]
    Ntot = sum(NperI)
    out = {}
    max_na = maxna
    
    def iter_arrays(arr1, arr2):
        for i in range(arr1.shape[0]):
            x = arr1[i,...]
            y = arr2[i,...]
            if skipna and (np.ma.count_masked(x) <= max_na) and (np.ma.count_masked(y) <= max_na):
                filt = x.mask | y.mask
                x.mask = filt
                y.mask = filt
                x = np.ma.compress_rowcols(x,0)
                y = np.ma.compress_rowcols(y,0)
            yield x,y
    
    quantiles = np.sort(np.concatenate((np.geomspace(0.001,1.,100),np.arange(0.,1.,0.01))))
    with Pool(workers) as p:
        for i in range(1, maxindicators + 1):
            for j, indices in enumerate(combinations(allindices, i)):
                n = sum(NperI[: i - 1]) + j + 1
                logger.info(f'Computing quantiles for {indices} - ({n} of {Ntot:.0f}, {n / Ntot:.0%})')
                logger.info(f'  Computing dissimilarity for {couples} random couples.')
                tgt = ds.sel(indices=list(indices)).isel(site=np.random.randint(0, ds.site.size, size=(couples,)))
                cnd = ds.sel(indices=list(indices)).isel(site=np.random.randint(0, ds.site.size, size=(couples,)))
                tgt,cnd = dask.compute(tgt,cnd)
                if skipna:
                    tgt,cnd = tgt.to_masked_array(),cnd.to_masked_array()
                else:
                    tgt,cnd = tgt.values, cnd.values
                diss = np.array(
                    list(
                        p.imap_unordered(
                            _zech_aslan,
                            iter_arrays(tgt, cnd),
                            chunksize=min(100, couples // (4 * workers))
                        )
                    )
                )
                out['_'.join(indices)] = list(np.nanquantile(diss, q=quantiles))

    df = pd.DataFrame.from_dict(out, orient='index', columns=quantiles)

    cdf = xr.DataArray(
        df.to_numpy(),
        dims=('indices', 'percentiles'),
        coords={'indices': df.index, 'percentiles': [p * 100. for p in df.columns]},
        name='cdf',
        attrs={
            'long_name': 'CDF of the Zech-Aslan scores',
            'description': (
                "Cumulative distribution function of Zech-Aslan scores generated from "
                f"{couples} random couples within the reference indices."
            ),
            'units': ''
        }
    )
    return cdf
