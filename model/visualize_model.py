"""
visualize_model.py — Visualisasi Lengkap Model Random Forest
=============================================================
Menghasilkan 4 file PNG:
  1. models/viz_pipeline.png        — Pipeline training & prediksi
  2. models/viz_feature_importance.png — Feature importance detail
  3. models/viz_evaluasi.png        — Evaluasi model (4 panel)
  4. models/viz_arsitektur_rf.png   — Arsitektur Random Forest
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
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import patheffects

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error

from app.database import get_db, load_csv
import app.database as db_module

# ── Color Scheme ──
PRIMARY   = "#1B4332"
ACCENT    = "#FFC107"
SUCCESS   = "#2D6A4F"
DANGER    = "#E63946"
INFO      = "#457B9D"
LIGHT     = "#F1FAF7"
WHITE     = "#FFFFFF"
GRAY      = "#6C757D"
DARK      = "#1D3557"
BLUE_SOFT = "#A8DADC"

# ── Load & prepare data (same as train.py) ──
load_csv()
surah_df = db_module.SURAH_DF.copy()
ayat_df  = db_module.AYAT_DF.copy()

conn = get_db(); cur = conn.cursor()
cur.execute("SELECT * FROM hafalan_log ORDER BY siswa_id, tanggal")
rows = cur.fetchall(); conn.close()
hafalan_df = pd.DataFrame(rows)
for col in ["id","siswa_id","guru_id","surah_id","ayat_mulai","ayat_selesai","jumlah_ayat"]:
    hafalan_df[col] = hafalan_df[col].astype(int)
hafalan_df["tanggal"] = pd.to_datetime(hafalan_df["tanggal"])

surah_features = surah_df.rename(columns={"nomor_surah":"surah_id"})
surah_features["surah_id"] = surah_features["surah_id"].astype(int)
surah_features = surah_features[["surah_id","jumlah_ayat"]]
surah_features.columns = ["surah_id","total_ayat_surah"]

ayat_df["surah"] = ayat_df["surah"].astype(int)
ayat_agg = ayat_df.groupby("surah").agg(
    rata_kata_per_ayat=("kata","mean"),
    rata_huruf_per_ayat=("huruf","mean"),
).reset_index().rename(columns={"surah":"surah_id"})
surah_features = surah_features.merge(ayat_agg, on="surah_id", how="left")
df = hafalan_df.merge(surah_features, on="surah_id", how="left")
df = df.sort_values(["siswa_id","tanggal"]).reset_index(drop=True)
global_median = df["jumlah_ayat"].median()

df["hari_ke"] = df.groupby(["siswa_id","surah_id"]).cumcount()+1
df["ayat_sudah_dihafal"] = (
    df.groupby(["siswa_id","surah_id"])["jumlah_ayat"]
    .apply(lambda x: x.cumsum().shift(1).fillna(0))
    .reset_index(level=[0,1], drop=True).astype(int)
)
df["progress_persen"] = (df["ayat_sudah_dihafal"]/df["total_ayat_surah"]*100).round(1).clip(0,100)
df["kecepatan_avg_sebelumnya"] = (
    df.groupby("siswa_id")["jumlah_ayat"].expanding().mean().shift(1)
    .reset_index(level=0, drop=True).fillna(global_median)
)
for i in [1,2,3]:
    df[f"lag_{i}"] = df.groupby("siswa_id")["jumlah_ayat"].shift(i).fillna(global_median)
df["rolling_mean_3"] = (
    df.groupby("siswa_id")["jumlah_ayat"]
    .apply(lambda g: g.rolling(window=3, min_periods=1).mean().shift(1))
    .reset_index(level=0, drop=True).fillna(global_median)
)
df["total_setoran_sebelumnya"] = df.groupby("siswa_id").cumcount()

FEATURES = [
    "total_ayat_surah","rata_kata_per_ayat","rata_huruf_per_ayat",
    "hari_ke","ayat_sudah_dihafal","progress_persen",
    "kecepatan_avg_sebelumnya","lag_1","lag_2","lag_3",
    "rolling_mean_3","total_setoran_sebelumnya",
]
TARGET = "jumlah_ayat"

df_sorted = df.sort_values("tanggal").reset_index(drop=True)
cutoff_idx = int(len(df_sorted)*0.8)
cutoff_date = df_sorted.iloc[cutoff_idx]["tanggal"]
train_df = df_sorted[df_sorted["tanggal"]<=cutoff_date].copy()
test_df  = df_sorted[df_sorted["tanggal"]>cutoff_date].copy()

X_train, y_train = train_df[FEATURES], train_df[TARGET]
X_test,  y_test  = test_df[FEATURES],  test_df[TARGET]

model = RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
pred_train = model.predict(X_train)
pred_test  = model.predict(X_test)

tscv = TimeSeriesSplit(n_splits=5)
cv = cross_validate(model, df_sorted[FEATURES], df_sorted[TARGET], cv=tscv, scoring=["neg_mean_absolute_error","r2"])
cv_mae = -cv["test_neg_mean_absolute_error"]
cv_r2  = cv["test_r2"]

os.makedirs("models", exist_ok=True)


def add_box(ax, x, y, w, h, text, color=PRIMARY, text_color=WHITE, fontsize=10, bold=True, radius=0.05):
    """Helper: draw a rounded box with centered text."""
    box = FancyBboxPatch((x-w/2, y-h/2), w, h,
                         boxstyle=f"round,pad={radius}",
                         facecolor=color, edgecolor="none",
                         transform=ax.transData, zorder=3)
    ax.add_patch(box)
    fw = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, fontweight=fw, zorder=4,
            path_effects=[patheffects.withStroke(linewidth=0, foreground=WHITE)])
    return box


def add_arrow(ax, x1, y1, x2, y2, color=GRAY):
    """Helper: draw an arrow between two points."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8),
                zorder=2)


