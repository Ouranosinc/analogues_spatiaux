# search.py
import dask
from dask.diagnostics import ProgressBar

import geopandas as gpd
from itertools import combinations
import logging
from multiprocessing import Pool
import numpy as np
import pandas as pd
from shapely.geometry import Point
import xarray as xr
from xclim import analog as xa
from xclim.core.utils import uses_dask
from .constants import num_bestanalogs, per_bestanalogs, best_analog_mode, num_realizations, quality_terms, analog_modes, max_real
from .utils import (
    get_distances,
    get_quality_flag,
    get_score_percentile,
    n_combinations,
    stack_drop_nans,
    _zech_aslan
)

from .compress import (
    simplify_args,
    _to_short,
    _to_float
)

from joblib import Memory
cachedir = "./cache/"
mem = Memory(cachedir, verbose=0, bytes_limit=1e9, compress=9)
logger = logging.getLogger('analogs')

@mem.cache(ignore=["cities","dref","dsim"])
def get_unusable_indices(cities, dref, dsim, iloc, ssp, tgt_period):
    """Return a set of indices that are not usable for this combination of city, scenario and target period.

    This simply tests that the standard deviation is null over any realization on the reference period or the target period,
    or over the reference.
    
    To speed up the check, it uses cached variables.
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

def is_computed(array):
    return not uses_dask(array) # no longer a dask array.

def analogs( dsim,
             dref,
             density,
             benchmark,
             city,cities,
             climate_indices,
             density_factor,max_density,
             tgt_period,periods,
             ssp,ssp_list,
             best_analog_mode=best_analog_mode, analog_modes=analog_modes,
             num_realizations=num_realizations, max_real=max_real):
    """ This function handles computation of the analogs search function"""
    sim = dsim[climate_indices].isel(location=city.location).sel(ssp=ssp).isel(realization=slice(0, num_realizations))
    ref = None
    
    all_indices = [x.name for k,x in dsim.data_vars.items()]
    
    arg_repr, full_args = simplify_args(best_analog_mode,analog_modes,
                                                       city, cities,  
                                                       climate_indices, all_indices,
                                                       density_factor, max_density,
                                                       tgt_period, periods,      
                                                       ssp,ssp_list,
                                                       num_realizations,max_real)
    need_call = _analogs_search.check_call_in_cache(sim,
                                   ref,
                                   benchmark,
                                   cities,
                                   full_args,
                                   arg_repr)
    analogDF = None
    if not need_call:
        mask = (density < (city.density * density_factor)) & (density > max(city.density / density_factor, 10))
        ref = stack_drop_nans(dref[climate_indices], mask).chunk({'site': 100})
        
    analogs_raw = _analogs_search(sim,
                                   ref,
                                   benchmark,
                                   cities,
                                   full_args,
                                   arg_repr)
    
    analogs = [_to_float(*x) for x in np.frombuffer(analogs_raw,'<u2').reshape((12,5))]
    
    analogDF = _compute_analog_vars(analogs,climate_indices,benchmark,density,sim)
    #ref_cities = dref[climate_indices].sel(site=[x.site for x in analogDF])
 
    return analogs,analogDF,sim#,ref_cities

def _compute_analog_vars(analogs, climate_indices, benchmark, density, sim):
    """ This function computes additional variables for each analog in analogs, based on given inputs.
        These additional variables are lookups, may produce large variables, but are fast to compute.
        Thus, they are not cached with _analogs_search."""
    analogDF = []
    for ireal,analog in enumerate(analogs):
        # unpack analog array:
        site,zscore,score,lat,lon = analog
        d = density.sel(lat=lat,lon=lon, method='nearest')
        
        lat = d.lat.item()
        lon = d.lon.item()
        densitypt = d.item()
        
        percentile = get_score_percentile(score, climate_indices, benchmark)
        qflag = get_quality_flag(percentile=percentile)
        quality = quality_terms[qflag]
        analogDict = dict(ireal = ireal,
                          site  = site,
                          zscore= zscore,
                          score = score,
                          lat   = lat,
                          lon   = lon,
                          realization = sim.isel(realization=ireal).realization.item(), 
                          density     = densitypt, 
                          geometry    = Point(lon,lat), 
                          percentile  = percentile  , 
                          qflag       = qflag       , 
                          quality     = quality     
                         )
        analogDF.append(analogDict)
    analogDF = gpd.GeoDataFrame.from_records(analogDF).sort_values('zscore').reset_index(drop=True).set_crs(epsg=4326)
    analogDF['rank'] = analogDF.index + 1
    return analogDF

from types import SimpleNamespace
@mem.cache(ignore=["sim","ref","benchmark","cities","full_args"])               
def _analogs_search( sim,
                     ref,
                     benchmark,
                     cities,
                     full_args,
                     a): # compressed arguments for caching efficiency.
    """ This function computes the analogs search. 
        It isn't meant to be called directly, as you should use the wrapper, analogs, to compute extra variables efficiently
    """
    ns = SimpleNamespace(**full_args) # call variables passed to simplify_args with ns.[varname]
    # Compute the Zech-Aslan dissimiarity
    # We also keep the simulated and reference timeseries in memory for the graphs.
    # percentiles are computed for the `closestPer` method.
    
    sim_tgt = sim.sel(time=ns.tgt_period).drop_vars(['lon', 'lat'])
    dissimilarity = xa.spatial_analogs(
        sim_tgt, ref, dist_dim='time', method='zech_aslan'
    )
    simzscore = xa.spatial_analogs(
        sim_tgt.mean('realization'), sim_tgt, dist_dim='time', method='seuclidean'
    )
    percs = get_score_percentile(dissimilarity, ns.climate_indices, benchmark)
    sim, ref, dissimilarity, percs, simzscore = dask.compute(sim, ref, dissimilarity, percs, simzscore)

    analogs = []
    for ireal,real in enumerate(sim.realization):
        diss = dissimilarity.sel(realization=real)
        perc = percs.sel(realization=real)

        if ns.best_analog_mode == 'min':
            i = diss.argmin().item()
        elif ns.best_analog_mode == 'closestN':
            diss = diss.sortby(diss).isel(site=slice(None, ns.num_bestanalogs))
            dists = get_distances(diss.lon, diss.lat, ns.city.geometry)
            i = dists.argmin()
        elif ns.best_analog_mode == 'closestPer':
            perc_min = perc.min()
            if perc_min.isnull().item():
                # Woups
                continue
            diss = diss.where(perc < perc_min + per_bestanalogs, drop=True)
            diss = diss.sortby(diss)
            dists = get_distances(diss.lon, diss.lat, ns.city.geometry)
            i = dists.argmin()

        score = diss.isel(site=i)
        site = score.site.item()
        lat = score.lat.item()
        lon = score.lon.item()
        zscore = simzscore.sel(realization=real).item()
        analogs.append(np.around(_to_short(site,zscore,score.item(),lat,lon)))
        
    return np.array(analogs,dtype='<u2').tobytes()


def montecarlo_distribution(ds, mask, maxindicators=5, couples=200000, workers=4):
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

    Returns
    -------
    cdf, xr.DataArray
      The quantized distributions, the indicator combinations are along `indices`,
      with the names joined by underscores in alphabetical order.
    """
    logger.info(f'Loading data where mask is True.')
    ds = stack_drop_nans(ds, mask).drop_vars(['lat', 'lon'])
    ds = ds.to_array('indices').transpose('site', 'time', 'indices')
    ds = ds.load()

    # Sort to ensure alphabetical order and thus consistent index in the final df.
    allindices = list(sorted(ds.indices.values))
    NperI = [n_combinations(len(allindices), i) for i in range(1, maxindicators + 1)]
    Ntot = sum(NperI)
    out = {}

    def iter_arrays(arr1, arr2):
        for i in range(arr1.shape[0]):
            yield arr1[i, ...], arr2[i, ...]

    quantiles = np.arange(0, 1, 0.01)
    with Pool(workers) as p:
        for i in range(1, maxindicators + 1):
            for j, indices in enumerate(combinations(allindices, i)):
                n = sum(NperI[: i - 1]) + j + 1
                logger.info(f'Computing quantiles for {indices} - ({n} of {Ntot:.0f}, {n / Ntot:.0%})')
                logger.info(f'  Computing dissimilarity for {couples} random couples.')
                tgt = ds.sel(indices=list(indices)).isel(site=np.random.randint(0, ds.site.size, size=(couples,))).values
                cnd = ds.sel(indices=list(indices)).isel(site=np.random.randint(0, ds.site.size, size=(couples,))).values

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

    df = pd.DataFrame.from_dict(out, orient='index', columns=[f"p{q * 100:02.0f}" for q in quantiles])

    cdf = xr.DataArray(
        df.to_numpy(),
        dims=('indices', 'percentiles'),
        coords={'indices': df.index, 'percentiles': [int(p[1:]) for p in df.columns]},
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
