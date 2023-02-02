"""
Analog  quantiles
-----------------
Monte-carlo algorithm to approximate the distributions the dissimilarity score for each
combination of indices. Distributions are saved through their percentiles.
"""
import dask
from dask.diagnostics import ProgressBar
from itertools import combinations
import logging
from multiprocessing import Pool
import numpy as np
import pandas as pd
import xarray as xr
from xclim import analog as xa
from config import CONFIG, load_config
logger = logging.getLogger('workflow')
ProgressBar().register()
load_config('config.yml', 'paths.yml', verbose=True)


def comb(n, k):
    return np.math.factorial(n) / (np.math.factorial(k) * np.math.factorial(n - k))


def stack_drop_nans(ds, mask):
    """Stack dimensions into a single axis and drops indexes where the mask is false."""
    mask_1d = mask.stack({'site': mask.dims})
    return ds.stack({'site': mask.dims}).where(mask_1d, drop=True).reset_index('site')


def zech_aslan(inputs):
    return xa.zech_aslan(inputs[0], inputs[1])


def iter_arrays(arr1, arr2):
    for i in range(arr1.shape[0]):
        yield arr1[i, ...], arr2[i, ...]


if __name__ == '__main__':
    Nc = CONFIG['analog_quantiles']['num_couples']
    dmin = CONFIG['analog_quantiles']['min_density']
    chnk = CONFIG['analog_quantiles']['chunksize']
    quantiles = np.arange(*CONFIG['analog_quantiles']['quantiles'])

    dask.config.set(**CONFIG['dask'])

    logger.info('Opening reference indices.')
    dref = xr.open_zarr(
        CONFIG['biasadjust']['reference_indices'], decode_timedelta=False
    ).sel(time=slice('1991', '2020'))

    masks = xr.open_zarr(CONFIG['project']['masks'])
    density = masks.dens_adj.sel(year=2020).where(
        masks.roi & dref.isel(time=0).notnull().to_array().all('variable')
    )

    logger.info(f'Loading data for places with density higher than {dmin}.')
    ref = stack_drop_nans(dref, (density > dmin)).drop_vars(['year', 'lat', 'lon'])
    ref = ref.to_array('indices').transpose('site', 'time', 'indices')
    ref = ref.load()

    # Sort to ensure alphabetical order and thus consistent index in the final df.
    allindices = list(sorted(ref.indices.values))
    NperI = [comb(len(allindices), i) for i in range(1, 5)]
    Ntot = sum(NperI)
    out = {}
    with Pool(CONFIG['dask']['num_workers']) as p:
        for i in range(1, 5):
            for j, indices in enumerate(combinations(allindices, i)):
                n = sum(NperI[: i - 1]) + j + 1
                logger.info(f'Computing quantiles for {indices} - ({n} of {Ntot:.0f}, {n / Ntot:.0%})')

                logger.info(f'  Computing dissimilarity for {Nc} random couples.')
                tgt = ref.sel(indices=list(indices)).isel(site=np.random.randint(0, ref.site.size, size=(Nc,))).values
                cnd = ref.sel(indices=list(indices)).isel(site=np.random.randint(0, ref.site.size, size=(Nc,))).values

                diss = np.array(list(
                    p.imap_unordered(zech_aslan, iter_arrays(tgt, cnd), chunksize=chnk)
                ))
                out['_'.join(indices)] = list(np.nanquantile(diss, q=quantiles))

    df = pd.DataFrame.from_dict(out, orient='index', columns=[f"p{q * 100:02.0f}" for q in quantiles])
    df.to_csv('analog_quantiles.csv')

    benchmark = xr.DataArray(
        (df := pd.read_csv('analog_quantiles.csv', index_col=0)).to_numpy(),
        dims=('indices', 'percentiles'),
        coords={'indices': df.index, 'percentiles': [int(p[1:]) for p in df.columns]},
        name='benchmark',
        attrs={
            'long_name': 'Percentiles of the Zech-Aslan score distribution',
            'description': (
                "Percentiles of a Zech-Aslan score distribution generated from "
                f"{Nc} random couples within the reference indices (1991-2020)"
                " including only urban areas (population densities higher than 10 hab/km²)"
            ),
            'units': ''
        }
    ).to_dataset()
    benchmark.attrs = {
        'title': 'Benchmark distributions of Zech-Aslan scores for the Spatial Analogs project',
        'title_fr': 'Distribution de comparaison de scores Zech-Aslan pour le projet Analogues Spatiaux',
        'contact': 'bourgault.pascal@ouranos.ca'
    }
    benchmark.to_netcdf(
        CONFIG['analog_quantiles']['output'],
        encoding={'percentiles': {'dtype': 'int32'}}
    )