# ================================================================
# 1. PIPELINE TRAINING & PREDIKSI
# ================================================================
print("Generating viz_pipeline.png ...")

fig, ax = plt.subplots(figsize=(18, 10))
fig.patch.set_facecolor(LIGHT)
ax.set_facecolor(LIGHT)
ax.set_xlim(0, 18)
ax.set_ylim(0, 10)
ax.axis("off")

ax.text(9, 9.5, "PIPELINE TRAINING & PREDIKSI MODEL", fontsize=18,
        ha="center", va="center", fontweight="bold", color=PRIMARY,
        path_effects=[patheffects.withStroke(linewidth=3, foreground=WHITE)])

# ── Training Pipeline (left) ──
ax.text(4.5, 8.7, "TRAINING PIPELINE", fontsize=13, ha="center",
        fontweight="bold", color=SUCCESS)

boxes_train = [
    (4.5, 7.8, "📦 Data MySQL\nhafalan_log (592 rows)", INFO),
    (4.5, 6.5, "📊 Feature Engineering\n12 Fitur (Surah + Temporal)", SUCCESS),
    (4.5, 5.2, "✂️ Time-Based Split\nTrain 80% | Test 20%", PRIMARY),
    (4.5, 3.9, "🌲 Random Forest\n200 trees, depth=8", ACCENT),
    (4.5, 2.6, "📈 Evaluasi\nR²=0.39 | MAE=1.33", DANGER),
    (4.5, 1.3, "💾 Simpan Model\ndecision_tree.joblib", DARK),
]

for (x, y, text, color) in boxes_train:
    tc = WHITE if color != ACCENT else PRIMARY
    add_box(ax, x, y, 3.8, 0.85, text, color=color, text_color=tc, fontsize=9)

for i in range(len(boxes_train)-1):
    add_arrow(ax, boxes_train[i][0], boxes_train[i][1]-0.43,
              boxes_train[i+1][0], boxes_train[i+1][1]+0.43, color=GRAY)

# ── Prediction Pipeline (right) ──
ax.text(13.5, 8.7, "PREDICTION PIPELINE", fontsize=13, ha="center",
        fontweight="bold", color=SUCCESS)

