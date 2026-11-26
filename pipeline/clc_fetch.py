import sys, os, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
from PIL import Image
import urllib.request, urllib.parse
from common import RAW

z = np.load(f"{RAW}/world_cache.npz")
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
R, W, H = 25 / math.sqrt(3), 25.0, 1.5 * 25 / math.sqrt(3)
xmin = (x0 - W) * 1000
ymin = (y0 - H) * 1000
xmax = (x0 + W * cols) * 1000
ymax = (y0 + H * rows) * 1000
print("bbox m", xmin, ymin, xmax, ymax)

PATH = f"{RAW}/clc_fr.png"
if not os.path.exists(PATH):
    # 4 tiles
    nx, ny = 2, 2
    tw, th = 2200, 2100
    tw, th = 2200, 2100
    full = Image.new("RGB", (tw * nx, th * ny))
    for ty in range(ny):
        for tx in range(nx):
            bx0 = xmin + (xmax - xmin) * tx / nx
            bx1 = xmin + (xmax - xmin) * (tx + 1) / nx
            by0 = ymax - (ymax - ymin) * (ty + 1) / ny
            by1 = ymax - (ymax - ymin) * ty / ny
            q = urllib.parse.urlencode({
                "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
                "LAYERS": "LANDCOVER.CLC18_FR", "STYLES": "", "CRS": "EPSG:2154",
                "BBOX": f"{bx0},{by0},{bx1},{by1}", "WIDTH": tw, "HEIGHT": th, "FORMAT": "image/png"})
            url = "https://data.geopf.fr/wms-r/wms?" + q
            print("tile", tx, ty)
            urllib.request.urlretrieve(url, f"/tmp/clc_{tx}_{ty}.png")
            im = Image.open(f"/tmp/clc_{tx}_{ty}.png").convert("RGB")
            full.paste(im, (tx * tw, ty * th))
    full.save(PATH)
im = Image.open(PATH).convert("RGB")
print("image", im.size)

a = np.asarray(im).reshape(-1, 3)
col, cnt = np.unique(a, axis=0, return_counts=True)
order = np.argsort(-cnt)
print("unique colours", len(col))
for k in order[:40]:
    print(tuple(int(v) for v in col[k]), cnt[k], round(100 * cnt[k] / len(a), 2))
