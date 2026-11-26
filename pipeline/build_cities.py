"""Build cities.json, nation.json and states.json from INSEE RP 2023, revenus, loyers, URSSAF."""
import sys, os, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
import pandas as pd
from common import RAW, R, W, H, write_json, TO_L93

z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
owner = z["owner"].astype(int)
county = z["county"].astype(int)
water = z["water"].astype(int)

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
    if 0 <= row < rows and 0 <= col < cols:
        return row * cols + col, x, y
    return -1, x, y

# --- communes
com = json.load(open(f"{RAW}/communes.json"))
com = {c["code"]: c for c in com if c.get("population")}
print("communes", len(com))

# --- AAV
aav = pd.read_csv(f"{RAW}/aav2020.csv", sep=";", encoding="utf-8-sig", dtype=str)
aav["aav2020"] = aav["aav2020"].str.zfill(3)
aav = aav.set_index("aav2020")
dec = pd.read_csv(f"{RAW}/decomposition_zaav2020.csv", sep=";", encoding="utf-8-sig", dtype=str)
dec["aav2020"] = dec["aav2020"].str.zfill(3)
dec["com2020"] = dec["com2020"].str.zfill(5)
print("aav", len(aav), "decomp", len(dec))

# --- employment (AAV + COM)
act = pd.read_csv(f"{RAW}/act_reduced.csv", sep=";", dtype=str)
act["OBS_VALUE"] = pd.to_numeric(act["OBS_VALUE"], errors="coerce").fillna(0)

def sector_table(df):
    t = df.pivot_table(index="GEO", columns=["EMP_ACTIVITY", "PCS"], values="OBS_VALUE", aggfunc="sum").fillna(0)
    return t

# --- diplomas
dip = pd.read_csv(f"{RAW}/dip_reduced.csv", sep=";", dtype=str)
dip["OBS_VALUE"] = pd.to_numeric(dip["OBS_VALUE"], errors="coerce").fillna(0)
dip_tot = dip[dip.EDUC == "_T"].groupby(["GEO_OBJECT", "GEO"]).OBS_VALUE.sum()
dip_sup = dip[dip.EDUC == "700_RP"].groupby(["GEO_OBJECT", "GEO"]).OBS_VALUE.sum()

# --- income
inc = pd.read_excel(f"{RAW}/revenus.xlsx", sheet_name=0)
inc = inc[inc["Code géographique"].astype(str).str.len() == 5]
inc["code"] = inc["Code géographique"].astype(str).str.zfill(5)
inc_map = dict(zip(inc["code"], pd.to_numeric(inc["[DISP] Médiane (€)"], errors="coerce")))
print("income communes", len(inc_map))

# --- rents
rent = pd.read_csv(f"{RAW}/loyers_app.csv", sep=";", encoding="latin-1", dtype={"INSEE_C": str})
rent["INSEE_C"] = rent["INSEE_C"].str.zfill(5)
rent["loypredm2"] = pd.to_numeric(rent["loypredm2"].astype(str).str.replace(",", "."), errors="coerce")
rent_map = dict(zip(rent["INSEE_C"], rent["loypredm2"]))
print("rent communes", len(rent_map))

# --- unemployment from status file if present
unemp = {}
p = f"{RAW}/act_status.csv"
if os.path.exists(p):
    st = pd.read_csv(p, sep=";", dtype=str)
    st["OBS_VALUE"] = pd.to_numeric(st["OBS_VALUE"], errors="coerce").fillna(0)
    g = st.groupby(["GEO_OBJECT", "GEO", "EMPSTA_ENQ"]).OBS_VALUE.sum().unstack(fill_value=0)
    for (obj, geo), row in g.iterrows():
        occ = row.get("1", 0); cho = row.get("2", 0)
        if occ + cho > 0:
            unemp[(obj, geo)] = cho / (occ + cho)
print("unemployment entries", len(unemp))

