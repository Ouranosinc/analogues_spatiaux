# constants.py
# Colors for the plots. Names colors are listed here: https://matplotlib.org/stable/gallery/color/named_colors.html
# for the dahsboard we use hex codes.
fut_col = '#800080'  # The target city at the target period, purple
hist_col = '#FFFFFF'  # The target city at the reference period
ana_col = '#DAA520'  # The best analog at the reference period, goldenrod

# Thresholds, names and colors for the different quality categories (lists must all be the same length)
quality_thresholds = [1, 5, 10, 100]  # Upper percentile associated with the category (reference distributions only go up to the 20th percentile)
quality_terms_en = ['Excellent', 'Good', 'Average', 'Poor']
quality_terms_fr = ['Excellent','Bon','Moyen','Faible']
#quality_colors = ['#28a745', '#509bdd','#ffc107', '#fd7e14']  # Translated from matplotlib's : ['lightgreen', 'lightyellow', 'bisque', 'lightcoral']
quality_colors = ['#50bb50', '#509bdd','#ffd750', '#fd7e50'] # chosen so the alpha-converted version is always around 0.7

min_density = 10 # minimum density to consider
minpts =   500 # minimum size of search space (closest density priority)
maxpts = 10000 # maximum size of search space

num_realizations = 12  # Number of realization included in the results
max_real = 24

max_na = 5

best_analog_mode = 'min'  # closestN or min, see below
analog_modes = ['closestPer','closestDens','min']
num_bestanalogs = 10  # for closestN
per_bestanalogs = 1  # for closestPer
analog_modes_desc = {"en":[f"Closest to location of target city within {per_bestanalogs} percentile of best analogue",
                           f"Closest to density of target city within {per_bestanalogs} percentile of best analogue",
                           f"Best analogue"],
                     "fr":[f"Plus près de l'emplacement de la ville cible d'au plus {per_bestanalogs} centile du meilleur analogue",
                           f"Plus près de la densité de la ville cible d'au plus {per_bestanalogs} centile du meilleur analogue",
                           f"Meilleur analogue"]}

from pathlib import Path
WRITE_DIR = Path('/notebook_dir/writable-workspace/analogues_spatiaux/')

benchmark_path = WRITE_DIR / Path('benchmark.obj')
density_path = WRITE_DIR /  Path('density.obj')
datavar_path = WRITE_DIR / Path('datavars.json')
cache_path = WRITE_DIR / Path('cache/')
version_path = WRITE_DIR / Path('versions.json')
cities_file = Path('cities_tmp.geojson')