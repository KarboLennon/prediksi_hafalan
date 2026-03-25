# Update Dashboard Siswa

## Perubahan yang Dilakukan

### 1. Struktur Layout yang Lebih Baik
- **Header dengan informasi user**: Menampilkan nama siswa di pojok kanan atas
- **Cards statistik yang lebih menarik**: Menggunakan ikon Font Awesome dan efek hover
- **Layout responsif**: Menggunakan Bootstrap grid system yang lebih baik

### 2. Pagination untuk Riwayat Hafalan
- **10 data per halaman**: Riwayat hafalan dibatasi 10 data per halaman
- **Navigasi halaman**: Tombol Previous/Next dengan smart pagination
- **Info pagination**: Menampilkan informasi halaman saat ini dan total data
- **URL parameter**: Mendukung parameter `?page=X` untuk navigasi langsung

### 3. Filter Surah untuk Riwayat Hafalan
- **Dropdown filter**: Pilihan surah berdasarkan data hafalan siswa
- **Auto-submit**: Filter otomatis submit saat pilihan berubah
- **Reset filter**: Tombol untuk menghapus filter dan kembali ke semua data
- **Kombinasi dengan pagination**: Filter tetap aktif saat navigasi halaman

### 4. **BARU: Pagination dan Filter untuk Estimasi AI (Decision Tree)**
- **10 prediksi per halaman**: Estimasi AI dibatasi 10 data per halaman
- **Filter surah khusus AI**: Dropdown terpisah untuk memfilter prediksi AI berdasarkan surah
- **Navigasi independen**: Pagination AI terpisah dari pagination riwayat hafalan
- **Parameter URL terpisah**: Menggunakan `ai_page` dan `ai_filter_surah` untuk AI
- **Preservasi state**: Kedua section (AI dan riwayat) mempertahankan filter dan pagination masing-masing

### 5. Peningkatan UI/UX
- **Ikon Font Awesome**: Menambahkan ikon untuk setiap elemen
- **Warna dan badge**: Menggunakan badge Bootstrap untuk data numerik
- **Progress bar animasi**: Progress bar dengan efek striped
- **Responsive design**: Tampilan yang optimal di mobile dan desktop
- **Loading state**: Indikator loading saat memfilter data
- **Layout grid responsif**: Cards AI menggunakan col-md-6 col-lg-4 untuk tampilan yang lebih baik

## Fitur Backend

### Parameter Query yang Didukung
**Untuk Riwayat Hafalan:**
- `page`: Nomor halaman (default: 1)
- `filter_surah`: Nama surah untuk filter (optional)

**Untuk Estimasi AI:**
- `ai_page`: Nomor halaman AI (default: 1)
- `ai_filter_surah`: Nama surah untuk filter AI (optional)

### Data Tambahan yang Dikirim ke Template
**Riwayat Hafalan:**
- `current_page`: Halaman saat ini
- `total_pages`: Total halaman
- `total_records`: Total data
- `per_page`: Data per halaman (10)
- `has_prev/has_next`: Boolean untuk navigasi
- `prev_page/next_page`: Nomor halaman sebelum/sesudah
- `filter_surah`: Filter surah yang aktif
- `surah_options`: Daftar surah untuk dropdown filter

**Estimasi AI:**
- `ai_current_page`: Halaman AI saat ini
- `ai_total_pages`: Total halaman AI
- `ai_total_records`: Total prediksi AI
- `ai_per_page`: Prediksi per halaman (10)
- `ai_has_prev/ai_has_next`: Boolean untuk navigasi AI
- `ai_prev_page/ai_next_page`: Nomor halaman AI sebelum/sesudah
- `ai_filter_surah`: Filter surah AI yang aktif
- `ai_surah_options`: Daftar surah untuk dropdown filter AI

## Cara Penggunaan

### Filter Surah untuk Riwayat
1. Pilih surah dari dropdown "Filter Surah untuk Riwayat"
2. Data riwayat akan otomatis difilter
3. Klik "Reset" untuk menghapus filter

### Filter Surah untuk Estimasi AI
1. Pilih surah dari dropdown "Filter Surah untuk Prediksi AI"
2. Prediksi AI akan otomatis difilter
3. Klik "Reset AI" untuk menghapus filter AI

### Navigasi Halaman
1. **Riwayat**: Gunakan pagination di bagian bawah tabel riwayat
2. **AI**: Gunakan pagination di bagian bawah section estimasi AI
3. **Independen**: Kedua pagination bekerja secara terpisah
4. **State preservation**: Filter dan pagination satu section tidak mempengaruhi section lainnya

### Responsive Design
- Desktop: Tampilan penuh dengan semua kolom dan 3 cards AI per baris
- Tablet: 2 cards AI per baris
- Mobile: 1 card AI per baris, font size yang disesuaikan

## File yang Dimodifikasi

1. **app/main.py**: 
   - Fungsi `siswa_dashboard()` dengan dual pagination dan filter logic
   - Pagination terpisah untuk AI dan riwayat hafalan
   - Filter logic untuk kedua section

2. **app/templates/siswa/dashboard.html**:
   - Section AI dengan header, filter, dan pagination terpisah
   - Form filter AI dengan dropdown surah
   - Pagination component AI dengan navigasi independen
   - Parameter preservation untuk kedua section
   - JavaScript yang mendukung kedua filter

3. **app/templates/base.html**:
   - Menambahkan Font Awesome CDN untuk ikon

## Teknologi yang Digunakan

- **Backend**: FastAPI dengan Jinja2 templates
- **Frontend**: Bootstrap 5.3.0, Font Awesome 6.4.0
- **Database**: MySQL dengan query pagination
- **JavaScript**: Vanilla JS untuk interaktivitas dual filter

## URL Structure Examples

- Dashboard default: `/siswa/dashboard`
- Riwayat page 2: `/siswa/dashboard?page=2`
- AI page 2: `/siswa/dashboard?ai_page=2`
- Kombinasi: `/siswa/dashboard?page=2&filter_surah=Al-Fatihah&ai_page=1&ai_filter_surah=Al-Baqarah`
- Filter AI saja: `/siswa/dashboard?ai_filter_surah=Al-Fatihah`