## Comment interpréter les résultats

__Information sommaire__:

- __Choix d'analogue__: Au-dessus de la carte, il y a jusqu'à 12 pastilles, chacun représentant un analogue provenant d'une seule simulation de modèle climatique.
Par défaut, ces pastilles sont classées en ordre croissant basé sur une balance entre la qualité de chaque analogue, et la représentativité de chaque simulation
(voir le score de représentativité ci-dessous). La couleur des pastilles représente la qualité de chaque analogue,
vert étant un excellent analogue, le bleu un bon analogue et le jaune un analogue moyen. 

- __Carte__: La carte montre tous les analogues comme points liés à la ville ciblée (étoile mauve).
Comme décrit ci-dessus, la couleur de chaque point représente la qualité de l'analogue, le vert indiquant un analogue excellent, le bleu un analogue bon et le jaune un analogue moyen. 

- __Qualité de l'analogue__: Ce score indique dans quelle mesure les conditions actuelles à l'emplacement de l'analogue correspondent aux conditions projetées de la ville cible pour
les indices climatiques choisis, par rapport à tous les autres emplacements possibles. Par exemple, si le score de qualité se situe dans le 10e percentile,
il y a une chance de 10% qu’un autre point, choisi au hazard dans l’Amérique du Nord, sera un meilleur analogue.
Les détails du calcul de ce score de qualité sont donnés dans le rapport téléchargeable au bas de cette page. 

- __Score de représentativité__: Il s'agit d'une mesure de l'alignement de l'analogue d'un modèle climatique particulier sur la moyenne de tous les modèles climatiques de l'ensemble.
Plus ce score est faible, plus le modèle est proche de la moyenne de l'ensemble. Il est toutefois possible qu'un analogue médiocre ait un score de représentativité élevé,
car cette mesure est indépendante de la qualité de l'analogue.

- __Tableau sommaire__: Ce tableau présente de l'information sommaire pour l'analogue choisi, incluant la densité de population et la distance, en kilomètres, à la ville cible.

- __Exportation__: Cette section permet le téléchargement des données des analogues dans une variété de formats, incluant en _comma-separated values_ (.csv) ou en NetCDF (.nc).

__Indices climatiques__: Au bas de la carte, chaque indice climatique sélectionné génère trois graphiques lorsque cliqué dessu: (1) La comparaison des distributions, (2) le changement moyen, et (3) la série temporelle complète. Des informations sur la qualité de l’analogie pour chacun de ces indices est également disponible. 

- __Comparaison des distributions__: Ce graphique montre la distribution de probabilité de l'indice climatique dans le présent (blanc avec zône hachurée mauve)
et dans le futur pour la ville ciblée (mauve), ainsi que la distribution de l'analogue dans le présent (jaune).
Notez que la couleur de la distribution actuelle de l'analogue change en fonction de la qualité globale de l'analogue, c'est-à-dire que le vert indique un excellent analogue,
le bleu un bon analogue et le jaune un analogue moyen. Cela peut vous aider à décider si l'analogue est approprié ou non. 

- __Changement moyen__: Ce graphique montre l'évolution moyenne de l'indice climatique considéré, ainsi que les 10, 25, 75 et 90e centiles.
L'étoile blanche indique la valeur actuelle de la ville cible pour l'indice climatique indiqué, l'étoile violette indique la valeur future de la ville cible et le cercle coloré la valeur actuelle de l'analogue.

- __Série temporelle complète__: Ce graphique montre la série chronologique complète de l'indice climatique (violet) pour l'analogue choisi pour la ville cible.
Les valeurs actuelles pour la ville analogue (colorées en fonction de la qualité de l'analogue) sont également représentées sur la période future pour faciliter la comparaison.
Enfin, la médiane et la gamme (10e à 90e percentile) de l'ensemble des modèles climatiques sont indiquées en gris. 
