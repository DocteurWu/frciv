import sys, json, math, collections
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
from common import RAW, R, W, H, write_json

world = json.load(open(f"{RAW}/../out/data/world.json"))
cities = json.load(open(f"{RAW}/../out/data/cities.json"))
cols = world["grid"]["cols"]; rows = world["grid"]["rows"]
water = np.array(world["water"]); owner = np.array(world["owner"])
elev = np.array(world["elev"])
pctk = {k: np.array(v) for k, v in world["pct"].items()}
states_meta = world["states"]
x0 = float(np.load(f"{RAW}/world_cache.npz")["x0"]); y0 = float(np.load(f"{RAW}/world_cache.npz")["y0"])

def centre(i):
    r, c = i // cols, i % cols
    return x0 + W * c + 0.5 * W * (r & 1), y0 + H * r

agg = {}
for si, s in enumerate(states_meta):
    k = s["fips"]
    cells = [i for i in range(len(owner)) if owner[i] == si]
    agg[k] = {"cells": cells, "pop": 0.0, "gdp": 0.0, "emp": 0.0, "jobs": collections.defaultdict(float),
              "inc": 0.0, "iw": 0.0, "rent": 0.0, "home": 0.0, "unemp": 0.0, "uw": 0.0, "y": collections.defaultdict(float)}

for c in cities:
    for st in c["states"]:
        if st not in agg:
            continue
        a = agg[st]
        a["pop"] += c["population"]; a["gdp"] += c["gdp"]; a["emp"] += c["employed"]
        for kk, vv in c["jobs"].items():
            a["jobs"][kk] += vv
        if c.get("median_income"):
            a["inc"] += c["median_income"] * c["population"]; a["iw"] += c["population"]
        if c.get("median_rent"):
            a["rent"] += c["median_rent"] * c["population"]
        if c.get("home_value"):
            a["home"] += c["home_value"] * c["population"]
        if c.get("unemployment") is not None:
            a["unemp"] += c["unemployment"] * c["population"]; a["uw"] += c["population"]
        for yk in ("food", "production", "gold", "science", "culture"):
            a["y"][yk] += c["yields"][yk]

out = []
for s in states_meta:
    a = agg[s["fips"]]
    cells = a["cells"]
    if not cells:
        continue
    xs, ys = zip(*[centre(i) for i in cells])
    label = {"x": round(float(np.mean(xs)), 1), "y": round(float(np.mean(ys)), 1), "angle": 0.0,
             "size": round(float(min(90, max(24, 18 + math.sqrt(len(cells)) * 3.2))), 1)}
    land = {k: round(float(np.mean(pctk[k][cells])), 3) for k in pctk}
    pop = a["pop"] or 1
    out.append({
        "fips": s["fips"], "abbr": s["fips"], "name": s["name"], "population": float(a["pop"]),
        "yields": {k: float(v) for k, v in a["y"].items()},
        "jobs": {k: float(v) for k, v in a["jobs"].items()},
        "employed": float(a["emp"]),
        "median_income": float(a["inc"] / a["iw"]) if a["iw"] else None,
        "median_rent": float(a["rent"] / a["iw"]) if a["iw"] else None,
        "home_value": float(a["home"] / a["iw"]) if a["iw"] else None,
        "unemployment": float(a["unemp"] / a["uw"]) if a["uw"] else None,
        "rent_burden": float(a["rent"] * 12 / a["inc"]) if a["inc"] else None,
        "gdp": float(a["gdp"]), "gdp_year": 2023,
        "growth": None, "growth_years": [2017, 2023],
        "label": label, "land": land,
        "cities": len([c for c in cities if s["fips"] in c["states"]]),
    })
    out[-1]["rent_burden"] = float((a["rent"] / a["iw"]) * 12 / (a["inc"] / a["iw"])) if a["iw"] and a["inc"] else None

# ranks
for key, field in (("food", None), ("production", None), ("gold", None), ("science", None), ("culture", None)):
    vals = sorted(out, key=lambda o: -o["yields"][key])
    for i, o in enumerate(vals):
        o.setdefault("ranks", {})[key] = i + 1
write_json("states", out)
print("states", len(out), [(o["name"], round(o["population"] / 1e6, 2)) for o in out])