boxes_pred = [
    (13.5, 7.8, "👤 Input\nsiswa_id + surah_id", INFO),
    (13.5, 6.5, "📊 Build 12 Fitur\ndari MySQL real-time", SUCCESS),
    (13.5, 5.2, "🌲 Model Predict\nkecepatan (ayat/hari)", PRIMARY),
    (13.5, 3.9, "⚙️ Post-Processing\nBlend + Context + Clamp", ACCENT),
    (13.5, 2.6, "📅 Estimasi Hari\nsisa_ayat ÷ kecepatan", DANGER),
    (13.5, 1.3, "✅ Output\nestimasi_low ~ estimasi_high", DARK),
]

for (x, y, text, color) in boxes_pred:
    tc = WHITE if color != ACCENT else PRIMARY
    add_box(ax, x, y, 3.8, 0.85, text, color=color, text_color=tc, fontsize=9)

for i in range(len(boxes_pred)-1):
    add_arrow(ax, boxes_pred[i][0], boxes_pred[i][1]-0.43,
              boxes_pred[i+1][0], boxes_pred[i+1][1]+0.43, color=GRAY)

# Connecting arrow from saved model to prediction
add_arrow(ax, 6.4, 1.3, 11.6, 5.2, color=ACCENT)
ax.text(8.9, 3.0, "load model", fontsize=8, ha="center", color=ACCENT,
        fontstyle="italic", rotation=28)

# Vertical divider
ax.plot([9, 9], [0.5, 8.5], '--', color=GRAY, alpha=0.3, lw=1)

plt.tight_layout()
plt.savefig("models/viz_pipeline.png", dpi=150, bbox_inches="tight", facecolor=LIGHT)
plt.close()
print("  ✅ models/viz_pipeline.png")


# ================================================================
# 2. FEATURE IMPORTANCE (detail)
# ================================================================
print("Generating viz_feature_importance.png ...")

importance_df = pd.DataFrame({
    "fitur": FEATURES,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=True)

fig, axes = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={"width_ratios": [1.2, 1]})
fig.patch.set_facecolor(LIGHT)
fig.suptitle("FEATURE IMPORTANCE — Random Forest", fontsize=16,
             fontweight="bold", color=PRIMARY, y=1.02)

# Left: horizontal bar
ax = axes[0]; ax.set_facecolor(LIGHT)
colors = [ACCENT if v >= importance_df["importance"].quantile(0.7) else PRIMARY
          for v in importance_df["importance"]]
bars = ax.barh(importance_df["fitur"], importance_df["importance"],
               color=colors, edgecolor="none", height=0.65)
for bar, val in zip(bars, importance_df["importance"]):
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
            f"{val:.1%}", va="center", fontsize=9, color=GRAY, fontweight="bold")
