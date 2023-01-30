# constants.py
# Colors for the plots. Names colors are listed here: https://matplotlib.org/stable/gallery/color/named_colors.html
# for the dahsboard we use hex codes.
fut_col = '#800080'  # The target city at the target period, purple
hist_col = '#FFFFFF'  # The target city at the reference period
ana_col = '#DAA520'  # The best analog at the reference period, goldenrod

# Thresholds, names and colors for the different quality categories (lists must all be the same length)
quality_thresholds = [1, 5, 10, 100]  # Upper percentile associated with the category (reference distributions only go up to the 20th percentile)
quality_terms = ['Excellent', 'Good', 'Average', 'Poor']
quality_colors = ['#90EE90', '#FFFFE0', '#FFE4C4', '#F08080']  # Translated from matplotlib's : ['lightgreen', 'lightyellow', 'bisque', 'lightcoral']

num_realizations = 12  # Number of realization included in the results
best_analog_mode = 'closestPer'  # closestN or min, see below
num_bestanalogs = 10  # for closestN
per_bestanalogs = 1  # for closestPer
