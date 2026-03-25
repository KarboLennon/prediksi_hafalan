"""
Generate data dummy hafalan yang realistis.
- 25 siswa, 3 guru
- Tiap siswa hafal 2-5 surah selama 60-90 hari
- Kecepatan bervariasi: lambat, sedang, cepat
- Ayat panjang (banyak kata) → lebih sedikit ayat/hari
- Ada hari skip (libur, sakit, dll)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from app.database import get_db, hash_password, load_csv, SURAH_DICT
import app.database as db_module

random.seed(42)
np.random.seed(42)

# Load CSV dulu
load_csv()

# ============================
# CONFIG
# ============================
NAMA_GURU = ["Ustadz Ahmad", "Ustadz Bilal", "Ustadzah Khadijah"]
NAMA_SISWA = [
    "Abdullah", "Aisyah", "Bilal", "Dina", "Farid",
    "Ghani", "Hafizah", "Ibrahim", "Jamilah", "Khalid",
    "Layla", "Mahmud", "Nadia", "Omar", "Putri",
    "Qasim", "Rahma", "Salman", "Taufik", "Umar",
    "Vina", "Wahyu", "Yasmin", "Zaid", "Zahra",
]

# Surah yang umum dihafal (pendek-sedang-panjang)
SURAH_POOL = [
    # Juz 30 (pendek, sering dihafal pertama)
    78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
    91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102,
    103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
    # Surah populer (sedang-panjang)
    1, 36, 55, 56, 67, 18, 32, 71, 72, 73, 74, 75, 76, 77,
]

# Tipe siswa
TIPE_SISWA = {
    "lambat":  {"base_speed": (2, 4),  "skip_chance": 0.30, "count": 8},
    "sedang":  {"base_speed": (5, 8),  "skip_chance": 0.20, "count": 10},
    "cepat":   {"base_speed": (9, 15), "skip_chance": 0.10, "count": 7},
}

START_DATE = datetime(2025, 9, 1)  # mulai semester


def get_avg_kata_per_ayat(surah_id):
    """Hitung rata-rata kata per ayat dari CSV."""
    ayat_surah = db_module.AYAT_DF[db_module.AYAT_DF["surah"] == surah_id]
    if len(ayat_surah) == 0:
        return 10
    return ayat_surah["kata"].mean()


def generate_hafalan(siswa_id, guru_id, surah_id, tipe, start_date):
    """Generate log hafalan satu siswa untuk satu surah."""
    surah = SURAH_DICT[surah_id]
    total_ayat = surah["jumlah_ayat"]
    avg_kata = get_avg_kata_per_ayat(surah_id)

    base_min, base_max = tipe["base_speed"]
    skip_chance = tipe["skip_chance"]

    # Faktor kompleksitas: ayat panjang → lebih lambat
    # Baseline: 5 kata/ayat = normal speed, 25 kata/ayat = 0.4x speed
    complexity_factor = max(0.3, min(1.2, 5.0 / max(avg_kata, 3)))

    logs = []
    current_ayat = 1
    current_date = start_date
    hari_ke = 0

    while current_ayat <= total_ayat:
        hari_ke += 1

        # Skip hari (libur, sakit, dll)
        if random.random() < skip_chance:
            current_date += timedelta(days=1)
            continue

        # Hitung berapa ayat hari ini
        base = random.randint(base_min, base_max)
        noise = np.random.normal(0, 1)  # variasi harian
        ayat_hari_ini = max(1, int((base + noise) * complexity_factor))

        # Jangan melebihi sisa ayat
        ayat_selesai = min(current_ayat + ayat_hari_ini - 1, total_ayat)
        jumlah = ayat_selesai - current_ayat + 1

        logs.append({
            "siswa_id": siswa_id,
            "guru_id": guru_id,
            "surah_id": surah_id,
            "ayat_mulai": current_ayat,
            "ayat_selesai": ayat_selesai,
            "jumlah_ayat": jumlah,
            "tanggal": current_date.strftime("%Y-%m-%d"),
        })

        current_ayat = ayat_selesai + 1
        current_date += timedelta(days=1)

        # Safety: jangan lebih dari 120 hari per surah
        if hari_ke > 120:
            break

    return logs


def main():
    conn = get_db()
    cur = conn.cursor()

    # ============================
    # 1. Insert guru
    # ============================
    guru_ids = []
    for nama in NAMA_GURU:
        email = nama.lower().replace(" ", ".") + "@guru.com"
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            guru_ids.append(existing["id"])
        else:
            cur.execute(
                "INSERT INTO users (nama, email, password, role) VALUES (%s, %s, %s, 'guru')",
                (nama, email, hash_password("guru123"))
            )
            guru_ids.append(cur.lastrowid)
    conn.commit()
    print(f"[+] {len(guru_ids)} guru ready (IDs: {guru_ids})")

    # ============================
    # 2. Insert siswa
    # ============================
    siswa_data = []  # [(id, tipe), ...]
    idx = 0
    for tipe_nama, tipe_config in TIPE_SISWA.items():
        for i in range(tipe_config["count"]):
            nama = NAMA_SISWA[idx]
            email = nama.lower() + "@siswa.com"
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing = cur.fetchone()
            if existing:
                sid = existing["id"]
            else:
                cur.execute(
                    "INSERT INTO users (nama, email, password, role) VALUES (%s, %s, %s, 'siswa')",
                    (nama, email, hash_password("siswa123"))
                )
                sid = cur.lastrowid
            siswa_data.append((sid, tipe_nama, tipe_config))
            idx += 1
    conn.commit()
    print(f"[+] {len(siswa_data)} siswa ready")

    # ============================
    # 3. Generate hafalan logs
    # ============================
    cur.execute("DELETE FROM hafalan_log")
    conn.commit()
    print("[~] Cleared old hafalan_log")

    total_logs = 0
    for siswa_id, tipe_nama, tipe_config in siswa_data:
        # Tiap siswa hafal 2-5 surah
        num_surah = random.randint(2, 5)
        surah_ids = random.sample(SURAH_POOL, num_surah)

        # Surah dihafal berurutan, mulai dari tanggal berbeda
        offset_days = random.randint(0, 14)
        surah_start = START_DATE + timedelta(days=offset_days)

        for surah_id in surah_ids:
            guru_id = random.choice(guru_ids)
            logs = generate_hafalan(siswa_id, guru_id, surah_id, tipe_config, surah_start)

            for log in logs:
                cur.execute(
                    """INSERT INTO hafalan_log
                    (siswa_id, guru_id, surah_id, ayat_mulai, ayat_selesai, jumlah_ayat, tanggal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (log["siswa_id"], log["guru_id"], log["surah_id"],
                     log["ayat_mulai"], log["ayat_selesai"], log["jumlah_ayat"],
                     log["tanggal"])
                )

            total_logs += len(logs)

            # Surah berikutnya mulai setelah surah sebelumnya selesai + jeda
            if logs:
                last_date = datetime.strptime(logs[-1]["tanggal"], "%Y-%m-%d")
                surah_start = last_date + timedelta(days=random.randint(1, 5))

        print(f"  [{tipe_nama:>6}] Siswa {siswa_id}: {num_surah} surah generated")

    conn.commit()
    conn.close()

    print(f"\n{'='*40}")
    print(f"DONE! Total {total_logs} hafalan logs generated")
    print(f"  - {len(siswa_data)} siswa")
    print(f"  - {len(guru_ids)} guru")
    print(f"  - Password guru:  guru123")
    print(f"  - Password siswa: siswa123")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