ax.set_xlabel("Importance Score", color=GRAY, fontsize=11)
ax.set_title("Kontribusi Setiap Fitur", color=PRIMARY, fontweight="bold", fontsize=13)
ax.tick_params(colors=GRAY, labelsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Right: grouped categories
ax2 = axes[1]; ax2.set_facecolor(LIGHT)
categories = {
    "Riwayat Siswa\n(kecepatan_avg, lag_1/2/3,\nrolling_mean_3, total_setoran)": 0,
    "Progress Surah\n(hari_ke, ayat_sudah,\nprogress_persen)": 0,
    "Karakteristik Surah\n(total_ayat, rata_kata,\nrata_huruf)": 0,
}
imp_dict = dict(zip(importance_df["fitur"], importance_df["importance"]))
categories["Riwayat Siswa\n(kecepatan_avg, lag_1/2/3,\nrolling_mean_3, total_setoran)"] = (
    imp_dict["kecepatan_avg_sebelumnya"] + imp_dict["lag_1"] + imp_dict["lag_2"] +
    imp_dict["lag_3"] + imp_dict["rolling_mean_3"] + imp_dict["total_setoran_sebelumnya"]
)
categories["Progress Surah\n(hari_ke, ayat_sudah,\nprogress_persen)"] = (
    imp_dict["hari_ke"] + imp_dict["ayat_sudah_dihafal"] + imp_dict["progress_persen"]
)
categories["Karakteristik Surah\n(total_ayat, rata_kata,\nrata_huruf)"] = (
    imp_dict["total_ayat_surah"] + imp_dict["rata_kata_per_ayat"] + imp_dict["rata_huruf_per_ayat"]
)

cat_names = list(categories.keys())
cat_vals  = list(categories.values())
cat_colors = [INFO, SUCCESS, ACCENT]

wedges, texts, autotexts = ax2.pie(
    cat_vals, labels=cat_names, colors=cat_colors, autopct="%1.1f%%",
    startangle=90, textprops={"fontsize": 9, "color": PRIMARY},
    pctdistance=0.75, labeldistance=1.15
)
for t in autotexts:
    t.set_fontweight("bold"); t.set_fontsize(11); t.set_color(WHITE)
ax2.set_title("Kelompok Fitur", color=PRIMARY, fontweight="bold", fontsize=13)

plt.tight_layout()
plt.savefig("models/viz_feature_importance.png", dpi=150, bbox_inches="tight", facecolor=LIGHT)
plt.close()
print("  ✅ models/viz_feature_importance.png")


# ================================================================
# 3. EVALUASI MODEL (4 panel)
# ================================================================
print("Generating viz_evaluasi.png ...")

fig, axes = plt.subplots(2, 2, figsize=(14, 11))
fig.patch.set_facecolor(LIGHT)
fig.suptitle(
    f"EVALUASI MODEL — Random Forest\n"
    f"R² Test = {r2_score(y_test, pred_test):.3f}  |  MAE = {mean_absolute_error(y_test, pred_test):.2f} ayat/hari  |  "
    f"CV R² = {cv_r2.mean():.3f} ± {cv_r2.std():.3f}",
    fontsize=14, fontweight="bold", color=PRIMARY, y=1.02
)

# Panel 1: Actual vs Predicted scatter
ax = axes[0, 0]; ax.set_facecolor(LIGHT)
lim = max(y_test.max(), pred_test.max()) * 1.1
ax.scatter(y_test, pred_test, alpha=0.5, s=35, color=PRIMARY, edgecolors="none", label="Test data")
ax.scatter(y_train, pred_train, alpha=0.1, s=15, color=BLUE_SOFT, edgecolors="none", label="Train data")
ax.plot([0, lim], [0, lim], "--", color=ACCENT, lw=2, label="Perfect prediction")
ax.fill_between([0, lim], [0-1, lim-1], [0+1, lim+1], alpha=0.08, color=SUCCESS, label="±1 ayat zone")
ax.set_xlabel("Actual (ayat/hari)", color=GRAY, fontsize=10)
ax.set_ylabel("Predicted (ayat/hari)", color=GRAY, fontsize=10)
ax.set_title("Actual vs Predicted", color=PRIMARY, fontweight="bold", fontsize=12)
ax.legend(fontsize=8, loc="upper left"); ax.tick_params(colors=GRAY)

# Panel 2: Error distribution
ax = axes[0, 1]; ax.set_facecolor(LIGHT)
resid = y_test.values - pred_test
ax.hist(resid, bins=25, color=PRIMARY, edgecolor=WHITE, alpha=0.85)
ax.axvline(0, color=ACCENT, ls="--", lw=2, label="Zero error")
ax.axvline(resid.mean(), color=DANGER, ls=":", lw=2, label=f"Mean = {resid.mean():.2f}")
ax.axvline(np.median(resid), color=INFO, ls="-.", lw=1.5, label=f"Median = {np.median(resid):.2f}")
ax.axvspan(resid.mean()-resid.std(), resid.mean()+resid.std(), alpha=0.1, color=ACCENT,
           label=f"±1σ ({resid.std():.2f})")
ax.set_xlabel("Error (actual − predicted)", color=GRAY, fontsize=10)
ax.set_ylabel("Frekuensi", color=GRAY, fontsize=10)
ax.set_title(f"Distribusi Error (MAE = {mean_absolute_error(y_test, pred_test):.2f})",
             color=PRIMARY, fontweight="bold", fontsize=12)
ax.legend(fontsize=8); ax.tick_params(colors=GRAY)

# Panel 3: Cross-validation scores
ax = axes[1, 0]; ax.set_facecolor(LIGHT)
folds = range(1, 6)
ax.bar([f-0.18 for f in folds], cv_r2, width=0.35, color=PRIMARY, label="R²", edgecolor="none")
ax.bar([f+0.18 for f in folds], -cv["test_neg_mean_absolute_error"], width=0.35,
       color=ACCENT, label="MAE", edgecolor="none")
ax.axhline(cv_r2.mean(), color=PRIMARY, ls="--", lw=1, alpha=0.6)
ax.axhline(cv_mae.mean(), color=ACCENT, ls="--", lw=1, alpha=0.6)
ax.set_xlabel("Fold", color=GRAY, fontsize=10)
ax.set_ylabel("Score", color=GRAY, fontsize=10)
ax.set_title(f"Cross-Validation (5-Fold TimeSeriesSplit)\nR² = {cv_r2.mean():.3f} ± {cv_r2.std():.3f}  |  MAE = {cv_mae.mean():.3f} ± {cv_mae.std():.3f}",
             color=PRIMARY, fontweight="bold", fontsize=11)
ax.set_xticks(list(folds))
ax.set_xticklabels([f"Fold {f}" for f in folds])
ax.legend(fontsize=9); ax.tick_params(colors=GRAY)

# Panel 4: Prediction over time
ax = axes[1, 1]; ax.set_facecolor(LIGHT)
test_sorted = test_df.sort_values("tanggal").reset_index(drop=True)
idx = range(len(test_sorted))
ax.plot(idx, test_sorted[TARGET].values, color=PRIMARY, lw=1.2, alpha=0.7, label="Actual")
ax.plot(idx, pred_test[test_sorted.index - test_sorted.index.min()], color=ACCENT, lw=1.2, alpha=0.7, label="Predicted")
ax.fill_between(idx,
                pred_test[test_sorted.index - test_sorted.index.min()] - mean_absolute_error(y_test, pred_test),
                pred_test[test_sorted.index - test_sorted.index.min()] + mean_absolute_error(y_test, pred_test),
                alpha=0.15, color=ACCENT, label="±MAE band")
ax.set_xlabel("Test Data Index (time →)", color=GRAY, fontsize=10)
ax.set_ylabel("Ayat/hari", color=GRAY, fontsize=10)
ax.set_title("Prediksi vs Aktual (Test Set, by Time)", color=PRIMARY, fontweight="bold", fontsize=12)
ax.legend(fontsize=8); ax.tick_params(colors=GRAY)

plt.tight_layout()
plt.savefig("models/viz_evaluasi.png", dpi=150, bbox_inches="tight", facecolor=LIGHT)
plt.close()
print("  ✅ models/viz_evaluasi.png")


# ================================================================
# 4. ARSITEKTUR RANDOM FOREST
# ================================================================
print("Generating viz_arsitektur_rf.png ...")

fig, ax = plt.subplots(figsize=(16, 10))
fig.patch.set_facecolor(LIGHT)
ax.set_facecolor(LIGHT)
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis("off")

ax.text(8, 9.6, "ARSITEKTUR RANDOM FOREST", fontsize=18,
        ha="center", fontweight="bold", color=PRIMARY)
ax.text(8, 9.2, "200 Decision Trees  |  max_depth=8  |  min_samples_leaf=5",
        fontsize=11, ha="center", color=GRAY)

# Input features box
add_box(ax, 8, 8.2, 6, 0.7, "INPUT: 12 Fitur (Surah + Temporal + Riwayat)", color=INFO, fontsize=11)

# Feature groups
feat_groups = [
    (2.5, 7.1, "Karakteristik Surah\ntotal_ayat_surah\nrata_kata_per_ayat\nrata_huruf_per_ayat", SUCCESS),
    (8, 7.1, "Progress\nhari_ke\nayat_sudah_dihafal\nprogress_persen", PRIMARY),
    (13.5, 7.1, "Riwayat Siswa\nkecepatan_avg\nlag_1, lag_2, lag_3\nrolling_mean_3", DARK),
]
for (x, y, text, color) in feat_groups:
    add_box(ax, x, y, 4, 1.0, text, color=color, fontsize=8, bold=False)

for (x, y, _, _) in feat_groups:
    add_arrow(ax, x, 7.65, x, 7.85, color=GRAY)

# Bootstrap sampling
add_box(ax, 8, 5.8, 10, 0.6, "🎲 Bootstrap Sampling → Setiap tree dapat subset data & fitur yang berbeda",
        color=ACCENT, text_color=PRIMARY, fontsize=10)
add_arrow(ax, 8, 6.55, 8, 6.15, color=GRAY)

# Individual trees
tree_positions = [2, 4.5, 7, 9.5, 12, 14.5]
tree_labels = ["Tree 1", "Tree 2", "Tree 3", "...", "Tree 199", "Tree 200"]
for i, (x, label) in enumerate(zip(tree_positions, tree_labels)):
    color = PRIMARY if label != "..." else LIGHT
    tc = WHITE if label != "..." else GRAY
    ec = PRIMARY if label != "..." else GRAY
    if label == "...":
        ax.text(x, 4.6, "...", fontsize=20, ha="center", va="center", color=GRAY, fontweight="bold")
    else:
        # Tree trunk
        add_box(ax, x, 4.6, 1.8, 0.55, label, color=PRIMARY, fontsize=9)
        # Mini tree visualization
        # Root node
        ax.plot(x, 4.0, 'o', markersize=8, color=SUCCESS, zorder=5)
        # Branches
        ax.plot([x, x-0.4], [4.0, 3.55], '-', color=SUCCESS, lw=1.2, zorder=4)
        ax.plot([x, x+0.4], [4.0, 3.55], '-', color=SUCCESS, lw=1.2, zorder=4)
        ax.plot(x-0.4, 3.5, 'o', markersize=6, color=ACCENT, zorder=5)
        ax.plot(x+0.4, 3.5, 'o', markersize=6, color=ACCENT, zorder=5)
        # Deeper branches
        ax.plot([x-0.4, x-0.6], [3.5, 3.15], '-', color=ACCENT, lw=0.8, zorder=4)
        ax.plot([x-0.4, x-0.2], [3.5, 3.15], '-', color=ACCENT, lw=0.8, zorder=4)
        ax.plot([x+0.4, x+0.2], [3.5, 3.15], '-', color=ACCENT, lw=0.8, zorder=4)
        ax.plot([x+0.4, x+0.6], [3.5, 3.15], '-', color=ACCENT, lw=0.8, zorder=4)
        # Leaf nodes
        for lx in [x-0.6, x-0.2, x+0.2, x+0.6]:
            ax.plot(lx, 3.1, 's', markersize=5, color=INFO, zorder=5)

    if label != "...":
        add_arrow(ax, x, 5.45, x, 4.9, color=GRAY)

# Prediction from each tree
for x in [2, 4.5, 7, 9.5, 12, 14.5]:
    if x != 7:  # skip "..."
        add_arrow(ax, x, 2.8, 8, 2.15, color=GRAY)

# Aggregation
add_box(ax, 8, 1.8, 8, 0.6,
        "📊 AGGREGASI: Rata-rata prediksi dari 200 trees → Prediksi Final",
        color=DANGER, fontsize=10)

# Post-processing
add_box(ax, 8, 0.8, 10, 0.65,
        "⚙️ POST-PROCESSING: Blending (0.7×model + 0.3×rolling) → Context Adjust → Clamp → Estimasi Hari",
        color=DARK, fontsize=9)
add_arrow(ax, 8, 1.45, 8, 1.15, color=GRAY)

# Output
ax.text(8, 0.15, "OUTPUT: prediksi_ayat_per_hari → estimasi_hari = sisa_ayat ÷ kecepatan",
        ha="center", fontsize=10, color=PRIMARY, fontstyle="italic")

plt.tight_layout()
plt.savefig("models/viz_arsitektur_rf.png", dpi=150, bbox_inches="tight", facecolor=LIGHT)
plt.close()
print("  ✅ models/viz_arsitektur_rf.png")


# ================================================================
# 5. POST-PROCESSING PIPELINE
# ================================================================
print("Generating viz_postprocessing.png ...")

fig, ax = plt.subplots(figsize=(16, 8))
fig.patch.set_facecolor(LIGHT)
ax.set_facecolor(LIGHT)
ax.set_xlim(0, 16)
ax.set_ylim(0, 8)
ax.axis("off")

ax.text(8, 7.6, "POST-PROCESSING PIPELINE", fontsize=18,
        ha="center", fontweight="bold", color=PRIMARY)
ax.text(8, 7.2, "Menyesuaikan prediksi model agar lebih realistis dan akurat",
        fontsize=11, ha="center", color=GRAY, fontstyle="italic")

# Step boxes
steps = [
    (2.5, 5.8, "STEP 1\nModel Predict", "Random Forest\nmenghasilkan\nprediksi mentah\n(ayat/hari)", INFO),
    (6.5, 5.8, "STEP 2\nBlending", "0.7 × model +\n0.3 × rolling_mean_3\nKombinasi prediksi\ndengan tren terkini", SUCCESS),
    (10.5, 5.8, "STEP 3\nContext Adjust", "Surah > 100 ayat:\npenalty -10%\n> 15 kata/ayat:\npenalty -5%", ACCENT),
    (14, 5.8, "STEP 4\nClamp", "Minimal: 1 ayat/hari\nMaksimal: 2× avg\nMencegah prediksi\nextrem", DANGER),
]

for (x, y, title, desc, color) in steps:
    tc = WHITE if color != ACCENT else PRIMARY
    add_box(ax, x, y, 3, 0.7, title, color=color, text_color=tc, fontsize=11)
    ax.text(x, y-0.75, desc, ha="center", va="top", fontsize=8.5,
            color=PRIMARY, linespacing=1.4,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=WHITE, edgecolor=color, alpha=0.8))

