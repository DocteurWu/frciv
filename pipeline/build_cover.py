import sys, os, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
from PIL import Image
from common import RAW, write_json

z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
R = 25 / math.sqrt(3); W = 25.0; H = 1.5 * R
xmin = x0 - W; ymin = y0 - H
im = Image.open(f"{RAW}/clc_fr.png").convert("RGB")
arr = np.asarray(im)
ih, iw = arr.shape[:2]
xmaxw = x0 + W * cols; ymaxw = y0 + H * rows
kmppx = (xmaxw - xmin) / iw
print("km/px", kmppx, iw, ih)

R3 = np.sqrt(3)
def cells_of(px_x, px_y):
    """pixel coords -> flat cell index (-1 outside)."""
    x = xmin + px_x * kmppx - x0
    y = ymaxw - px_y * (ymaxw - ymin) / ih - y0
    q = ((R3 / 3) * x - y / 3) / R
    r = ((2 / 3) * y) / R
    rx = np.round(q); rz = np.round(r); ry = np.round(-q - r)
    dx = np.abs(rx - q); dy = np.abs(ry - (-q - r)); dz = np.abs(rz - r)
    fixx = (dx > dy) & (dx > dz)
    rx = np.where(fixx, -ry - rz, rx)
    fixz = (~fixx) & (dy <= dz)
    rz = np.where(fixz, -rx - ry, rz)
    row = rz.astype(int)
    col = (rx + ((row - (row & 1)) >> 1)).astype(int)
    ok = (col >= 0) & (col < cols) & (row >= 0) & (row < rows)
    return np.where(ok, row * cols + col, -1)

def classify(c):
    R_, G_, B_ = c[..., 0].astype(int), c[..., 1].astype(int), c[..., 2].astype(int)
    mx = np.maximum(np.maximum(R_, G_), B_)
    mn = np.minimum(np.minimum(R_, G_), B_)
    sat = mx - mn
    out = np.zeros(c.shape[:2], dtype=np.int8)  # 0 = unclassified
    white = (R_ > 250) & (G_ > 250) & (B_ > 250)
    blue = (B_ > R_ + 25) & (B_ > G_ + 10)
    out[blue] = 12  # water (temporary id)
    green = (G_ > R_ + 15) & (G_ > B_ + 15) & ~blue
    out[green & (G_ < 190)] = 1
    out[green & (G_ >= 190) & (R_ < 150)] = 1
    out[green & (G_ >= 190) & (R_ >= 150)] = 5
    yellow = (R_ > 170) & (G_ > 170) & (B_ < 160) & ~green & ~blue
    out[yellow] = 7
    orange = (R_ > 170) & (G_ > 80) & (G_ < 190) & (B_ < 110) & ~green & ~yellow & ~blue
    out[orange] = 7
    red = (R_ > 140) & (R_ > G_ + 40) & (R_ > B_ + 40) & ~orange
    out[red] = 9
    purple = (R_ > 120) & (B_ > 120) & (G_ < 170) & ~blue
    out[purple] = 9
    grey = (sat < 45) & (mx > 100) & ~white & ~blue
    out[grey] = 9
    brown = (R_ > 100) & (R_ <= 200) & (G_ > 60) & (G_ < 170) & (B_ < 130) & ~green & ~yellow & ~orange & ~red & ~purple & ~grey
    out[brown] = 4
    out[white] = 0
    return out

cls = classify(arr)
print("class counts", {int(k): int(v) for k, v in zip(*np.unique(cls, return_counts=True))})

yy, xx = np.mgrid[0:ih, 0:iw]
idx = cells_of(xx, yy).ravel()
cls_flat = cls.ravel()
valid = (idx >= 0) & (cls_flat > 0)
print("valid px", valid.sum(), "of", idx.size)
n = cols * rows
counts = np.zeros((13, n), dtype=np.int64)
pair = idx[valid].astype(np.int64) * 13 + cls_flat[valid]
b = np.bincount(pair, minlength=n * 13)
counts[:] = b.reshape(n, 13).T

tot = counts[1:].sum(0)
np.savez(f"{RAW}/cover_counts.npz", counts=counts, tot=tot)
print("cells with cover", (tot > 0).sum())
# dominant per cell sample
for name, (lon, lat) in {"Paris": (2.3522, 48.8566), "Fontainebleau": (2.70, 48.40), "Beauce": (1.70, 48.30),
                          "Landes": (0.90, 44.0), "Camargue": (4.40, 43.50), "Alpes": (6.87, 45.90)}.items():
    lonm, latm = lon * 1000, lat * 1000
    # quick: use pyproj
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    X, Y = t.transform(lon, lat)
    ci = cells_of(np.array([(X / 1000 - xmin) / kmppx]), np.array([(ymaxw - Y / 1000) / ((ymaxw - ymin) / ih)]))[0]
    if ci >= 0:
        print(name, ci, counts[:, ci])
