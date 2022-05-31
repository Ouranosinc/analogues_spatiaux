"""
Bias-adjust : Daily
-------------------
The bias adjustment of the daily timeseries of CMIP6 data.
Based on the ESPO-R5v1 procedure, but there may be some differences.
The initial code for the PCA+EQM (with detrending) is still here, but it did not work.
We recommend against using it.
"""
from dask.diagnostics import ProgressBar
from dask import config as dskconf
import logging
import xarray as xr
import xclim as xc
from xclim.core.calendar import convert_calendar
from xclim.core.units import convert_units_to
from xclim import sdba
from pathlib import Path
from config import load_config, CONFIG
logger = logging.getLogger("workflow")


@xc.units.declare_units(dtr="[temperature]", tasmax="[temperature]")
def _tasmin_from_dtr(dtr: xr.DataArray, tasmax: xr.DataArray):
    """Tasmin computed from DTR and tasmax.

    Tasmin as dtr subtracted from tasmax.

    Parameters
    ----------
    dtr: xr.DataArray
      Daily temperature range
    tasmax: xr.DataArray
      Daily maximal temperature.

    Returns
    -------
    xr.DataArray, [same as tasmax]
         Daily minium temperature
    """
    dtr = xc.units.convert_units_to(dtr, tasmax)
    tasmin = tasmax - dtr
    tasmin.attrs['units'] = tasmax.units
    return tasmin


tasmin_from_dtr = xc.core.indicator.Indicator(
    src_freq="D",
    identifier="tn_from_dtr",
    compute=_tasmin_from_dtr,
    standard_name="air_temperature",
    description="Daily minimal temperature as computed from tasmax and dtr.",
    units='K',
    cell_methods="time: minimum within days",
    var_name='tasmin',
    module='workflow',
    realm='atmos'
)


@xc.units.declare_units(tasmin="[temperature]", tasmax="[temperature]")
def _dtr(tasmin: xr.DataArray, tasmax: xr.DataArray):
    """DTR computed from tasmin and tasmax.

    Dtr as tasmin subtracted from tasmax.

    Parameters
    ----------
    tasmin: xr.DataArray
      Daily minimal temperature.
    tasmax: xr.DataArray
      Daily maximal temperature.

    Returns
    -------
    xr.DataArray, K
         Daily temperature range
    """
    tasmin = xc.units.convert_units_to(tasmin, 'K')
    tasmax = xc.units.convert_units_to(tasmax, 'K')
    dtr = tasmax - tasmin
    dtr.attrs['units'] = "K"
    return dtr


dtr = xc.core.indicator.Indicator(
    src_freq="D",
    identifier="dtr",
    compute=_dtr,
    description="Daily temperature range.",
    units='K',
    cell_methods="time: range within days",
    module='workflow',
    realm='atmos'
)


