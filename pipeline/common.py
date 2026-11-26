"""Common helpers: paths, Lambert-93 grid, data loading."""
import json, math, os
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shp_transform, unary_union

ROOT = "/home/dietpi/frciv"
RAW = f"{ROOT}/data_raw"
OUT = f"{ROOT}/out/data"

# 25 km between neighbouring hex centres -> pointy-top hex radius
STEP_KM = 25.0
R = STEP_KM / math.sqrt(3)          # 14.4338
W = math.sqrt(3) * R                # 25.0
H = 1.5 * R                         # 21.6506

TO_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
TO_WGS = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def load_geojson(path):
    return json.load(open(path, encoding="utf-8"))


def project_geom(g):
    return shp_transform(TO_L93.transform, shape(g))


def load_admin():
    """Departments and regions projected to Lambert-93 (metres)."""
    deps = load_geojson(f"{RAW}/departements.geojson")["features"]
    regs = load_geojson(f"{RAW}/regions.geojson")["features"]
    dep_list = []
    for f in deps:
        code = f["properties"]["code"]
        name = f["properties"]["nom"]
        dep_list.append({"code": code, "name": name, "geom": project_geom(f["geometry"])})
    reg_list = []
    for f in regs:
        code = f["properties"]["code"]
        name = f["properties"]["nom"]
        reg_list.append({"code": code, "name": name, "geom": project_geom(f["geometry"])})
    return dep_list, reg_list


def grid_bounds(dep_list):
    u = unary_union([d["geom"] for d in dep_list])
    xmin, ymin, xmax, ymax = u.bounds
    return u, xmin / 1000, ymin / 1000, xmax / 1000, ymax / 1000


def make_grid(xmin, ymin, xmax, ymax, pad=1):
    x0 = math.floor(xmin / W) * W - pad * W
    y0 = math.floor(ymin / H) * H - pad * H
    cols = int(math.ceil((xmax - x0) / W)) + 1 + pad
    rows = int(math.ceil((ymax - y0) / H)) + 1 + pad
    return {"x0": x0, "y0": y0, "cols": cols, "rows": rows, "radius": R, "W": W, "H": H}


def centres(g):
    cols, rows = g["cols"], g["rows"]
    n = cols * rows
    i = np.arange(n)
    r = i // cols
    c = i % cols
    x = g["x0"] + W * c + 0.5 * W * (r & 1)
    y = g["y0"] + H * r
    return x, y, r, c


def ring_points(g, i):
    """Centre plus 18 sample points inside the hex (fractions of R)."""
    r = int(i) // g["cols"]
    c = int(i) % g["cols"]
    cx = g["x0"] + W * c + 0.5 * W * (r & 1)
    cy = g["y0"] + H * r
    pts = [(cx, cy)]
    for frac, k in ((0.55, 6), (0.87, 12)):
        for j in range(k):
            a = 2 * math.pi * j / k + (math.pi / 6 if k == 12 else 0)
            pts.append((cx + R * frac * math.cos(a), cy + R * frac * math.sin(a)))
    return pts


def haversine_km(lon1, lat1, lon2, lat2):
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110.57
    return math.hypot(dx, dy)


def write_json(name, obj):
    os.makedirs(OUT, exist_ok=True)
    p = f"{OUT}/{name}.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print(name, os.path.getsize(p) // 1024, "KB")
