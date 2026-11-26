# frciv — la France comme carte de stratégie

Portage français du projet [usaciv](https://karpathy.ai/usaciv/) d'Andrej Karpathy : la France dessinée
comme une carte 4X, sur une grille hexagonale de 25 km, à partir de données publiques réelles.

**En ligne :** https://frciv.24dw24.duckdns.org/

## Ce qui est dedans

| Couche | Source | Millésime |
|---|---|---|
| Grille, régions, départements | IGN / france-geojson (contours simplifiés) | 2024 |
| Altitude, relief | EU-DEM 25 m via OpenTopoData | v1.1 |
| Occupation du sol | CORINE Land Cover 2018, WMS Géoplateforme (`LANDCOVER.CLC18_FR`) | 2018 |
| Population, emploi, diplômes | INSEE, recensement de la population (API Melodi) | 2023 |
| Revenus médians | FiLoSoFi, diffusion Geoptis | 2021 |
| Loyers d'annonce | Carte des loyers, ministère de la Transition écologique | 2025 |
| Aires d'attraction (villes) | INSEE ZAAV | 2020 |
| Rivières et lacs | Natural Earth 10m | v5 |

Résultat : **2 805 hexagones** (1 044 français, 938 étrangers, 823 en mer), **682 aires d'attraction**
jouables, **13 régions**, **11 filtres** statistiques, **9 sources** documentées dans l'Almanach.

## Les rendements (yields)

Faute de PIB local publié, les rendements sont dérivés de l'emploi réel :

- **Nourriture** = emplois dans l'agriculture, la sylviculture et la pêche ;
- **Production** = emplois dans l'industrie manufacturière + la construction ;
- **Or** = PIB estimé, emplois par secteur × productivité sectorielle calibrée sur le PIB national
  (2 684 Md€ au total, contre ~2 900 Md€ réels) — c'est une **estimation**, pas une donnée officielle ;
- **Science** = emplois de cadres et professions intellectuelles supérieures (PCS 3) ;
- **Services publics** = emplois dans l'administration, l'enseignement, la santé et l'action sociale.

Le vocabulaire de Civilization est conservé, mais le cinquième rendement s'appelle « Services publics »
plutôt que « Culture » : aucune source publique communale ne mesure l'emploi culturel.

## Ce qui manque encore

- **Ressources** : centrales électriques, ports, aéroports, universités, parcs nationaux, bases
  militaires, flux de marchandises — les fichiers `resources.json`, `infrastructure.json`, `wonders.json`,
  `military.json` et `trade.json` ne sont pas produits.
- **Chômage** : la table RP utilisée ne contient que les actifs occupés, donc le taux est affiché « – ».
- Traduction : les boutons « Share » et « Almanac » sont encore en anglais.
- Quelques libellés d'accessibilité et d'aide sont encore en anglais.

## Structure

```
pipeline/          # scripts de construction (Python, venv local)
  common.py            constantes de grille, projection Lambert-93
  build_world.py       masques terre/mer/étranger, owner, relief, cover, rivières
  clc_fetch.py         téléchargement des 4 tuiles WMS CORINE
  build_cover2.py      classification CORINE → classes du moteur
  build_world_json.py  assemblage de world.json
  reduce_insee2.py     réduction des fichiers RP 2023 (activité + diplômes)
  build_cities.py      cities.json, nation.json
  build_states2.py     states.json (agrégats par commune, sans double comptage)
  build_lenses.py      lenses.json (11 filtres par hexagone)
  build_sources.py     sources.json
  fix_coastal_cities.py  replace les villes côtières sur la terre ferme
site-fr/           # le site servi (moteur usaciv + données françaises)
out/data/          # JSON produits
```

## Le moteur

Le front-end est le moteur JavaScript d'usaciv, récupéré depuis le site public et **non modifié
structurellement** : seuls les libellés, le formatage des nombres (euro, virgule décimale) et les
définitions de rendements ont été adaptés. Le pipeline Python de Karpathy n'étant pas publié, tout le
traitement des données françaises a été réécrit ici.

## Relancer le pipeline

```bash
cd /home/dietpi/frciv
.venv/bin/python pipeline/build_world.py
.venv/bin/python pipeline/clc_fetch.py
.venv/bin/python pipeline/build_cover2.py
.venv/bin/python pipeline/build_world_json.py
.venv/bin/python pipeline/reduce_insee2.py      # ~2 min, 943 Mo en entrée
.venv/bin/python pipeline/build_cities.py
.venv/bin/python pipeline/build_states2.py
.venv/bin/python pipeline/build_lenses.py
.venv/bin/python pipeline/build_sources.py
.venv/bin/python pipeline/fix_coastal_cities.py
```

Les sources brutes vont dans `data_raw/` (non versionné : plusieurs centaines de Mo).