for i in range(len(steps)-1):
    add_arrow(ax, steps[i][0]+1.6, steps[i][1], steps[i+1][0]-1.6, steps[i+1][1], color=GRAY)

# Example calculation
ax.text(8, 3.2, "CONTOH PERHITUNGAN", fontsize=13, ha="center", fontweight="bold", color=PRIMARY)

example_data = [
    ("Model predict", "5.2 ayat/hari", INFO),
    ("Blending (0.7×5.2 + 0.3×4.0)", "4.84 ayat/hari", SUCCESS),
    ("Context (Al-Baqarah: 286 ayat, penalty -10%)", "4.36 ayat/hari", ACCENT),
    ("Clamp (min=1, max=2×4.5=9.0)", "4.36 ayat/hari  ✅", DANGER),
]

for i, (label, value, color) in enumerate(example_data):
    y = 2.5 - i * 0.55
    add_box(ax, 5, y, 6.5, 0.42, label, color=color,
            text_color=WHITE if color != ACCENT else PRIMARY, fontsize=9, bold=False)
    ax.text(11.5, y, f"→  {value}", ha="left", va="center", fontsize=10,
            color=PRIMARY, fontweight="bold")

# Final output
add_box(ax, 8, 0.35, 12, 0.5,
        "Estimasi hari = sisa_ayat ÷ 4.36 = 216 ÷ 4.36 ≈ 50 hari  |  Range: 42–60 hari",
        color=DARK, fontsize=10)
