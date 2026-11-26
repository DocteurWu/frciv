"""Build world.json: hex grid, land/sea/foreign, regions/departments, elevation, land cover."""
import json, math, os, sys, time
import numpy as np
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(__file__))
from common import (RAW, R, W, H, load_admin, grid_bounds, make_grid, centres,
                    ring_points, write_json, project_geom, load_geojson, TO_WGS)

CACHE = f"{RAW}/world_cache.npz"


def build_masks(force=False):
    deps, regs = load_admin()
    france, xmin, ymin, xmax, ymax = grid_bounds(deps)
    g = make_grid(xmin, ymin, xmax, ymax, pad=2)
    x, y, row, col = centres(g)
    n = len(x)

    # sample points for every cell: shape (n, 19)
    pts = np.array([ring_points(g, i) for i in range(n)])  # n,19,2 (km)
    px, py = pts[:, :, 0].ravel() * 1000, pts[:, :, 1].ravel() * 1000  # metres

    inside_fr = shapely.contains_xy(france, px, py).reshape(n, pts.shape[1])
    frac_fr = inside_fr.mean(1)

    # neighbouring countries (explicit list: antimeridian geometries project absurdly)
    NB = {"Spain", "Italy", "Switzerland", "Belgium", "Luxembourg", "Germany",
          "United Kingdom", "Andorra", "Monaco", "Netherlands"}
    world = load_geojson(f"{RAW}/ne_countries.geojson")["features"]
    neighbours = [f for f in world if f["properties"]["ADMIN"] in NB]
    any_land = inside_fr.copy()
    for f in neighbours:
        geom = project_geom(f["geometry"])
        b = geom.bounds
        if b[2] < xmin * 1000 - 50000 or b[0] > xmax * 1000 + 50000 or b[3] < ymin * 1000 - 50000 or b[1] > ymax * 1000 + 50000:
            continue
        any_land |= shapely.contains_xy(geom, px, py).reshape(n, pts.shape[1])
    frac_any = any_land.mean(1)

    dep_idx = np.full(n, -1, dtype=int)
    dep_pts = np.zeros((len(deps), n), dtype=np.int16)
    for k, d in enumerate(deps):
        m = shapely.contains_xy(d["geom"], px, py).reshape(n, pts.shape[1])
        cnt = m.sum(1)
        dep_pts[k] = cnt
    dep_idx = dep_pts.argmax(0)
    dep_best = dep_pts.max(0)

    reg_idx = np.full(n, -1, dtype=int)
    reg_pts = np.zeros((len(regs), n), dtype=np.int16)
    for k, r in enumerate(regs):
        reg_pts[k] = shapely.contains_xy(r["geom"], px, py).reshape(n, pts.shape[1]).sum(1)
    reg_idx = reg_pts.argmax(0)
    reg_best = reg_pts.max(0)

    water = ((frac_fr < 0.35) & (frac_any < 0.35)).astype(int)
    owner = np.where(water == 1, -1, np.where(frac_fr >= 0.35, reg_idx, -2)).astype(int)
    county = np.where(water == 1, -1, np.where(frac_fr >= 0.35, dep_idx, -1)).astype(int)
    # owner must respect region winner
    land = (water == 0) & (owner >= 0)
    owner[land & (reg_best == 0)] = -2
    county[land & (dep_best == 0)] = -1

    np.savez(CACHE, x=x, y=y, row=row.astype(np.int32), col=col.astype(np.int32),
             frac_fr=frac_fr, frac_any=frac_any, owner=owner, county=county, water=water,
             x0=g["x0"], y0=g["y0"], cols=g["cols"], rows=g["rows"])
    return g, x, y, owner, county, water, frac_fr


def elevation(g, x, y, owner, water, force=False):
    """EU-DEM 25 m elevation at every hex centre, via opentopodata."""
    path = f"{RAW}/elev_cache.json"
    key = f"{g['x0']:.1f},{g['y0']:.1f},{g['cols']},{g['rows']}"
    if os.path.exists(path) and not force:
        c = json.load(open(path))
        if c.get("key") == key:
            return np.array(c["elev"], dtype=float)
    import urllib.request, urllib.parse
    lon, lat = TO_WGS.transform(x * 1000, y * 1000)
    elev = np.full(len(x), -60.0)
    idx = np.where(water == 0)[0]
    out = {}
    B = 100
    for s in range(0, len(idx), B):
        chunk = idx[s:s + B]
        locs = "|".join(f"{lat[i]:.5f},{lon[i]:.5f}" for i in chunk)
        url = "https://api.opentopodata.org/v1/eudem25m?locations=" + urllib.parse.quote(locs)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = json.load(r)
                if data.get("status") == "OK":
                    for i, res in zip(chunk, data["results"]):
                        e = res.get("elevation")
                        out[int(i)] = float(e) if e is not None else 0.0
                    break
                raise RuntimeError(data.get("status"))
            except Exception as e:
                print("retry", s, e)
                time.sleep(3)
        time.sleep(1.05)
    for i, v in out.items():
        elev[i] = v
    # sea: rough depth by distance from coast is overkill; keep a shallow shelf
    elev[water == 1] = np.where(np.abs(elev[water == 1] + 60) < 1, -60, elev[water == 1])
    json.dump({"key": key, "elev": [round(float(v), 1) for v in elev]}, open(path, "w"))
    return elev


if __name__ == "__main__":
    force = "--force" in sys.argv
    if os.path.exists(CACHE) and not force:
        z = np.load(CACHE)
        g = {"x0": float(z["x0"]), "y0": float(z["y0"]), "cols": int(z["cols"]), "rows": int(z["rows"]),
             "radius": R, "W": W, "H": H}
        x, y, owner, county, water, frac_fr = z["x"], z["y"], z["owner"], z["county"], z["water"], z["frac_fr"]
    else:
        g, x, y, owner, county, water, frac_fr = build_masks(force)
    print("grid", g["cols"], "x", g["rows"], "=", g["cols"] * g["rows"], "cells",
          "land", int((water == 0).sum()))
    elev = elevation(g, x, y, owner, water, force="--elev" in sys.argv)
    np.savez(f"{RAW}/world_elev.npz", elev=elev)
    print("elev", float(np.nanmin(elev)), float(np.nanmax(elev)))
