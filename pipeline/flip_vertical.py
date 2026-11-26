"""Flip the whole map vertically: usaciv's engine uses screen coordinates (y down),
our Lambert-93 data uses y up. Permutes every per-cell table and every point."""
import json, math, sys

BASE = "/home/dietpi/frciv/out/data"
W = 25.0
R = 25 / math.sqrt(3)
H = 1.5 * R
SQ3 = math.sqrt(3)

world = json.load(open(f"{BASE}/world.json"))
cols, rows = world["grid"]["cols"], world["grid"]["rows"]
A = H * (rows - 1)

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
    if 0 <= row < rows and 0 <= col < cols:
        return row * cols + col
    return -1

perm = []
for i in range(cols * rows):
    r, c = i // cols, i % cols
    x = W * (c + 0.5 * (r & 1))
    y = H * r
    j = cell_at(x, A - y)
    if j < 0:
        raise SystemExit(f"cell {i} maps outside")
    perm.append(j)
assert sorted(perm) == list(range(cols * rows)), "not a bijection"

def flip(t):
    out = [None] * len(t)
    for i, j in enumerate(perm):
        out[j] = t[i]
    return out

for k in ("owner", "county", "elev", "elev_max", "water", "relief", "cover"):
    world[k] = flip(world[k])
for k in list(world["pct"].keys()):
    world["pct"][k] = flip(world["pct"][k])
for rv in world["rivers"]:
    p = rv["pts"]
    for i in range(1, len(p), 2):
        p[i] = round(A - p[i], 1)
world["height"] = round(world["height"], 1)
json.dump(world, open(f"{BASE}/world.json", "w"), ensure_ascii=False)

cities = json.load(open(f"{BASE}/cities.json"))
for c in cities:
    c["y"] = round(A - c["y"], 1)
    j = cell_at(c["x"], c["y"])
    if j >= 0:
        c["cell"] = j
json.dump(cities, open(f"{BASE}/cities.json", "w"), ensure_ascii=False)

states = json.load(open(f"{BASE}/states.json"))
for s in states:
    s["label"]["y"] = round(A - s["label"]["y"], 1)
json.dump(states, open(f"{BASE}/states.json", "w"), ensure_ascii=False)

lenses = json.load(open(f"{BASE}/lenses.json"))
for l in lenses["lenses"]:
    l["values"] = flip(l["values"])
json.dump(lenses, open(f"{BASE}/lenses.json", "w"), ensure_ascii=False)

print("flipped", cols * rows, "cells; A=", round(A, 2))