# --- aggregate per AAV
rows_out = []
for code, a in aav.iterrows():
    if code == "000":
        continue
    sub = dec[dec.aav2020 == code]
    if not len(sub):
        continue
    pops = [(c, com[c]["population"]) for c in sub.com2020 if c in com]
    if not pops:
        continue
    pop = sum(v for _, v in pops)
    # centre = most populated commune
    centre, _ = max(pops, key=lambda t: t[1])
    c = com[centre]
    lon, lat = c["centre"]["coordinates"]
    cell, xx, yy = cell_of(lon, lat)
    if cell < 0:
        continue
    fp = sorted({cell_of(*com[k]["centre"]["coordinates"])[0] for k, _ in pops} - {-1})
    deps = sorted({k[:2] for k, _ in pops})
    regs = sorted({(com[k].get("codeRegion") or "") for k, _ in pops})
    # income weighted by population
    iv = [(inc_map[k], v) for k, v in pops if k in inc_map and np.isfinite(inc_map.get(k, np.nan))]
    inc_med = (sum(a1 * b1 for a1, b1 in iv) / sum(b1 for _, b1 in iv)) if iv else None
    rv = [(rent_map[k], v) for k, v in pops if k in rent_map and np.isfinite(rent_map.get(k, np.nan))]
    rent_m2 = (sum(a1 * b1 for a1, b1 in rv) / sum(b1 for _, b1 in rv)) if rv else None
    rent_m = rent_m2 * 45 if rent_m2 else None
    # jobs
    jobs = {}
    a_act = act[(act.GEO_OBJECT == "AAV2020") & (act.GEO == code)]
    for sect, key in (("AZ", "agriculture"), ("BE", "manufacturing"), ("FZ", "construction"),
                      ("GU", "professional"), ("OQ", "public_admin")):
        v = a_act[(a_act.EMP_ACTIVITY == sect) & (a_act.PCS == "_T")].OBS_VALUE.sum()
        if v > 0:
            jobs[key] = float(v)
    employed = a_act[(a_act.EMP_ACTIVITY == "_T") & (a_act.PCS == "_T")].OBS_VALUE.sum()
    cadres = a_act[(a_act.EMP_ACTIVITY == "_T") & (a_act.PCS == "3")].OBS_VALUE.sum()
    sup = dip_sup.get(("AAV2020", code), 0)
    tot15 = dip_tot.get(("AAV2020", code), 0)
    ur = unemp.get(("AAV2020", code))
    rows_out.append({
        "id": code, "name": a["lib_aav2020"], "full": f"Aire d'attraction de {a['lib_aav2020']}",
        "states": regs, "counties": deps, "metro": bool(pop > 200000), "capital": code == "001",
        "x": round(xx, 1), "y": round(yy, 1), "cell": cell, "footprint": fp,
        "population": float(pop), "pop2017": float(sub.pop2017_aav2020.iloc[0]), "employed": float(employed),
        "jobs": jobs, "cadres": float(cadres), "graduates": float(sup), "pop15": float(tot15),
        "median_income": float(inc_med) if inc_med else None,
        "median_rent": float(rent_m) if rent_m else None,
        "rent_m2": float(rent_m2) if rent_m2 else None,
        "unemployment": float(ur) if ur is not None else None,
        "centre": centre,
    })

df = pd.DataFrame(rows_out)
print("aires", len(df))
# productivity (k€ per job) calibrated below
prod = {"agriculture": 72, "manufacturing": 108, "construction": 86, "professional": 118, "public_admin": 78}

def gdp_of(j):
    return sum(v * prod.get(k, 100) * 1000 for k, v in j.items())

df["gdp"] = df.jobs.apply(gdp_of)
nat_gdp = df.gdp.sum()
print("gdp total Md€", round(nat_gdp / 1e9, 1))
df["gdp_pc"] = df.gdp / df.population
df["growth"] = (df.population - df.pop2017) / df.pop2017
df["rent_burden"] = df.median_rent * 12 / df.median_income
df["home_value"] = df.median_rent * 12 / 0.045

# yields
df["y_food"] = df.jobs.apply(lambda j: j.get("agriculture", 0))
df["y_prod"] = df.jobs.apply(lambda j: j.get("manufacturing", 0) + j.get("construction", 0))
df["y_gold"] = df.gdp
df["y_sci"] = df.cadres
df["y_cult"] = df.jobs.apply(lambda j: j.get("public_admin", 0))

for col, key in (("population", "population"), ("gdp", "gdp"), ("gdp_pc", "gdp_per_capita"),
                 ("growth", "growth"), ("y_food", "food"), ("y_prod", "production"),
                 ("y_gold", "gold"), ("y_sci", "science"), ("y_cult", "culture")):
    df["r_" + key] = df[col].rank(ascending=False, method="min").astype(int)

cities = []
for _, r in df.iterrows():
    cities.append({
        "id": r.id, "name": r["name"], "full": r.full, "states": r.states, "metro": bool(r.metro),
        "capital": bool(r.capital), "x": float(r.x), "y": float(r.y), "cell": int(r.cell),
        "population": float(r.population),
        "yields": {"food": float(r.y_food), "production": float(r.y_prod), "gold": float(r.y_gold),
                   "science": float(r.y_sci), "culture": float(r.y_cult)},
        "jobs": {k: float(v) for k, v in r.jobs.items()},
        "employed": float(r.employed),
        "median_income": None if pd.isna(r.median_income) else float(r.median_income),
        "median_rent": None if pd.isna(r.median_rent) else float(r.median_rent),
        "home_value": None if pd.isna(r.home_value) else float(r.home_value),
        "unemployment": None if pd.isna(r.unemployment) else float(r.unemployment),
        "rent_burden": None if pd.isna(r.rent_burden) else float(r.rent_burden),
        "gdp": float(r.gdp), "gdp_year": 2023,
        "gdp_by_industry": {k: float(v * prod.get(k, 100) * 1000) for k, v in r.jobs.items()},
        "growth": float(r.growth), "growth_years": [2017, 2023],
        "counties": r.counties,
        "pop_series": {"2017": int(r.pop2017), "2023": int(r.population)},
        "footprint": r.footprint,
        "ranks": {"population": int(r.r_population), "gdp": int(r.r_gdp), "gdp_per_capita": int(r.r_gdp_per_capita),
                  "growth": int(r.r_growth), "food": int(r.r_food), "production": int(r.r_production),
                  "gold": int(r.r_gold), "science": int(r.r_science), "culture": int(r.r_culture)},
        "graduates_share": (float(r.graduates) / float(r.pop15)) if r.pop15 else None,
    })

