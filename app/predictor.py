"""
Predictor — Load model Decision Tree dan prediksi kemampuan hafalan.
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

print(f"[ML] Model loaded: {len(FEATURES)} features, R²={METADATA['metrics']['R² (test)']:.3f}")


def get_surah_features(surah_id: int) -> dict:
    """Hitung fitur surah dari CSV (ayat_df)."""
    ayat_df = db_module.AYAT_DF
    surah = db_module.SURAH_DICT.get(surah_id)
    if not surah:
        return None

    ayat_surah = ayat_df[ayat_df["surah"].astype(int) == surah_id]

    return {
        "total_ayat_surah": surah["jumlah_ayat"],
        "rata_kata_per_ayat": float(ayat_surah["kata"].mean()) if len(ayat_surah) > 0 else 5.0,
        "rata_huruf_per_ayat": float(ayat_surah["huruf"].mean()) if len(ayat_surah) > 0 else 20.0,
        "std_kata_per_ayat": float(ayat_surah["kata"].std()) if len(ayat_surah) > 1 else 0.0,
    }


def get_siswa_history(siswa_id: int, surah_id: int) -> dict:
    """Hitung fitur siswa dari hafalan_log di MySQL."""
    conn = get_db()
    cur = conn.cursor()

    # Kecepatan rata-rata siswa (semua surah)
    cur.execute(
        "SELECT AVG(jumlah_ayat) AS avg_speed FROM hafalan_log WHERE siswa_id = %s",
        (siswa_id,)
    )
    row = cur.fetchone()
    avg_speed = float(row["avg_speed"]) if row and row["avg_speed"] else 4.0  # default median

    # Progress surah ini
    cur.execute(
        "SELECT SUM(jumlah_ayat) AS total, COUNT(*) AS hari FROM hafalan_log WHERE siswa_id = %s AND surah_id = %s",
        (siswa_id, surah_id)
    )
    row = cur.fetchone()
    ayat_sudah = int(row["total"]) if row and row["total"] else 0
    hari_ke = int(row["hari"]) if row and row["hari"] else 0

    conn.close()

    return {
        "kecepatan_avg_sebelumnya": avg_speed,
        "ayat_sudah_dihafal": ayat_sudah,
        "hari_ke": hari_ke + 1,  # hari berikutnya
    }


def prediksi_hafalan(siswa_id: int, surah_id: int) -> dict:
    """
    Prediksi kemampuan hafalan siswa untuk surah tertentu.

    Returns:
        {
            "siswa_id": int,
            "surah_id": int,
            "nama_surah": str,
            "total_ayat": int,
            "ayat_sudah": int,
            "sisa_ayat": int,
            "prediksi_ayat_per_hari": float,
            "estimasi_hari": int,
            "kecepatan_avg": float,
        }
    """
    # Ambil fitur surah dari CSV
    surah_feat = get_surah_features(surah_id)
    if not surah_feat:
        return None

    # Ambil fitur siswa dari MySQL
    siswa_feat = get_siswa_history(siswa_id, surah_id)

    total_ayat = surah_feat["total_ayat_surah"]
    ayat_sudah = siswa_feat["ayat_sudah_dihafal"]
    sisa = max(total_ayat - ayat_sudah, 0)

    # Hitung progress persen
    progress = (ayat_sudah / total_ayat * 100) if total_ayat > 0 else 0

    # Susun feature array sesuai urutan training
    feature_values = {
        "total_ayat_surah": surah_feat["total_ayat_surah"],
        "rata_kata_per_ayat": surah_feat["rata_kata_per_ayat"],
        "rata_huruf_per_ayat": surah_feat["rata_huruf_per_ayat"],
        "std_kata_per_ayat": surah_feat["std_kata_per_ayat"],
        "hari_ke": siswa_feat["hari_ke"],
        "ayat_sudah_dihafal": ayat_sudah,
        "progress_persen": progress,
        "kecepatan_avg_sebelumnya": siswa_feat["kecepatan_avg_sebelumnya"],
    }

    X = pd.DataFrame([[feature_values[f] for f in FEATURES]], columns=FEATURES)
    prediksi = float(MODEL.predict(X)[0])
    prediksi = max(prediksi, 1.0)  # minimal 1 ayat/hari

    estimasi_hari = int(np.ceil(sisa / prediksi)) if sisa > 0 else 0

    return {
        "siswa_id": siswa_id,
        "surah_id": surah_id,
        "nama_surah": db_module.get_surah_name(surah_id),
        "total_ayat": total_ayat,
        "ayat_sudah": ayat_sudah,
        "sisa_ayat": sisa,
        "prediksi_ayat_per_hari": round(prediksi, 1),
        "estimasi_hari": estimasi_hari,
        "kecepatan_avg": round(siswa_feat["kecepatan_avg_sebelumnya"], 1),
        "progress_persen": round(progress, 1),
    }
