"""
Training Decision Tree — Prediksi Kemampuan Hafalan Al-Qur'an

Flow:
1. Ambil hafalan_log dari MySQL
2. Gabung dengan data surah & ayat dari CSV
3. Feature engineering
4. Train Decision Tree
5. Evaluasi model
6. Simpan model ke file
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.tree import DecisionTreeRegressor, export_text
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.database import get_db, load_csv
import app.database as db_module


# ============================
# 1. LOAD DATA
# ============================
print("=" * 50)
print("STEP 1: Load Data")
print("=" * 50)

# Load CSV
load_csv()
surah_df = db_module.SURAH_DF.copy()
ayat_df = db_module.AYAT_DF.copy()

# Load hafalan_log dari MySQL (manual fetch, bukan pd.read_sql)
conn = get_db()
cur = conn.cursor()
cur.execute("SELECT * FROM hafalan_log ORDER BY siswa_id, tanggal")
rows = cur.fetchall()
conn.close()
hafalan_df = pd.DataFrame(rows)

# Cast tipe data
for col in ["id", "siswa_id", "guru_id", "surah_id", "ayat_mulai", "ayat_selesai", "jumlah_ayat"]:
    hafalan_df[col] = hafalan_df[col].astype(int)

print(f"  Hafalan logs : {len(hafalan_df)} rows")
print(f"  Surah        : {len(surah_df)} rows")
print(f"  Ayat         : {len(ayat_df)} rows")


# ============================
# 2. FEATURE ENGINEERING
# ============================
print("\n" + "=" * 50)
print("STEP 2: Feature Engineering")
print("=" * 50)

# --- Fitur dari CSV (per surah) ---
surah_features = surah_df.rename(columns={"nomor_surah": "surah_id"})
surah_features["surah_id"] = surah_features["surah_id"].astype(int)
surah_features = surah_features[["surah_id", "jumlah_ayat", "jumlah_kata", "jumlah_huruf"]]
surah_features.columns = ["surah_id", "total_ayat_surah", "total_kata_surah", "total_huruf_surah"]

# Rata-rata kata & huruf per ayat (per surah) dari ayat CSV
ayat_df["surah"] = ayat_df["surah"].astype(int)
ayat_agg = ayat_df.groupby("surah").agg(
    rata_kata_per_ayat=("kata", "mean"),
    rata_huruf_per_ayat=("huruf", "mean"),
    std_kata_per_ayat=("kata", "std"),
).reset_index().rename(columns={"surah": "surah_id"})
ayat_agg["std_kata_per_ayat"] = ayat_agg["std_kata_per_ayat"].fillna(0)

surah_features = surah_features.merge(ayat_agg, on="surah_id", how="left")

# --- Gabung ke hafalan_log ---
df = hafalan_df.merge(surah_features, on="surah_id", how="left")

# --- Fitur per siswa per surah (rolling/historical) ---
# Sort by siswa + surah + tanggal
df = df.sort_values(["siswa_id", "surah_id", "tanggal"]).reset_index(drop=True)

# Hari ke-berapa siswa ini menghafal surah ini
df["hari_ke"] = df.groupby(["siswa_id", "surah_id"]).cumcount() + 1

# Progress: berapa ayat sudah dihafal sebelum hari ini (cumulative shift)
df["ayat_sudah_dihafal"] = df.groupby(["siswa_id", "surah_id"])["jumlah_ayat"].cumsum().shift(1).fillna(0).astype(int)
df["progress_persen"] = (df["ayat_sudah_dihafal"] / df["total_ayat_surah"] * 100).round(1)

# Kecepatan rata-rata siswa sebelumnya (expanding mean dari semua surah)
df["kecepatan_avg_sebelumnya"] = (
    df.groupby("siswa_id")["jumlah_ayat"]
    .expanding().mean()
    .shift(1)
    .reset_index(level=0, drop=True)
)
# Isi NaN (hari pertama) dengan median keseluruhan
median_speed = df["jumlah_ayat"].median()
df["kecepatan_avg_sebelumnya"] = df["kecepatan_avg_sebelumnya"].fillna(median_speed)

print(f"  Total rows   : {len(df)}")
print(f"  Features     :")

# --- Definisi fitur ---
FEATURES = [
    "total_ayat_surah",         # total ayat dalam surah
    "rata_kata_per_ayat",       # kompleksitas: avg kata per ayat
    "rata_huruf_per_ayat",      # kompleksitas: avg huruf per ayat
    "std_kata_per_ayat",        # variasi panjang ayat dalam surah
    "hari_ke",                  # hari ke-berapa menghafal surah ini
    "ayat_sudah_dihafal",       # berapa ayat sudah dihafal
    "progress_persen",          # progress dalam persen
    "kecepatan_avg_sebelumnya", # avg ayat/hari siswa sebelumnya
]

TARGET = "jumlah_ayat"  # yang diprediksi: berapa ayat dihafal hari itu

for f in FEATURES:
    print(f"    - {f}: {df[f].dtype} (mean={df[f].mean():.2f})")

X = df[FEATURES]
y = df[TARGET]


# ============================
# 3. SPLIT DATA
# ============================
print("\n" + "=" * 50)
print("STEP 3: Train-Test Split")
print("=" * 50)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"  Train: {len(X_train)} rows")
print(f"  Test : {len(X_test)} rows")


# ============================
# 4. TRAIN DECISION TREE
# ============================
print("\n" + "=" * 50)
print("STEP 4: Train Decision Tree")
print("=" * 50)

model = DecisionTreeRegressor(
    max_depth=8,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
)

model.fit(X_train, y_train)

# Feature importance
importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)

print("\n  Feature Importance:")
for _, row in importance.iterrows():
    bar = "█" * int(row["importance"] * 40)
    print(f"    {row['feature']:30s} {row['importance']:.4f} {bar}")


# ============================
# 5. EVALUASI
# ============================
print("\n" + "=" * 50)
print("STEP 5: Evaluasi Model")
print("=" * 50)

y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

metrics = {
    "MAE (train)": mean_absolute_error(y_train, y_pred_train),
    "MAE (test)": mean_absolute_error(y_test, y_pred_test),
    "RMSE (train)": np.sqrt(mean_squared_error(y_train, y_pred_train)),
    "RMSE (test)": np.sqrt(mean_squared_error(y_test, y_pred_test)),
    "R² (train)": r2_score(y_train, y_pred_train),
    "R² (test)": r2_score(y_test, y_pred_test),
}

for name, val in metrics.items():
    print(f"  {name:20s}: {val:.4f}")

print(f"\n  Interpretasi R² test = {metrics['R² (test)']:.4f}:")
r2 = metrics["R² (test)"]
if r2 >= 0.8:
    print("  → Sangat Baik: model menjelaskan >80% variasi data")
elif r2 >= 0.6:
    print("  → Baik: model cukup reliable untuk prediksi")
elif r2 >= 0.4:
    print("  → Cukup: model bisa digunakan dengan catatan")
else:
    print("  → Kurang: model perlu improvement")


# ============================
# 6. SIMPAN MODEL + ARTIFACTS
# ============================
print("\n" + "=" * 50)
print("STEP 6: Simpan Model")
print("=" * 50)

model_path = "models/decision_tree.joblib"
metadata = {
    "features": FEATURES,
    "target": TARGET,
    "metrics": metrics,
    "tree_depth": model.get_depth(),
    "tree_leaves": model.get_n_leaves(),
}

joblib.dump({"model": model, "metadata": metadata}, model_path)
print(f"  Model saved: {model_path}")
print(f"  Tree depth : {model.get_depth()}")
print(f"  Tree leaves: {model.get_n_leaves()}")

# Export tree rules (ringkas)
tree_rules = export_text(model, feature_names=FEATURES, max_depth=3)
with open("models/tree_rules.txt", "w") as f:
    f.write(tree_rules)
print(f"  Rules saved: models/tree_rules.txt")

# Save dataset yang sudah di-engineer (buat referensi)
df.to_csv("data/hafalan_features.csv", index=False)
print(f"  Dataset saved: data/hafalan_features.csv")


# ============================
# 7. VISUALISASI
# ============================
print("\n" + "=" * 50)
print("STEP 7: Generate Visualisasi")
print("=" * 50)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Decision Tree — Evaluasi Model Prediksi Hafalan", fontsize=14, fontweight="bold")

# Plot 1: Actual vs Predicted
ax = axes[0, 0]
ax.scatter(y_test, y_pred_test, alpha=0.5, s=20, color="#2d9b6e")
ax.plot([0, y_test.max()], [0, y_test.max()], "r--", linewidth=1)
ax.set_xlabel("Actual (ayat/hari)")
ax.set_ylabel("Predicted (ayat/hari)")
ax.set_title(f"Actual vs Predicted (R²={metrics['R² (test)']:.3f})")

# Plot 2: Feature Importance
ax = axes[0, 1]
importance_sorted = importance.sort_values("importance")
ax.barh(importance_sorted["feature"], importance_sorted["importance"], color="#2d9b6e")
ax.set_xlabel("Importance")
ax.set_title("Feature Importance")

# Plot 3: Residual Distribution
ax = axes[1, 0]
residuals = y_test - y_pred_test
ax.hist(residuals, bins=20, color="#2d9b6e", edgecolor="white", alpha=0.8)
ax.axvline(0, color="red", linestyle="--")
ax.set_xlabel("Residual (actual - predicted)")
ax.set_ylabel("Count")
ax.set_title(f"Distribusi Error (MAE={metrics['MAE (test)']:.2f})")

# Plot 4: Predicted by Complexity
ax = axes[1, 1]
scatter = ax.scatter(
    df["rata_kata_per_ayat"], df["jumlah_ayat"],
    c=df["kecepatan_avg_sebelumnya"], cmap="RdYlGn", alpha=0.5, s=15
)
plt.colorbar(scatter, ax=ax, label="Kecepatan avg siswa")
ax.set_xlabel("Rata-rata kata per ayat (kompleksitas)")
ax.set_ylabel("Jumlah ayat dihafal/hari")
ax.set_title("Kompleksitas vs Kemampuan Hafalan")

plt.tight_layout()
plt.savefig("models/evaluasi_model.png", dpi=150, bbox_inches="tight")
print(f"  Chart saved: models/evaluasi_model.png")

print("\n" + "=" * 50)
print("SELESAI!")
print("=" * 50)
