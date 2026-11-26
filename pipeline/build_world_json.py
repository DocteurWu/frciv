"""Assemble out/data/world.json from cached grid, elevation and land-cover counts."""
import sys, os, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
import shapely
from shapely.ops import unary_union
from common import RAW, OUT, R, W, H, write_json, load_admin, TO_L93, load_geojson, project_geom

z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
owner = z["owner"].astype(int)
county = z["county"].astype(int)
water = z["water"].astype(int)
frac_fr = z["frac_fr"]
x, y = z["x"], z["y"]
n = cols * rows
elev = np.load(f"{RAW}/world_elev.npz")["elev"].astype(float)

deps, regs = load_admin()
deps = sorted(deps, key=lambda d: d["code"])
regs = sorted(regs, key=lambda r: r["code"])

cov = np.load(f"{RAW}/cover_counts.npz")
counts = cov["counts"].astype(np.float64)
tot = counts[1:].sum(0)
# internal classes: 1 dark forest, 3 mid green, 5 light green, 7 yellow/orange crops, 9 urban, 12 water
pct_forest = (counts[1] + counts[3]) / np.maximum(tot, 1)
pct_crop = counts[7] / np.maximum(tot, 1)
pct_grass = counts[5] / np.maximum(tot, 1)
pct_urban = counts[9] / np.maximum(tot, 1)
pct_wet = counts[12] / np.maximum(tot, 1)
# split the light-green bucket: half pasture, half grassland
pct_pasture = pct_grass * 0.5
pct_grass = pct_grass * 0.5
pct_shrub = np.zeros(n)
s = pct_forest + pct_crop + pct_pasture + pct_grass + pct_urban + pct_wet
s = np.maximum(s, 1e-6)
for k in ("forest", "crop", "pasture", "grass", "urban", "wet"):
    pass

def norm(a):
    return np.round(a / s, 3)

pct = {
    "forest": norm(pct_forest),
    "crop": norm(pct_crop),
    "pasture": norm(pct_pasture),
    "grass": norm(pct_grass),
    "shrub": norm(pct_shrub),
    "wetland": norm(pct_wet),
    "developed": norm(pct_urban),
}

# dominant cover id (table contract)
cover = np.zeros(n, dtype=int)
best = np.zeros(n)
for cid, arr in ((1, pct["forest"]), (7, pct["crop"]), (6, pct["pasture"]), (5, pct["grass"]), (9, pct["developed"]), (8, pct["wetland"])):
    m = arr > best
    best[m] = arr[m]
    cover[m] = cid
cover[(tot == 0)] = 0
cover[(water == 1)] = 0

# relief from local elevation roughness
E = elev.reshape(rows, cols)
rough = np.zeros((rows, cols))
for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
    pass
# neighbour differences using the odd-r layout
def nb(i, d):
    r, c = i // cols, i % cols
    if r % 2 == 0:
        dd = [(1, 0), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1)]
    else:
        dd = [(1, 0), (1, 1), (0, 1), (-1, 0), (0, -1), (1, -1)]
    rr, cc = r + dd[d][1], c + dd[d][0]
    return rr * cols + cc if 0 <= rr < rows and 0 <= cc < cols else -1

relief = np.zeros(n, dtype=int)
for i in range(n):
    if water[i]:
        continue
    vals = [elev[j] for j in (nb(i, k) for k in range(6)) if j >= 0 and not water[j]]
    if len(vals) < 3:
        continue
    rng = max(vals) - min(vals)
    if elev[i] > 2200 or rng > 900:
        relief[i] = 3
    elif rng > 450 or elev[i] > 1200:
        relief[i] = 2
    elif rng > 120:
        relief[i] = 1

elev_max = elev + np.where(relief == 3, 500, np.where(relief == 2, 250, np.where(relief == 1, 60, 10)))

# lakes from Natural Earth
lakes = load_geojson(f"{RAW}/ne_lakes.geojson")["features"]
lake_geoms = []
for f in lakes:
    b = f["geometry"]
    geom = project_geom(b)
    if geom.bounds[2] > 0 and geom.bounds[0] < 1400000 and geom.bounds[3] > 5900000 and geom.bounds[1] < 7300000:
        lake_geoms.append(geom)
if lake_geoms:
    u = unary_union(lake_geoms)
    inside = shapely.contains_xy(u, x * 1000, y * 1000)
    water = np.where((water == 0) & inside, 3, water)
print("lakes", len(lake_geoms), int((water == 3).sum()))

