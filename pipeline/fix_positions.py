"""Recompute every city position from its centre commune, in the flipped (screen) frame."""
import json, math, sys
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
from common import RAW, TO_L93
import numpy as np

W = 25.0
R = 25 / math.sqrt(3)
H = 1.5 * R
SQ3 = math.sqrt(3)
z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
A = H * (rows - 1)
world = json.load(open(f"{RAW}/../out/data/world.json"))
water = world["water"]

def cell_at(x, y):
    q = ((SQ3 / 3) * x - y / 3) / R
    r = ((2 / 3) * y) / R
    rx, rz = round(q), round(r)
    ry = round(-q - r)
    dx, dy, dz = abs(rx - q), abs(ry - (-q - r)), abs(rz - r)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy <= dz:
        rz = -rx - ry
    row = int(rz)
    col = int(rx + ((row - (row & 1)) >> 1))
    return row * cols + col if 0 <= row < rows and 0 <= col < cols else -1

def nb(i):
    r, c = i // cols, i % cols
    dd = [(1, 0), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1)] if r % 2 == 0 else [(1, 0), (1, 1), (0, 1), (-1, 0), (0, -1), (1, -1)]
    return [rr * cols + cc for dc, dr in dd for rr, cc in [(r + dr, c + dc)] if 0 <= rr < rows and 0 <= cc < cols]

com = {c["code"]: c for c in json.load(open(f"{RAW}/communes.json"))}
cities = json.load(open(f"{RAW}/../out/data/cities.json"))
moved = 0
for c in cities:
    cc = com.get(c.get("centre"))
    if not cc:
        continue
    lon, lat = cc["centre"]["coordinates"]
    X, Y = TO_L93.transform(lon, lat)
    x = X / 1000 - x0
    y = A - (Y / 1000 - y0)
    i = cell_at(x, y)
    if i < 0:
        continue
    if water[i] == 1:
        best = None
        seen = {i}; frontier = [i]
        for _ in range(3):
            nxt = []
            for j in frontier:
                for k in nb(j):
                    if k in seen: continue
                    seen.add(k)
                    if water[k] == 0:
                        best = k; break
                    nxt.append(k)
                if best is not None: break
            if best is not None: break
            frontier = nxt
        if best is None:
            continue
        i = best; moved += 1
        r, col = divmod(i, cols)
        x = W * (col + 0.5 * (r & 1)); y = H * r
    c["x"] = round(x, 1); c["y"] = round(y, 1); c["cell"] = i
json.dump(cities, open(f"{RAW}/../out/data/cities.json", "w"), ensure_ascii=False)
print("moved", moved, "total", len(cities))
for n in ("Paris", "Marseille - Aix-en-Provence", "Lille (partie française)", "Toulouse", "Brest"):
    v = [c for c in cities if c["name"].startswith(n)]
    if v: print(n, v[0]["y"], v[0]["cell"], "water", water[v[0]["cell"]])
