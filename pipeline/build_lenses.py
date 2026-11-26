"""Build lenses.json: per-hex values from commune-level INSEE data."""
import sys, json, math, os
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
import pandas as pd
from common import RAW, R, W, H, write_json, TO_L93

z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
water = z["water"].astype(int)
owner = z["owner"].astype(int)
n = cols * rows
world = json.load(open(f"{RAW}/../out/data/world.json"))
elev = np.array(world["elev"])
pct = {k: np.array(v) for k, v in world["pct"].items()}

def cell_of(lon, lat):
    X, Y = TO_L93.transform(lon, lat)
    x, y = X / 1000 - x0, Y / 1000 - y0
    q = ((math.sqrt(3) / 3) * x - y / 3) / R
    r = ((2 / 3) * y) / R
    rx, rz = round(q), round(r)
    ry = round(-q - r)
    dx, dy, dz = abs(rx - q), abs(ry - (-q - r)), abs(rz - r)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy <= dz:
        rz = -rx - ry
    row, col = rz, rx + ((rz - (rz & 1)) >> 1)
    return row * cols + col if 0 <= row < rows and 0 <= col < cols else -1

com = {c["code"]: c for c in json.load(open(f"{RAW}/communes.json")) if c.get("population")}
inc = pd.read_excel(f"{RAW}/revenus.xlsx", sheet_name=0)
inc = inc[inc["Code géographique"].astype(str).str.len() == 5]
inc["code"] = inc["Code géographique"].astype(str).str.zfill(5)
inc_map = dict(zip(inc["code"], pd.to_numeric(inc["[DISP] Médiane (€)"], errors="coerce")))

dip = pd.read_csv(f"{RAW}/dip_reduced.csv", sep=";", dtype=str)
dip["OBS_VALUE"] = pd.to_numeric(dip["OBS_VALUE"], errors="coerce").fillna(0)
dipc = dip[dip.GEO_OBJECT == "COM"].groupby(["GEO", "EDUC"]).OBS_VALUE.sum().unstack(fill_value=0)

act = pd.read_csv(f"{RAW}/act_reduced.csv", sep=";", dtype=str)
act["OBS_VALUE"] = pd.to_numeric(act["OBS_VALUE"], errors="coerce").fillna(0)
actc = act[act.GEO_OBJECT == "COM"].pivot_table(index="GEO", columns=["EMP_ACTIVITY", "PCS"],
                                               values="OBS_VALUE", aggfunc="sum", fill_value=0)

# aggregate by cell
N = np.zeros(n); IN = np.zeros(n); IW = np.zeros(n); SUP = np.zeros(n); T15 = np.zeros(n)
AGR = np.zeros(n); IND = np.zeros(n); SER = np.zeros(n); CAD = np.zeros(n); EMP = np.zeros(n)
for code, c in com.items():
    cell = cell_of(*c["centre"]["coordinates"])
    if cell < 0 or water[cell] == 1:
        continue
    p = c["population"]
    N[cell] += p
    v = inc_map.get(code)
    if v is not None and np.isfinite(v):
        IN[cell] += v * p; IW[cell] += p
    if code in dipc.index:
        row = dipc.loc[code]
        SUP[cell] += row.get("700_RP", 0); T15[cell] += row.get("_T", 0)
    if code in actc.index:
        a = actc.loc[code]
        AGR[cell] += float(a.get(("AZ", "_T"), 0))
        IND[cell] += float(a.get(("BE", "_T"), 0))
        SER[cell] += float(a.get(("GU", "_T"), 0)) + float(a.get(("OQ", "_T"), 0))
        CAD[cell] += float(a.get(("_T", "3"), 0))
        EMP[cell] += float(a.get(("_T", "_T"), 0))

income = np.where(IW > 0, IN / np.maximum(IW, 1), np.nan)
grad = np.where(T15 > 0, SUP / np.maximum(T15, 1), np.nan)
area = 541.0 * np.maximum(1 - pct["developed"] * 0.5, 0.2)
dens = np.where(water == 0, N / 541.0, np.nan)
cadre_share = np.where(EMP > 0, CAD / np.maximum(EMP, 1), np.nan)

def lens(id, group, name, icon, emoji, unit, fmt, scale, ramp, higher, src, desc, vals, lo=None, hi=None):
    v = np.array(vals, dtype=float)
    v[water == 1] = np.nan
    ok = v[np.isfinite(v) & (v != 0)]
    if lo is None:
        lo = float(np.percentile(ok, 2)) if len(ok) else 0
    if hi is None:
        hi = float(np.percentile(ok, 98)) if len(ok) else 1
    return {"id": id, "group": group, "name": name, "icon": icon, "emoji": emoji, "unit": unit,
            "format": fmt, "scale": scale, "ramp": ramp, "higher_is": higher, "source": src,
            "description": desc, "values": [None if not np.isfinite(x) else round(float(x), 4) for x in v],
            "domain": [round(lo, 4), round(hi, 4)]}

