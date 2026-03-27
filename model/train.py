"""
train.py — Prediksi Kecepatan Hafalan (ayat/hari) dengan Random Forest
=======================================================================
Alur:
  1. Target: jumlah_ayat (kecepatan hafalan per setoran)
  2. Model: RandomForestRegressor
  3. Estimasi hari selesai = sisa_ayat / prediksi_kecepatan
  4. Semua fitur berbasis masa lalu (no leakage)

Kenapa Random Forest?
  - Menangkap hubungan non-linear antar fitur (misal: siswa cepat di surah
    pendek tapi lambat di surah panjang)
  - Robust terhadap outlier dan skala fitur (tidak perlu StandardScaler)
  - Feature importance bawaan — langsung bisa lihat fitur mana yang paling
    berpengaruh terhadap prediksi kecepatan
  - Dengan parameter konservatif (max_depth, min_samples_leaf), cukup tahan
    overfit di dataset kecil (~600 rows)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.metrics import mean_absolute_error, r2_score

from app.database import get_db, load_csv
import app.database as db_module


# ============================================================
# 1. LOAD DATA
# ============================================================
print("=" * 60)
print("STEP 1: Load Data")
print("=" * 60)

load_csv()
surah_df = db_module.SURAH_DF.copy()
ayat_df  = db_module.AYAT_DF.copy()

conn = get_db()
cur  = conn.cursor()
cur.execute("SELECT * FROM hafalan_log ORDER BY siswa_id, tanggal")
rows = cur.fetchall()
conn.close()

hafalan_df = pd.DataFrame(rows)
for col in ["id", "siswa_id", "guru_id", "surah_id", "ayat_mulai", "ayat_selesai", "jumlah_ayat"]:
    hafalan_df[col] = hafalan_df[col].astype(int)
hafalan_df["tanggal"] = pd.to_datetime(hafalan_df["tanggal"])

print(f"  Rows    : {len(hafalan_df)}")
print(f"  Siswa   : {hafalan_df['siswa_id'].nunique()}")
print(f"  Surah   : {hafalan_df['surah_id'].nunique()}")
print(f"  Rentang : {hafalan_df['tanggal'].min().date()} → {hafalan_df['tanggal'].max().date()}")
print(f"  Target  : μ={hafalan_df['jumlah_ayat'].mean():.2f}, σ={hafalan_df['jumlah_ayat'].std():.2f}")


# ============================================================
# 2. FITUR SURAH (statis, dari CSV)
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: Fitur Surah")
print("=" * 60)

surah_features = surah_df.rename(columns={"nomor_surah": "surah_id"})
surah_features["surah_id"] = surah_features["surah_id"].astype(int)
surah_features = surah_features[["surah_id", "jumlah_ayat"]]
surah_features.columns = ["surah_id", "total_ayat_surah"]

ayat_df["surah"] = ayat_df["surah"].astype(int)
ayat_agg = ayat_df.groupby("surah").agg(
    rata_kata_per_ayat  = ("kata", "mean"),
    rata_huruf_per_ayat = ("huruf", "mean"),
).reset_index().rename(columns={"surah": "surah_id"})

surah_features = surah_features.merge(ayat_agg, on="surah_id", how="left")
df = hafalan_df.merge(surah_features, on="surah_id", how="left")

print(f"  Fitur surah: total_ayat_surah, rata_kata_per_ayat, rata_huruf_per_ayat")


# ============================================================
# 3. FEATURE ENGINEERING
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: Feature Engineering")
print("=" * 60)

df = df.sort_values(["siswa_id", "tanggal"]).reset_index(drop=True)
global_median = df["jumlah_ayat"].median()

# 3a. Progress per surah
df["hari_ke"] = df.groupby(["siswa_id", "surah_id"]).cumcount() + 1

df["ayat_sudah_dihafal"] = (
    df.groupby(["siswa_id", "surah_id"])["jumlah_ayat"]
    .apply(lambda x: x.cumsum().shift(1).fillna(0))
    .reset_index(level=[0, 1], drop=True)
    .astype(int)
)
df["progress_persen"] = (
    df["ayat_sudah_dihafal"] / df["total_ayat_surah"] * 100
).round(1).clip(0, 100)

# 3b. Kecepatan rata-rata sebelumnya (expanding mean, shifted)
df["kecepatan_avg_sebelumnya"] = (
    df.groupby("siswa_id")["jumlah_ayat"]
    .expanding().mean().shift(1)
    .reset_index(level=0, drop=True)
    .fillna(global_median)
)

# 3c. Lag features: jumlah ayat pada 1/2/3 setoran sebelumnya
for i in [1, 2, 3]:
    df[f"lag_{i}"] = (
        df.groupby("siswa_id")["jumlah_ayat"]
        .shift(i)
        .fillna(global_median)
    )

# 3d. Rolling mean 3 setoran terakhir (shifted)
df["rolling_mean_3"] = (
    df.groupby("siswa_id")["jumlah_ayat"]
    .apply(lambda g: g.rolling(window=3, min_periods=1).mean().shift(1))
    .reset_index(level=0, drop=True)
    .fillna(global_median)
)

# 3e. Total setoran sebelumnya (pengalaman siswa)
df["total_setoran_sebelumnya"] = df.groupby("siswa_id").cumcount()

print(f"  Fitur temporal:")
print(f"    - hari_ke, ayat_sudah_dihafal, progress_persen")
print(f"    - kecepatan_avg_sebelumnya")
print(f"    - lag_1, lag_2, lag_3, rolling_mean_3")
print(f"    - total_setoran_sebelumnya")
print(f"  Total rows: {len(df)}")


# ============================================================
# 4. DEFINISI FITUR
# ============================================================
FEATURES = [
    # Karakteristik surah
    "total_ayat_surah",
    "rata_kata_per_ayat",
    "rata_huruf_per_ayat",

    # Progress di surah ini
    "hari_ke",
    "ayat_sudah_dihafal",
    "progress_persen",

    # Riwayat kecepatan siswa
    "kecepatan_avg_sebelumnya",
    "lag_1",
    "lag_2",
    "lag_3",
    "rolling_mean_3",
    "total_setoran_sebelumnya",
]

TARGET = "jumlah_ayat"

print(f"\n  Fitur yang digunakan ({len(FEATURES)}):")
for f in FEATURES:
    print(f"    - {f}")


# ============================================================
# 5. TIME-BASED SPLIT
# ============================================================
print("\n" + "=" * 60)
print("STEP 4: Time-Based Split (80/20)")
print("=" * 60)

df_sorted = df.sort_values("tanggal").reset_index(drop=True)

cutoff_idx  = int(len(df_sorted) * 0.8)
cutoff_date = df_sorted.iloc[cutoff_idx]["tanggal"]

train_df = df_sorted[df_sorted["tanggal"] <= cutoff_date].copy()
test_df  = df_sorted[df_sorted["tanggal"] >  cutoff_date].copy()

print(f"  Cutoff : {cutoff_date.date()}")
print(f"  Train  : {len(train_df)} rows ({train_df['tanggal'].min().date()} → {train_df['tanggal'].max().date()})")
print(f"  Test   : {len(test_df)} rows ({test_df['tanggal'].min().date()} → {test_df['tanggal'].max().date()})")

train_mean = train_df[TARGET].mean()
test_mean  = test_df[TARGET].mean()
shift_pct  = abs(train_mean - test_mean) / train_mean * 100
print(f"\n  Distribution: train μ={train_mean:.2f}, test μ={test_mean:.2f} (shift {shift_pct:.1f}%)")

X_train = train_df[FEATURES]
y_train = train_df[TARGET]
X_test  = test_df[FEATURES]
y_test  = test_df[TARGET]


# ============================================================
# 6. TRAIN MODEL
# ============================================================
print("\n" + "=" * 60)
print("STEP 5: Train Random Forest")
print("=" * 60)

# Parameter konservatif untuk dataset kecil:
#   max_depth=8    → batasi kedalaman agar tidak overfit
#   min_samples_leaf=5 → setiap leaf minimal 5 sampel
#   n_estimators=200   → cukup banyak tree untuk stabilitas
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1,
)

model.fit(X_train, y_train)

# Evaluasi train & test
pred_train = model.predict(X_train)
pred_test  = model.predict(X_test)

mae_train = mean_absolute_error(y_train, pred_train)
r2_train  = r2_score(y_train, pred_train)
mae_test  = mean_absolute_error(y_test, pred_test)
r2_test   = r2_score(y_test, pred_test)

print(f"\n  Train — MAE={mae_train:.3f}, R²={r2_train:.4f}")
print(f"  Test  — MAE={mae_test:.3f}, R²={r2_test:.4f}")

# Cross-validation (TimeSeriesSplit)
tscv = TimeSeriesSplit(n_splits=5)
cv = cross_validate(
    model, df_sorted[FEATURES], df_sorted[TARGET],
    cv=tscv, scoring=["neg_mean_absolute_error", "r2"],
)
cv_mae = -cv["test_neg_mean_absolute_error"]
cv_r2  = cv["test_r2"]
print(f"\n  Cross-Validation (TimeSeriesSplit, 5 folds):")
print(f"    MAE = {cv_mae.mean():.3f} ± {cv_mae.std():.3f}")
print(f"    R²  = {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")


# ============================================================
# 7. FEATURE IMPORTANCE
# ============================================================
print("\n" + "=" * 60)
print("STEP 6: Feature Importance")
print("=" * 60)

importance_df = pd.DataFrame({
    "fitur": FEATURES,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)

print(f"\n  {'Fitur':35s}  {'Importance':>10s}")
print(f"  {'-' * 50}")
for _, row in importance_df.iterrows():
    bar = "█" * int(row["importance"] * 50)
    print(f"  {row['fitur']:35s}  {row['importance']:>10.4f}  {bar}")


# ============================================================
# 8. SIMPAN MODEL
# ============================================================
print("\n" + "=" * 60)
print("STEP 7: Simpan Model")
print("=" * 60)

os.makedirs("models", exist_ok=True)

metadata = {
    "model_name": "Random Forest",
    "features": FEATURES,
    "target": TARGET,
    "cutoff_date": str(cutoff_date.date()),
    "train_size": len(X_train),
    "test_size": len(X_test),
    "metrics": {
        "R² (test)": round(r2_test, 4),
        "MAE (test)": round(mae_test, 4),
        "R² (train)": round(r2_train, 4),
        "MAE (train)": round(mae_train, 4),
        "CV R² mean": round(cv_r2.mean(), 4),
        "CV R² std": round(cv_r2.std(), 4),
        "CV MAE mean": round(cv_mae.mean(), 4),
    },
    "global_median": float(global_median),
}

joblib.dump({"model": model, "metadata": metadata}, "models/decision_tree.joblib")
print(f"  File     : models/decision_tree.joblib")
print(f"  Model    : Random Forest (n_estimators=200, max_depth=8)")
print(f"  Features : {len(FEATURES)}")
print(f"  R² test  : {r2_test:.4f}")
print(f"  MAE test : {mae_test:.4f}")


# ============================================================
# 9. VISUALISASI (3 panel)
# ============================================================
print("\n" + "=" * 60)
print("STEP 8: Visualisasi")
print("=" * 60)

C1 = "#1B4332"
C2 = "#FFC107"
C3 = "#6C757D"
BG = "#F1FAF7"

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.patch.set_facecolor(BG)
fig.suptitle(
    f"Evaluasi Prediksi Kecepatan Hafalan — Random Forest\n"
    f"R²={r2_test:.3f}  |  MAE={mae_test:.2f} ayat/hari  |  "
    f"CV R²={cv_r2.mean():.3f}±{cv_r2.std():.3f}",
    fontsize=12, fontweight="bold", color=C1, y=1.02,
)

# Panel 1: Actual vs Predicted
ax = axes[0]; ax.set_facecolor(BG)
lim = max(y_test.max(), pred_test.max()) * 1.1
ax.scatter(y_test, pred_test, alpha=0.5, s=25, color=C1, edgecolors="none")
ax.plot([0, lim], [0, lim], "--", color=C2, lw=1.5, label="Ideal")
ax.set_xlabel("Actual (ayat/hari)", color=C3)
ax.set_ylabel("Predicted (ayat/hari)", color=C3)
ax.set_title("Actual vs Predicted", color=C1, fontweight="bold")
ax.legend(fontsize=9); ax.tick_params(colors=C3)

# Panel 2: Feature Importance
ax = axes[1]; ax.set_facecolor(BG)
top = importance_df.sort_values("importance")
bar_colors = [C2 if v >= importance_df["importance"].quantile(0.7) else C1
              for v in top["importance"]]
ax.barh(top["fitur"], top["importance"], color=bar_colors, edgecolor="none")
ax.set_xlabel("Importance", color=C3)
ax.set_title("Feature Importance", color=C1, fontweight="bold")
ax.tick_params(colors=C3, labelsize=8)

# Panel 3: Distribusi Error
ax = axes[2]; ax.set_facecolor(BG)
resid = y_test.values - pred_test
ax.hist(resid, bins=20, color=C1, edgecolor="white", alpha=0.85)
ax.axvline(0, color=C2, ls="--", lw=1.5)
ax.axvline(resid.mean(), color="red", ls=":", lw=1.2, label=f"Mean={resid.mean():.2f}")
ax.set_xlabel("Error (actual − predicted)", color=C3)
ax.set_ylabel("Frekuensi", color=C3)
ax.set_title(f"Distribusi Error (MAE={mae_test:.2f})", color=C1, fontweight="bold")
ax.legend(fontsize=9); ax.tick_params(colors=C3)

plt.tight_layout()
plt.savefig("models/evaluasi_model.png", dpi=150, bbox_inches="tight", facecolor=BG)
print(f"  Chart: models/evaluasi_model.png")


# ============================================================
# 10. CONTOH PENGGUNAAN
# ============================================================
print("\n" + "=" * 60)
print("CONTOH PENGGUNAAN")
print("=" * 60)

contoh = test_df.iloc[-1]
siswa_id = int(contoh["siswa_id"])
surah_id = int(contoh["surah_id"])
surah_info = db_module.SURAH_DICT.get(surah_id, {})
total_ayat = surah_info.get("jumlah_ayat", int(contoh["total_ayat_surah"]))
ayat_sudah = int(contoh["ayat_sudah_dihafal"])
sisa_ayat  = max(total_ayat - ayat_sudah, 0)

X_contoh = contoh[FEATURES].values.reshape(1, -1)
prediksi_kecepatan = max(float(model.predict(X_contoh)[0]), 1.0)
estimasi_hari = int(np.ceil(sisa_ayat / prediksi_kecepatan)) if sisa_ayat > 0 else 0

print(f"""
  Input:
    Siswa ID         : {siswa_id}
    Surah            : {surah_id} ({db_module.get_surah_name(surah_id)})
    Total ayat surah : {total_ayat}
    Ayat sudah       : {ayat_sudah}
    Sisa ayat        : {sisa_ayat}

  Output (dari model):
    Prediksi kecepatan : {prediksi_kecepatan:.1f} ayat/hari

  Estimasi waktu selesai:
    estimasi_hari = sisa_ayat / prediksi_kecepatan
    estimasi_hari = {sisa_ayat} / {prediksi_kecepatan:.1f} = {estimasi_hari} hari
""")

# Leakage Audit
print("  Leakage Audit:")
print("    kecepatan_avg_sebelumnya : ✅ expanding mean + shift(1)")
print("    lag_1, lag_2, lag_3      : ✅ shift(1/2/3) per siswa")
print("    rolling_mean_3           : ✅ rolling(3) + shift(1) per siswa")
print("    ayat_sudah_dihafal       : ✅ cumsum + shift(1) per (siswa, surah)")
print("    progress_persen          : ✅ derived dari ayat_sudah_dihafal")
print("    hari_ke, total_setoran   : ✅ cumcount (before current row)")
print("    Fitur surah (statis)     : ✅ tidak berubah")

print("\n" + "=" * 60)
print("SELESAI!")
print("=" * 60)
