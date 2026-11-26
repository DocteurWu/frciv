import sys, os, json, math
sys.path.insert(0, "/home/dietpi/frciv/pipeline")
import numpy as np
from PIL import Image, ImageDraw
from common import R, W, H

z = np.load("/home/dietpi/frciv/data_raw/world_cache.npz")
e = np.load("/home/dietpi/frciv/data_raw/world_elev.npz")["elev"]
cols, rows = int(z["cols"]), int(z["rows"])
x0, y0 = float(z["x0"]), float(z["y0"])
owner, water, county = z["owner"], z["water"], z["county"]
scale = 1.6
xmin, xmax = x0 - W / 2, x0 + W * (cols - 1) + W
ymin, ymax = y0 - R, y0 + H * (rows - 1) + R
img = Image.new("RGB", (int((xmax - xmin) * scale), int((ymax - ymin) * scale)), (10, 25, 45))
d = ImageDraw.Draw(img)
pal = [(200,80,80),(80,160,200),(120,200,120),(220,180,70),(180,120,200),(90,200,180),
       (240,140,90),(150,150,220),(200,200,120),(120,180,90),(210,110,150),(90,140,200),(160,200,140)]
def P(x, y):
    return ((x - xmin) * scale, (ymax - y) * scale)
for i in range(cols * rows):
    r, c = i // cols, i % cols
    cx = x0 + W * c + 0.5 * W * (r & 1)
    cy = y0 + H * r
    pts = [P(cx + R * math.cos(math.radians(60 * k - 30)), cy + R * math.sin(math.radians(60 * k - 30))) for k in range(6)]
    if water[i]:
        col = (26, 60, 100) if e[i] < -20 else (45, 100, 150)
    elif owner[i] == -2:
        col = (60, 70, 80)
    else:
        base = pal[owner[i] % len(pal)]
        t = min(1, max(0, (e[i] + 50) / 1500))
        col = tuple(int(min(255, v * (0.55 + 0.45 * t))) for v in base)
    d.polygon(pts, fill=col, outline=(20, 30, 40))
img.save("/home/dietpi/frciv/out/check_world.png")
print("ok", img.size)