L = []
L.append(lens("density", "people", "Densité de population", "l-people", "👥", "hab / km²", "int", "log",
              ["#1b1035", "#4b2377", "#9a3b8a", "#e0645e", "#f9b24a", "#fff3a8"], "neutral", "rp2023",
              "Habitants par km². Population communale (INSEE RP 2023) répartie sur l'hexagone de 25 km contenant le chef-lieu.",
              dens, 0.5, 400))
L.append(lens("income", "prosperity", "Revenu médian", "l-income", "💶", "€ / an", "int", "linear",
              ["#2b1b3d", "#5b3a7e", "#9a5f9e", "#d98b6a", "#f2c94c", "#fff6c9"], "higher", "filosofi",
              "Revenu disponible médian par unité de consommation, moyenne des communes de l'hexagone pondérée par la population (FiLoSoFi, Geoptis).",
              income, 14000, 32000))
L.append(lens("graduates", "knowledge", "Diplômés du supérieur", "l-degrees", "🎓", "% des 15+", "pct", "linear",
              ["#1a1a2e", "#33406b", "#4f7fa0", "#79bfb0", "#c9e6a0", "#f6ffd9"], "higher", "rp2023",
              "Part de la population non scolarisée de 15 ans ou plus titulaire d'un diplôme de l'enseignement supérieur (INSEE RP 2023).",
              grad, 0.08, 0.35))
L.append(lens("cadres", "knowledge", "Cadres", "l-briefcase", "💼", "% des emplois", "pct", "linear",
              ["#1b1630", "#3d2a5c", "#6b4a8a", "#a86fa6", "#d9a3a0", "#f7e6d0"], "higher", "rp2023",
              "Part des cadres et professions intellectuelles supérieures dans l'emploi total (INSEE RP 2023).",
              cadre_share, 0.03, 0.18))
L.append(lens("forest", "land", "Forêt", "l-tree", "🌳", "% du sol", "pct", "linear",
              ["#101c14", "#1f3a24", "#356238", "#5c8f4a", "#8fbf62", "#d9edb0"], "neutral", "clc2018",
              "Part de la surface classée forêt par CORINE Land Cover 2018 dans l'hexagone.",
              pct["forest"], 0.02, 0.55))
L.append(lens("cropland", "land", "Terres agricoles", "l-wheat", "🌾", "% du sol", "pct", "linear",
              ["#241d10", "#4a3a1c", "#7f6529", "#b39245", "#dcbf72", "#f7ebb5"], "neutral", "clc2018",
              "Part de la surface en terres arables et cultures permanentes (CORINE Land Cover 2018).",
              pct["crop"], 0.05, 0.8))
L.append(lens("developed", "land", "Zones artificialisées", "l-city", "🏙️", "% du sol", "pct", "linear",
              ["#1a1a1a", "#3a3238", "#5f4f52", "#8a7370", "#b8a094", "#e8dbd2"], "neutral", "clc2018",
              "Part de la surface artificialisée (tissu urbain, zones industrielles, infrastructures) selon CORINE 2018.",
              pct["developed"], 0.005, 0.35))
L.append(lens("elevation", "land", "Altitude", "l-mountain", "⛰️", "m", "int", "linear",
              ["#3b6b3a", "#6f8f4a", "#a89a5c", "#a87f5c", "#9a7a70", "#e8e8e8"], "neutral", "eudem",
              "Altitude du centre de l'hexagone (EU-DEM 25 m).",
              elev, 0, 1800))
L.append(lens("agri_jobs", "prosperity", "Emplois agricoles", "y-food", "🚜", "emplois", "int", "log",
              ["#1c2410", "#3a4a1c", "#5f7a2a", "#8fa845", "#c2d470", "#f0f7c0"], "neutral", "rp2023",
              "Actifs occupés dans l'agriculture, la sylviculture et la pêche, au lieu de résidence (INSEE RP 2023).",
              AGR, 0.5, 300))
L.append(lens("industry_jobs", "prosperity", "Emplois industriels", "y-production", "⚙️", "emplois", "int", "log",
              ["#241408", "#4a2a12", "#7f4a1c", "#b3702f", "#dc9c52", "#f7d9a8"], "neutral", "rp2023",
              "Actifs occupés dans l'industrie manufacturière (INSEE RP 2023).",
              IND, 0.5, 3000))
L.append(lens("services", "prosperity", "Emplois de services", "y-gold", "🛎️", "emplois", "int", "log",
              ["#1a1424", "#33244a", "#553a70", "#7f5a96", "#b08ab8", "#e8d4e0"], "neutral", "rp2023",
              "Actifs occupés dans les services marchands et non marchands (INSEE RP 2023).",
              SER, 5, 20000))

out = {"vintage": "INSEE RP 2023 · FiLoSoFi · CORINE 2018 · EU-DEM", "groups": [
    {"id": "people", "name": "Population"}, {"id": "prosperity", "name": "Économie"},
    {"id": "knowledge", "name": "Savoir"}, {"id": "land", "name": "Territoire"}], "lenses": L}
write_json("lenses", out)
print("lenses", len(L), [(l["id"], l["domain"]) for l in L])
