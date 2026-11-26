import sys, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
from PIL import Image, ImageDraw
from common import R, W, H

w = json.load(open("/home/dietpi/frciv/out/data/world.json"))
cols, rows = w["grid"]["cols"], w["grid"]["rows"]
x0 = float(np.load("/home/dietpi/frciv/data_raw/world_cache.npz")["x0"])
y0 = float(np.load("/home/dietpi/frciv/data_raw/world_cache.npz")["y0"])
cover = w["cover"]; water = w["water"]; relief = w["relief"]; elev = w["elev"]
pct = w["pct"]
COL = {0: (90, 90, 80), 1: (47, 95, 58), 2: (47, 95, 58), 3: (67, 109, 54), 4: (184, 162, 106),
       5: (159, 179, 90), 6: (168, 184, 98), 7: (194, 182, 92), 8: (79, 127, 104), 9: (140, 135, 128),
       10: (185, 171, 148), 11: (232, 238, 242)}
scale = 1.6
xmin, xmax = x0 - W, x0 + W * cols
ymin, ymax = y0 - R, y0 + H * rows
img = Image.new("RGB", (int((xmax - xmin) * scale), int((ymax - ymin) * scale)), (13, 42, 71))
d = ImageDraw.Draw(img)
def P(x, y):
    return ((x - xmin) * scale, (ymax - y) * scale)
for i in range(cols * rows):
    r, c = i // cols, i % cols
    cx = x0 + W * c + 0.5 * W * (r & 1); cy = y0 + H * r
    pts = [P(cx + R * math.cos(math.radians(60 * k - 30)), cy + R * math.sin(math.radians(60 * k - 30))) for k in range(6)]
    if water[i] == 1:
        col = (27, 66, 102) if elev[i] < -40 else (45, 109, 151)
    elif water[i] == 3:
        col = (58, 128, 176)
    else:
        base = COL.get(cover[i], (90, 90, 80))
        shade = 1.0 + max(-0.35, min(0.25, (elev[i] - 200) / 6000))
        if relief[i] >= 2:
            shade *= 0.85
        col = tuple(int(max(0, min(255, v * shade))) for v in base)
    d.polygon(pts, fill=col, outline=(20, 30, 40))
img.save("/home/dietpi/frciv/out/check_cover.png")
print("ok", img.size)
