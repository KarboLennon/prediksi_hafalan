-- ================================
-- QURAN HAFALAN MONITORING
-- MySQL: cuma users + hafalan_log
-- Data Quran (surah & ayat) dibaca dari CSV
-- ================================

CREATE DATABASE IF NOT EXISTS quran_hafalan;
USE quran_hafalan;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    nis VARCHAR(20) NULL UNIQUE,
    nuptk VARCHAR(20) NULL UNIQUE,
    email VARCHAR(100) NULL UNIQUE,
    password VARCHAR(64) NOT NULL,
    must_change_password TINYINT(1) NOT NULL DEFAULT 0,
    role ENUM('admin', 'siswa', 'guru') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hafalan_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    siswa_id INT NOT NULL,
    guru_id INT NOT NULL,
    surah_id INT NOT NULL,
    ayat_mulai INT NOT NULL,
    ayat_selesai INT NOT NULL,
    jumlah_ayat INT NOT NULL,
    tanggal DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (siswa_id) REFERENCES users(id),
    FOREIGN KEY (guru_id) REFERENCES users(id)
);

-- Default admin: admin@admin.com / admin123
INSERT INTO users (nama, email, password, role)
VALUES ('Admin', 'admin@admin.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin');
