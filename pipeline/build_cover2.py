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
iw, ih = im.size
xmaxw = x0 + W * cols; ymaxw = y0 + H * rows
kmppx = (xmaxw - xmin) / iw
R3 = np.sqrt(3)
n = cols * rows
counts = np.zeros((13, n), dtype=np.int64)


def classify_row(R_, G_, B_):
    out = np.zeros(R_.shape, dtype=np.int8)
    mx = np.maximum(np.maximum(R_, G_), B_)
    mn = np.minimum(np.minimum(R_, G_), B_)
    sat = mx - mn
    white = (R_ > 250) & (G_ > 250) & (B_ > 250)
    blue = (B_ > R_ + 25) & (B_ > G_ + 10)
    out[blue] = 12
    green = (G_ > R_ + 15) & (G_ > B_ + 15) & ~blue
    out[green & (R_ < 90)] = 1          # dark green -> forest
    out[green & (R_ >= 90) & (R_ < 190)] = 3  # mid green -> mixed forest
    out[green & (R_ >= 190)] = 5        # light green -> grass/pasture
    yellow = (R_ > 170) & (G_ > 170) & (B_ < 175) & ~green & ~blue
    out[yellow] = 7
    orange = (R_ > 170) & (G_ > 70) & (G_ < 195) & (B_ < 120) & ~green & ~yellow & ~blue
    out[orange] = 7
    red = (R_ > 140) & (R_ > G_ + 40) & (R_ > B_ + 40) & ~orange
    out[red] = 9
    purple = (R_ > 120) & (B_ > 120) & (G_ < 170) & ~blue
    out[purple] = 9
    grey = (sat < 45) & (mx > 100) & ~white & ~blue
    out[grey] = 9
    out[white] = 0
    return out


BAND = 200
for y0p in range(0, ih, BAND):
    y1p = min(ih, y0p + BAND)
    band = np.asarray(im.crop((0, y0p, iw, y1p)))
    R_, G_, B_ = band[:, :, 0].astype(np.int16), band[:, :, 1].astype(np.int16), band[:, :, 2].astype(np.int16)
    cls = classify_row(R_, G_, B_)
    yy, xx = np.mgrid[y0p:y1p, 0:iw]
    x = (xmin + xx * kmppx - x0).astype(np.float32)
    y = (ymaxw - yy * (ymaxw - ymin) / ih - y0).astype(np.float32)
    q = ((R3 / 3) * x - y / 3) / R
    r = ((2 / 3) * y) / R
    rx = np.round(q); rz = np.round(r); ry = np.round(-q - r)
    dx = np.abs(rx - q); dy = np.abs(ry - (-q - r)); dz = np.abs(rz - r)
    fixx = (dx > dy) & (dx > dz)
    rx = np.where(fixx, -ry - rz, rx)
    fixz = (~fixx) & (dy <= dz)
    rz = np.where(fixz, -rx - ry, rz)
    row = rz.astype(np.int32)
    col = (rx + ((row - (row & 1)) >> 1)).astype(np.int32)
    ok = (col >= 0) & (col < cols) & (row >= 0) & (row < rows) & (cls > 0)
    idx = (row * cols + col)[ok]
    cf = cls[ok]
    pair = idx.astype(np.int64) * 13 + cf
    counts += np.bincount(pair, minlength=n * 13).reshape(n, 13).T

tot = counts[1:].sum(0)
np.savez(f"{RAW}/cover_counts.npz", counts=counts, tot=tot)
print("cells with cover", int((tot > 0).sum()), "of", n)
print("dominant classes", {int(k): int(v) for k, v in zip(*np.unique(np.argmax(counts, 0), return_counts=True))})
