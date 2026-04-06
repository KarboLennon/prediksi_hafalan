# Dokumentasi Machine Learning — Prediksi Hafalan Al-Qur'an

**Judul Skripsi:** Penerapan Machine Learning Menggunakan Algoritma Decision Tree
untuk Memprediksi Kemampuan Hafalan Al-Qur'an pada Sistem Monitoring Hafalan
Berbasis Website

---

## DAFTAR ISI

1. [Gambaran Umum Sistem](#1-gambaran-umum-sistem)
2. [Dataset](#2-dataset)
3. [Feature Engineering](#3-feature-engineering)
4. [Algoritma: Random Forest Regressor](#4-algoritma-random-forest-regressor)
5. [Training Pipeline](#5-training-pipeline)
6. [Evaluasi Model](#6-evaluasi-model)
7. [Post-Processing & Prediksi Runtime](#7-post-processing--prediksi-runtime)
8. [Arsitektur Sistem](#8-arsitektur-sistem)
9. [Jawaban untuk Pertanyaan Sidang](#9-jawaban-untuk-pertanyaan-sidang)

---

## 1. GAMBARAN UMUM SISTEM

### Apa yang diprediksi?

Model ML memprediksi **kecepatan hafalan siswa** (satuan: **ayat per hari**).

Model TIDAK langsung memprediksi "berapa hari lagi selesai". Estimasi hari
dihitung dari rumus sederhana:

```
estimasi_hari = sisa_ayat / prediksi_kecepatan
```

### Kenapa pendekatan ini?

- Kecepatan hafalan adalah sesuatu yang **terukur** dan **punya pola** — siswa
  cenderung konsisten (cepat ya cepat, lambat ya lambat)
- Langsung memprediksi "hari selesai" jauh lebih sulit karena tergantung banyak
  faktor luar (siswa sakit, libur, motivasi turun, dll)
- Dengan memprediksi kecepatan, kita bisa menghitung estimasi untuk surah
  APAPUN, bahkan yang belum pernah dihafal siswa tersebut

### Alur kerja (end-to-end)

```
                  TRAINING (offline, sekali)
                  ─────────────────────────
hafalan_log ──→ feature engineering ──→ RandomForest.fit() ──→ model.joblib
  (MySQL)          (12 fitur)

                  PREDIKSI (runtime, per request)
                  ────────────────────────────────
siswa_id ──→ query MySQL ──→ hitung fitur ──→ model.predict() ──→ post-process ──→ output
surah_id      (riwayat)      (12 fitur)        (raw speed)        (blending,       (kecepatan,
                                                                    clamp,           estimasi hari,
                                                                    context)         insight)
```

---

## 2. DATASET

### Sumber data

| Sumber | Isi | Format |
|--------|-----|--------|
| `hafalan_log` (MySQL) | Catatan setoran harian siswa | Tabel relasional |
| `quran_stats.csv` | Statistik per surah (jumlah ayat, kata, huruf) | CSV |
| `ayah_stats_sync.csv` | Statistik per ayat (jumlah kata, huruf) | CSV |

### Statistik dataset

| Item | Nilai |
|------|-------|
| Total rows | 586 |
| Jumlah siswa | 27 |
| Jumlah surah | 45 |
| Rentang waktu | September 2025 — Maret 2026 |
| Target (jumlah_ayat) rata-rata | 4.12 ayat/hari |
| Target standar deviasi | 3.44 |

### Struktur tabel `hafalan_log`

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | INT | Primary key |
| siswa_id | INT | FK ke tabel users |
| guru_id | INT | FK ke tabel users |
| surah_id | INT | 1–114 |
| ayat_mulai | INT | Ayat awal yang disetorkan |
| ayat_selesai | INT | Ayat akhir yang disetorkan |
| jumlah_ayat | INT | ayat_selesai - ayat_mulai + 1 **(TARGET)** |
| tanggal | DATE | Tanggal setoran |
| catatan | TEXT | Catatan dari guru |

### Target variable

**jumlah_ayat** — jumlah ayat yang berhasil disetorkan dalam satu sesi.
Ini merepresentasikan "kecepatan hafalan" siswa pada hari itu.

---

## 3. FEATURE ENGINEERING

### Kenapa feature engineering penting?

Data mentah (hafalan_log) hanya berisi "siswa X menyetor Y ayat pada tanggal Z".
Model tidak bisa langsung belajar dari ini karena:

- Tidak tahu konteks surah (panjang? sulit?)
- Tidak tahu riwayat siswa (biasanya cepat atau lambat?)
- Tidak tahu tren terbaru (sedang naik atau turun?)

Feature engineering mengubah data mentah menjadi sinyal yang bermakna.

### Daftar 12 fitur

#### A. Fitur Surah (statis, dari CSV — 3 fitur)

| Fitur | Cara hitung | Arti | Contoh |
|-------|-------------|------|--------|
| `total_ayat_surah` | Dari quran_stats.csv | Jumlah ayat dalam surah | Al-Baqarah = 286 |
| `rata_kata_per_ayat` | mean(kata) per surah dari ayah_stats | Rata-rata kata per ayat | Proxy kesulitan surah |
| `rata_huruf_per_ayat` | mean(huruf) per surah dari ayah_stats | Rata-rata huruf per ayat | Proxy panjang ayat |

**Kenapa ini penting?** Surah An-Nas (6 ayat, pendek-pendek) jauh lebih mudah
dihafal per ayat dibanding Al-Baqarah (286 ayat, banyak ayat panjang).

#### B. Fitur Progress (per siswa per surah — 3 fitur)

| Fitur | Cara hitung | Arti |
|-------|-------------|------|
| `hari_ke` | cumcount per (siswa, surah) + 1 | Hari ke-berapa siswa menghafal surah ini |
| `ayat_sudah_dihafal` | cumsum(jumlah_ayat) per (siswa, surah), **di-shift 1** | Total ayat yang sudah dihafal SEBELUM hari ini |
| `progress_persen` | (ayat_sudah / total_ayat) * 100 | Persentase penyelesaian surah |

**Kenapa di-shift?** Supaya tidak bocor (leakage). Kalau kita pakai cumsum TANPA
shift, berarti kita sudah tahu hasil hari ini sebelum memprediksi — itu curang.
Shift(1) artinya kita hanya pakai data sampai KEMARIN.

#### C. Fitur Riwayat Kecepatan (per siswa — 6 fitur)

| Fitur | Cara hitung | Arti |
|-------|-------------|------|
| `kecepatan_avg_sebelumnya` | expanding mean per siswa, **shift(1)** | Rata-rata kecepatan siswa dari SEMUA setoran sebelumnya |
| `lag_1` | shift(1) per siswa | Jumlah ayat yang disetorkan **1 setoran lalu** |
| `lag_2` | shift(2) per siswa | Jumlah ayat yang disetorkan **2 setoran lalu** |
| `lag_3` | shift(3) per siswa | Jumlah ayat yang disetorkan **3 setoran lalu** |
| `rolling_mean_3` | rolling(3).mean() per siswa, **shift(1)** | Rata-rata kecepatan 3 setoran terakhir |
| `total_setoran_sebelumnya` | cumcount per siswa | Berapa kali siswa sudah setor sebelum hari ini |

**Penjelasan lag features:**

```
Setoran siswa A: [3, 5, 2, 7, 4, ...]
                                    ↑ hari ini (yang mau diprediksi)
                              lag_1 = 4 (kemarin)
                        lag_2 = 7 (2 hari lalu)
                  lag_3 = 2 (3 hari lalu)
      rolling_mean_3 = mean(4, 7, 2) = 4.33
```

**Kenapa lag penting?** Siswa yang kemarin menyetor 7 ayat kemungkinan besar
besok juga menyetor sekitar segitu — bukan tiba-tiba 1 ayat. Lag menangkap
"momentum" ini.

### Data Leakage Audit

Data leakage = fitur yang secara tidak sengaja "bocor" informasi dari masa
depan. Ini FATAL karena bikin model terlihat bagus di training tapi gagal total
di production.

| Fitur | Aman? | Mekanisme pencegahan |
|-------|-------|---------------------|
| kecepatan_avg_sebelumnya | Ya | expanding().mean().**shift(1)** — hanya data sebelum hari ini |
| lag_1, lag_2, lag_3 | Ya | **shift(1/2/3)** per siswa — data N hari sebelumnya |
| rolling_mean_3 | Ya | rolling(3).mean().**shift(1)** — rata-rata SEBELUM hari ini |
| ayat_sudah_dihafal | Ya | cumsum().**shift(1)** — total SEBELUM hari ini |
| progress_persen | Ya | Diturunkan dari ayat_sudah_dihafal (yang sudah di-shift) |
| hari_ke | Ya | cumcount — hitungan baris sebelumnya, bukan termasuk hari ini |
| total_setoran_sebelumnya | Ya | cumcount — sama seperti hari_ke |
| Fitur surah (3 fitur) | Ya | Data statis dari CSV, tidak berubah |

**Prinsip utama:** Semua fitur temporal menggunakan `shift()` — artinya model
HANYA melihat data yang sudah terjadi, tidak pernah data hari ini atau masa depan.

---

## 4. ALGORITMA: RANDOM FOREST REGRESSOR

### Apa itu Random Forest?

Random Forest adalah **ensemble** (kumpulan) dari banyak Decision Tree yang
bekerja bersama.

```
                    Data Training
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
        Tree 1       Tree 2  ...  Tree 200
     (subset data)  (subset data)  (subset data)
            │            │            │
        pred: 3.2    pred: 4.1    pred: 3.8
            │            │            │
            └────────────┼────────────┘
                         ▼
                  RATA-RATA = 3.7
                  (prediksi akhir)
```

Setiap tree dilatih dengan:
- **Subset baris** (bootstrap sampling) — setiap tree melihat data yang berbeda
- **Subset fitur** (feature bagging) — setiap split hanya mempertimbangkan
  sebagian fitur

### Kenapa Random Forest (bukan Decision Tree biasa)?

| Aspek | Decision Tree | Random Forest |
|-------|---------------|---------------|
| Overfit | Sangat mudah | Jauh lebih tahan |
| Stabilitas | Prediksi bisa "loncat-loncat" | Lebih smooth (rata-rata 200 tree) |
| Akurasi | Oke | Lebih baik (wisdom of crowds) |
| Interpretasi | Bisa di-export jadi rules | Feature importance |
| Cocok untuk dataset kecil? | Rawan overfit | Aman dengan parameter konservatif |

### Parameter yang digunakan

```python
RandomForestRegressor(
    n_estimators=200,      # Jumlah tree
    max_depth=8,           # Kedalaman maksimal tiap tree
    min_samples_leaf=5,    # Minimal 5 sampel di setiap leaf
    random_state=42,       # Reproducibility
    n_jobs=-1,             # Pakai semua CPU core
)
```

**Penjelasan parameter:**

| Parameter | Nilai | Kenapa? |
|-----------|-------|---------|
| `n_estimators=200` | 200 tree | Cukup banyak untuk stabilitas, lebih dari 200 diminishing returns |
| `max_depth=8` | Max 8 level | Mencegah tree terlalu dalam (overfit). Dataset 586 rows, depth 8 sudah lebih dari cukup |
| `min_samples_leaf=5` | Min 5 data per leaf | Mencegah tree membuat "rules" yang terlalu spesifik (cuma berlaku untuk 1-2 siswa) |
| `random_state=42` | Seed tetap | Supaya hasil bisa di-reproduce (run ulang hasilnya sama) |

### Bagaimana Random Forest membuat prediksi?

Contoh sederhana — prediksi untuk siswa A, surah Al-Mulk:

```
Tree 1:
  IF kecepatan_avg > 3.5 AND lag_1 > 2 AND total_ayat_surah < 50
  THEN prediksi = 4.2

Tree 2:
  IF rolling_mean_3 > 3.0 AND progress_persen < 50
  THEN prediksi = 3.8

Tree 3:
  IF lag_1 > 3 AND kecepatan_avg > 4.0
  THEN prediksi = 5.1

... (197 tree lainnya) ...

Prediksi akhir = rata-rata(4.2, 3.8, 5.1, ...) = 4.1 ayat/hari
```

---

## 5. TRAINING PIPELINE

### Alur lengkap

```
STEP 1: Load Data
  └→ Baca hafalan_log dari MySQL + data surah/ayat dari CSV

STEP 2: Fitur Surah
  └→ Gabungkan statistik surah (total ayat, rata-rata kata, rata-rata huruf)

STEP 3: Feature Engineering
  └→ Hitung 12 fitur per baris (progress, kecepatan, lag, rolling)
  └→ Semua fitur pakai shift() untuk mencegah leakage

STEP 4: Time-Based Split (80/20)
  └→ Sort data berdasarkan tanggal
  └→ 80% pertama = training, 20% terakhir = testing
  └→ Cutoff: 27 Oktober 2025
  └→ Train: 469 rows (Sep–Okt 2025)
  └→ Test: 117 rows (Okt 2025–Mar 2026)

STEP 5: Train Random Forest
  └→ Fit model dengan X_train, y_train
  └→ Evaluasi di train set dan test set
  └→ Cross-validation dengan TimeSeriesSplit (5 fold)

STEP 6: Feature Importance
  └→ Ranking fitur berdasarkan kontribusi ke prediksi

STEP 7: Simpan Model
  └→ Simpan ke models/decision_tree.joblib (model + metadata)

STEP 8: Visualisasi
  └→ 3 panel: Actual vs Predicted, Feature Importance, Distribusi Error
```

### Kenapa Time-Based Split (bukan Random Split)?

```
SALAH (random split):
  Train: [Jan, Mar, Feb, Apr, Jun, ...]  ← campur aduk
  Test:  [Feb, May, Jan, ...]            ← model sudah "lihat" bulan yang sama

BENAR (time-based split):
  Train: [Sep, Sep, Sep, Okt, Okt, ...]  ← masa lalu
  Test:  [Nov, Des, Jan, Feb, Mar, ...]  ← masa depan
```

Random split menyebabkan **temporal leakage** — model bisa "menghafal" pola
dari bulan yang sama. Time-based split mensimulasikan kondisi nyata: model
dilatih dengan data masa lalu dan diminta memprediksi masa depan.

### Distribution Shift

```
Rata-rata kecepatan hafalan:
  Train (Sep–Okt): 4.62 ayat/hari
  Test  (Nov–Mar): 2.10 ayat/hari
  Shift: 54.5%
```

**Kenapa shift besar?** Kemungkinan penyebab:
- Siswa mulai menghafal surah yang lebih sulit
- Mendekati ujian, fokus beralih ke pelajaran lain
- Libur semester mengganggu konsistensi
- Surah yang mudah (pendek) sudah selesai lebih dulu

**Dampak ke model:** R² test lebih rendah dari R² train, tapi ini NORMAL dan
EXPECTED. Model tidak "gagal" — dunia memang berubah.

---

## 6. EVALUASI MODEL

### Metrik yang digunakan

#### MAE (Mean Absolute Error)

```
MAE = rata-rata( |actual - predicted| )
```

**Artinya:** Rata-rata, prediksi meleset berapa ayat?

| Set | MAE | Interpretasi |
|-----|-----|-------------|
| Train | 1.00 | Prediksi rata-rata meleset ~1 ayat di data training |
| Test | 0.95 | Prediksi rata-rata meleset ~1 ayat di data baru |

**MAE ~1 ayat itu bagus atau jelek?**
Target rata-rata = 4.12 ayat/hari. Meleset 1 ayat artinya error sekitar 24%.
Untuk konteks prediksi perilaku manusia, ini **sangat reasonable**.

#### R² (R-Squared / Koefisien Determinasi)

```
R² = 1 - (sum of squared errors / total variance)
```

**Artinya:** Berapa persen variasi data yang bisa dijelaskan model?

| Set | R² | Interpretasi |
|-----|-----|-------------|
| Train | 0.84 | Model menjelaskan 84% variasi di data training |
| Test | 0.37 | Model menjelaskan 37% variasi di data baru |
| CV (rata-rata) | 0.56 | Rata-rata 56% di 5 fold cross-validation |

**Kenapa R² test lebih rendah?**
- Distribution shift 54.5% (lihat penjelasan di atas)
- Data test memiliki pola yang BERBEDA dari training
- Ini BUKAN kegagalan model — ini realita data temporal

**R² 0.37 itu bagus?**
Untuk prediksi perilaku manusia dengan dataset kecil (~600 rows) dan
distribution shift >50%, R² 0.37 pada test set artinya model MASIH bisa
menangkap pola. Yang lebih penting: MAE = 0.95 (meleset ~1 ayat, usable).

### Cross-Validation: TimeSeriesSplit

```
Fold 1: Train [───────]  Test [──]
Fold 2: Train [──────────]  Test [──]
Fold 3: Train [─────────────]  Test [──]
Fold 4: Train [────────────────]  Test [──]
Fold 5: Train [───────────────────]  Test [──]
```

**Kenapa TimeSeriesSplit (bukan K-Fold biasa)?**
K-Fold biasa mengacak data → bisa bocor informasi waktu. TimeSeriesSplit
selalu melatih dengan data SEBELUMNYA dan menguji dengan data SESUDAHNYA,
persis seperti kondisi nyata.

**Hasil:**
- CV R² = 0.56 ± 0.11 → model cukup konsisten di berbagai periode
- CV MAE = 1.39 ± 0.33 → error stabil sekitar 1–2 ayat

### Feature Importance

| Rank | Fitur | Importance | Penjelasan |
|------|-------|------------|------------|
| 1 | kecepatan_avg_sebelumnya | 43.3% | Riwayat kecepatan siswa = prediktor #1 |
| 2 | rolling_mean_3 | 19.8% | Performa 3 setoran terakhir |
| 3 | progress_persen | 8.6% | Makin jauh progress, makin pelan |
| 4 | lag_1 | 6.2% | Setoran terakhir |
| 5 | total_ayat_surah | 5.1% | Surah panjang = lebih lambat |
| 6 | rata_kata_per_ayat | 4.9% | Ayat kompleks = lebih lambat |
| 7 | rata_huruf_per_ayat | 4.3% | Ayat panjang = lebih lambat |
| 8 | lag_2 | 2.5% | 2 setoran lalu |
| 9 | total_setoran_sebelumnya | 1.7% | Pengalaman siswa |
| 10 | ayat_sudah_dihafal | 1.5% | Berapa ayat sudah dihafal |
| 11 | hari_ke | 1.3% | Hari ke-berapa di surah ini |
| 12 | lag_3 | 0.9% | 3 setoran lalu |

**Insight:**
- 63% prediksi ditentukan oleh 2 fitur saja: kecepatan historis + performa
  terbaru
- Fitur surah (kesulitan, panjang) berkontribusi ~15%
- Fitur progress (sudah berapa jauh) ~11%
- Ini masuk akal: kecepatan hafalan BESOK paling ditentukan oleh kecepatan
  hafalan KEMARIN

---

## 7. POST-PROCESSING & PREDIKSI RUNTIME

### Kenapa perlu post-processing?

Model ML memberikan angka "mentah" yang kadang:
- Terlalu optimis (overpredict)
- Tidak mempertimbangkan konteks surah
- Bisa menghasilkan nilai yang tidak realistis

Post-processing = lapisan pengolahan SETELAH model predict, supaya output
lebih realistis dan bisa dipercaya user.

### Pipeline post-processing (3 langkah)

#### Langkah 1: Blending

```python
final_speed = 0.7 * pred_model + 0.3 * rolling_mean_3
```

**Kenapa?** Model kadang "terlalu percaya diri". Rolling_mean_3 adalah performa
AKTUAL siswa 3 setoran terakhir. Dengan mencampurkan keduanya (70% model + 30%
data aktual), prediksi jadi lebih stabil.

**Contoh:**
```
Model bilang: 6 ayat/hari (mungkin terlalu tinggi)
Rolling mean: 4 ayat/hari (kenyataan terakhir)
Final: 0.7 * 6 + 0.3 * 4 = 5.4 ayat/hari (lebih realistis)
```

#### Langkah 2: Context-Aware Adjustment

```python
penalty = 0.0
if total_ayat_surah > 100:   penalty += 0.05   # surah panjang
if rata_kata_per_ayat > 15:   penalty += 0.05   # ayat kompleks
if total_ayat_surah > 200:    penalty += 0.05   # surah sangat panjang
speed = speed * (1.0 - penalty)                  # max -15%
```

**Kenapa?** Surah Al-Baqarah (286 ayat, banyak ayat panjang) tentu lebih
lambat dihafal per ayat dibanding An-Nas (6 ayat pendek). Adjustment ini
RINGAN (max -15%) — hanya "koreksi kecil", bukan override model.

**Contoh:**
```
Al-Baqarah (286 ayat, >15 kata/ayat):
  penalty = 0.05 + 0.05 + 0.05 = 0.15
  5.4 * (1 - 0.15) = 4.6 ayat/hari

An-Nas (6 ayat, <15 kata/ayat):
  penalty = 0 (tidak kena satupun)
  5.4 * (1 - 0) = 5.4 ayat/hari
```

#### Langkah 3: Clamp (Batasan Realistis)

```python
max_speed = max(kecepatan_avg * 2.0, 10.0)
speed = max(1.0, min(speed, max_speed))
```

| Batas | Nilai | Alasan |
|-------|-------|--------|
| Minimum | 1 ayat/hari | Tidak mungkin menyetor 0 ayat (kalau menyetor, pasti minimal 1) |
| Maximum | 2x rata-rata siswa, minimal 10 | Siswa yang biasa 3 ayat/hari tidak mungkin tiba-tiba 15 ayat/hari. Max = 2x kecepatannya |

**Kenapa max dinamis?**
- Siswa A (avg 3 ayat) → max = 6 ayat/hari
- Siswa B (avg 8 ayat) → max = 16 ayat/hari
- Siswa baru (belum ada data) → max = 10 ayat/hari (default)

### Estimasi Hari + Confidence Range

```python
estimasi_hari = ceil(sisa_ayat / final_speed)
estimasi_low  = ceil(estimasi_hari * 0.9)    # skenario optimis
estimasi_high = ceil(estimasi_hari * 1.2)    # skenario konservatif
```

**Contoh lengkap:**
```
Siswa: Ahmad
Surah: Al-Mulk (30 ayat)
Sudah dihafal: 12 ayat
Sisa: 18 ayat

Model prediksi: 4.1 ayat/hari
Post-processing: 3.8 ayat/hari (setelah blend + context + clamp)

Estimasi = 18 / 3.8 = 5 hari
Range = 5–6 hari (optimis–konservatif)
```

### Insight Generator

```python
ratio = rolling_mean_3 / kecepatan_avg

if ratio >= 1.15:  → "Performa terakhir di atas rata-rata. Pertahankan!"
elif ratio <= 0.85: → "Kecepatan terakhir sedikit menurun dari biasanya."
else:               → "Kecepatan hafalan cukup stabil."

# Bonus jika progress >= 75%:
→ + "Tinggal sedikit lagi, semangat!"
```

Insight membandingkan performa TERBARU (3 setoran terakhir) vs rata-rata
KESELURUHAN. Ini memberi feedback yang actionable ke siswa.

---

## 8. ARSITEKTUR SISTEM

### Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Backend | Python + FastAPI |
| Database | MySQL (XAMPP) |
| Frontend | Jinja2 Templates (server-side rendering) |
| ML Library | scikit-learn (RandomForestRegressor) |
| Data Processing | pandas, numpy |
| Model Storage | joblib (.joblib file) |

### File structure (ML-related)

```
quran-ml/
├── model/
│   └── train.py              ← Training pipeline (jalankan untuk re-train)
├── models/
│   ├── decision_tree.joblib  ← Model tersimpan (model + metadata)
│   ├── evaluasi_model.png    ← Grafik evaluasi
│   └── tree_rules.txt        ← Rules (untuk referensi)
├── app/
│   ├── predictor.py          ← Prediksi runtime (dipanggil dari API)
│   ├── main.py               ← FastAPI routes
│   └── database.py           ← Koneksi MySQL + load CSV
├── data/
│   ├── quran_stats.csv       ← Statistik surah
│   ├── ayah_stats_sync.csv   ← Statistik ayat
│   └── hafalan_features.csv  ← Dataset hasil feature engineering
```

### Alur request prediksi (di aplikasi)

```
Browser → GET /api/prediksi?siswa_id=5&surah_id=67
           │
           ▼
        main.py (FastAPI route)
           │
           ▼
        predictor.py → prediksi_hafalan(5, 67)
           │
           ├→ get_surah_features(67)     → query CSV (statis)
           ├→ get_siswa_history(5, 67)   → query MySQL (riwayat)
           ├→ MODEL.predict(X)           → Random Forest prediksi
           ├→ compute_final_speed(...)   → post-processing
           ├→ generate_insight(...)      → insight teks
           │
           ▼
        Response JSON:
        {
          "prediksi_ayat_per_hari": 3.8,
          "estimasi_hari": 5,
          "estimasi_low": 5,
          "estimasi_high": 6,
          "insight": "Kecepatan hafalan cukup stabil.",
          ...
        }
```

---

## 9. JAWABAN UNTUK PERTANYAAN SIDANG

### "Kenapa pakai Random Forest, bukan algoritma lain?"

> Random Forest dipilih karena 3 alasan:
>
> 1. **Tahan overfit di dataset kecil** — Dataset saya hanya 586 rows.
>    Decision Tree tunggal sangat mudah overfit. Random Forest menggunakan
>    200 tree dengan data dan fitur berbeda, lalu rata-ratakan hasilnya.
>    Ini seperti "bertanya ke 200 pakar lalu ambil konsensus".
>
> 2. **Menangkap hubungan non-linear** — Hubungan antara fitur dan kecepatan
>    tidak selalu linear. Misalnya, siswa yang sudah hafal 80% surah bisa
>    LEBIH LAMBAT (fatigue), bukan lebih cepat. Ridge Regression tidak bisa
>    menangkap pola ini, Random Forest bisa.
>
> 3. **Feature importance bawaan** — Langsung bisa lihat fitur mana yang
>    paling berpengaruh tanpa analisis tambahan. Ini penting untuk
>    interpretasi dan penjelasan ke stakeholder.
>
> Saya juga mencoba Ridge Regression sebagai perbandingan, hasilnya R² = -0.10
> (negatif, artinya lebih buruk dari sekadar menebak rata-rata). Random Forest
> memberikan R² = 0.37 yang jauh lebih baik.

### "Kenapa R² nya cuma 0.37? Itu kan rendah?"

> R² 0.37 memang tidak tinggi, tapi ada konteks penting:
>
> 1. **Distribution shift 54.5%** — Rata-rata kecepatan di training period
>    (Sep–Okt) = 4.62 ayat/hari, di test period (Nov–Mar) = 2.10 ayat/hari.
>    Ini artinya perilaku siswa berubah drastis. Tidak ada model yang bisa
>    memprediksi perubahan perilaku manusia dengan sempurna.
>
> 2. **Cross-validation R² = 0.56** — Kalau diukur dengan TimeSeriesSplit
>    (lebih fair karena melihat beberapa periode), model menjelaskan 56%
>    variasi. Ini jauh lebih representatif.
>
> 3. **MAE = 0.95 ayat** — Yang lebih penting dari R² adalah: rata-rata
>    model hanya meleset ~1 ayat. Kalau siswa menyetor 3 ayat, model
>    memprediksi 2–4. Untuk keperluan estimasi waktu, ini sangat usable.
>
> 4. **Konteks domain** — Ini prediksi perilaku manusia, bukan prediksi
>    harga saham atau suhu udara. Manusia tidak konsisten. R² 0.37 dengan
>    distribution shift >50% itu sudah bagus.

### "Apa itu data leakage dan bagaimana kamu mencegahnya?"

> Data leakage adalah ketika model secara tidak sengaja "melihat" informasi
> dari masa depan saat training. Ini membuat model terlihat bagus di
> evaluasi tapi gagal total di dunia nyata.
>
> Contoh leakage yang BERBAHAYA:
> Kalau saya menghitung "rata-rata kecepatan siswa" TERMASUK data hari ini,
> berarti model sudah tahu jawaban sebelum memprediksi — seperti ujian buka
> buku.
>
> Pencegahan di sistem saya:
> - Semua fitur temporal menggunakan `shift()` — hanya melihat data
>   SEBELUM hari yang diprediksi
> - Time-based split — model dilatih dengan data masa lalu, diuji dengan
>   data masa depan
> - TimeSeriesSplit untuk cross-validation — fold selalu berurutan waktu
>
> Saya melakukan audit leakage untuk semua 12 fitur dan semuanya aman.

### "Kenapa pakai time-based split, bukan random split?"

> Data hafalan punya urutan waktu. Kalau saya acak, model bisa melihat data
> bulan Maret saat training dan diminta memprediksi bulan Januari — ini
> tidak realistis.
>
> Time-based split mensimulasikan kondisi nyata: "Saya punya data sampai
> Oktober, bisakah saya memprediksi November?" Ini yang sebenarnya terjadi
> saat aplikasi digunakan.

### "Apa itu feature engineering dan kenapa penting?"

> Data mentah dari database hanya berisi "siswa X menyetor Y ayat tanggal Z".
> Model ML tidak bisa langsung belajar dari ini.
>
> Feature engineering mengubah data mentah menjadi sinyal yang bermakna:
> - Dari tanggal → "ini hari ke-berapa siswa menghafal surah ini"
> - Dari riwayat → "rata-rata siswa ini menghafal berapa ayat per hari"
> - Dari 3 setoran terakhir → "apakah siswa sedang naik atau turun"
>
> Feature yang paling penting ternyata `kecepatan_avg_sebelumnya` (43%) —
> riwayat kecepatan siswa. Ini intuitif: cara terbaik memprediksi kecepatan
> besok adalah melihat kecepatan kemarin.

### "Kenapa ada post-processing? Apa model-nya kurang bagus?"

> Post-processing bukan karena model kurang bagus, tapi karena output model
> perlu disesuaikan untuk keperluan production:
>
> 1. **Blending** — Model kadang overpredict. Dengan mencampur 70% prediksi
>    model + 30% data aktual terbaru, output jadi lebih stabil.
>
> 2. **Context adjustment** — Model sudah mengerti perbedaan surah lewat
>    fitur, tapi adjustment ringan (max -15%) untuk surah sangat panjang
>    membuat output lebih masuk akal.
>
> 3. **Clamp** — Supaya prediksi tidak keluar batas wajar. Siswa yang biasa
>    3 ayat/hari tidak mungkin tiba-tiba diprediksi 20 ayat/hari.
>
> Ini praktik standar di industri. Model ML di production hampir selalu
> punya post-processing layer.

### "Bagaimana estimasi hari dihitung?"

> Rumusnya sederhana:
>
> ```
> estimasi_hari = sisa_ayat / prediksi_kecepatan
> ```
>
> Contoh: Surah Al-Mulk punya 30 ayat. Siswa sudah hafal 12 ayat, sisa 18.
> Model memprediksi kecepatan siswa = 3.8 ayat/hari.
> Estimasi = 18 / 3.8 = 5 hari.
>
> Saya juga menambahkan range: 5–6 hari (90%–120% dari estimasi utama).
> Range ini memberi gambaran optimis vs konservatif.

### "Bagaimana kalau siswa baru yang belum punya data?"

> Untuk siswa baru, semua fitur riwayat diisi dengan GLOBAL MEDIAN
> (nilai tengah dari seluruh dataset = 3.0 ayat/hari). Ini artinya model
> akan memprediksi "siswa rata-rata".
>
> Setelah 3+ setoran, model mulai mempersonalisasi prediksi berdasarkan
> data aktual siswa tersebut. Insight juga menampilkan pesan: "Data masih
> sedikit, estimasi akan lebih akurat setelah beberapa setoran."

### "Kenapa file model-nya bernama decision_tree.joblib tapi isinya Random Forest?"

> Ini untuk backward compatibility — supaya aplikasi yang sudah berjalan
> tidak perlu diubah path-nya. File tersebut berisi model apapun yang
> terbaik hasil training. Di dalam metadata tersimpan informasi bahwa
> model sebenarnya adalah "Random Forest".

### "Tools/library apa yang kamu pakai?"

> - **scikit-learn** — Library ML standar industri. RandomForestRegressor,
>   TimeSeriesSplit, metrics (MAE, R²)
> - **pandas** — Manipulasi data tabular, feature engineering
> - **numpy** — Operasi numerik
> - **joblib** — Menyimpan dan memuat model ke/dari file
> - **matplotlib** — Visualisasi evaluasi model
> - **FastAPI** — Web framework untuk serving prediksi via API
> - **PyMySQL** — Koneksi ke database MySQL
