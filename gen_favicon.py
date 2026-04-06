"""
Generate favicon untuk Sistem Monitoring Hafalan Al-Qur'an
Tema: hijau #1B4332 + aksen emas #FFC107
Ikon: buku terbuka (Al-Qur'an) dengan cahaya di atas
"""

from PIL import Image, ImageDraw
import math
import os

OUTPUT_DIR = "app/static/gambar"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Warna tema
C_GREEN  = (27, 67, 50)        # #1B4332
C_GOLD   = (255, 193, 7)       # #FFC107
C_WHITE  = (255, 255, 255)
C_LGREEN = (52, 120, 90)       # highlight

def draw_favicon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    s   = size

    # ── Background: rounded square hijau gelap ──────────────────────────
    r = s // 5   # corner radius
    d.rounded_rectangle([0, 0, s-1, s-1], radius=r, fill=C_GREEN)

    # ── Buku terbuka (Al-Qur'an) ────────────────────────────────────────
    # Dimensi buku
    bw = int(s * 0.72)   # lebar total buku
    bh = int(s * 0.48)   # tinggi buku
    bx = (s - bw) // 2   # left
    by = int(s * 0.40)   # top (agak ke bawah biar ada ruang cahaya)

    # Halaman kiri (sedikit miring)
    pl_pts = [
        (bx,          by + int(bh*0.08)),
        (bx + bw//2,  by),
        (bx + bw//2,  by + bh),
        (bx,          by + bh - int(bh*0.05)),
    ]
    d.polygon(pl_pts, fill=C_WHITE)

    # Halaman kanan (mirror)
    pr_pts = [
        (bx + bw//2,  by),
        (bx + bw,     by + int(bh*0.08)),
        (bx + bw,     by + bh - int(bh*0.05)),
        (bx + bw//2,  by + bh),
    ]
    d.polygon(pr_pts, fill=(235, 250, 242))   # sedikit lebih gelap

    # Garis tengah (binding / punggung buku)
    cx = s // 2
    d.line([(cx, by - 4), (cx, by + bh + 4)], fill=C_GOLD, width=max(3, s//64))

    # Garis baris teks di halaman kiri
    line_color = (180, 210, 195)
    margins = int(bw * 0.06)
    line_gap = bh // 6
    for i in range(1, 5):
        y_line = by + line_gap * i
        x0 = bx + margins
        x1 = cx - margins
        d.line([(x0, y_line), (x1, y_line)], fill=line_color, width=max(1, s//128))

    # Garis baris teks di halaman kanan
    for i in range(1, 5):
        y_line = by + line_gap * i
        x0 = cx + margins
        x1 = bx + bw - margins
        d.line([(x0, y_line), (x1, y_line)], fill=line_color, width=max(1, s//128))

    # ── Bintang / cahaya emas di atas ──────────────────────────────────
    star_cx = s // 2
    star_cy = int(s * 0.22)
    star_r_outer = int(s * 0.13)
    star_r_inner = int(s * 0.055)
    points = 5
    star_pts = []
    for i in range(points * 2):
        angle = math.radians(-90 + i * (360 / (points * 2)))
        r = star_r_outer if i % 2 == 0 else star_r_inner
        x = star_cx + r * math.cos(angle)
        y = star_cy + r * math.sin(angle)
        star_pts.append((x, y))
    d.polygon(star_pts, fill=C_GOLD)

    # Outline tipis emas di pinggir buku
    d.polygon(pl_pts, outline=C_GOLD, width=max(1, s//128))
    d.polygon(pr_pts, outline=C_GOLD, width=max(1, s//128))

    return img


def make_ico(sizes=(256, 128, 64, 48, 32, 16)):
    frames = []
    for sz in sizes:
        img = draw_favicon(sz)
        frames.append(img)

    # Simpan .ico (multi-size)
    ico_path = os.path.join(OUTPUT_DIR, "favicon.ico")
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[1:],
    )
    print(f"✅ favicon.ico  → {ico_path}")

    # Simpan juga PNG 32 & 192 untuk <link rel="icon"> modern
    for sz in (32, 192):
        img = draw_favicon(sz)
        png_path = os.path.join(OUTPUT_DIR, f"favicon-{sz}.png")
        img.save(png_path, "PNG")
        print(f"✅ favicon-{sz}.png → {png_path}")


if __name__ == "__main__":
    make_ico()
    print("🎉 Done!")
