"""
Predictor — Load model Random Forest dan prediksi kecepatan hafalan.

Post-processing pipeline:
  1. Model prediksi → raw speed (ayat/hari)
  2. Blending: 70% model + 30% rolling_mean_3 (stabilisasi)
  3. Context adjustment: surah panjang/kompleks → turunkan sedikit
  4. Clamp: min 1, max dinamis berdasarkan riwayat siswa
  5. Estimasi hari = sisa_ayat / final_speed
  6. Confidence range: low (90%) — high (120%)
"""

import joblib
import numpy as np
import pandas as pd
import os

import app.database as db_module
from app.database import get_db

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models/decision_tree.joblib"
)

# Load model sekali saat import
_data = joblib.load(MODEL_PATH)
MODEL = _data["model"]
METADATA = _data["metadata"]
FEATURES = METADATA["features"]
GLOBAL_MEDIAN = METADATA.get("global_median", 3.0)

_metrics = METADATA.get("metrics", {})
print(f"[ML] Model loaded: {METADATA.get('model_name', 'unknown')}, "
      f"{len(FEATURES)} features, R²={_metrics.get('R² (test)', 0):.3f}")


def get_surah_features(surah_id: int) -> dict:
    """Fitur statis surah dari CSV."""
    ayat_df = db_module.AYAT_DF
    surah = db_module.SURAH_DICT.get(surah_id)
    if not surah:
        return None

    ayat_surah = ayat_df[ayat_df["surah"].astype(int) == surah_id]

    return {
        "total_ayat_surah":   surah["jumlah_ayat"],
        "rata_kata_per_ayat": float(ayat_surah["kata"].mean()) if len(ayat_surah) > 0 else 5.0,
        "rata_huruf_per_ayat":float(ayat_surah["huruf"].mean()) if len(ayat_surah) > 0 else 20.0,
        "std_kata_per_ayat":  float(ayat_surah["kata"].std())  if len(ayat_surah) > 1 else 0.0,
    }


