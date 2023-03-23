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
from .constants import num_bestanalogs, per_bestanalogs, best_analog_mode, num_realizations, quality_terms
from .utils import (
    get_distances,
    get_quality_flag,
    get_score_percentile,
    n_combinations,
    stack_drop_nans,
    _zech_aslan
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
             cities,
             icity,
             climate_indices,
             density_factor,
             tgt_period,
             ssp,
             best_analog_mode=best_analog_mode, 
             num_realizations=num_realizations):
    """ This function handles computation of the analogs search function"""
    city = cities.iloc[icity]
    sim = dsim[climate_indices].isel(location=city.location).sel(ssp=ssp).isel(realization=slice(0, num_realizations))
    ref = None
    if _analogs_search.check_call_in_cache(sim,
                                   ref,
                                   benchmark,
                                   cities,
                                   best_analog_mode, 
                                   icity,
                                   climate_indices,# not used, but used to identify ref/sim
                                   density_factor,  # not used, but used to identify ref
                                   tgt_period,
                                   ssp,
                                   num_realizations):
        # don't need to compute ref, only need to compute on city.
        analogs = _analogs_search(sim,
                                   ref,
                                   benchmark,
                                   cities,
                                   best_analog_mode, 
                                   icity,
                                   climate_indices,# not used, but used to identify ref/sim
                                   density_factor,  # not used, but used to identify ref
                                   tgt_period,
                                   ssp,
                                   num_realizations)
        analogDF = _compute_analog_vars(analogs,climate_indices,benchmark,density,sim)
        
        #ref_cities = dref[climate_indices].sel(site=[x.site for x in analogDF])
        dask.compute(sim) # can parallelize both tasks
    else:
        mask = (density < (city.density * density_factor)) & (density > max(city.density / density_factor, 10))
        
        ref = stack_drop_nans(dref[climate_indices], mask).chunk({'site': 100})
        analogs = _analogs_search( sim,
                                   ref,
                                   benchmark,
                                   cities,
                                   best_analog_mode, 
                                   icity,
                                   climate_indices,# not used, but used to identify ref/sim
                                   density_factor,  # not used, but used to identify ref
                                   tgt_period,
                                   ssp,
                                   num_realizations)
        analogDF = _compute_analog_vars(analogs,climate_indices,benchmark,density,sim)
        #ref_cities = dref[climate_indices].sel(site=[x.site for x in analogDF])
        # compute step takes place in get_best_analogs...
        # lets double check though, and recompute if not:
        dask.compute(sim)
    return analogs,analogDF,sim#,ref_cities

def _compute_analog_vars(analogs, climate_indices, benchmark, density, sim):
    """ This function computes additional variables for each analog in analogs, based on given inputs.
        These additional variables are lookups, may produce large variables, but are fast to compute.
        Thus, they are not cached with _analogs_search."""
    analogDF = []
    for analog in analogs:
        # unpack analog array:
        ireal,site,zscore,score,lat,lon = analog
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
                          density     = density.sel(lon=lon,lat=lat).item(), 
                          geometry    = Point(lon,lat), 
                          percentile  = percentile  , 
                          qflag       = qflag       , 
                          quality     = quality     
                         )
        analogDF.append(analogDict)
    analogDF = gpd.GeoDataFrame.from_records(analogDF).sort_values('zscore').reset_index(drop=True).set_crs(epsg=4326)
    analogDF['rank'] = analogDF.index + 1
    return analogDF

class BEST_ANALOG_MODES(Enum):
    CLOSESTPER = 0
    CLOSESTN   = 1
    MIN        = 2

class SSP(Enum):
    SSP45 = 0
    SSP85 = 1

def _simplify_args(dsim,
                   best_analog_mode, # 2 bits
                   icity,            # 8 bits (65 cities)
                   climate_indices,  # 20 bits
                   density_factor,   # 4 bits (up to 10)
                   tgt_period,       # 4 bits (11 different ones)
                   ssp,              # 1 bit
                   num_realizations):# 4 bits (up to 12), total: 30+8+5 = 43 bits => 48/8 = 7 bytes
    
    ssp_bit = ssp == 'ssp45' # 1 bit
    
    all_indices = [x.name for k,x in dsim.data_vars.items()] 
    climate_bits = [x in climate_indices for x in all_indices] #20 bits
    
    _to_utf(best_analog_bits + 
            icity_bits +
            climate_bits +
            density_bits +
            tgt_bits +
            [ssp_bit] +
            real_bits + [0,0,0,0,0])

