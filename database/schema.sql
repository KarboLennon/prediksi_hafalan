-- ============================================
-- QURAN HAFALAN MONITORING SYSTEM
-- ============================================

-- 1. Data referensi surah (dari quran_stats.csv)
CREATE TABLE surah (
    id INT PRIMARY KEY,
    nama VARCHAR(50) NOT NULL,
    jumlah_ayat INT NOT NULL,
    jumlah_kata INT NOT NULL,
    jumlah_huruf INT NOT NULL
);

-- 2. Data referensi per ayat (dari ayah_stats_sync.csv)
CREATE TABLE ayat (
    id INT PRIMARY KEY AUTO_INCREMENT,
    surah_id INT NOT NULL,
    ayat_ke INT NOT NULL,
    jumlah_kata INT NOT NULL,
    jumlah_huruf INT NOT NULL,
    cum_kata INT NOT NULL,
    cum_huruf INT NOT NULL,
    FOREIGN KEY (surah_id) REFERENCES surah(id),
    UNIQUE KEY uq_surah_ayat (surah_id, ayat_ke)
);

-- 3. Users (siswa & guru)
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nama VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('siswa', 'guru') NOT NULL DEFAULT 'siswa',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Log hafalan harian (INI YANG JADI DATASET ML)
CREATE TABLE hafalan_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    siswa_id INT NOT NULL,
    surah_id INT NOT NULL,
    ayat_mulai INT NOT NULL,
    ayat_selesai INT NOT NULL,
    jumlah_ayat INT GENERATED ALWAYS AS (ayat_selesai - ayat_mulai + 1) STORED,
    tanggal DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (siswa_id) REFERENCES users(id),
    FOREIGN KEY (surah_id) REFERENCES surah(id)
);

-- 5. Ringkasan progress siswa per surah
CREATE VIEW v_progress_siswa AS
SELECT
    h.siswa_id,
    h.surah_id,
    s.jumlah_ayat AS total_ayat,
    s.jumlah_kata AS total_kata,
    SUM(h.jumlah_ayat) AS ayat_dihafal,
    COUNT(h.id) AS total_hari_aktif,
    MIN(h.tanggal) AS tanggal_mulai,
    MAX(h.tanggal) AS tanggal_terakhir,
    DATEDIFF(MAX(h.tanggal), MIN(h.tanggal)) + 1 AS rentang_hari,
    ROUND(SUM(h.jumlah_ayat) / s.jumlah_ayat * 100, 2) AS progress_persen,
    ROUND(SUM(h.jumlah_ayat) / COUNT(h.id), 2) AS rata_ayat_per_hari
FROM hafalan_log h
JOIN surah s ON s.id = h.surah_id
GROUP BY h.siswa_id, h.surah_id, s.jumlah_ayat, s.jumlah_kata;

-- 6. View untuk ekstrak dataset ML
--    Setiap row = 1 sesi hafalan + context siswa + context surah
CREATE VIEW v_dataset_ml AS
SELECT
    h.id,
    h.siswa_id,
    h.surah_id,
    h.ayat_mulai,
    h.ayat_selesai,
    h.jumlah_ayat AS ayat_dihafal_hari_ini,
    h.tanggal,

    -- fitur surah
    s.jumlah_ayat AS total_ayat_surah,
    s.jumlah_kata AS total_kata_surah,
    s.jumlah_huruf AS total_huruf_surah,
    ROUND(s.jumlah_kata / s.jumlah_ayat, 2) AS rata_kata_per_ayat,
    ROUND(s.jumlah_huruf / s.jumlah_ayat, 2) AS rata_huruf_per_ayat,

    -- fitur siswa (history sebelum tanggal ini)
    (
        SELECT ROUND(AVG(h2.jumlah_ayat), 2)
        FROM hafalan_log h2
        WHERE h2.siswa_id = h.siswa_id
          AND h2.surah_id = h.surah_id
          AND h2.tanggal < h.tanggal
    ) AS avg_ayat_sebelumnya,

    (
        SELECT COUNT(*)
        FROM hafalan_log h3
        WHERE h3.siswa_id = h.siswa_id
          AND h3.surah_id = h.surah_id
          AND h3.tanggal < h.tanggal
    ) + 1 AS hari_ke

FROM hafalan_log h
JOIN surah s ON s.id = h.surah_id;
