import sys, json, pandas as pd
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
from common import RAW, write_json

cities = json.load(open(f"{RAW}/../out/data/cities.json"))
st = pd.read_csv(f"{RAW}/act_status.csv", sep=";", dtype=str)
st["OBS_VALUE"] = pd.to_numeric(st["OBS_VALUE"], errors="coerce").fillna(0)
g = st.groupby(["GEO_OBJECT", "GEO", "EMPSTA_ENQ"]).OBS_VALUE.sum().unstack(fill_value=0)
u = {}
for (obj, geo), r in g.iterrows():
    occ, cho = r.get("1", 0), r.get("2", 0)
    if occ + cho > 0:
        u[(obj, geo)] = cho / (occ + cho)
n = 0
for c in cities:
    v = u.get(("AAV2020", c["id"]))
    if v is not None:
        c["unemployment"] = round(float(v), 4)
        n += 1
print("patched", n, "of", len(cities))
for c in sorted(cities, key=lambda x: -x["population"])[:5]:
    print(c["name"], c["unemployment"])
write_json("cities", cities)
