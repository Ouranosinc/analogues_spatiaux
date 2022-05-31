"""
Bias-adjust : Indices
---------------------
The second bias adjustment. It aims to improve the results of the self-analog test.
Available in two flavours : "scaling" and "DQM".
Many points are skipped, according to the feasibility of the adjustment.
"""
from dask.diagnostics import ProgressBar
import dask
import logging
import numpy as np
from pathlib import Path
import sys
import xarray as xr
from xclim import sdba
from xclim.core.calendar import convert_calendar
from xclim.core.formatting import update_history
from config import load_config, CONFIG
logger = logging.getLogger("workflow")
ProgressBar().register()


if __name__ == '__main__':
    load_config('config.yml', 'paths.yml', verbose=True)
    dask.config.set(**CONFIG['dask'])
    period = slice('1991', '2020')
    method = sys.argv[-1]

    logger.info('Opening files and extracting indices from reference.')
    sim = xr.open_zarr(CONFIG['biasadjust']['output_indices_single'], decode_timedelta=False)
    ref_map = xr.open_zarr(CONFIG['biasadjust']['reference_indices'], decode_timedelta=False)

    ref = convert_calendar(
        ref_map.sel(lon=sim.lon, lat=sim.lat).sel(time=period).chunk({'time': -1}),
        'noleap'
    )
    hist = sim.sel(time=period)
    fut = sim.sel(time=slice('2071', '2100'))
    ref, hist, fut = dask.compute(ref, hist, fut)
    logger.info('Bias adjusting.')

    scen = xr.Dataset(attrs=CONFIG['biasadjust']['attrs_double']['global'])
    scen.attrs['source'] = CONFIG['biasadjust']['attrs_double']['source'].format(double_method={'DQM': 'Detrended Quantile Mapping'}.get(method))

    for name in sim.data_vars.keys():
        kind = sdba.utils.ADDITIVE if name in CONFIG['biasadjust']['additive_indices'] else sdba.utils.MULTIPLICATIVE

        refm = ref[name].mean('time')
        refx = ref[name].max()
        histm = hist[name].mean('time')
        histx = hist[name].max()
        hists = hist[name].std('time')
        futs = fut[name].std('time')

        logger.info(f'{name} - {kind}')
        extra = ""

        if method == 'scaling':
            if kind is sdba.utils.MULTIPLICATIVE:
                af = refm / histm
                scenda = sim[name] * af
            else:
                af = refm - histm
                scenda = sim[name] + af
        elif method == 'DQM':
            DQM = sdba.DetrendedQuantileMapping.train(
                ref[name], hist[name], nquantiles=50, group="time", kind=kind
            )
            scenda = DQM.adjust(
                sim[name], detrend=sdba.detrending.LoessDetrend(f=0.2, niter=1, d=0, kind=kind),
                extrapolation='constant', interp='nearest'
            )
        if kind is sdba.utils.MULTIPLICATIVE:
            fishes = (histm * 1000 < histx) | (refm * 1000 < refx) | (futs / hists > 5)
            if fishes.any():
                fishes = fishes.any(['realization'])
                logger.warning(
                    'Something\'s fishy:\n'
                    f'min(mean(ref)) = {refm.min().item()}, min(mean(hist)) = {histm.min().item()}\n'
                    f'max(ref) = {refx.item()}, max(hist) = {histx.item()}\n'
                    f"max(σ(fut) / σ(hist)) = {(futs/hists).max().item()}\n"
                    f"{fishes.sum().item()} cities/ssps will not be adjusted."
                )
                extra = (
                    " The adjustment was not performed for locations and ssps with a "
                    "near-zero historical mean in either the reference or any "
                    "of the simulated realizations."
                )
                with open(f"noadj_report_{name}", 'w') as f:
                    indexes = np.where(fishes)
                    for i in range(len(indexes[0])):
                        f.write(
                            ', '.join(
                                [f"{dim}={ii[i]:02d}" for dim, ii in zip(fishes.dims, indexes)]
                            ) + '\n'
                        )
                scenda = scenda.where(~fishes, sim[name])
        scenda.attrs.update(sim[name].attrs)
        kindstr = 'multiplicative' if kind == '*' else 'additive'
        scenda.attrs["history"] = update_history(f"Bias-adjusted with {kindstr} {method}", sim)

        scenda.attrs["bias_adjustment"] = (
            f"Bias-adjusted with {kindstr} scaling over the {period.start}-{period.stop} period." + extra
        )
        scen = scen.assign({name: scenda})

    scen.realization.encoding = {}  # not sure why, but numcodecs whines otherwise
    scen.ssp.encoding = {}
    if method == 'DQM':
        out = CONFIG['biasadjust']['output_indices_double_dqm']
    else:
        out = CONFIG['biasadjust']['output_indices_double']
    scen.to_zarr(out)

    logger.info("Spitting netCDFs")
    scen = xr.open_zarr(out)
    cities = xr.open_dataset('geo/cities.nc')
    outpath = Path(CONFIG['indicators']['sim_netcdf'])
    encoding = {'time': {'dtype': 'int32'}}
    for name, var in scen.data_vars.items():
        enc = encoding.copy()
        enc[name] = {'dtype': 'float32'}
        if 'is_dayofyear' in var.attrs:
            var.attrs['is_dayofyear'] = np.int32(var.attrs['is_dayofyear'])
        if 'location' in var.dims:
            var = var.assign_coords(city=cities.city).to_dataset()
            enc['location'] = {'dtype': 'int32'}
        var.attrs = scen.attrs
        var.to_netcdf(outpath / f"cmip6_{method}_{name}_1950-2100.nc", encoding=enc)