add_arrow(ax, 8, 0.85, 8, 0.65, color=GRAY)

plt.tight_layout()
plt.savefig("models/viz_postprocessing.png", dpi=150, bbox_inches="tight", facecolor=LIGHT)
plt.close()
print("  ✅ models/viz_postprocessing.png")


# ================================================================
# 6. DISTRIBUSI DATA & SHIFT
# ================================================================
print("Generating viz_data_analysis.png ...")

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.patch.set_facecolor(LIGHT)
fig.suptitle("ANALISIS DATA & DISTRIBUTION SHIFT", fontsize=14,
             fontweight="bold", color=PRIMARY, y=1.02)

# Panel 1: Target distribution train vs test
ax = axes[0]; ax.set_facecolor(LIGHT)
ax.hist(y_train, bins=20, alpha=0.6, color=PRIMARY, edgecolor=WHITE, label=f"Train (μ={y_train.mean():.2f})")
ax.hist(y_test, bins=20, alpha=0.6, color=ACCENT, edgecolor=WHITE, label=f"Test (μ={y_test.mean():.2f})")
ax.axvline(y_train.mean(), color=PRIMARY, ls="--", lw=1.5)
ax.axvline(y_test.mean(), color=ACCENT, ls="--", lw=1.5)
ax.set_xlabel("Jumlah Ayat / Hari", color=GRAY)
ax.set_ylabel("Frekuensi", color=GRAY)
ax.set_title(f"Distribution Shift ({abs(y_train.mean()-y_test.mean())/y_train.mean()*100:.1f}%)",
             color=PRIMARY, fontweight="bold")
