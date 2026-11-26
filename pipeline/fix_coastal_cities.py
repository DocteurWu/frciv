import sys, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
from common import RAW, R, W, H, write_json

z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
water = z["water"].astype(int)
cities = json.load(open(f"{RAW}/../out/data/cities.json"))

def nb(i):
    r, c = i // cols, i % cols
    dd = [(1, 0), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1)] if r % 2 == 0 else [(1, 0), (1, 1), (0, 1), (-1, 0), (0, -1), (1, -1)]
    out = []
    for dc, dr in dd:
        rr, cc = r + dr, c + dc
        if 0 <= rr < rows and 0 <= cc < cols:
            out.append(rr * cols + cc)
    return out

moved = 0
for c in cities:
    if water[c["cell"]] != 1:
        continue
    # nearest land cell by increasing ring search
    best = None
    frontier = [c["cell"]]
    seen = {c["cell"]}
    for _ in range(3):
        nxt = []
        for i in frontier:
            for j in nb(i):
                if j in seen:
                    continue
                seen.add(j)
                if water[j] == 0:
                    best = j
                    break
                nxt.append(j)
            if best is not None:
                break
        if best is not None:
            break
        frontier = nxt
    if best is None:
        continue
    r, cc = best // cols, best % cols
    c["cell"] = best
    c["x"] = round(x0 + W * cc + 0.5 * W * (r & 1), 1)
    c["y"] = round(y0 + H * r, 1)
    moved += 1
print("moved", moved)
write_json("cities", cities)
