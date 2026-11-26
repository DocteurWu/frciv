"""states.json aggregated from communes (population, jobs, income) — no double counting."""
import sys, json, math, collections
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
import pandas as pd
from common import RAW, R, W, H, write_json

world = json.load(open(f"{RAW}/../out/data/world.json"))
cols = world["grid"]["cols"]; rows = world["grid"]["rows"]
owner = np.array(world["owner"])
pctk = {k: np.array(v) for k, v in world["pct"].items()}
states_meta = world["states"]
x0 = float(np.load(f"{RAW}/world_cache.npz")["x0"]); y0 = float(np.load(f"{RAW}/world_cache.npz")["y0"])

com = {c["code"]: c for c in json.load(open(f"{RAW}/communes.json")) if c.get("population")}
inc = pd.read_excel(f"{RAW}/revenus.xlsx", sheet_name=0)
inc = inc[inc["Code géographique"].astype(str).str.len() == 5]
inc["code"] = inc["Code géographique"].astype(str).str.zfill(5)
inc_map = dict(zip(inc["code"], pd.to_numeric(inc["[DISP] Médiane (€)"], errors="coerce")))

act = pd.read_csv(f"{RAW}/act_reduced.csv", sep=";", dtype=str)
act["OBS_VALUE"] = pd.to_numeric(act["OBS_VALUE"], errors="coerce").fillna(0)
actc = act[act.GEO_OBJECT == "COM"].pivot_table(index="GEO", columns=["EMP_ACTIVITY", "PCS"],
                                                values="OBS_VALUE", aggfunc="sum", fill_value=0)

prod = {"agriculture": 72, "manufacturing": 108, "construction": 86, "professional": 118, "public_admin": 78}
S = {s["fips"]: {"pop": 0.0, "inc": 0.0, "iw": 0.0, "jobs": collections.defaultdict(float), "emp": 0.0} for s in states_meta}
for code, c in com.items():
    reg = c.get("codeRegion")
    if reg not in S:
        continue
    a = S[reg]
    p = c["population"]
    a["pop"] += p
    v = inc_map.get(code)
    if v is not None and np.isfinite(v):
        a["inc"] += v * p; a["iw"] += p
    if code in actc.index:
        row = actc.loc[code]
        ag = float(row.get(("AZ", "_T"), 0)); ma = float(row.get(("BE", "_T"), 0))
        co = float(row.get(("FZ", "_T"), 0)); pr = float(row.get(("GU", "_T"), 0))
        pu = float(row.get(("OQ", "_T"), 0)); em = float(row.get(("_T", "_T"), 0))
        a["jobs"]["agriculture"] += ag; a["jobs"]["manufacturing"] += ma; a["jobs"]["construction"] += co
        a["jobs"]["professional"] += pr; a["jobs"]["public_admin"] += pu; a["emp"] += em

out = []
for si, s in enumerate(states_meta):
    a = S[s["fips"]]
    cells = [i for i in range(len(owner)) if owner[i] == si]
    if not cells:
        continue
    xs, ys = [], []
    for i in cells:
        r, c = i // cols, i % cols
        xs.append(x0 + W * c + 0.5 * W * (r & 1)); ys.append(y0 + H * r)
    j = dict(a["jobs"])
    gdp = sum(j[k] * prod[k] * 1000 for k in prod)
    out.append({
        "fips": s["fips"], "abbr": s["fips"], "name": s["name"], "population": float(a["pop"]),
        "yields": {"food": j["agriculture"], "production": j["manufacturing"] + j["construction"],
                   "gold": gdp, "science": 0.0, "culture": j["public_admin"]},
        "jobs": j, "employed": a["emp"],
        "median_income": float(a["inc"] / a["iw"]) if a["iw"] else None,
        "median_rent": None, "home_value": None, "unemployment": None, "rent_burden": None,
        "gdp": float(gdp), "gdp_year": 2023, "growth": None, "growth_years": [2017, 2023],
        "label": {"x": round(float(np.mean(xs)), 1), "y": round(float(np.mean(ys)), 1), "angle": 0.0,
                  "size": round(float(min(90, max(24, 18 + math.sqrt(len(cells)) * 3.2))), 1)},
        "land": {k: round(float(np.mean(pctk[k][cells])), 3) for k in pctk},
        "cities": 0,
    })
for key in ("food", "production", "gold", "science", "culture"):
    for i, o in enumerate(sorted(out, key=lambda o: -o["yields"][key])):
        o.setdefault("ranks", {})[key] = i + 1
write_json("states", out)
print("states", len(out), [(o["name"], round(o["population"] / 1e6, 2)) for o in out])