ax.legend(fontsize=9); ax.tick_params(colors=GRAY)

# Panel 2: Timeline
ax = axes[1]; ax.set_facecolor(LIGHT)
daily = df_sorted.groupby("tanggal")[TARGET].mean()
ax.plot(daily.index, daily.values, color=PRIMARY, lw=1, alpha=0.5)
ax.plot(daily.index, daily.rolling(7).mean().values, color=ACCENT, lw=2, label="7-day avg")
ax.axvline(cutoff_date, color=DANGER, ls="--", lw=2, label=f"Cutoff ({cutoff_date.date()})")
ax.fill_betweenx([0, daily.max()*1.1], daily.index.min(), cutoff_date, alpha=0.05, color=PRIMARY)
ax.fill_betweenx([0, daily.max()*1.1], cutoff_date, daily.index.max(), alpha=0.05, color=DANGER)
ax.text(cutoff_date - pd.Timedelta(days=15), daily.max()*0.95, "TRAIN", fontsize=10,
        color=PRIMARY, fontweight="bold", ha="center")
ax.text(cutoff_date + pd.Timedelta(days=25), daily.max()*0.95, "TEST", fontsize=10,
        color=DANGER, fontweight="bold", ha="center")
ax.set_xlabel("Tanggal", color=GRAY)
ax.set_ylabel("Rata-rata Ayat/Hari", color=GRAY)
ax.set_title("Timeline Data & Split Point", color=PRIMARY, fontweight="bold")
ax.legend(fontsize=9); ax.tick_params(colors=GRAY)

