from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import date
import hmac
import hashlib
import json
import base64

from app.database import (
    get_db, hash_password, init_db,
    get_surah, get_surah_list, get_surah_name,
)
from app.predictor import prediksi_hafalan
import app.database as db_module

app = FastAPI()
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
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = db_fetchone("SELECT * FROM users WHERE email = %s", (email,))

    if not user or user["password"] != hash_password(password):
        return templates.TemplateResponse("login.html", {
            "request": request, "user": None, "error": "Email atau password salah"
        })

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
    })


@app.post("/admin/tambah-user")
def admin_tambah_user(
    request: Request,
    nama: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    user = require_role(request, "admin")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if role not in ("guru", "siswa"):
        return RedirectResponse("/admin?alert=danger&msg=Role tidak valid", status_code=302)

    existing = db_fetchone("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        return RedirectResponse("/admin?alert=danger&msg=Email sudah terdaftar", status_code=302)

    db_execute(
        "INSERT INTO users (nama, email, password, role) VALUES (%s, %s, %s, %s)",
        (nama, email, hash_password(password), role)
    )
    return RedirectResponse(f"/admin?alert=success&msg=User {nama} berhasil ditambahkan", status_code=302)


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
    return RedirectResponse(f"/admin?alert=success&msg=User berhasil dihapus", status_code=302)


# ============================
# GURU ROUTES
# ============================
@app.get("/guru", response_class=HTMLResponse)
def guru_dashboard(request: Request):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    # Siswa dari MySQL, surah dari CSV
    daftar_siswa = db_fetchall("SELECT id, nama FROM users WHERE role='siswa' ORDER BY nama")
    daftar_surah = get_surah_list()  # ← dari CSV

    # Log hafalan dari MySQL, nama surah di-inject dari CSV
    logs_raw = db_fetchall("""
        SELECT h.*, u.nama AS nama_siswa
        FROM hafalan_log h
        JOIN users u ON u.id = h.siswa_id
        WHERE h.guru_id = %s
        ORDER BY h.tanggal DESC, h.created_at DESC
        LIMIT 50
    """, (user["id"],))

    logs = []
    for log in logs_raw:
        log["nama_surah"] = get_surah_name(log["surah_id"])
        logs.append(log)

    alert = None
    alert_type = request.query_params.get("alert")
    alert_msg = request.query_params.get("msg")
    if alert_type and alert_msg:
        alert = {"type": alert_type, "message": alert_msg}

    return templates.TemplateResponse("guru/dashboard.html", {
        "request": request,
        "user": user,
        "daftar_siswa": daftar_siswa,
        "daftar_surah": daftar_surah,
        "logs": logs,
        "today": date.today().isoformat(),
        "alert": alert,
    })


@app.post("/guru/input-hafalan")
def guru_input_hafalan(
    request: Request,
    siswa_id: int = Form(...),
    surah_id: int = Form(...),
    ayat_mulai: int = Form(...),
    ayat_selesai: int = Form(...),
    tanggal: str = Form(...),
):
    user = require_role(request, "guru")
    if not user:
        return RedirectResponse("/login", status_code=302)

    if ayat_selesai < ayat_mulai:
        return RedirectResponse("/guru?alert=danger&msg=Ayat selesai harus >= ayat mulai", status_code=302)

    # Validasi surah dari CSV
    surah = get_surah(surah_id)
    if not surah:
        return RedirectResponse("/guru?alert=danger&msg=Surah tidak ditemukan", status_code=302)

    if ayat_mulai < 1 or ayat_selesai > surah["jumlah_ayat"]:
        return RedirectResponse(
            f"/guru?alert=danger&msg=Ayat harus antara 1 - {surah['jumlah_ayat']}",
            status_code=302
        )

    jumlah = ayat_selesai - ayat_mulai + 1

    # Simpan ke MySQL
    db_execute(
        "INSERT INTO hafalan_log (siswa_id, guru_id, surah_id, ayat_mulai, ayat_selesai, jumlah_ayat, tanggal) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (siswa_id, user["id"], surah_id, ayat_mulai, ayat_selesai, jumlah, tanggal)
    )

    return RedirectResponse(f"/guru?alert=success&msg=Hafalan berhasil disimpan ({jumlah} ayat)", status_code=302)


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
    })


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
