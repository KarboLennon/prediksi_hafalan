import pandas as pd

df_ayat = pd.read_csv("data/ayah_stats.csv")
df_surah = pd.read_csv("data/quran_stats.csv", sep=";")

result = []

for surah in df_ayat["surah"].unique():

    df_s = df_ayat[df_ayat["surah"] == surah].copy()

    total_api_kata = df_s["cum_kata"].max()
    total_api_huruf = df_s["cum_huruf"].max()

    ref = df_surah[df_surah["nomor_surah"] == surah].iloc[0]

    ratio_kata = ref["jumlah_kata"] / total_api_kata
    ratio_huruf = ref["jumlah_huruf"] / total_api_huruf

    df_s["cum_kata_sync"] = df_s["cum_kata"] * ratio_kata
    df_s["cum_huruf_sync"] = df_s["cum_huruf"] * ratio_huruf

    result.append(df_s)

df_final = pd.concat(result)

df_final["cum_kata_sync"] = df_final["cum_kata_sync"].round().astype(int)
df_final["cum_huruf_sync"] = df_final["cum_huruf_sync"].round().astype(int)

df_final.to_csv("data/ayah_stats_sync.csv", index=False)

print("✅ ayah_stats_sync.csv siap")