# Panel 3: Per-siswa stats
ax = axes[2]; ax.set_facecolor(LIGHT)
siswa_stats = df_sorted.groupby("siswa_id").agg(
    mean_speed=(TARGET, "mean"),
    count=(TARGET, "count")
).sort_values("mean_speed", ascending=True)
colors_bar = [ACCENT if v > siswa_stats["mean_speed"].median() else PRIMARY for v in siswa_stats["mean_speed"]]
ax.barh(range(len(siswa_stats)), siswa_stats["mean_speed"], color=colors_bar, edgecolor="none", height=0.7)
ax.axvline(siswa_stats["mean_speed"].median(), color=DANGER, ls="--", lw=1.5,
           label=f"Median = {siswa_stats['mean_speed'].median():.1f}")
ax.set_xlabel("Rata-rata Ayat/Hari", color=GRAY)
ax.set_ylabel("Siswa", color=GRAY)
ax.set_title(f"Kecepatan per Siswa ({len(siswa_stats)} siswa)", color=PRIMARY, fontweight="bold")
ax.set_yticks(range(0, len(siswa_stats), max(1, len(siswa_stats)//10)))
ax.legend(fontsize=9); ax.tick_params(colors=GRAY, labelsize=8)

plt.tight_layout()
plt.savefig("models/viz_data_analysis.png", dpi=150, bbox_inches="tight", facecolor=LIGHT)
plt.close()
print("  ✅ models/viz_data_analysis.png")


print("\n" + "="*50)
print("SEMUA VISUALISASI BERHASIL!")
print("="*50)
print("""
File yang dihasilkan:
  1. models/viz_pipeline.png           — Pipeline training & prediksi
  2. models/viz_feature_importance.png  — Feature importance detail
  3. models/viz_evaluasi.png           — Evaluasi model (4 panel)
  4. models/viz_arsitektur_rf.png      — Arsitektur Random Forest
  5. models/viz_postprocessing.png     — Post-processing pipeline
  6. models/viz_data_analysis.png      — Analisis data & distribution shift
""")