def _to_utf(bitlist):
    # convert list of bits [1, 0, 1...] to a utf-8 string
    s = ''.join([str(x) for x in bitlist])
    bytelistb = [s[i:i+8].rjust(8,'0') for i in range(0, len(s), 8)] # bytelist of bits
    bytelistB = [int(b,2) for b in bytelistb]
    ustring = ''.join([chr(x) for x in bytelistB])
    return ustring

def _to_bitlist(ustring):
    bytelist = [ord(b) for b in ustring]
    return [bin(b)[2:].rjust(8,'0') for b in bytelist]

def _unsimplify_args(args):
    return best_analog_mode, icity, climate_indices, density_factor, tgt_perior, ssp, num_realizations

def _to_short(site,zscore,score,lat,lon):
    latmin = 20.
    latmax = 85.
    lonmin = -168.
    lonmax = -48.

    scoremin = -50.
    scoremax = 50.
    zscale = 10.
    # transform lat from 0 to 1:
    lat_to_norm = lambda lat : (lat - latmin) / (latmax - latmin)
    lon_to_norm = lambda lon : (lon - lonmin) / (lonmax - lonmin)
    zscore_to_norm = lambda zscore : zscore / zscale
    score_to_norm  = lambda score : (score - scoremin) / (scoremax - scoremin)

    # transform lat from 0 to 65535 (ushort)
    umax = 65535
    norm_to_short = lambda x: x * umax

    
    return (site, norm_to_short(zscore_to_norm(zscore)), norm_to_short(score_to_norm(score)), norm_to_short(lat_to_norm(lat)), norm_to_short(lon_to_norm(lon)))

def _to_float(site,zscore,score,lat,lon):
    latmin = 20.
    latmax = 85.
    lonmin = -168.
    lonmax = -48.

    scoremin = -50.
    scoremax = 50.
    zscale = 10.
    # transform from ushortnorm to 0-1:
    short_to_norm = lambda x: x / umax

    # transform from unorm to lat,lon:
    norm_to_lat = lambda x: (x * (latmax - latmin)) + latmin
    norm_to_lon = lambda x: (x * (lonmax - lonmin)) + lonmin
    norm_to_score = lambda x: (x * (scoremax - scoremin)) + scoremin
    norm_to_zscore = lambda x: (x * zscale)
    return (site, norm_to_zscore(short_to_norm(zscore)), norm_to_score(short_to_norm(score)), norm_to_lat(short_to_norm(lat)), norm_to_lon(short_to_norm(lon)))
@mem.cache(ignore=["sim","ref","benchmark","cities"])               
def _analogs_search( sim,
                     ref,
                     benchmark,
                     cities,
                     a): # compressed arguments for caching efficiency.
    """ This function computes the analogs search. 
        It isn't meant to be called directly, as you should use the wrapper, analogs, to compute extra variables efficiently
    """
    # Compute the Zech-Aslan dissimiarity
    # We also keep the simulated and reference timeseries in memory for the graphs.
    # percentiles are computed for the `closestPer` method.
    best_analog_mode, icity, climate_indices, density_factor, tgt_perior, ssp, num_realizations = _unsimplify_args(args)
    
    city = cities.iloc[icity]
    
    sim_tgt = sim.sel(time=tgt_period).drop_vars(['lon', 'lat'])
    dissimilarity = xa.spatial_analogs(
        sim_tgt, ref, dist_dim='time', method='zech_aslan'
    )
    simzscore = xa.spatial_analogs(
        sim_tgt.mean('realization'), sim_tgt, dist_dim='time', method='seuclidean'
    )
    percs = get_score_percentile(dissimilarity, climate_indices, benchmark)
    sim, ref, dissimilarity, percs, simzscore = dask.compute(sim, ref, dissimilarity, percs, simzscore)

    analogs = []
    for ireal,real in enumerate(sim.realization):
        diss = dissimilarity.sel(realization=real)
        perc = percs.sel(realization=real)

        if best_analog_mode == 'min':
            i = diss.argmin().item()
        elif best_analog_mode == 'closestN':
            diss = diss.sortby(diss).isel(site=slice(None, num_bestanalogs))
            dists = get_distances(diss.lon, diss.lat, city.geometry)
            i = dists.argmin()
        elif best_analog_mode == 'closestPer':
            perc_min = perc.min()
            if perc_min.isnull().item():
                # Woups
                continue
            diss = diss.where(perc < perc_min + per_bestanalogs, drop=True)
            diss = diss.sortby(diss)
            dists = get_distances(diss.lon, diss.lat, city.geometry)
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
