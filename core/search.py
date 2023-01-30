# search.py
import dask
from dask.diagnostics import ProgressBar
import geopandas as gpd
from shapely.geometry import Point
from xclim import analog as xa
from .constants import num_bestanalogs, per_bestanalogs, best_analog_mode, num_realizations, quality_terms
from .utils import stack_drop_nans, get_distances, get_quality_flag, get_score_percentile


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
