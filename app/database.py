import pymysql
import hashlib
import pandas as pd
import os
from urllib.parse import urlparse

# ============================
# CONFIG MySQL
# ============================
# Support both local development and production (Render)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production: parse DATABASE_URL from Render
    url = urlparse(DATABASE_URL)
    DB_CONFIG = {
        "host": url.hostname,
        "user": url.username,
        "password": url.password,
        "database": url.path[1:],  # Remove leading slash
        "port": url.port or 3306,
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }
else:
    # Local development: XAMPP
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "quran_hafalan"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }

# ============================
# DATA QURAN — dari CSV, di-load sekali ke memory
# ============================
SURAH_DF = None      # DataFrame 114 surah
AYAT_DF = None       # DataFrame 6236 ayat
SURAH_DICT = {}      # {id: {id, nama, jumlah_ayat, jumlah_kata, jumlah_huruf}}
SURAH_LIST = []      # list of dict buat dropdown


NAMA_SURAH = [
    "", "Al-Fatihah", "Al-Baqarah", "Ali 'Imran", "An-Nisa'", "Al-Ma'idah",
    "Al-An'am", "Al-A'raf", "Al-Anfal", "At-Taubah", "Yunus",
    "Hud", "Yusuf", "Ar-Ra'd", "Ibrahim", "Al-Hijr",
    "An-Nahl", "Al-Isra'", "Al-Kahf", "Maryam", "Taha",
    "Al-Anbiya'", "Al-Hajj", "Al-Mu'minun", "An-Nur", "Al-Furqan",
    "Asy-Syu'ara'", "An-Naml", "Al-Qasas", "Al-'Ankabut", "Ar-Rum",
    "Luqman", "As-Sajdah", "Al-Ahzab", "Saba'", "Fatir",
    "Ya-Sin", "As-Saffat", "Sad", "Az-Zumar", "Gafir",
    "Fussilat", "Asy-Syura", "Az-Zukhruf", "Ad-Dukhan", "Al-Jasiyah",
    "Al-Ahqaf", "Muhammad", "Al-Fath", "Al-Hujurat", "Qaf",
    "Az-Zariyat", "At-Tur", "An-Najm", "Al-Qamar", "Ar-Rahman",
    "Al-Waqi'ah", "Al-Hadid", "Al-Mujadalah", "Al-Hasyr", "Al-Mumtahanah",
    "As-Saff", "Al-Jumu'ah", "Al-Munafiqun", "At-Tagabun", "At-Talaq",
    "At-Tahrim", "Al-Mulk", "Al-Qalam", "Al-Haqqah", "Al-Ma'arij",
    "Nuh", "Al-Jinn", "Al-Muzzammil", "Al-Muddassir", "Al-Qiyamah",
    "Al-Insan", "Al-Mursalat", "An-Naba'", "An-Nazi'at", "'Abasa",
    "At-Takwir", "Al-Infitar", "Al-Mutaffifin", "Al-Insyiqaq", "Al-Buruj",
    "At-Tariq", "Al-A'la", "Al-Gasiyah", "Al-Fajr", "Al-Balad",
    "Asy-Syams", "Al-Lail", "Ad-Duha", "Asy-Syarh", "At-Tin",
    "Al-'Alaq", "Al-Qadr", "Al-Bayyinah", "Az-Zalzalah", "Al-'Adiyat",
    "Al-Qari'ah", "At-Takasur", "Al-'Asr", "Al-Humazah", "Al-Fil",
    "Quraisy", "Al-Ma'un", "Al-Kausar", "Al-Kafirun", "An-Nasr",
    "Al-Lahab", "Al-Ikhlas", "Al-Falaq", "An-Nas"
]


def load_csv():
    """Load data Quran dari CSV ke memory. Dipanggil sekali saat startup."""
    global SURAH_DF, AYAT_DF, SURAH_DICT, SURAH_LIST

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Load surah
    SURAH_DF = pd.read_csv(os.path.join(base, "data/quran_stats.csv"), delimiter=";")
    SURAH_DF["nama"] = SURAH_DF["nomor_surah"].apply(lambda x: NAMA_SURAH[x])

    # Load ayat
    AYAT_DF = pd.read_csv(os.path.join(base, "data/ayah_stats_sync.csv"))

    # Build lookup dict & list
    for _, row in SURAH_DF.iterrows():
        sid = int(row["nomor_surah"])
        entry = {
            "id": sid,
            "nama": NAMA_SURAH[sid],
            "jumlah_ayat": int(row["jumlah_ayat"]),
            "jumlah_kata": int(row["jumlah_kata"]),
            "jumlah_huruf": int(row["jumlah_huruf"]),
        }
        SURAH_DICT[sid] = entry
        SURAH_LIST.append(entry)

    print(f"[CSV] Loaded {len(SURAH_LIST)} surah, {len(AYAT_DF)} ayat from CSV")


def get_surah(surah_id: int):
    """Get satu surah by ID dari memory."""
    return SURAH_DICT.get(surah_id)


def get_surah_list():
    """Get semua surah buat dropdown."""
    return SURAH_LIST


def get_surah_name(surah_id: int) -> str:
    """Get nama surah by ID."""
    s = SURAH_DICT.get(surah_id)
    return s["nama"] if s else f"Surah {surah_id}"


# ============================
# MySQL — cuma users + hafalan_log
# ============================
def get_db():
    """Return MySQL connection with DictCursor."""
    conn = pymysql.connect(**DB_CONFIG)
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def find_user_by_identifier(identifier: str):
    """Cari user berdasarkan email, NIS, atau NUPTK."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE email = %s OR nis = %s OR nuptk = %s",
        (identifier, identifier, identifier)
    )
    user = cur.fetchone()
    conn.close()
    return user


def init_db():
    """Load CSV + cek koneksi MySQL."""
    # Load data Quran dari CSV
    load_csv()

    # Cek MySQL
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        count = cur.fetchone()["c"]
        print(f"[DB] Connected to MySQL — {count} users in database")
        conn.close()
    except pymysql.err.OperationalError as e:
        print(f"[DB] ERROR: Gagal connect ke MySQL: {e}")
        print(f"[DB] Pastikan XAMPP MySQL running dan database 'quran_hafalan' sudah ada.")
        raise
