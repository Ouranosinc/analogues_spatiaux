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
quality_colors = ['#28a745', '#a9b5e4','#ffc107', '#fd7e14']  # Translated from matplotlib's : ['lightgreen', 'lightyellow', 'bisque', 'lightcoral']

num_realizations = 12  # Number of realization included in the results
max_real = 24

best_analog_mode = 'closestPer'  # closestN or min, see below
analog_modes = ['closestPer','closestN','min','clusterPer']
num_bestanalogs = 10  # for closestN
per_bestanalogs = 1  # for closestPer
analog_modes_desc = {"en":[f"Closest to target within {per_bestanalogs}% of best",
                           f"Closest to target within {num_bestanalogs} of best",
                           f"Best analogue",
                           f"Closest to eachother within {per_bestanalogs} percentile"],
                     "fr":[f"Plus près de la cible dans le meilleur {per_bestanalogs}%",
                           f"Plus près de la cible dans le meilleur {num_bestanalogs}",
                           f"Meilleur analogue",
                           f"Analogues les plus près d'eux-même, dans les meilleurs {per_bestanalogs}%."]}