# peers by population proximity
cities.sort(key=lambda c: -c["population"])
for i, c in enumerate(cities):
    cand = sorted(cities, key=lambda o: abs(math.log(max(o["population"], 1)) - math.log(max(c["population"], 1))))
    c["peers"] = [o["id"] for o in cand if o["id"] != c["id"]][:5]

write_json("cities", cities)

# --- nation
nat_jobs = {}
for k in ("agriculture", "manufacturing", "construction", "professional", "public_admin"):
    nat_jobs[k] = float(df.jobs.apply(lambda j: j.get(k, 0)).sum())
nation = {
    "vintage": "Recensement 2023 (INSEE), revenus 2021, loyers 2025",
    "year": 2023, "gdp_vintage": "estimation emploi × productivité sectorielle, 2023",
    "nation": {
        "population": float(df.population.sum()),
        "yields": {"food": float(df.y_food.sum()), "production": float(df.y_prod.sum()),
                   "gold": float(df.y_gold.sum()), "science": float(df.y_sci.sum()),
                   "culture": float(df.y_cult.sum())},
        "jobs": nat_jobs,
        "industries": {"agriculture": "Agriculture", "manufacturing": "Industrie",
                       "construction": "Construction", "professional": "Services marchands",
                       "public_admin": "Services publics"},
        "employed": float(df.employed.sum()),
        "median_income": float((df.median_income * df.population).sum() / df.population.sum()),
        "median_rent": float((df.median_rent * df.population).sum() / df.population.sum()),
        "home_value": float((df.home_value * df.population).sum() / df.population.sum()),
        "unemployment": float((df.unemployment.fillna(0.073) * df.population).sum() / df.population.sum()),
        "rent_burden": float((df.rent_burden * df.population).sum() / df.population.sum()),
        "gdp": float(df.gdp.sum()), "gdp_year": 2023,
        "gdp_by_industry": {k: float(v * prod.get(k, 100) * 1000) for k, v in nat_jobs.items()},
        "gdp_undisclosed": None, "gdp_estimated": list(nat_jobs.keys()),
        "growth": float((df.population.sum() - df.pop2017.sum()) / df.pop2017.sum()),
        "growth_years": [2017, 2023],
    },
    "industries": {"agriculture": "Agriculture", "manufacturing": "Industrie",
                   "construction": "Construction", "professional": "Services marchands",
                   "public_admin": "Services publics"},
    "yields": [
        {"key": "food", "icon": "y-food", "emoji": "🌾", "label": "Nourriture", "color": "#7fbf3f",
         "unit": "emplois", "industries": ["agriculture"],
         "description": "Emplois dans l'agriculture, la sylviculture et la pêche (INSEE RP 2023, actifs occupés au lieu de résidence)."},
        {"key": "production", "icon": "y-production", "emoji": "⚙️", "label": "Production", "color": "#d9823b",
         "unit": "emplois", "industries": ["manufacturing", "construction"],
         "description": "Emplois dans l'industrie manufacturière et la construction (INSEE RP 2023)."},
        {"key": "gold", "icon": "y-gold", "emoji": "💰", "label": "Or", "color": "#f2c94c",
         "unit": "eur", "industries": [],
         "description": "PIB estimé en euros par an : emplois par grand secteur multipliés par une productivité sectorielle calibrée sur le PIB national. Estimation, pas une donnée BEA."},
        {"key": "science", "icon": "y-science", "emoji": "🔬", "label": "Science", "color": "#5aa9d6",
         "unit": "emplois", "industries": [],
         "description": "Emplois de cadres et professions intellectuelles supérieures (PCS 3), tous secteurs (INSEE RP 2023)."},
        {"key": "culture", "icon": "y-culture", "emoji": "🏛️", "label": "Services publics", "color": "#a97fd6",
         "unit": "emplois", "industries": ["public_admin"],
         "description": "Emplois dans l'administration publique, l'enseignement, la santé et l'action sociale (INSEE RP 2023)."},
    ],
}
write_json("nation", nation)

# --- states (regions)
states = []
reg_names = {}
for c in cities:
    pass
import collections
reg_agg = collections.defaultdict(lambda: {"pop": 0.0, "gdp": 0.0, "emp": 0.0, "jobs": collections.defaultdict(float),
                                           "cells": set(), "cities": []})
for c in cities:
    for rg in c["states"]:
        a = reg_agg[rg]
        a["pop"] += c["population"]; a["gdp"] += c["gdp"]; a["emp"] += c["employed"]
        for k, v in c["jobs"].items():
            a["jobs"][k] += v
        a["cells"].update(c["footprint"])
        a["cities"].append(c["id"])
print("regions", len(reg_agg))
write_json("_states_debug", {k: {"pop": v["pop"], "gdp": v["gdp"]} for k, v in reg_agg.items()})
print("OK cities", len(cities))
