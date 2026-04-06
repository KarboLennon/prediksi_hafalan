"""Preview favicon semua ukuran dalam satu grid PNG"""
from PIL import Image
import os

sizes = [256, 128, 64, 48, 32, 16]
imgs = [Image.open(f"app/static/gambar/favicon.ico").resize((s, s), Image.LANCZOS)
        for s in sizes]

# Buat canvas preview: tiap favicon berdampingan dengan padding
pad = 10
total_w = sum(s + pad*2 for s in sizes)
total_h = max(sizes) + pad*2
canvas = Image.new("RGBA", (total_w, total_h), (245, 245, 245, 255))

x = 0
for img, s in zip(imgs, sizes):
    # Tempel di tengah vertikal
    y = pad + (max(sizes) - s) // 2
    canvas.paste(img, (x + pad, y), img)
    x += s + pad*2

canvas.save("favicon_preview.png")
print("✅ Tersimpan: favicon_preview.png")
