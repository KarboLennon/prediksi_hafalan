from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timezone, timedelta
import hmac
import hashlib
import json
import base64

from app.database import (
    get_db, hash_password, init_db,
    get_surah, get_surah_list, get_surah_name,
    find_user_by_identifier,
)
from typing import Optional
from app.predictor import prediksi_hafalan
import app.database as db_module

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

SECRET = "quran-hafalan-secret-key-2024"


# ============================
# DB HELPER — MySQL cuma buat users + hafalan_log
# ============================
def db_fetchall(sql, params=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    conn.close()
    return rows


def db_fetchone(sql, params=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    row = cur.fetchone()
    conn.close()
    return row


def db_execute(sql, params=None, commit=True):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    if commit:
        conn.commit()
    conn.close()


# ============================
# SESSION HELPERS
# ============================
def create_session(user_id: int, role: str, nama: str) -> str:
    data = json.dumps({"id": user_id, "role": role, "nama": nama})
    payload = base64.b64encode(data.encode()).decode()
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def get_session(request: Request):
    cookie = request.cookies.get("session")
    if not cookie or "." not in cookie:
        return None
    payload, sig = cookie.rsplit(".", 1)
    expected = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return json.loads(base64.b64decode(payload))


def require_role(request: Request, role: str):
    user = get_session(request)
    if not user:
        return None
    if user["role"] != role:
        return None
    # Cek must_change_password dari DB
    db_user = db_fetchone("SELECT must_change_password FROM users WHERE id = %s", (user["id"],))
    if db_user and db_user.get("must_change_password"):
        return None  # akan redirect ke login → ganti password
    return user


# ============================
# STARTUP
# ============================
@app.on_event("startup")
def startup():
    init_db()


# ============================
# AUTH ROUTES
# ============================
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    user = get_session(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return RedirectResponse(f"/{user['role']}", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, identifier: str = Form(...), password: str = Form(...)):
    # Cari user by email, NIS, atau NUPTK
    user = find_user_by_identifier(identifier)

    if not user or user["password"] != hash_password(password):
        return templates.TemplateResponse("login.html", {
            "request": request, "user": None, "error": "NIS/NUPTK/Email atau password salah"
        })

    # Cek apakah harus ganti password dulu
    if user.get("must_change_password"):
        token = create_session(user["id"], user["role"], user["nama"])
        response = RedirectResponse("/ganti-password", status_code=302)
        response.set_cookie("session", token, httponly=True, max_age=86400)
        return response

    token = create_session(user["id"], user["role"], user["nama"])
    response = RedirectResponse(f"/{user['role']}", status_code=302)
    response.set_cookie("session", token, httponly=True, max_age=86400)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("session")
    return response


# ============================
# GANTI PASSWORD (first login)
# ============================
@app.get("/ganti-password", response_class=HTMLResponse)
def ganti_password_page(request: Request):
    user = get_session(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Cek apakah memang harus ganti password
    db_user = db_fetchone("SELECT must_change_password FROM users WHERE id = %s", (user["id"],))
    if not db_user or not db_user["must_change_password"]:
        return RedirectResponse(f"/{user['role']}", status_code=302)

    return templates.TemplateResponse("ganti_password.html", {
        "request": request, "user": user, "error": None, "alert": None,
    })


@app.post("/ganti-password", response_class=HTMLResponse)
def ganti_password(
    request: Request,
    password_baru: str = Form(...),
    konfirmasi: str = Form(...),
):
    user = get_session(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    if len(password_baru) < 6:
        return templates.TemplateResponse("ganti_password.html", {
            "request": request, "user": user, "alert": None,
            "error": "Password minimal 6 karakter",
        })

    if password_baru != konfirmasi:
        return templates.TemplateResponse("ganti_password.html", {
            "request": request, "user": user, "alert": None,
            "error": "Password dan konfirmasi tidak cocok",
        })

    # Update password + set must_change_password = 0
    db_execute(
        "UPDATE users SET password = %s, must_change_password = 0 WHERE id = %s",
        (hash_password(password_baru), user["id"])
    )

    response = RedirectResponse(f"/{user['role']}", status_code=302)
    return response


# ============================
# ADMIN ROUTES
# ============================
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = require_role(request, "admin")
    if not user:
        return RedirectResponse("/login", status_code=302)

    users = db_fetchall("SELECT * FROM users ORDER BY role, nama")
    total_guru = db_fetchone("SELECT COUNT(*) AS c FROM users WHERE role='guru'")["c"]
    total_siswa = db_fetchone("SELECT COUNT(*) AS c FROM users WHERE role='siswa'")["c"]
    total_hafalan = db_fetchone("SELECT COUNT(*) AS c FROM hafalan_log")["c"]

    alert = None
    alert_type = request.query_params.get("alert")
    alert_msg = request.query_params.get("msg")
    if alert_type and alert_msg:
        alert = {"type": alert_type, "message": alert_msg}

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "users": users,
        "total_guru": total_guru,
        "total_siswa": total_siswa,
        "total_hafalan": total_hafalan,
        "alert": alert,
        "active_page": "dashboard",
    })


@app.post("/admin/tambah-user")
def admin_tambah_user(
    request: Request,
    nama: str = Form(...),
    role: str = Form(...),
    nis: Optional[str] = Form(None),
    nuptk: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
):
    user = require_role(request, "admin")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if role not in ("guru", "siswa"):
        return RedirectResponse("/admin?alert=danger&msg=Role tidak valid", status_code=302)

    default_password = ""  # Will be set based on role

    # Validasi: siswa harus punya NIS, guru harus punya NUPTK
    if role == "siswa":
        if not nis or not nis.strip():
            return RedirectResponse("/admin?alert=danger&msg=NIS wajib diisi untuk siswa", status_code=302)
        nis = nis.strip()
        nuptk = None
        # Cek duplikat NIS
        existing = db_fetchone("SELECT id FROM users WHERE nis = %s", (nis,))
        if existing:
            return RedirectResponse("/admin?alert=danger&msg=NIS sudah terdaftar", status_code=302)
        # Password default = NIS
        default_password = nis

    elif role == "guru":
        if not nuptk or not nuptk.strip():
            return RedirectResponse("/admin?alert=danger&msg=NUPTK wajib diisi untuk guru", status_code=302)
        nuptk = nuptk.strip()
        nis = None
        # Cek duplikat NUPTK
        existing = db_fetchone("SELECT id FROM users WHERE nuptk = %s", (nuptk,))
        if existing:
            return RedirectResponse("/admin?alert=danger&msg=NUPTK sudah terdaftar", status_code=302)
        # Password default = NUPTK
        default_password = nuptk

    # Email opsional — cek duplikat kalau diisi
    email = email.strip() if email and email.strip() else None
    if email:
        existing = db_fetchone("SELECT id FROM users WHERE email = %s", (email,))
        if existing:
            return RedirectResponse("/admin?alert=danger&msg=Email sudah terdaftar", status_code=302)

    db_execute(
        "INSERT INTO users (nama, nis, nuptk, email, password, must_change_password, role) VALUES (%s, %s, %s, %s, %s, 1, %s)",
        (nama, nis, nuptk, email, hash_password(default_password), role)
    )

    id_label = f"NIS: {nis}" if role == "siswa" else f"NUPTK: {nuptk}"
    return RedirectResponse(
        f"/admin?alert=success&msg={nama} berhasil ditambahkan ({id_label}). Password default = {default_password}",
        status_code=302
    )


@app.post("/admin/hapus-user/{user_id}")
def admin_hapus_user(request: Request, user_id: int):
    user = require_role(request, "admin")
    if not user:
        return RedirectResponse("/login", status_code=302)

    target = db_fetchone("SELECT * FROM users WHERE id = %s", (user_id,))
    if not target or target["role"] == "admin":
        return RedirectResponse("/admin?alert=danger&msg=Tidak bisa menghapus user ini", status_code=302)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM hafalan_log WHERE siswa_id = %s OR guru_id = %s", (user_id, user_id))
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin?alert=success&msg=User berhasil dihapus", status_code=302)


@app.post("/admin/reset-password/{user_id}")
def admin_reset_password(request: Request, user_id: int):
    """Reset password user ke NIS/NUPTK dan paksa ganti password."""
    user = require_role(request, "admin")
    if not user:
        return RedirectResponse("/login", status_code=302)

    target = db_fetchone("SELECT * FROM users WHERE id = %s", (user_id,))
    if not target or target["role"] == "admin":
        return RedirectResponse("/admin?alert=danger&msg=Tidak bisa reset user ini", status_code=302)

    # Reset ke NIS atau NUPTK
    if target["role"] == "siswa" and target.get("nis"):
        new_pw = target["nis"]
    elif target["role"] == "guru" and target.get("nuptk"):
        new_pw = target["nuptk"]
    else:
        return RedirectResponse("/admin?alert=danger&msg=User tidak punya NIS/NUPTK", status_code=302)

    db_execute(
        "UPDATE users SET password = %s, must_change_password = 1 WHERE id = %s",
        (hash_password(new_pw), user_id)
    )
    return RedirectResponse(
        f"/admin?alert=success&msg=Password {target['nama']} direset. Password baru = {new_pw}",
        status_code=302
    )


# ============================
# GURU ROUTES
# ============================
WIB = timezone(timedelta(hours=7))


def _get_alert(request: Request):
    t = request.query_params.get("alert")
    m = request.query_params.get("msg")
    return {"type": t, "message": m} if t and m else None


@app.get("/guru", response_class=HTMLResponse)
def guru_dashboard(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    now_wib = datetime.now(WIB)
    today_str = now_wib.strftime("%Y-%m-%d")

    lb_bulan = int(request.query_params.get("lb_bulan", now_wib.month))
    lb_tahun = int(request.query_params.get("lb_tahun", now_wib.year))

    leaderboard_hari = db_fetchall("""
        SELECT u.id AS siswa_id, u.nama, SUM(h.jumlah_ayat) AS total_ayat, COUNT(h.id) AS total_setoran
        FROM hafalan_log h JOIN users u ON u.id = h.siswa_id
        WHERE h.tanggal = %s
        GROUP BY h.siswa_id ORDER BY total_ayat DESC LIMIT 10
    """, (today_str,))

    leaderboard_bulan = db_fetchall("""
        SELECT u.id AS siswa_id, u.nama, SUM(h.jumlah_ayat) AS total_ayat, COUNT(h.id) AS total_setoran,
               COUNT(DISTINCT h.tanggal) AS hari_aktif
        FROM hafalan_log h JOIN users u ON u.id = h.siswa_id
        WHERE MONTH(h.tanggal) = %s AND YEAR(h.tanggal) = %s
        GROUP BY h.siswa_id ORDER BY total_ayat DESC LIMIT 10
    """, (lb_bulan, lb_tahun))

    tahun_raw = db_fetchall("SELECT DISTINCT YEAR(tanggal) AS y FROM hafalan_log ORDER BY y DESC")
    tahun_list = [r["y"] for r in tahun_raw] if tahun_raw else [now_wib.year]

    return templates.TemplateResponse("guru/dashboard.html", {
        "request": request, "user": user, "alert": _get_alert(request),
        "active_page": "dashboard",
        "leaderboard_hari": leaderboard_hari, "leaderboard_bulan": leaderboard_bulan,
        "lb_bulan": lb_bulan, "lb_tahun": lb_tahun,
        "tahun_list": tahun_list, "today_str": today_str,
    })


@app.get("/guru/input-hafalan", response_class=HTMLResponse)
def guru_input_hafalan_page(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    daftar_siswa = db_fetchall("SELECT id, nama FROM users WHERE role='siswa' ORDER BY nama")
    daftar_surah = get_surah_list()

    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 10))
    if per_page not in (10, 25, 50, 100, 250):
        per_page = 10

    total_row = db_fetchone("SELECT COUNT(*) AS c FROM hafalan_log WHERE guru_id = %s", (user["id"],))
    total_logs = total_row["c"] if total_row else 0
    total_pages = max(1, (total_logs + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    logs_raw = db_fetchall("""
        SELECT h.*, u.nama AS nama_siswa FROM hafalan_log h
        JOIN users u ON u.id = h.siswa_id
        WHERE h.guru_id = %s ORDER BY h.tanggal DESC, h.created_at DESC
        LIMIT %s OFFSET %s
    """, (user["id"], per_page, offset))

    logs = [{**log, "nama_surah": get_surah_name(log["surah_id"])} for log in logs_raw]

    return templates.TemplateResponse("guru/input_hafalan.html", {
        "request": request, "user": user, "alert": _get_alert(request),
        "active_page": "input_hafalan",
        "daftar_siswa": daftar_siswa, "daftar_surah": daftar_surah,
        "logs": logs, "page": page, "per_page": per_page,
        "total_logs": total_logs, "total_pages": total_pages,
    })


@app.get("/guru/data-pribadi", response_class=HTMLResponse)
def guru_data_pribadi(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    db_user = db_fetchone("SELECT * FROM users WHERE id = %s", (user["id"],))
    return templates.TemplateResponse("guru/data_pribadi.html", {
        "request": request, "user": user, "db_user": db_user,
        "alert": _get_alert(request), "active_page": "data_pribadi",
    })


@app.post("/guru/data-pribadi")
def guru_data_pribadi_post(
    request: Request,
    provinsi: Optional[str] = Form(None),
    kabupaten: Optional[str] = Form(None),
    kecamatan: Optional[str] = Form(None),
    kelurahan: Optional[str] = Form(None),
    alamat_detail: Optional[str] = Form(None),
):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    db_execute("""
        UPDATE users SET provinsi=%s, kabupaten=%s, kecamatan=%s, kelurahan=%s, alamat_detail=%s
        WHERE id=%s
    """, (
        provinsi or None, kabupaten or None, kecamatan or None,
        kelurahan or None, alamat_detail or None, user["id"]
    ))
    return RedirectResponse("/guru/data-pribadi?alert=success&msg=Data pribadi berhasil disimpan", status_code=302)


@app.get("/guru/ubah-password", response_class=HTMLResponse)
def guru_ubah_password(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse("guru/ubah_password.html", {
        "request": request, "user": user,
        "alert": _get_alert(request), "active_page": "ubah_password",
    })


@app.post("/guru/ubah-password")
def guru_ubah_password_post(
    request: Request,
    password_lama: str = Form(...),
    password_baru: str = Form(...),
    konfirmasi: str = Form(...),
):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    db_user = db_fetchone("SELECT password FROM users WHERE id = %s", (user["id"],))
    if db_user["password"] != hash_password(password_lama):
        return templates.TemplateResponse("guru/ubah_password.html", {
            "request": request, "user": user, "active_page": "ubah_password",
            "alert": {"type": "danger", "message": "Password lama salah"},
        })

    if len(password_baru) < 6:
        return templates.TemplateResponse("guru/ubah_password.html", {
            "request": request, "user": user, "active_page": "ubah_password",
            "alert": {"type": "danger", "message": "Password baru minimal 6 karakter"},
        })

    if password_baru != konfirmasi:
        return templates.TemplateResponse("guru/ubah_password.html", {
            "request": request, "user": user, "active_page": "ubah_password",
            "alert": {"type": "danger", "message": "Konfirmasi password tidak cocok"},
        })

    db_execute("UPDATE users SET password = %s WHERE id = %s", (hash_password(password_baru), user["id"]))
    return RedirectResponse("/guru/ubah-password?alert=success&msg=Password berhasil diubah", status_code=302)


# ============================
# GURU — REKAP / LAPORAN
# ============================
@app.get("/guru/rekap", response_class=HTMLResponse)
def guru_rekap(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    daftar_siswa = db_fetchall("SELECT id, nama FROM users WHERE role='siswa' ORDER BY nama")

    siswa_id = request.query_params.get("siswa_id")
    rekap = None
    selected_siswa = int(siswa_id) if siswa_id else None

    if selected_siswa:
        rekap = _build_rekap(selected_siswa)

    return templates.TemplateResponse("guru/rekap.html", {
        "request": request, "user": user, "alert": _get_alert(request),
        "active_page": "rekap",
        "daftar_siswa": daftar_siswa,
        "rekap": rekap,
        "selected_siswa": selected_siswa,
    })


@app.get("/guru/rekap/cetak/{siswa_id}", response_class=HTMLResponse)
def guru_rekap_cetak(request: Request, siswa_id: int):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    rekap = _build_rekap(siswa_id)
    if not rekap:
        return RedirectResponse("/guru/rekap?alert=danger&msg=Data tidak ditemukan", status_code=302)

    now_wib = datetime.now(WIB)
    tanggal_cetak = now_wib.strftime("%d %B %Y")

    return templates.TemplateResponse("guru/rekap_cetak.html", {
        "request": request,
        "rekap": rekap,
        "guru_nama": user["nama"],
        "tanggal_cetak": tanggal_cetak,
    })


def _build_rekap(siswa_id: int):
    """Build rekap data for a specific student (total keseluruhan)."""
    siswa = db_fetchone("SELECT id, nama, nis FROM users WHERE id = %s AND role = 'siswa'", (siswa_id,))
    if not siswa:
        return None

    params = [siswa_id]

    # Logs detail
    logs_raw = db_fetchall("""
        SELECT h.*, u.nama AS nama_guru
        FROM hafalan_log h
        JOIN users u ON u.id = h.guru_id
        WHERE h.siswa_id = %s
        ORDER BY h.tanggal ASC, h.created_at ASC
    """, params)

    logs = []
    for log in logs_raw:
        log["nama_surah"] = get_surah_name(log["surah_id"])
        logs.append(log)

    # Progress per surah
    progress_raw = db_fetchall("""
        SELECT surah_id,
               SUM(jumlah_ayat) AS ayat_dihafal,
               COUNT(id) AS hari_aktif
        FROM hafalan_log h
        WHERE h.siswa_id = %s
        GROUP BY surah_id ORDER BY surah_id
    """, params)

    progress = []
    for p in progress_raw:
        surah = get_surah(p["surah_id"])
        total_ayat = surah["jumlah_ayat"] if surah else 1
        persen = round(p["ayat_dihafal"] / total_ayat * 100, 1)

        # Last rating for this surah
        lr_row = db_fetchone(
            "SELECT rating FROM hafalan_log WHERE siswa_id = %s AND surah_id = %s AND rating > 0 ORDER BY tanggal DESC, created_at DESC LIMIT 1",
            (siswa_id, p["surah_id"])
        )
        last_rating = lr_row["rating"] if lr_row and lr_row.get("rating") else 0

        progress.append({
            "surah_id": p["surah_id"],
            "nama_surah": get_surah_name(p["surah_id"]),
            "total_ayat": total_ayat,
            "ayat_dihafal": int(p["ayat_dihafal"]),
            "hari_aktif": p["hari_aktif"],
            "persen": min(persen, 100.0),
            "last_rating": last_rating,
        })

    # Stats
    total_ayat = sum(p["ayat_dihafal"] for p in progress) if progress else 0
    total_setoran = len(logs)
    hari_aktif_row = db_fetchone(
        "SELECT COUNT(DISTINCT tanggal) AS c FROM hafalan_log WHERE siswa_id = %s",
        (siswa_id,)
    )
    hari_aktif = hari_aktif_row["c"] if hari_aktif_row else 0

    avg_rating_row = db_fetchone(
        "SELECT ROUND(AVG(rating), 1) AS avg_r FROM hafalan_log WHERE siswa_id = %s AND rating > 0",
        (siswa_id,)
    )
    avg_rating = float(avg_rating_row["avg_r"]) if avg_rating_row and avg_rating_row["avg_r"] else 0

    # Build all 114 surah list with progress & avg rating
    # Create lookup from progress data
    progress_map = {p["surah_id"]: p for p in progress}

    # Get avg rating per surah for this student
    avg_rating_per_surah = {}
    rating_rows = db_fetchall(
        "SELECT surah_id, ROUND(AVG(rating), 1) AS avg_r FROM hafalan_log WHERE siswa_id = %s AND rating > 0 GROUP BY surah_id",
        (siswa_id,)
    )
    for rr in rating_rows:
        avg_rating_per_surah[rr["surah_id"]] = float(rr["avg_r"]) if rr["avg_r"] else 0

    surah_list = get_surah_list()
    all_surah = []
    for s in surah_list:
        sid = s["id"]
        p = progress_map.get(sid)
        ayat_dihafal = p["ayat_dihafal"] if p else 0
        total_ayat = s["jumlah_ayat"]
        persen = min(round(ayat_dihafal / total_ayat * 100, 1), 100.0) if total_ayat > 0 else 0

        if persen >= 100:
            status = "selesai"
        elif ayat_dihafal > 0:
            status = "proses"
        else:
            status = "belum"

        all_surah.append({
            "nomor": sid,
            "nama": s["nama"],
            "total_ayat": total_ayat,
            "ayat_dihafal": ayat_dihafal,
            "persen": persen,
            "status": status,
            "avg_rating": avg_rating_per_surah.get(sid, 0),
        })

    return {
        "siswa": siswa,
        "logs": logs,
        "progress": progress,
        "all_surah": all_surah,
        "stats": {
            "total_ayat": total_ayat,
            "total_surah": len(progress),
            "total_setoran": total_setoran,
            "hari_aktif": hari_aktif,
            "avg_rating": avg_rating,
        },
    }


# ============================
# GURU — DAFTAR SISWA
# ============================
@app.get("/guru/daftar-siswa", response_class=HTMLResponse)
def guru_daftar_siswa(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    siswa_list = db_fetchall("""
        SELECT
            u.id, u.nama, u.nis,
            COALESCE(s.total_ayat, 0)    AS total_ayat,
            COALESCE(s.surah_aktif, 0)   AS surah_aktif,
            COALESCE(s.hari_aktif, 0)    AS hari_aktif,
            COALESCE(s.total_setoran, 0) AS total_setoran,
            s.last_tanggal
        FROM users u
        LEFT JOIN (
            SELECT
                siswa_id,
                SUM(jumlah_ayat)            AS total_ayat,
                COUNT(DISTINCT surah_id)    AS surah_aktif,
                COUNT(DISTINCT tanggal)     AS hari_aktif,
                COUNT(id)                   AS total_setoran,
                MAX(tanggal)                AS last_tanggal
            FROM hafalan_log
            GROUP BY siswa_id
        ) s ON s.siswa_id = u.id
        WHERE u.role = 'siswa'
        ORDER BY total_ayat DESC, u.nama ASC
    """)

    return templates.TemplateResponse("guru/daftar_siswa.html", {
        "request": request, "user": user, "alert": _get_alert(request),
        "active_page": "daftar_siswa",
        "siswa_list": siswa_list,
    })


# ============================
# GURU — DETAIL SISWA
# ============================
@app.get("/guru/siswa/{siswa_id}", response_class=HTMLResponse)
def guru_detail_siswa(request: Request, siswa_id: int):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    siswa = db_fetchone("SELECT id, nama, nis FROM users WHERE id = %s AND role = 'siswa'", (siswa_id,))
    if not siswa:
        return RedirectResponse("/guru/daftar-siswa?alert=danger&msg=Siswa tidak ditemukan", status_code=302)

    # Progress per surah
    progress_raw = db_fetchall("""
        SELECT surah_id, SUM(jumlah_ayat) AS ayat_dihafal, COUNT(id) AS hari_aktif
        FROM hafalan_log
        WHERE siswa_id = %s
        GROUP BY surah_id ORDER BY surah_id
    """, (siswa_id,))

    progress = []
    for p in progress_raw:
        surah = get_surah(p["surah_id"])
        total_ayat = surah["jumlah_ayat"] if surah else 1
        persen = round(p["ayat_dihafal"] / total_ayat * 100, 1)
        lr_row = db_fetchone(
            "SELECT rating FROM hafalan_log WHERE siswa_id = %s AND surah_id = %s AND rating > 0 ORDER BY tanggal DESC, created_at DESC LIMIT 1",
            (siswa_id, p["surah_id"])
        )
        progress.append({
            "surah_id": p["surah_id"],
            "nama_surah": get_surah_name(p["surah_id"]),
            "total_ayat": total_ayat,
            "ayat_dihafal": int(p["ayat_dihafal"]),
            "hari_aktif": p["hari_aktif"],
            "persen": min(persen, 100.0),
            "last_rating": lr_row["rating"] if lr_row and lr_row["rating"] else 0,
        })

    # Stats
    total_ayat_dihafal = sum(p["ayat_dihafal"] for p in progress)
    total_hari_row = db_fetchone("SELECT COUNT(DISTINCT tanggal) AS c FROM hafalan_log WHERE siswa_id = %s", (siswa_id,))
    total_hari = total_hari_row["c"] if total_hari_row else 0
    avg_rating_row = db_fetchone(
        "SELECT ROUND(AVG(rating), 1) AS avg_r FROM hafalan_log WHERE siswa_id = %s AND rating > 0", (siswa_id,)
    )
    avg_rating = float(avg_rating_row["avg_r"]) if avg_rating_row and avg_rating_row["avg_r"] else 0

    # Prediksi AI untuk semua surah aktif
    prediksi_list = []
    for p in progress:
        pred = prediksi_hafalan(siswa_id, p["surah_id"])
        if pred:
            prediksi_list.append(pred)

    # Riwayat setoran terbaru (20 terakhir)
    logs_raw = db_fetchall("""
        SELECT h.*, u.nama AS nama_guru
        FROM hafalan_log h
        JOIN users u ON u.id = h.guru_id
        WHERE h.siswa_id = %s
        ORDER BY h.tanggal DESC, h.created_at DESC
        LIMIT 20
    """, (siswa_id,))
    for log in logs_raw:
        log["nama_surah"] = get_surah_name(log["surah_id"])

    return templates.TemplateResponse("guru/detail_siswa.html", {
        "request": request, "user": user,
        "active_page": "daftar_siswa",
        "siswa": siswa,
        "progress": progress,
        "prediksi_list": prediksi_list,
        "logs": logs_raw,
        "total_ayat_dihafal": total_ayat_dihafal,
        "total_surah_aktif": len(progress),
        "total_hari": total_hari,
        "avg_rating": avg_rating,
    })


@app.post("/guru/input-hafalan")
def guru_input_hafalan(
    request: Request,
    siswa_id: int = Form(...),
    surah_id: int = Form(...),
    ayat_mulai: int = Form(...),
    ayat_selesai: int = Form(...),
    catatan: Optional[str] = Form(None),
    rating: int = Form(0),
):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if ayat_selesai < ayat_mulai:
        return RedirectResponse("/guru/input-hafalan?alert=danger&msg=Ayat selesai harus >= ayat mulai", status_code=302)

    surah = get_surah(surah_id)
    if not surah:
        return RedirectResponse("/guru/input-hafalan?alert=danger&msg=Surah tidak ditemukan", status_code=302)

    if ayat_mulai < 1 or ayat_selesai > surah["jumlah_ayat"]:
        return RedirectResponse(
            f"/guru/input-hafalan?alert=danger&msg=Ayat harus antara 1 - {surah['jumlah_ayat']}",
            status_code=302
        )

    jumlah = ayat_selesai - ayat_mulai + 1
    tanggal = datetime.now(WIB).strftime("%Y-%m-%d")

    rating = max(0, min(5, rating))
    db_execute(
        "INSERT INTO hafalan_log (siswa_id, guru_id, surah_id, ayat_mulai, ayat_selesai, jumlah_ayat, catatan, tanggal, rating) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (siswa_id, user["id"], surah_id, ayat_mulai, ayat_selesai, jumlah, catatan or None, tanggal, rating)
    )
    return RedirectResponse(f"/guru/input-hafalan?alert=success&msg=Hafalan berhasil disimpan ({jumlah} ayat)", status_code=302)


@app.post("/guru/edit-hafalan/{log_id}")
def guru_edit_hafalan(
    request: Request,
    log_id: int,
    surah_id: int = Form(...),
    ayat_mulai: int = Form(...),
    ayat_selesai: int = Form(...),
    catatan: Optional[str] = Form(None),
    rating: int = Form(0),
):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Pastikan log ini milik guru yang login
    log = db_fetchone("SELECT * FROM hafalan_log WHERE id = %s AND guru_id = %s", (log_id, user["id"]))
    if not log:
        return RedirectResponse("/guru/input-hafalan?alert=danger&msg=Log tidak ditemukan atau bukan milik Anda", status_code=302)

    if ayat_selesai < ayat_mulai:
        return RedirectResponse("/guru/input-hafalan?alert=danger&msg=Ayat selesai harus >= ayat mulai", status_code=302)

    surah = get_surah(surah_id)
    if not surah:
        return RedirectResponse("/guru/input-hafalan?alert=danger&msg=Surah tidak valid", status_code=302)

    if ayat_mulai < 1 or ayat_selesai > surah["jumlah_ayat"]:
        return RedirectResponse(
            f"/guru/input-hafalan?alert=danger&msg=Ayat harus antara 1 - {surah['jumlah_ayat']}",
            status_code=302
        )

    jumlah = ayat_selesai - ayat_mulai + 1
    rating = max(0, min(5, rating))
    db_execute(
        "UPDATE hafalan_log SET surah_id=%s, ayat_mulai=%s, ayat_selesai=%s, jumlah_ayat=%s, catatan=%s, rating=%s WHERE id=%s",
        (surah_id, ayat_mulai, ayat_selesai, jumlah, catatan or None, rating, log_id)
    )
    return RedirectResponse("/guru/input-hafalan?alert=success&msg=Log hafalan berhasil diperbarui", status_code=302)


# ============================
# SISWA ROUTES
# ============================
@app.get("/siswa", response_class=HTMLResponse)
def siswa_dashboard(request: Request):
    user = require_role(request, "siswa")
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Get pagination and filter parameters for riwayat
    page = int(request.query_params.get("page", 1))
    per_page = 10
    filter_surah = request.query_params.get("filter_surah", "")
    
    # Get pagination and filter parameters for prediksi AI
    ai_page = int(request.query_params.get("ai_page", 1))
    ai_per_page = 10
    ai_filter_surah = request.query_params.get("ai_filter_surah", "")
    
    # Progress per surah — query MySQL, join nama surah dari CSV
    progress_raw = db_fetchall("""
        SELECT
            surah_id,
            SUM(jumlah_ayat) AS ayat_dihafal,
            COUNT(id) AS hari_aktif
        FROM hafalan_log
        WHERE siswa_id = %s
        GROUP BY surah_id
        ORDER BY surah_id
    """, (user["id"],))

    progress = []
    for p in progress_raw:
        surah = get_surah(p["surah_id"])
        total_ayat = surah["jumlah_ayat"] if surah else 1
        persen = round(p["ayat_dihafal"] / total_ayat * 100, 1)
        progress.append({
            "nama_surah": get_surah_name(p["surah_id"]),
            "total_ayat": total_ayat,
            "ayat_dihafal": int(p["ayat_dihafal"]),
            "hari_aktif": p["hari_aktif"],
            "persen": min(persen, 100.0),
        })

    # Stats
    total_ayat_dihafal = sum(p["ayat_dihafal"] for p in progress) if progress else 0
    total_surah_aktif = len(progress)
    total_hari_row = db_fetchone(
        "SELECT COUNT(DISTINCT tanggal) AS c FROM hafalan_log WHERE siswa_id = %s",
        (user["id"],)
    )
    total_hari = total_hari_row["c"] if total_hari_row else 0

    # Rata-rata rating (hanya yang sudah dinilai, rating > 0)
    avg_rating_row = db_fetchone(
        "SELECT ROUND(AVG(rating), 1) AS avg_r FROM hafalan_log WHERE siswa_id = %s AND rating > 0",
        (user["id"],)
    )
    avg_rating = float(avg_rating_row["avg_r"]) if avg_rating_row and avg_rating_row["avg_r"] else 0

    # Surah yang sudah selesai (progress >= 100%)
    surah_selesai = []
    for p in progress:
        if p["persen"] >= 100:
            # Ambil rating terakhir untuk surah ini
            sid = None
            for s_id, s_data in db_module.SURAH_DICT.items():
                if s_data["nama"] == p["nama_surah"]:
                    sid = s_id
                    break
            last_rating = 0
            if sid:
                lr_row = db_fetchone(
                    "SELECT rating FROM hafalan_log WHERE siswa_id = %s AND surah_id = %s ORDER BY tanggal DESC, created_at DESC LIMIT 1",
                    (user["id"], sid)
                )
                if lr_row and lr_row["rating"]:
                    last_rating = lr_row["rating"]
            surah_selesai.append({
                "nama_surah": p["nama_surah"],
                "total_ayat": p["total_ayat"],
                "last_rating": last_rating,
            })

    # Build query for riwayat with filter
    where_clause = "h.siswa_id = %s"
    params = [user["id"]]
    
    if filter_surah:
        # Find surah_id from name
        surah_id = None
        for sid, s in db_module.SURAH_DICT.items():
            if filter_surah.lower() in s["nama"].lower():
                surah_id = sid
                break
        
        if surah_id:
            where_clause += " AND h.surah_id = %s"
            params.append(surah_id)

    # Count total records for pagination
    count_query = f"""
        SELECT COUNT(*) as total
        FROM hafalan_log h
        JOIN users u ON u.id = h.guru_id
        WHERE {where_clause}
    """
    total_records = db_fetchone(count_query, params)["total"]
    total_pages = (total_records + per_page - 1) // per_page

    # Get paginated data
    offset = (page - 1) * per_page
    logs_raw = db_fetchall(f"""
        SELECT h.*, u.nama AS nama_guru
        FROM hafalan_log h
        JOIN users u ON u.id = h.guru_id
        WHERE {where_clause}
        ORDER BY h.tanggal DESC, h.created_at DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])

    logs = []
    for log in logs_raw:
        log["nama_surah"] = get_surah_name(log["surah_id"])
        logs.append(log)

    # Get unique surah names for filter dropdown
    surah_options = []
    surah_ids_in_logs = db_fetchall("""
        SELECT DISTINCT surah_id 
        FROM hafalan_log 
        WHERE siswa_id = %s 
        ORDER BY surah_id
    """, (user["id"],))
    
    for row in surah_ids_in_logs:
        surah_name = get_surah_name(row["surah_id"])
        if surah_name:
            surah_options.append(surah_name)

    # Prediksi untuk surah yang sedang aktif dengan pagination dan filter
    all_prediksi_list = []
    for p in progress:
        # cari surah_id dari nama
        for sid, s in db_module.SURAH_DICT.items():
            if s["nama"] == p["nama_surah"]:
                pred = prediksi_hafalan(user["id"], sid)
                if pred:
                    all_prediksi_list.append(pred)
                break

    # Filter prediksi berdasarkan ai_filter_surah
    filtered_prediksi_list = []
    if ai_filter_surah:
        for pred in all_prediksi_list:
            if ai_filter_surah.lower() in pred["nama_surah"].lower():
                filtered_prediksi_list.append(pred)
    else:
        filtered_prediksi_list = all_prediksi_list

    # Pagination untuk prediksi AI
    ai_total_records = len(filtered_prediksi_list)
    ai_total_pages = (ai_total_records + ai_per_page - 1) // ai_per_page if ai_total_records > 0 else 1
    ai_offset = (ai_page - 1) * ai_per_page
    prediksi_list = filtered_prediksi_list[ai_offset:ai_offset + ai_per_page]

    # Get unique surah names for AI filter dropdown (from progress data)
    ai_surah_options = [p["nama_surah"] for p in progress if p["nama_surah"]]

    return templates.TemplateResponse("siswa/dashboard.html", {
        "request": request,
        "user": user,
        "progress": progress,
        "logs": logs,
        "total_ayat_dihafal": total_ayat_dihafal,
        "total_surah_aktif": total_surah_aktif,
        "total_hari": total_hari,
        "avg_rating": avg_rating,
        "surah_selesai": surah_selesai,
        "prediksi_list": prediksi_list,
        "alert": None,
        # Pagination data for riwayat
        "current_page": page,
        "total_pages": total_pages,
        "total_records": total_records,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else None,
        "next_page": page + 1 if page < total_pages else None,
        # Filter data for riwayat
        "filter_surah": filter_surah,
        "surah_options": surah_options,
        # Pagination data for AI predictions
        "ai_current_page": ai_page,
        "ai_total_pages": ai_total_pages,
        "ai_total_records": ai_total_records,
        "ai_per_page": ai_per_page,
        "ai_has_prev": ai_page > 1,
        "ai_has_next": ai_page < ai_total_pages,
        "ai_prev_page": ai_page - 1 if ai_page > 1 else None,
        "ai_next_page": ai_page + 1 if ai_page < ai_total_pages else None,
        # Filter data for AI predictions
        "ai_filter_surah": ai_filter_surah,
        "ai_surah_options": ai_surah_options,
        "active_page": "dashboard",
    })


# ============================
# SISWA — REKAP HAFALAN
# ============================
@app.get("/siswa/rekap", response_class=HTMLResponse)
def siswa_rekap(request: Request):
    user = require_role(request, "siswa")
    if not user:
        return RedirectResponse("/login", status_code=302)

    rekap = _build_rekap(user["id"])
    now_wib = datetime.now(WIB)
    tanggal_cetak = now_wib.strftime("%d %B %Y")

    return templates.TemplateResponse("siswa/rekap_cetak.html", {
        "request": request,
        "rekap": rekap,
        "tanggal_cetak": tanggal_cetak,
    })


# ============================
# SISWA — DATA PRIBADI & UBAH PASSWORD
# ============================
@app.get("/siswa/data-pribadi", response_class=HTMLResponse)
def siswa_data_pribadi(request: Request):
    user = require_role(request, "siswa")
    if not user:
        return RedirectResponse("/login", status_code=302)

    db_user = db_fetchone("SELECT * FROM users WHERE id = %s", (user["id"],))
    return templates.TemplateResponse("siswa/data_pribadi.html", {
        "request": request, "user": user, "db_user": db_user,
        "alert": _get_alert(request), "active_page": "data_pribadi",
    })


@app.post("/siswa/data-pribadi")
def siswa_data_pribadi_post(
    request: Request,
    provinsi: Optional[str] = Form(None),
    kabupaten: Optional[str] = Form(None),
    kecamatan: Optional[str] = Form(None),
    kelurahan: Optional[str] = Form(None),
    alamat_detail: Optional[str] = Form(None),
):
    user = require_role(request, "siswa")
    if not user:
        return RedirectResponse("/login", status_code=302)

    db_execute("""
        UPDATE users SET provinsi=%s, kabupaten=%s, kecamatan=%s, kelurahan=%s, alamat_detail=%s
        WHERE id=%s
    """, (
        provinsi or None, kabupaten or None, kecamatan or None,
        kelurahan or None, alamat_detail or None, user["id"]
    ))
    return RedirectResponse("/siswa/data-pribadi?alert=success&msg=Data pribadi berhasil disimpan", status_code=302)


@app.get("/siswa/ubah-password", response_class=HTMLResponse)
def siswa_ubah_password(request: Request):
    user = require_role(request, "siswa")
    if not user:
        return RedirectResponse("/login", status_code=302)

    return templates.TemplateResponse("siswa/ubah_password.html", {
        "request": request, "user": user,
        "alert": _get_alert(request), "active_page": "ubah_password",
    })


@app.post("/siswa/ubah-password")
def siswa_ubah_password_post(
    request: Request,
    password_lama: str = Form(...),
    password_baru: str = Form(...),
    konfirmasi: str = Form(...),
):
    user = require_role(request, "siswa")
    if not user:
        return RedirectResponse("/login", status_code=302)

    db_user = db_fetchone("SELECT password FROM users WHERE id = %s", (user["id"],))
    if db_user["password"] != hash_password(password_lama):
        return templates.TemplateResponse("siswa/ubah_password.html", {
            "request": request, "user": user, "active_page": "ubah_password",
            "alert": {"type": "danger", "message": "Password lama salah"},
        })

    if len(password_baru) < 6:
        return templates.TemplateResponse("siswa/ubah_password.html", {
            "request": request, "user": user, "active_page": "ubah_password",
            "alert": {"type": "danger", "message": "Password baru minimal 6 karakter"},
        })

    if password_baru != konfirmasi:
        return templates.TemplateResponse("siswa/ubah_password.html", {
            "request": request, "user": user, "active_page": "ubah_password",
            "alert": {"type": "danger", "message": "Konfirmasi password tidak cocok"},
        })

    db_execute("UPDATE users SET password = %s WHERE id = %s", (hash_password(password_baru), user["id"]))
    return RedirectResponse("/siswa/ubah-password?alert=success&msg=Password berhasil diubah", status_code=302)


# ============================
# API SEARCH SISWA (autocomplete)
# ============================
@app.get("/api/search-siswa")
def api_search_siswa(request: Request, q: str = ""):
    user = get_session(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    q = q.strip()
    if len(q) < 2:
        return JSONResponse([])

    # Multi-keyword: "andi saputra" → AND nama LIKE '%andi%' AND nama LIKE '%saputra%'
    keywords = q.split()
    conditions = " AND ".join(["nama LIKE %s"] * len(keywords))
    params = [f"%{kw}%" for kw in keywords] + [10]

    results = db_fetchall(
        f"SELECT id, nama FROM users WHERE role='siswa' AND {conditions} ORDER BY nama LIMIT %s",
        params
    )
    return JSONResponse([{"id": r["id"], "nama": r["nama"]} for r in results])


# ============================
# API PREDIKSI (untuk AJAX dari guru dashboard)
# ============================
@app.get("/api/last-ayat")
def api_last_ayat(request: Request, siswa_id: int, surah_id: int):
    """Ambil ayat terakhir yang sudah dihafal siswa pada surah tertentu."""
    user = get_session(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    row = db_fetchone("""
        SELECT ayat_selesai
        FROM hafalan_log
        WHERE siswa_id = %s AND surah_id = %s
        ORDER BY ayat_selesai DESC
        LIMIT 1
    """, (siswa_id, surah_id))

    surah = get_surah(surah_id)
    total_ayat = surah["jumlah_ayat"] if surah else 0

    if row:
        next_ayat = row["ayat_selesai"] + 1
        return JSONResponse({
            "last_ayat": row["ayat_selesai"],
            "next_ayat": min(next_ayat, total_ayat),
            "total_ayat": total_ayat,
            "selesai": next_ayat > total_ayat,
        })
    else:
        return JSONResponse({
            "last_ayat": 0,
            "next_ayat": 1,
            "total_ayat": total_ayat,
            "selesai": False,
        })


@app.get("/api/prediksi")
def api_prediksi(request: Request, siswa_id: int, surah_id: int):
    user = get_session(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    result = prediksi_hafalan(siswa_id, surah_id)
    if not result:
        return JSONResponse({"error": "Data tidak ditemukan"}, status_code=404)

    return JSONResponse(result)