# rivers
rivers = []
riv = load_geojson(f"{RAW}/ne_rivers.geojson")["features"]
for f in riv:
    g = f["geometry"]
    if g["type"] not in ("LineString", "MultiLineString"):
        continue
    geom = project_geom(g)
    if geom.bounds[2] < 0 or geom.bounds[0] > 1400000 or geom.bounds[3] < 5900000 or geom.bounds[1] > 7300000:
        continue
    lines = [geom] if geom.geom_type == "LineString" else list(geom.geoms)
    for ln in lines:
        pts = []
        for px, py in ln.coords:
            kx, ky = px / 1000 - x0, py / 1000 - y0
            if -50 <= kx <= W * cols + 50 and -50 <= ky <= H * rows + 50:
                pts += [round(kx, 1), round(ky, 1)]
        if len(pts) >= 4:
            rivers.append({"name": f["properties"].get("name") or "", "rank": int(f["properties"].get("scalerank") or 6),
                           "pts": pts})
rivers.sort(key=lambda r: (r["rank"], -len(r["pts"])))
rivers = rivers[:45]
print("rivers", len(rivers))

world = {
    "version": 2,
    "grid": {"radius": round(R, 4), "cols": cols, "rows": rows},
    "width": round(W * cols, 1),
    "height": round(H * (rows - 1) + 2 * R, 1),
    "margin": 200.0,
    "owner": owner.tolist(),
    "county": county.tolist(),
    "elev": [round(float(v), 1) for v in elev],
    "elev_max": [round(float(v), 1) for v in elev_max],
    "water": water.astype(int).tolist(),
    "relief": relief.astype(int).tolist(),
    "cover": cover.astype(int).tolist(),
    "pct": {k: v.tolist() for k, v in pct.items()},
    "tables": {
        "water": [
            {"id": 0, "name": "Terre"},
            {"id": 1, "name": "Océan", "color": "#1b4266", "rule": "Mer et eau profonde."},
            {"id": 2, "name": "Côte", "color": "#2d6d97", "rule": "Eau peu profonde proche des terres."},
            {"id": 3, "name": "Lac", "color": "#3a80b0", "rule": "Centre de l'hexagone dans un lac Natural Earth."},
        ],
        "relief": [
            {"id": 0, "name": "Plaine", "rule": "Terrain doux."},
            {"id": 1, "name": "Collines", "rule": "Dénivelé local supérieur à 120 m."},
            {"id": 2, "name": "Montagnes", "rule": "Dénivelé local supérieur à 450 m ou altitude supérieure à 1 200 m."},
            {"id": 3, "name": "Sommets", "rule": "Dénivelé supérieur à 900 m ou altitude supérieure à 2 200 m."},
        ],
        "cover": [
            {"id": 0, "key": "none", "name": "Inconnu"},
            {"id": 1, "key": "forest_deciduous", "name": "Forêt de feuillus", "color": "#4f7a35"},
            {"id": 2, "key": "forest_evergreen", "name": "Forêt de conifères", "color": "#2f5f3a"},
            {"id": 3, "key": "forest_mixed", "name": "Forêt mixte", "color": "#436d36"},
            {"id": 4, "key": "scrub", "name": "Landes et broussailles", "color": "#b8a26a"},
            {"id": 5, "key": "grassland", "name": "Pelouses et prairies naturelles", "color": "#9fb35a"},
            {"id": 6, "key": "pasture", "name": "Prairies agricoles", "color": "#a8b862"},
            {"id": 7, "key": "cropland", "name": "Terres arables", "color": "#c2b65c"},
            {"id": 8, "key": "wetland", "name": "Zones humides", "color": "#4f7f68"},
            {"id": 9, "key": "urban", "name": "Zones artificialisées", "color": "#8c8780"},
            {"id": 10, "key": "barren", "name": "Sols nus", "color": "#b9ab94"},
            {"id": 11, "key": "ice", "name": "Neige et glace", "color": "#e8eef2"},
        ],
        "notes": "Occupation du sol : CORINE Land Cover 2018 (IGN/Copernicus), agrégée par hexagone de 25 km. Altitude : EU-DEM 25 m (opentopodata). Contours : IGN Admin Express via france-geojson.",
    },
    "states": [{"fips": r["code"], "abbr": r["code"], "name": r["name"]} for r in regs],
    "counties": [{"geoid": d["code"], "name": d["name"]} for d in deps],
    "rivers": rivers,
}
write_json("world", world)
print("done", cols * rows)
