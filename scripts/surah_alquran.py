import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://qurananalysis.com/analysis/basic-statistics.php?lang=AR"

res = requests.get(URL)
soup = BeautifulSoup(res.text, "html.parser")

# cari semua table
tables = soup.find_all("table")

target_table = None

# cari table yang ada header
for table in tables:
    if "Chapter Index" in table.text:
        target_table = table
        break

rows = target_table.find_all("tr")

data = []

# 🔥 asumsi kemampuan hafalan
KEMAMPUAN_PER_HARI = 50   # kata per hari
KONSISTENSI = 0.8         # 80%

for row in rows[1:]:  # skip header
    cols = row.find_all("td")

    if len(cols) < 5:
        continue

    chapter_index = cols[0].text.strip()
    jumlah_ayat = cols[2].text.strip()
    jumlah_kata = cols[3].text.strip()
    jumlah_huruf = cols[4].text.strip()

    # 🔥 convert ke int
    jumlah_ayat = int(jumlah_ayat)
    jumlah_kata = int(jumlah_kata)
    jumlah_huruf = int(jumlah_huruf)

    # 🔥 LABEL (estimasi hari)
    estimasi_hari = jumlah_kata / (KEMAMPUAN_PER_HARI * KONSISTENSI)

    data.append({
        "nomor_surah": int(chapter_index),
        "jumlah_ayat": jumlah_ayat,
        "jumlah_kata": jumlah_kata,
        "jumlah_huruf": jumlah_huruf,
        "estimasi_hari": round(estimasi_hari, 2)
    })

df = pd.DataFrame(data)

df.to_csv("data/quran_stats.csv", index=False, sep=";", decimal=".")

print("✅ Dataset berhasil disimpan di data/quran_stats.csv")