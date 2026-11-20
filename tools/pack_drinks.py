"""Packt die Drehteller-Renderings (turntable.py) als animierte WebP-Kacheln fuers Profil.

Jede Kachel ist ein Fach im Kuehlschrank: dunkler Grund mit Licht von oben, runde Ecken,
das Teil dreht sich einmal pro Durchlauf. Aufruf: python3 tools/pack_drinks.py <render-ordner> <ziel-ordner>
"""
import os
import sys
from PIL import Image, ImageDraw

W, H = 270, 360          # angezeigt mit 180 px Breite, also 1,5-fach scharf
RADIUS = 18
FRAME_MS = 90
TOP, BOTTOM = (38, 42, 48), (17, 19, 22)
SHELF = (64, 70, 78)


def tile_background():
    bg = Image.new("RGBA", (W, H))
    px = bg.load()
    for y in range(H):
        t = y / (H - 1)
        c = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = (*c, 255)
    ImageDraw.Draw(bg).rectangle((0, H - 14, W, H - 12), fill=(*SHELF, 255))
    return bg


def rounded_mask():
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W - 1, H - 1), RADIUS, fill=255)
    return m


def pack(frame_dir, out_path, bg, mask):
    names = sorted(f for f in os.listdir(frame_dir) if f.endswith(".png"))
    if not names:
        raise SystemExit("keine Bilder in " + frame_dir)
    frames = []
    for n in names:
        item = Image.open(os.path.join(frame_dir, n)).convert("RGBA").resize((W, H), Image.LANCZOS)
        f = bg.copy()
        f.alpha_composite(item)
        f.putalpha(mask)
        frames.append(f)
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0,
                   quality=78, method=6, lossless=False)


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    bg, mask = tile_background(), rounded_mask()
    for pid in sorted(os.listdir(src)):
        d = os.path.join(src, pid)
        if os.path.isdir(d):
            out = os.path.join(dst, pid + ".webp")
            pack(d, out, bg, mask)
            print(pid, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
