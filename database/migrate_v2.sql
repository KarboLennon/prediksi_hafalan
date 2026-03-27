-- ================================
-- MIGRASI v2: NISN, NUPTK, Force Change Password
-- Jalankan di phpMyAdmin atau MySQL CLI
-- ================================

USE quran_hafalan;

-- Tambah kolom baru
ALTER TABLE users ADD COLUMN nisn VARCHAR(20) NULL UNIQUE AFTER nama;
ALTER TABLE users ADD COLUMN nuptk VARCHAR(20) NULL UNIQUE AFTER nisn;
ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0 AFTER password;

-- Email jadi opsional (hapus NOT NULL)
ALTER TABLE users MODIFY COLUMN email VARCHAR(100) NULL;

-- Drop unique constraint dari email (karena bisa NULL)
ALTER TABLE users DROP INDEX email;
ALTER TABLE users ADD UNIQUE INDEX uq_email (email);

-- Update admin supaya tetap login pake email
UPDATE users SET must_change_password = 0 WHERE role = 'admin';

-- Update siswa dummy: set NISN (10 digit), password = hash NISN, must_change = 1
-- Ini untuk data dummy yang sudah ada, skip kalau fresh install
