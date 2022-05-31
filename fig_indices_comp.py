"""
Figure painter
--------------
Generates timeseries plot for each index and city.
Also splits the Zarrs into netCDFs.
"""
from dask import config as dskconf
from pathlib import Path
import logging
import sys
import xclim as xc
import xarray as xr
import matplotlib.pyplot as plt
from config import load_config, CONFIG
logger = logging.getLogger("workflow")
load_config('config.yml', 'paths.yml', verbose=True)


def fig_ts(scen, ind, loc, ssp, Nr, mode='spag'):
    fig, ax = plt.subplots(figsize=(8, 4))
    city = cities.city.sel(location=loc).item()
    sts = scen[ind].sel(location=loc, ssp=ssp).isel(realization=slice(None, Nr)).load()
    if mode.endswith('roll'):
        sts = sts.rolling(time=29, min_periods=1, center=True).mean()
    if mode.startswith('spag'):
        sts.plot(
            ax=ax, hue='realization', color='lightgray', add_legend=False
        )
        sts.median('realization').plot(
            ax=ax, color='black', label=f'Median of {Nr} doubly-adjusted simulations'
        )
    elif mode.endswith('ruban'):
        qs = sts.quantile([0.10, 0.50, 0.90], 'realization')
        ax.fill_between(qs.time.values, qs.sel(quantile=0.10).values, qs.sel(quantile=0.90).values,
                        color='lightgray', label='10th to 90th percentiles')
        qs.sel(quantile=0.50).plot(ax=ax, color='black', label=f'Median of {Nr} doubly-adjusted simulations.')

    Zscore = ((sts - sts.mean('realization')) / sts.std('realization')).max().item()
    if Zscore > 4.5:
        logger.warn(f'{ind} - {city} ({loc.item()}) - {ssp.item()} - Z = {Zscore} > 4.5')
    ref[ind].sel(location=loc).plot(ax=ax, color='red', label='Reference (ERA5-land)')
    ax.set_title(f"{ind} - {city} - {ssp.item()}")
    plt.legend()
    return fig


if __name__ == '__main__':
    dskconf.set(**CONFIG['dask'])

    level = sys.argv[-2]
    mode = sys.argv[-1]

    scen = xr.open_zarr(CONFIG['biasadjust'][f'output_indices_{level}'], decode_timedelta=False)
    ref_map = xr.open_zarr(CONFIG['biasadjust']['reference_indices'], decode_timedelta=False)
    ref = xc.core.calendar.convert_calendar(ref_map.sel(lon=scen.lon, lat=scen.lat), 'noleap')
    cities = xr.open_dataset('geo/cities.nc')

    for ind in scen.data_vars.keys():
        logger.info(f"Figuring indicator: {ind}")
        for loc in scen.location:
            Nr = 12
            for ssp in scen.ssp:
                fig = fig_ts(scen, ind, loc, ssp, Nr, mode=mode)
                city = cities.city.sel(location=loc).item()
                outpath = Path(CONFIG['indicators']['figures']['folder'].format(mode=mode, level=level)) / f"{city}"
                outpath.mkdir(exist_ok=True, parents=True)
                fig.savefig(outpath / f"comp_{ind}_{ssp.item()}.png")
                plt.close(fig)
