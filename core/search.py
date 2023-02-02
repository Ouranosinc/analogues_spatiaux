# search.py
import dask
import geopandas as gpd
from itertools import combinations
import logging
from multiprocessing import Pool
import numpy as np
import pandas as pd
from shapely.geometry import Point
import xarray as xr
from xclim import analog as xa
from .constants import num_bestanalogs, per_bestanalogs, best_analog_mode, num_realizations, quality_terms
from .utils import (
    get_distances,
    get_quality_flag,
    get_score_percentile,
    n_combinations,
    stack_drop_nans,
    _zech_aslan
)
logger = logging.getLogger('analogs')


def analogs_search(sim, ref, density, city, tgt_period, benchmark, density_factor):
    density_mask = (density < (city.density * density_factor)) & (density > max(city.density / density_factor, 10))

    sim = sim.isel(realization=slice(0, num_realizations))
    ref = stack_drop_nans(ref, density_mask).chunk({'site': 100})

    # Compute the Zech-Aslan dissimiarity
    # We also keep the simulated and reference timeseries in memory for the graphs.
    # percentiles are computed for the `closestPer` method.
    sim_tgt = sim.sel(time=tgt_period).drop_vars(['lon', 'lat'])
    dissimilarity = xa.spatial_analogs(
        sim_tgt, ref, dist_dim='time', method='zech_aslan'
    )
    simzscore = xa.spatial_analogs(
        sim_tgt.mean('realization'), sim_tgt, dist_dim='time', method='seuclidean'
    )
    percs = get_score_percentile(dissimilarity, list(sim.data_vars.keys()), benchmark)
    sim, ref, dissimilarity, percs, simzscore = dask.compute(sim, ref, dissimilarity, percs, simzscore)

    analogs = []
    for real in dissimilarity.realization:
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
        percentile = get_score_percentile(score.item(), list(sim.data_vars.keys()), benchmark)
        qflag = get_quality_flag(percentile=percentile)
        analogs.append(
            dict(
                simulation=real.item(),
                site=score.site.item(),
                zscore=simzscore.sel(realization=real).item(),
                inner_rank=i,
                density=density.sel(lon=score.lon, lat=score.lat).item(),
                score=score.item(),
                percentile=percentile,
                qflag=qflag,
                quality=quality_terms[qflag],
                geometry=Point(score.lon.item(), score.lat.item())
            )
        )

    analogs = gpd.GeoDataFrame.from_records(analogs).sort_values('zscore').reset_index(drop=True).set_crs(epsg=4326)
    analogs['rank'] = analogs.index + 1
    return analogs, sim, ref


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