if __name__ == '__main__':
    load_config('config.yml', 'paths.yml', verbose=True)
    dskconf.set(**CONFIG['dask'])

    with ProgressBar():
        logger.info(f'Opening sim dataset.')
        dsim_raw = xr.open_zarr(CONFIG['biasadjust']['simulations'])
        dsim_raw.lon.load()
        dsim_raw.lat.load()

        if not Path(CONFIG['biasadjust']['reference']).is_dir():
            logger.info('Extracting ref')
            dref_cit = convert_calendar(
                xr.open_zarr(CONFIG['biasadjust']['reference_raw'], drop_variables=['tas']),
                'noleap',
            ).sel(time=slice('1991', '2020')).sel(lat=dsim_raw.lat, lon=dsim_raw.lon)
            dref_cit.chunk({'time': -1, 'location': -1}).to_zarr(CONFIG['biasadjust']['reference'])
        dref_raw = xr.open_zarr(CONFIG['biasadjust']['reference'])
        dref_raw.lon.load()
        dref_raw.lat.load()

        logger.info('Creating dtr, converting units, adding jitter')
        dref = dref_raw.drop_vars('tasmin').assign(
            dtr=sdba.processing.jitter(
                dtr(tasmin=dref_raw.tasmin, tasmax=dref_raw.tasmax),
                lower="0.001 K",
                minimum="0 K"
            ),
            tasmax=convert_units_to(dref_raw.tasmax, 'K'),
            pr=sdba.processing.jitter(
                convert_units_to(dref_raw.pr, 'mm/d'),
                lower="0.01 mm/d",
                minimum="0 mm/d"
            ),
        )
        dsim = dsim_raw.drop_vars('tasmin').assign(
            dtr=sdba.processing.jitter(
                dtr(tasmin=dsim_raw.tasmin, tasmax=dsim_raw.tasmax),
                lower="0.001 K",
                minimum="0 K"
            ),
            tasmax=convert_units_to(dsim_raw.tasmax, 'K'),
            pr=sdba.processing.jitter(
                convert_units_to(dsim_raw.pr, 'mm/d'),
                lower="0.01 mm/d",
                minimum="0 mm/d"
            )
        )

        group = sdba.Grouper('time.dayofyear', window=31)

        if CONFIG['biasadjust']['method'] == 'PCA+EQM':
            logger.info('Transforming to additive space with jitter, stacking.')

            dref_as = dref.assign(
                pr=sdba.processing.to_additive_space(
                    dref.pr,
                    lower_bound="0 mm/d",
                    upper_bound="500 mm/d",
                    trans="logit",
                ),
                dtr=sdba.processing.to_additive_space(
                    dref.dtr,
                    lower_bound="0 K",
                    trans="log",
                ),
            )
            ref = sdba.stack_variables(dref_as).chunk({'time': -1})

            dsim_as = dsim.assign(
                pr=sdba.processing.to_additive_space(
                    dsim.pr,
                    lower_bound="0 mm/d",
                    upper_bound="500 mm/d",
                    trans="logit",
                ),
                dtr=sdba.processing.to_additive_space(
                    dsim.dtr,
                    lower_bound="0 K",
                    trans="log",
                ),
            )
            sim = sdba.stack_variables(dsim_as)
            hist = sim.sel(time=slice("1991", "2020")).chunk({'time': -1})
            sim = sim.chunk({'time': -1})

            logger.info('Normalizing and scaling sim.')
            ref_res, ref_norm = sdba.processing.normalize(ref, group=group, kind="+")
            hist_res, hist_norm = sdba.processing.normalize(hist, group=group, kind="+")
            scaling = sdba.utils.get_correction(hist_norm, ref_norm, kind="+")

            sim_scaled = sdba.utils.apply_correction(
                sim, sdba.utils.broadcast(scaling, sim, group=group), kind="+"
            )

            logger.info('Detrending sim.')
            loess = sdba.detrending.LoessDetrend(group=group, f=0.2, d=0, kind="+", niter=1)
            simfit = loess.fit(sim_scaled)
            sim_res = simfit.detrend(sim_scaled)

            logger.info('PCA - Train')
            with xr.set_options(keep_attrs=True):
                ref_res_std = ref_res / ref_res.std('time')
                histstd = hist_res.std('time')
                hist_res_std = hist_res / histstd
                sim_res_std = sim_res / histstd

            PCA = sdba.adjustment.PrincipalComponents.train(
                ref_res_std, hist_res_std, group=group, crd_dim="multivar", best_orientation="simple"
            )

            logger.info('PCA - Adjust')
            scen1_res_std = PCA.adjust(sim_res_std)
            with xr.set_options(keep_attrs=True):
                scen1_res = scen1_res_std * histstd
            hist2_res = scen1_res.sel(time=slice("1991", "2020"))

            logger.info('EQM - Train')
            EQM = sdba.adjustment.EmpiricalQuantileMapping.train(
                ref_res,
                hist2_res,
                group=group,
                nquantiles=50,
                kind="+",
            )

            logger.info('EQM - Adjust')
            scen2_res = EQM.adjust(scen1_res, interp="nearest", extrapolation="constant")

            logger.info('Retrending, unstacking, transforming to physical space.')
            scen = simfit.retrend(scen2_res)
            dscen_as = sdba.unstack_variables(scen)
            dscen = dscen_as.assign(
                pr=sdba.processing.from_additive_space(dscen_as.pr),
                dtr=sdba.processing.from_additive_space(dscen_as.dtr)
            )
        else:
            dhist = dsim.sel(time=slice("1991", "2020"))

            dscen = xr.Dataset(coords=dsim.coords)
            for var, kind in zip(['tasmax', 'dtr', 'pr'], ['+', '*', '*']):
                logger.info(f'Detrended Quantile Mapping - {var} ({kind}) - Train')
                dqm = sdba.DetrendedQuantileMapping.train(
                    dref[var],
                    dhist[var],
                    nquantiles=50,
                    group=group,
                    kind=kind
                )

                logger.info(f'Detrended Quantile Mapping - {var} ({kind}) - Adjust')
                detrend = sdba.detrending.LoessDetrend(
                    group=group, f=0.2, d=0, kind=kind, weights='tricube', niter=1
                )
                # detrend = sdba.detrending.RollingMeanDetrend(group=group, kind=kind, win=30, min_periods=1)
                scen = dqm.adjust(
                    dsim[var], interp='nearest', extrapolation='constant', detrend=detrend
                )
                dscen = dscen.assign({var: scen})

        logger.info('Computing tasmin, adding attributes, flushing to file.')
        dscen_final = dscen.drop_vars('dtr').assign(
            tasmin=tasmin_from_dtr(dtr=dscen.dtr, tasmax=dscen.tasmax)
        )
        dscen_final.attrs.update(CONFIG['biasadjust']['attrs_single']['global'])
        dscen_final.tasmax.attrs.update(CONFIG['biasadjust']['attrs_single']['tasmax'])
        dscen_final.tasmin.attrs.update(CONFIG['biasadjust']['attrs_single']['tasmin'])
        dscen_final.pr.attrs.update(CONFIG['biasadjust']['attrs_single']['pr'])

        outpath = Path(CONFIG['biasadjust']['output'])
        dscen_final.to_zarr(outpath)
        logger.info('Everything done.')