def get_siswa_history(siswa_id: int, surah_id: int) -> dict:
    """Hitung fitur siswa dari hafalan_log di MySQL."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT jumlah_ayat FROM hafalan_log "
        "WHERE siswa_id = %s ORDER BY tanggal ASC",
        (siswa_id,)
    )
    all_rows = cur.fetchall()

    cur.execute(
        "SELECT SUM(jumlah_ayat) AS total, COUNT(*) AS hari "
        "FROM hafalan_log WHERE siswa_id = %s AND surah_id = %s",
        (siswa_id, surah_id)
    )
    prog_row = cur.fetchone()
    conn.close()

    if not all_rows:
        return {
            "hari_ke": 1,
            "ayat_sudah_dihafal": 0,
            "progress_persen": 0.0,
            "kecepatan_avg_sebelumnya": GLOBAL_MEDIAN,
            "lag_1": GLOBAL_MEDIAN,
            "lag_2": GLOBAL_MEDIAN,
            "lag_3": GLOBAL_MEDIAN,
            "rolling_mean_3": GLOBAL_MEDIAN,
            "total_setoran_sebelumnya": 0,
        }

    ayat_list = [r["jumlah_ayat"] for r in all_rows]
    n = len(ayat_list)

    ayat_sudah = int(prog_row["total"]) if prog_row and prog_row["total"] else 0
    hari_ke = int(prog_row["hari"]) if prog_row and prog_row["hari"] else 0

    avg_speed = float(np.mean(ayat_list))

    lag_1 = float(ayat_list[-1]) if n >= 1 else GLOBAL_MEDIAN
    lag_2 = float(ayat_list[-2]) if n >= 2 else GLOBAL_MEDIAN
    lag_3 = float(ayat_list[-3]) if n >= 3 else GLOBAL_MEDIAN

    recent_3 = ayat_list[-3:] if n >= 3 else ayat_list
    rolling_mean_3 = float(np.mean(recent_3))

    recent_7 = ayat_list[-7:] if n >= 7 else ayat_list
    kecepatan_7hari = float(np.mean(recent_7))
    std_kecepatan   = float(np.std(ayat_list)) if n > 1 else 0.0

    return {
        "hari_ke": hari_ke + 1,
        "ayat_sudah_dihafal": ayat_sudah,
        "progress_persen": 0.0,
        "kecepatan_avg_sebelumnya": avg_speed,
        "std_kecepatan": std_kecepatan,
        "kecepatan_7hari": kecepatan_7hari,
        "lag_1": lag_1,
        "lag_2": lag_2,
        "lag_3": lag_3,
        "rolling_mean_3": rolling_mean_3,
        "total_setoran_sebelumnya": n,
    }


# ================================================================
# POST-PROCESSING
# ================================================================

def compute_final_speed(pred_model, rolling_mean_3, total_ayat_surah,
                        rata_kata_per_ayat, kecepatan_avg):
    """
    Post-processing: gabungkan prediksi model dengan data historis,
    sesuaikan dengan konteks surah, dan batasi ke range realistis.

    Langkah:
      1. Blending  — stabilkan prediksi dengan rolling_mean_3
      2. Context   — adjustment ringan untuk surah panjang/kompleks
      3. Clamp     — batasi ke range [1, max_dinamis]
    """
    # --- 1. Blending: 70% model + 30% rolling_mean_3 ---
    # Model kadang overpredict, rolling_mean_3 mencerminkan performa
    # aktual siswa belakangan ini. Blend keduanya untuk stabilitas.
    speed = 0.7 * pred_model + 0.3 * rolling_mean_3

    # --- 2. Context-aware adjustment ---
    # Surah panjang (>100 ayat) atau kompleks (rata-rata >15 kata/ayat)
    # cenderung lebih lambat dihafal. Turunkan sedikit (max -15%).
    penalty = 0.0
    if total_ayat_surah > 100:
        penalty += 0.05
    if rata_kata_per_ayat > 15:
        penalty += 0.05
    if total_ayat_surah > 200:
        penalty += 0.05
    speed = speed * (1.0 - penalty)

    # --- 3. Clamp ke range realistis ---
    # Min: 1 ayat/hari (tidak mungkin 0)
    # Max: 2x kecepatan rata-rata siswa (jangan terlalu optimis),
    #      atau minimal 10 ayat/hari untuk siswa baru
    max_speed = max(kecepatan_avg * 2.0, 10.0)
    speed = max(1.0, min(speed, max_speed))

    return round(speed, 1)


def generate_insight(final_speed, kecepatan_avg, rolling_mean_3,
                     total_setoran, progress_persen):
    """
    Insight sederhana berdasarkan performa siswa.
    Ditampilkan sebagai kalimat pendek di UI.
    """
    if total_setoran == 0:
        return "Belum ada data setoran. Estimasi berdasarkan rata-rata umum."

    if total_setoran < 3:
        return "Data masih sedikit, estimasi akan lebih akurat setelah beberapa setoran."

    # Bandingkan kecepatan terkini vs rata-rata keseluruhan
    ratio = rolling_mean_3 / kecepatan_avg if kecepatan_avg > 0 else 1.0

    if ratio >= 1.15:
        insight = "Performa terakhir di atas rata-rata. Pertahankan!"
    elif ratio <= 0.85:
        insight = "Kecepatan terakhir sedikit menurun dari biasanya."
    else:
        insight = "Kecepatan hafalan cukup stabil."

    if progress_persen >= 75:
        insight += " Tinggal sedikit lagi, semangat!"

    return insight


# ================================================================
# FUNGSI UTAMA
# ================================================================

def prediksi_hafalan(siswa_id: int, surah_id: int) -> dict:
    """
    Prediksi kecepatan hafalan + estimasi hari selesai.

    Pipeline:
      1. Ambil fitur surah (CSV) + fitur siswa (MySQL)
      2. Model predict → raw speed
      3. Post-processing → final speed
      4. estimasi_hari = sisa_ayat / final_speed
      5. Confidence range: low (90%) — high (120%)
    """
    surah_feat = get_surah_features(surah_id)
    if not surah_feat:
        return None

    siswa_feat = get_siswa_history(siswa_id, surah_id)

    total_ayat = surah_feat["total_ayat_surah"]
    ayat_sudah = siswa_feat["ayat_sudah_dihafal"]
    sisa = max(total_ayat - ayat_sudah, 0)
    progress = (ayat_sudah / total_ayat * 100) if total_ayat > 0 else 0

    # Susun fitur sesuai urutan training
    feature_values = {
        "total_ayat_surah":        surah_feat["total_ayat_surah"],
        "rata_kata_per_ayat":      surah_feat["rata_kata_per_ayat"],
        "rata_huruf_per_ayat":     surah_feat["rata_huruf_per_ayat"],
        "std_kata_per_ayat":       surah_feat["std_kata_per_ayat"],
        "hari_ke":                 siswa_feat["hari_ke"],
        "ayat_sudah_dihafal":      ayat_sudah,
        "progress_persen":         round(progress, 1),
        "kecepatan_avg_sebelumnya":siswa_feat["kecepatan_avg_sebelumnya"],
        "std_kecepatan":           siswa_feat["std_kecepatan"],
        "kecepatan_7hari":         siswa_feat["kecepatan_7hari"],
        "lag_1":                   siswa_feat["lag_1"],
        "lag_2":                   siswa_feat["lag_2"],
        "lag_3":                   siswa_feat["lag_3"],
        "rolling_mean_3":          siswa_feat["rolling_mean_3"],
        "total_setoran_sebelumnya":siswa_feat["total_setoran_sebelumnya"],
    }

    # --- Model predict ---
    X = pd.DataFrame([[feature_values[f] for f in FEATURES]], columns=FEATURES)
    pred_raw = float(MODEL.predict(X)[0])

    # --- Post-processing ---
    final_speed = compute_final_speed(
        pred_model=pred_raw,
        rolling_mean_3=siswa_feat["rolling_mean_3"],
        total_ayat_surah=total_ayat,
        rata_kata_per_ayat=surah_feat["rata_kata_per_ayat"],
        kecepatan_avg=siswa_feat["kecepatan_avg_sebelumnya"],
    )

    # --- Estimasi hari + confidence range ---
    if sisa > 0:
        estimasi_hari = int(np.ceil(sisa / final_speed))
        estimasi_low  = max(1, int(np.ceil(estimasi_hari * 0.9)))
        estimasi_high = int(np.ceil(estimasi_hari * 1.2))
    else:
        estimasi_hari = 0
        estimasi_low  = 0
        estimasi_high = 0

    # --- Insight ---
    insight = generate_insight(
        final_speed=final_speed,
        kecepatan_avg=siswa_feat["kecepatan_avg_sebelumnya"],
        rolling_mean_3=siswa_feat["rolling_mean_3"],
        total_setoran=siswa_feat["total_setoran_sebelumnya"],
        progress_persen=progress,
    )

    return {
        "siswa_id": siswa_id,
        "surah_id": surah_id,
        "nama_surah": db_module.get_surah_name(surah_id),
        "total_ayat": total_ayat,
        "ayat_sudah": ayat_sudah,
        "sisa_ayat": sisa,
        "prediksi_ayat_per_hari": final_speed,
        "estimasi_hari": estimasi_hari,
        "estimasi_low": estimasi_low,
        "estimasi_high": estimasi_high,
        "kecepatan_avg": round(siswa_feat["kecepatan_avg_sebelumnya"], 1),
        "progress_persen": round(progress, 1),
        "insight": insight,
    }
