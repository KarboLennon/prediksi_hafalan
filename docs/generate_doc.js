const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  Header, Footer, PageNumber, PageBreak, LevelFormat, ImageRun,
} = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "1a7a4c", type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, bold: true, color: "FFFFFF", font: "Arial", size: 20 })] })],
  });
}

function cell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    margins: cellMargins,
    children: [new Paragraph({ children: [new TextRun({ text: String(text), font: "Arial", size: 20 })] })],
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    ...opts,
    children: [new TextRun({ text, font: "Arial", size: 22, ...opts.run })],
  });
}

function bold(text) {
  return new TextRun({ text, font: "Arial", size: 22, bold: true });
}

function normal(text) {
  return new TextRun({ text, font: "Arial", size: 22 });
}

function heading(text, level) {
  return new Paragraph({
    heading: level,
    spacing: { before: 300, after: 150 },
    children: [new TextRun({ text, font: "Arial", bold: true, size: level === HeadingLevel.HEADING_1 ? 32 : level === HeadingLevel.HEADING_2 ? 26 : 22 })],
  });
}

function mixedP(runs, opts = {}) {
  return new Paragraph({ spacing: { after: 120 }, ...opts, children: runs });
}

// Load the chart image
let chartImage = null;
try {
  chartImage = fs.readFileSync("/Users/muchtar/quran-ml/models/evaluasi_model.png");
} catch (e) {
  console.log("Warning: evaluasi_model.png not found");
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1a7a4c" },
        paragraph: { spacing: { before: 300, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2d9b6e" },
        paragraph: { spacing: { before: 240, after: 150 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
      },
      {
        reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Penjelasan Training Model Decision Tree", font: "Arial", size: 16, color: "999999", italics: true })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Halaman ", font: "Arial", size: 16, color: "999999" }), new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "999999" })],
          })],
        }),
      },
      children: [
        // ========== COVER ==========
        new Paragraph({ spacing: { before: 3000 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "Penjelasan Proses Training Model", font: "Arial", size: 40, bold: true, color: "1a7a4c" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 100 },
          children: [new TextRun({ text: "Decision Tree", font: "Arial", size: 36, bold: true, color: "2d9b6e" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 600 },
          children: [new TextRun({ text: "Prediksi Kemampuan Hafalan Al-Qur'an", font: "Arial", size: 28, color: "555555" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 100 },
          children: [new TextRun({ text: "Sistem Monitoring Hafalan Berbasis Website", font: "Arial", size: 22, color: "777777" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 2000 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2d9b6e", space: 1 } },
          children: [],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Dokumen ini menjelaskan step-by-step proses training model Machine Learning\nmulai dari pengumpulan data hingga evaluasi hasil.", font: "Arial", size: 20, color: "888888", italics: true })],
        }),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== OVERVIEW ==========
        heading("Overview", HeadingLevel.HEADING_1),
        p("Dokumen ini menjelaskan proses training model Decision Tree untuk memprediksi kemampuan hafalan Al-Qur'an siswa. Model ini digunakan dalam Sistem Monitoring Hafalan berbasis website untuk memberikan estimasi berapa hari seorang siswa bisa menyelesaikan hafalan suatu surah."),

        mixedP([bold("Tujuan model: "), normal("Memprediksi berapa ayat yang bisa dihafal seorang siswa per hari, berdasarkan kebiasaan siswa dan karakteristik surah yang dihafal.")]),

        p("Berikut flow keseluruhan proses training:"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1872, 5616, 1872],
          rows: [
            new TableRow({ children: [headerCell("Step", 1872), headerCell("Proses", 5616), headerCell("Output", 1872)] }),
            new TableRow({ children: [cell("1", 1872), cell("Load Data dari CSV & MySQL", 5616), cell("582 rows", 1872)] }),
            new TableRow({ children: [cell("2", 1872), cell("Feature Engineering (extract 8 fitur)", 5616), cell("Dataset", 1872)] }),
            new TableRow({ children: [cell("3", 1872), cell("Split Train/Test (80%/20%)", 5616), cell("465 + 117", 1872)] }),
            new TableRow({ children: [cell("4", 1872), cell("Train Decision Tree", 5616), cell("Model", 1872)] }),
            new TableRow({ children: [cell("5", 1872), cell("Evaluasi (MAE, RMSE, R\u00B2)", 5616), cell("R\u00B2=0.62", 1872)] }),
            new TableRow({ children: [cell("6", 1872), cell("Simpan Model & Visualisasi", 5616), cell("Files", 1872)] }),
          ],
        }),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== STEP 1 ==========
        heading("Step 1: Load Data", HeadingLevel.HEADING_1),
        p("Data diambil dari 2 sumber yang berbeda, masing-masing punya peran sendiri:"),

        heading("Sumber 1: CSV (Data Al-Qur'an)", HeadingLevel.HEADING_2),
        mixedP([normal("File "), bold("quran_stats.csv"), normal(" berisi data statistik 114 surah Al-Qur'an (nomor surah, jumlah ayat, jumlah kata, jumlah huruf). File "), bold("ayah_stats_sync.csv"), normal(" berisi data detail per ayat (6.236 ayat) termasuk jumlah kata dan huruf tiap ayat.")]),
        p("Data ini bersifat statis (tidak berubah) dan digunakan untuk mengukur kompleksitas surah/ayat."),

        heading("Sumber 2: MySQL (Data Hafalan Siswa)", HeadingLevel.HEADING_2),
        mixedP([normal("Tabel "), bold("hafalan_log"), normal(" di database MySQL menyimpan catatan hafalan harian siswa. Total 582 baris dari 25 siswa selama periode September 2025 - Januari 2026.")]),

        p("Contoh isi tabel hafalan_log:"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1200, 1200, 1560, 1560, 1560, 2280],
          rows: [
            new TableRow({ children: [headerCell("siswa_id", 1200), headerCell("surah_id", 1200), headerCell("ayat_mulai", 1560), headerCell("ayat_selesai", 1560), headerCell("jumlah_ayat", 1560), headerCell("tanggal", 2280)] }),
            new TableRow({ children: [cell("5", 1200), cell("82", 1200), cell("1", 1560), cell("13", 1560), cell("13", 1560), cell("2025-09-01", 2280)] }),
            new TableRow({ children: [cell("5", 1200), cell("82", 1200), cell("14", 1560), cell("19", 1560), cell("6", 1560), cell("2025-09-02", 2280)] }),
            new TableRow({ children: [cell("8", 1200), cell("85", 1200), cell("1", 1560), cell("4", 1560), cell("4", 1560), cell("2025-09-02", 2280)] }),
            new TableRow({ children: [cell("12", 1200), cell("36", 1200), cell("1", 1560), cell("3", 1560), cell("3", 1560), cell("2025-09-03", 2280)] }),
          ],
        }),

        mixedP([normal("Artinya: siswa 5 pada tanggal 1 Sept 2025, menghafal surah 82 (Al-Infitar) dari ayat 1 sampai 13, total 13 ayat hari itu.")]),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== STEP 2 ==========
        heading("Step 2: Feature Engineering", HeadingLevel.HEADING_1),
        mixedP([normal("Model Machine Learning tidak bisa langsung membaca data mentah. Data harus diubah menjadi "), bold("fitur (features)"), normal(" \u2014 angka-angka yang merepresentasikan informasi penting dari data.")]),

        p("Dari data mentah 582 baris, di-extract 8 fitur yang dibagi jadi 2 kategori:"),

        heading("Fitur dari CSV (Karakteristik Surah)", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 6240],
          rows: [
            new TableRow({ children: [headerCell("Fitur", 3120), headerCell("Penjelasan", 6240)] }),
            new TableRow({ children: [cell("total_ayat_surah", 3120), cell("Total ayat dalam surah tersebut", 6240)] }),
            new TableRow({ children: [cell("rata_kata_per_ayat", 3120), cell("Rata-rata jumlah kata per ayat (ukuran kompleksitas)", 6240)] }),
            new TableRow({ children: [cell("rata_huruf_per_ayat", 3120), cell("Rata-rata jumlah huruf per ayat", 6240)] }),
            new TableRow({ children: [cell("std_kata_per_ayat", 3120), cell("Standar deviasi kata per ayat (variasi panjang ayat)", 6240)] }),
          ],
        }),

        heading("Fitur dari History Siswa (Pola Belajar)", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 6240],
          rows: [
            new TableRow({ children: [headerCell("Fitur", 3120), headerCell("Penjelasan", 6240)] }),
            new TableRow({ children: [cell("hari_ke", 3120), cell("Hari ke-berapa menghafal surah ini", 6240)] }),
            new TableRow({ children: [cell("ayat_sudah_dihafal", 3120), cell("Berapa ayat sudah dihafal sebelum hari ini", 6240)] }),
            new TableRow({ children: [cell("progress_persen", 3120), cell("Persentase progress hafalan surah ini", 6240)] }),
            new TableRow({ children: [cell("kecepatan_avg_sebelumnya", 3120), cell("Rata-rata ayat/hari siswa dari semua hafalan sebelumnya", 6240)] }),
          ],
        }),

        heading("Target (y)", HeadingLevel.HEADING_2),
        mixedP([normal("Yang diprediksi oleh model adalah "), bold("jumlah_ayat"), normal(" \u2014 berapa ayat yang berhasil dihafal siswa pada hari tersebut.")]),

        p("Contoh hasil feature engineering:"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1560, 1560, 1040, 1560, 1560, 1040, 1040],
          rows: [
            new TableRow({ children: [headerCell("total_ayat", 1560), headerCell("rata_kata", 1560), headerCell("hari_ke", 1040), headerCell("progress%", 1560), headerCell("kec_avg", 1560), headerCell("TARGET", 1040), headerCell("", 1040)] }),
            new TableRow({ children: [cell("19", 1560), cell("5.2", 1560), cell("1", 1040), cell("0%", 1560), cell("4.0", 1560), cell("13", 1040), cell("", 1040)] }),
            new TableRow({ children: [cell("19", 1560), cell("5.2", 1560), cell("2", 1040), cell("68%", 1560), cell("13.0", 1560), cell("6", 1040), cell("", 1040)] }),
            new TableRow({ children: [cell("22", 1560), cell("7.1", 1560), cell("1", 1040), cell("0%", 1560), cell("4.0", 1560), cell("4", 1040), cell("", 1040)] }),
          ],
        }),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== STEP 3 ==========
        heading("Step 3: Train-Test Split", HeadingLevel.HEADING_1),
        p("Dataset 582 baris dibagi menjadi 2 bagian:"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 2340, 4680],
          rows: [
            new TableRow({ children: [headerCell("Bagian", 2340), headerCell("Jumlah", 2340), headerCell("Fungsi", 4680)] }),
            new TableRow({ children: [cell("Train (80%)", 2340), cell("465 baris", 2340), cell("Model belajar pola dari data ini", 4680)] }),
            new TableRow({ children: [cell("Test (20%)", 2340), cell("117 baris", 2340), cell("Mengetes apakah model bisa prediksi data baru", 4680)] }),
          ],
        }),

        mixedP([bold("Kenapa harus dipisah?"), normal(" Supaya kita tahu apakah model beneran bisa prediksi data baru yang belum pernah dilihat. Kalau cuma ditest pakai data training, model bisa aja cuma \"menghapal\" jawaban (overfitting), bukan belajar pola.")]),

        p("Pembagian menggunakan random_state=42 untuk memastikan hasil reproducible (bisa diulang dengan hasil yang sama)."),

        // ========== STEP 4 ==========
        heading("Step 4: Train Decision Tree", HeadingLevel.HEADING_1),
        p("Decision Tree bekerja dengan cara membuat aturan (rules) berbentuk pohon keputusan. Model secara otomatis menemukan pola terbaik dari data training."),

        heading("Cara Kerja", HeadingLevel.HEADING_2),
        p("Model memecah data berdasarkan pertanyaan ya/tidak secara berurutan:"),

        mixedP([normal("Contoh rules yang dipelajari model:")]),
        p("Kecepatan avg siswa <= 3.5? (siswa lambat)"),
        p("   Ya \u2192 rata kata per ayat <= 5?"),
        p("      Ya \u2192 prediksi: 3 ayat/hari"),
        p("      Tidak \u2192 prediksi: 2 ayat/hari"),
        p("   Tidak (siswa cepat) \u2192 rata kata per ayat <= 6?"),
        p("      Ya \u2192 prediksi: 9 ayat/hari"),
        p("      Tidak \u2192 prediksi: 6 ayat/hari"),

        heading("Hyperparameter", HeadingLevel.HEADING_2),
        p("Parameter yang diset sebelum training:"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2600, 1560, 5200],
          rows: [
            new TableRow({ children: [headerCell("Parameter", 2600), headerCell("Nilai", 1560), headerCell("Penjelasan", 5200)] }),
            new TableRow({ children: [cell("max_depth", 2600), cell("8", 1560), cell("Kedalaman maksimal pohon (mencegah terlalu kompleks)", 5200)] }),
            new TableRow({ children: [cell("min_samples_split", 2600), cell("10", 1560), cell("Minimum data untuk bisa split (mencegah overfitting)", 5200)] }),
            new TableRow({ children: [cell("min_samples_leaf", 2600), cell("5", 1560), cell("Minimum data di setiap leaf/ujung pohon", 5200)] }),
          ],
        }),

        mixedP([normal("Hasil: pohon dengan kedalaman "), bold("8 level"), normal(" dan "), bold("62 leaf nodes"), normal(" (62 kemungkinan prediksi).")]),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== STEP 5 ==========
        heading("Step 5: Evaluasi Model", HeadingLevel.HEADING_1),
        p("Setelah model di-train, ditest menggunakan 117 baris data test yang belum pernah dilihat model."),

        heading("Metrik Evaluasi", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1872, 1560, 1560, 4368],
          rows: [
            new TableRow({ children: [headerCell("Metrik", 1872), headerCell("Train", 1560), headerCell("Test", 1560), headerCell("Arti", 4368)] }),
            new TableRow({ children: [cell("MAE", 1872), cell("0.88", 1560), cell("1.36", 1560), cell("Rata-rata error prediksi (dalam ayat). Prediksi meleset \u00B11.36 ayat", 4368)] }),
            new TableRow({ children: [cell("RMSE", 1872), cell("1.28", 1560), cell("1.89", 1560), cell("Seperti MAE tapi lebih menghukum error besar", 4368)] }),
            new TableRow({ children: [cell("R\u00B2", 1872), cell("0.86", 1560), cell("0.62", 1560), cell("Model menjelaskan 62% variasi data. Semakin dekat ke 1 = semakin baik", 4368)] }),
          ],
        }),

        heading("Interpretasi R\u00B2", HeadingLevel.HEADING_2),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2340, 7020],
          rows: [
            new TableRow({ children: [headerCell("Range R\u00B2", 2340), headerCell("Interpretasi", 7020)] }),
            new TableRow({ children: [cell("\u2265 0.80", 2340), cell("Sangat Baik: model menjelaskan >80% variasi data", 7020)] }),
            new TableRow({ children: [cell("0.60 - 0.79", 2340), cell("Baik: model cukup reliable untuk prediksi \u2190 model kita di sini (0.62)", 7020)] }),
            new TableRow({ children: [cell("0.40 - 0.59", 2340), cell("Cukup: model bisa digunakan dengan catatan", 7020)] }),
            new TableRow({ children: [cell("< 0.40", 2340), cell("Kurang: model perlu improvement", 7020)] }),
          ],
        }),

        mixedP([bold("Kesimpulan: "), normal("Dengan R\u00B2 = 0.62, model sudah cukup baik untuk memberikan estimasi. Rata-rata prediksi meleset sekitar 1-2 ayat, yang masih wajar untuk keperluan monitoring hafalan.")]),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== FEATURE IMPORTANCE ==========
        heading("Step 6: Feature Importance", HeadingLevel.HEADING_1),
        p("Feature importance menunjukkan seberapa besar kontribusi masing-masing fitur terhadap prediksi model:"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3744, 1872, 3744],
          rows: [
            new TableRow({ children: [headerCell("Fitur", 3744), headerCell("Importance", 1872), headerCell("Kontribusi", 3744)] }),
            new TableRow({ children: [cell("kecepatan_avg_sebelumnya", 3744), cell("64.16%", 1872), cell("\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588 DOMINAN", 3744)] }),
            new TableRow({ children: [cell("rata_kata_per_ayat", 3744), cell("17.68%", 1872), cell("\u2588\u2588\u2588\u2588\u2588", 3744)] }),
            new TableRow({ children: [cell("total_ayat_surah", 3744), cell("5.53%", 1872), cell("\u2588\u2588", 3744)] }),
            new TableRow({ children: [cell("ayat_sudah_dihafal", 3744), cell("5.08%", 1872), cell("\u2588\u2588", 3744)] }),
            new TableRow({ children: [cell("hari_ke", 3744), cell("4.89%", 1872), cell("\u2588", 3744)] }),
            new TableRow({ children: [cell("progress_persen", 3744), cell("2.26%", 1872), cell("\u2588", 3744)] }),
            new TableRow({ children: [cell("std_kata_per_ayat", 3744), cell("0.41%", 1872), cell("", 3744)] }),
            new TableRow({ children: [cell("rata_huruf_per_ayat", 3744), cell("0.00%", 1872), cell("", 3744)] }),
          ],
        }),

        heading("Insight", HeadingLevel.HEADING_2),
        mixedP([bold("Faktor paling menentukan adalah kebiasaan siswa (64%)."), normal(" Ini masuk akal: siswa yang biasa hafal banyak ayat per hari, cenderung terus hafal banyak. Siswa yang lambat, cenderung tetap lambat.")]),

        mixedP([bold("Faktor kedua adalah kompleksitas ayat (18%)."), normal(" Surah dengan ayat panjang (banyak kata) membuat siswa menghafal lebih sedikit ayat per hari dibandingkan surah dengan ayat pendek.")]),

        p("Gabungan keduanya (82%) menjelaskan bahwa prediksi hafalan sangat bergantung pada \"siapa siswanya\" dan \"surah apa yang dihafal\"."),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== VISUALISASI ==========
        heading("Step 7: Visualisasi Evaluasi", HeadingLevel.HEADING_1),
        p("Berikut adalah 4 chart yang dihasilkan dari evaluasi model:"),

        // Insert chart image
        ...(chartImage ? [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 200 },
            children: [new ImageRun({
              type: "png",
              data: chartImage,
              transformation: { width: 620, height: 440 },
              altText: { title: "Evaluasi Model", description: "4 chart evaluasi model Decision Tree", name: "evaluasi" },
            })],
          }),
        ] : [p("[Chart tidak tersedia - lihat models/evaluasi_model.png]")]),

        heading("Chart 1: Actual vs Predicted (Kiri Atas)", HeadingLevel.HEADING_2),
        mixedP([normal("Setiap titik mewakili 1 prediksi. "), bold("Sumbu X"), normal(" = jumlah ayat yang benar-benar dihafal, "), bold("Sumbu Y"), normal(" = prediksi model. Garis merah putus-putus adalah garis sempurna (prediksi = actual). Semakin dekat titik ke garis merah, semakin akurat prediksi.")]),

        heading("Chart 2: Feature Importance (Kanan Atas)", HeadingLevel.HEADING_2),
        p("Menampilkan seberapa besar pengaruh tiap fitur terhadap keputusan model. kecepatan_avg_sebelumnya mendominasi dengan 64%."),

        heading("Chart 3: Distribusi Error (Kiri Bawah)", HeadingLevel.HEADING_2),
        mixedP([normal("Histogram selisih (actual - predicted). Puncak di sekitar 0 artinya kebanyakan prediksi mendekati nilai sebenarnya. "), bold("MAE = 1.36"), normal(" artinya rata-rata error hanya 1-2 ayat.")]),

        heading("Chart 4: Kompleksitas vs Kemampuan (Kanan Bawah)", HeadingLevel.HEADING_2),
        mixedP([bold("Sumbu X"), normal(" = rata-rata kata per ayat (semakin kanan = ayat semakin panjang/sulit), "), bold("Sumbu Y"), normal(" = jumlah ayat dihafal per hari, "), bold("Warna"), normal(" = kecepatan rata-rata siswa (hijau = cepat, merah = lambat). Terlihat pola: ayat panjang \u2192 hafalan per hari lebih sedikit.")]),

        new Paragraph({ children: [new PageBreak()] }),

        // ========== OUTPUT FILES ==========
        heading("File Output", HeadingLevel.HEADING_1),
        p("Proses training menghasilkan file-file berikut:"),

        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [3120, 6240],
          rows: [
            new TableRow({ children: [headerCell("File", 3120), headerCell("Keterangan", 6240)] }),
            new TableRow({ children: [cell("models/decision_tree.joblib", 3120), cell("File model yang sudah di-train, siap dipakai untuk prediksi", 6240)] }),
            new TableRow({ children: [cell("models/tree_rules.txt", 3120), cell("Rules/aturan Decision Tree dalam format teks (bisa dibaca manusia)", 6240)] }),
            new TableRow({ children: [cell("models/evaluasi_model.png", 3120), cell("4 chart visualisasi evaluasi model", 6240)] }),
            new TableRow({ children: [cell("data/hafalan_features.csv", 3120), cell("Dataset lengkap dengan fitur yang sudah di-engineer", 6240)] }),
          ],
        }),

        // ========== CARA PAKAI ==========
        heading("Cara Penggunaan Model", HeadingLevel.HEADING_1),
        p("Setelah model di-train, model bisa digunakan untuk memprediksi kemampuan hafalan siswa:"),

        mixedP([bold("Input: "), normal("Data siswa (kecepatan rata-rata sebelumnya) + data surah (kompleksitas ayat)")]),
        mixedP([bold("Output: "), normal("Prediksi jumlah ayat yang bisa dihafal per hari")]),
        mixedP([bold("Estimasi hari: "), normal("sisa_ayat / prediksi_ayat_per_hari = estimasi hari untuk menyelesaikan surah")]),

        p("Contoh: siswa dengan kecepatan avg 5 ayat/hari ingin hafal surah Al-Mulk (30 ayat). Model mungkin prediksi 4 ayat/hari (karena ayat Al-Mulk cukup panjang). Estimasi selesai: 30/4 = sekitar 7-8 hari."),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/Users/muchtar/quran-ml/docs/penjelasan_training_model.docx", buffer);
  console.log("Document created: docs/penjelasan_training_model.docx");
});
