import requests
import pandas as pd
import re
import time

BASE_URL = "http://api.alquran.cloud/v1/surah/"

def count_words(text):
    return len(text.split())

def count_letters(text):
    text = re.sub(r'[\u064B-\u065F]', '', text)
    return len(re.findall(r'[\u0621-\u064A]', text))

data = []

for surah in range(1, 115):
    print("Surah", surah)

    res = requests.get(BASE_URL + str(surah)).json()
    ayahs = res["data"]["ayahs"]

    cum_kata = 0
    cum_huruf = 0

    for ayat in ayahs:
        teks = ayat["text"]

        kata = count_words(teks)
        huruf = count_letters(teks)

        cum_kata += kata
        cum_huruf += huruf

        data.append({
            "surah": surah,
            "ayat": ayat["numberInSurah"],
            "kata": kata,
            "huruf": huruf,
            "cum_kata": cum_kata,
            "cum_huruf": cum_huruf
        })

    time.sleep(0.3)

df = pd.DataFrame(data)
df.to_csv("data/ayah_stats.csv", index=False)

print("✅ ayah_stats.csv siap")