const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat,
} = require("docx");

const PRIMARY = "1B4332";
const ACCENT = "FFC107";
const NEUTRAL = "6C757D";
const BG_LIGHT = "F1FAF7";
const WHITE = "FFFFFF";
const BLACK = "000000";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorders = {
  top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
};

const cellPad = { top: 80, bottom: 80, left: 120, right: 120 };
const TABLE_W = 9360;

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, size: 32, font: "Arial", color: PRIMARY })],
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, bold: true, size: 26, font: "Arial", color: PRIMARY })],
  });
}

function heading3(text) {
  return new Paragraph({
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, bold: true, size: 22, font: "Arial", color: PRIMARY })],
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    alignment: opts.align || AlignmentType.LEFT,
    children: [new TextRun({ text, size: 21, font: "Arial", color: opts.color || BLACK, bold: opts.bold, italics: opts.italic })],
  });
}

function richPara(runs) {
  return new Paragraph({
    spacing: { after: 120 },
    children: runs.map(r => new TextRun({ size: 21, font: "Arial", color: BLACK, ...r })),
  });
}

function codeBlock(text) {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
    indent: { left: 360, right: 360 },
    children: [new TextRun({ text, size: 19, font: "Courier New", color: "333333" })],
  });
}

function makeRow(cells, opts = {}) {
  return new TableRow({
    children: cells.map((text, i) => {
      const widths = opts.widths || cells.map(() => Math.floor(TABLE_W / cells.length));
      return new TableCell({
        width: { size: widths[i], type: WidthType.DXA },
        borders,
        margins: cellPad,
        shading: opts.header ? { fill: PRIMARY, type: ShadingType.CLEAR } : (opts.alt ? { fill: BG_LIGHT, type: ShadingType.CLEAR } : undefined),
        children: [new Paragraph({
          children: [new TextRun({
            text: String(text), size: opts.header ? 20 : 19, font: "Arial",
            bold: opts.header || opts.bold, color: opts.header ? WHITE : BLACK,
          })],
        })],
      });
    }),
  });
}

function makeTable(headers, rows, widths) {
  const w = widths || headers.map(() => Math.floor(TABLE_W / headers.length));
  return new Table({
    width: { size: TABLE_W, type: WidthType.DXA },
    columnWidths: w,
    rows: [
      makeRow(headers, { header: true, widths: w }),
      ...rows.map((r, i) => makeRow(r, { widths: w, alt: i % 2 === 1 })),
    ],
  });
}

// Diagram as colored table (flowchart style)
function flowBox(text, color, textColor) {
  return new TableCell({
    width: { size: 2340, type: WidthType.DXA },
    borders: noBorders,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    shading: { fill: color, type: ShadingType.CLEAR },
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, size: 18, font: "Arial", bold: true, color: textColor || WHITE })],
    })],
  });
}

function arrowCell() {
  return new TableCell({
    width: { size: 360, type: WidthType.DXA },
    borders: noBorders,
    margins: { top: 0, bottom: 0, left: 0, right: 0 },
    verticalAlign: "center",
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "\u2192", size: 24, font: "Arial", bold: true, color: ACCENT })],
    })],
  });
}

// Load evaluation chart
let evalChartBuffer = null;
const chartPath = "/Users/muchtar/quran-ml/models/evaluasi_model.png";
if (fs.existsSync(chartPath)) {
  evalChartBuffer = fs.readFileSync(chartPath);
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: PRIMARY },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: PRIMARY },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [
    // ===== COVER PAGE =====
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 2880, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children: [
        new Paragraph({ spacing: { after: 600 }, alignment: AlignmentType.CENTER, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 200 },
          children: [new TextRun({ text: "DOKUMENTASI", size: 40, bold: true, font: "Arial", color: PRIMARY })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 200 },
          children: [new TextRun({ text: "MACHINE LEARNING", size: 48, bold: true, font: "Arial", color: PRIMARY })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 100 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 8 } },
          children: [new TextRun({ text: "Prediksi Kecepatan Hafalan Al-Qur\u2019an", size: 28, font: "Arial", color: NEUTRAL })],
        }),
        new Paragraph({ spacing: { after: 400 }, children: [] }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 100 },
          children: [new TextRun({ text: "Penerapan Machine Learning Menggunakan Algoritma Decision Tree", size: 22, font: "Arial", color: BLACK })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 100 },
          children: [new TextRun({ text: "untuk Memprediksi Kemampuan Hafalan Al-Qur\u2019an", size: 22, font: "Arial", color: BLACK })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 400 },
          children: [new TextRun({ text: "pada Sistem Monitoring Hafalan Berbasis Website", size: 22, font: "Arial", color: BLACK })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 100 },
          children: [new TextRun({ text: "Dokumen Persiapan Sidang Skripsi", size: 24, bold: true, font: "Arial", color: NEUTRAL })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "2026", size: 24, font: "Arial", color: NEUTRAL })],
        }),
      ],
    },
    // ===== MAIN CONTENT =====
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
            border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: PRIMARY, space: 4 } },
            children: [new TextRun({ text: "Dokumentasi ML \u2014 Prediksi Hafalan Al-Qur\u2019an", size: 16, font: "Arial", color: NEUTRAL, italics: true })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Halaman ", size: 16, font: "Arial", color: NEUTRAL }),
                       new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: NEUTRAL })],
          })],
        }),
      },
      children: [
        // ===== 1. GAMBARAN UMUM =====
        heading1("1. Gambaran Umum Sistem"),

        heading2("1.1 Apa yang Diprediksi?"),
        richPara([
          { text: "Model ML memprediksi " },
          { text: "kecepatan hafalan siswa", bold: true },
          { text: " (satuan: " },
          { text: "ayat per hari", bold: true },
          { text: ")." },
        ]),
        para("Model TIDAK langsung memprediksi berapa hari lagi selesai. Estimasi hari dihitung dari rumus sederhana:"),
        codeBlock("estimasi_hari = sisa_ayat / prediksi_kecepatan"),

        heading2("1.2 Kenapa Pendekatan Ini?"),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 },
          children: [new TextRun({ text: "Kecepatan hafalan terukur dan punya pola \u2014 siswa cenderung konsisten", size: 21, font: "Arial" })],
        }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 },
          children: [new TextRun({ text: "Memprediksi hari selesai langsung jauh lebih sulit (faktor luar: sakit, libur, motivasi)", size: 21, font: "Arial" })],
        }),
        new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
          children: [new TextRun({ text: "Dengan memprediksi kecepatan, bisa menghitung estimasi untuk surah apapun", size: 21, font: "Arial" })],
        }),

        heading2("1.3 Alur Kerja (End-to-End)"),
        heading3("Training (offline, sekali)"),
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [2340, 360, 2340, 360, 2340, 360, 820],
          rows: [new TableRow({ children: [
            flowBox("hafalan_log\n(MySQL)", PRIMARY),
            arrowCell(),
            flowBox("Feature\nEngineering\n(12 fitur)", "2D6A4F"),
            arrowCell(),
            flowBox("RandomForest\n.fit()", ACCENT, PRIMARY),
            arrowCell(),
            flowBox("model\n.joblib", NEUTRAL),
          ]})],
        }),
        new Paragraph({ spacing: { after: 200 }, children: [] }),

        heading3("Prediksi (runtime, per request)"),
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [1560, 360, 1560, 360, 1560, 360, 1560, 360, 1360],
          rows: [new TableRow({ children: [
            flowBox("Input\nsiswa + surah", PRIMARY),
            arrowCell(),
            flowBox("Query\nMySQL", "2D6A4F"),
            arrowCell(),
            flowBox("Hitung\n12 Fitur", "2D6A4F"),
            arrowCell(),
            flowBox("Model\nPredict", ACCENT, PRIMARY),
            arrowCell(),
            flowBox("Post-\nProcess", NEUTRAL),
          ]})],
        }),
        new Paragraph({ spacing: { after: 300 }, children: [] }),

        // ===== 2. DATASET =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("2. Dataset"),

        heading2("2.1 Sumber Data"),
        makeTable(
          ["Sumber", "Isi", "Format"],
          [
            ["hafalan_log (MySQL)", "Catatan setoran harian siswa", "Tabel relasional"],
            ["quran_stats.csv", "Statistik per surah (jumlah ayat, kata, huruf)", "CSV"],
            ["ayah_stats_sync.csv", "Statistik per ayat (jumlah kata, huruf)", "CSV"],
          ],
          [3120, 3120, 3120],
        ),

        heading2("2.2 Statistik Dataset"),
        makeTable(
          ["Item", "Nilai"],
          [
            ["Total rows", "586"],
            ["Jumlah siswa", "27"],
            ["Jumlah surah", "45"],
            ["Rentang waktu", "September 2025 \u2014 Maret 2026"],
            ["Target (jumlah_ayat) rata-rata", "4.12 ayat/hari"],
            ["Target standar deviasi", "3.44"],
          ],
          [4680, 4680],
        ),

        heading2("2.3 Struktur Tabel hafalan_log"),
        makeTable(
          ["Kolom", "Tipe", "Keterangan"],
          [
            ["id", "INT", "Primary key"],
            ["siswa_id", "INT", "FK ke tabel users"],
            ["guru_id", "INT", "FK ke tabel users"],
            ["surah_id", "INT", "1\u2013114"],
            ["ayat_mulai", "INT", "Ayat awal yang disetorkan"],
            ["ayat_selesai", "INT", "Ayat akhir yang disetorkan"],
            ["jumlah_ayat", "INT", "ayat_selesai - ayat_mulai + 1 (TARGET)"],
            ["tanggal", "DATE", "Tanggal setoran"],
            ["catatan", "TEXT", "Catatan dari guru"],
          ],
          [2340, 1560, 5460],
        ),

        // ===== 3. FEATURE ENGINEERING =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("3. Feature Engineering"),

        para("Data mentah hanya berisi \"siswa X menyetor Y ayat pada tanggal Z\". Model tidak bisa langsung belajar dari ini. Feature engineering mengubah data mentah menjadi sinyal yang bermakna."),

        heading2("3.1 Fitur Surah (statis, dari CSV \u2014 3 fitur)"),
        makeTable(
          ["Fitur", "Cara Hitung", "Arti"],
          [
            ["total_ayat_surah", "Dari quran_stats.csv", "Jumlah ayat dalam surah"],
            ["rata_kata_per_ayat", "mean(kata) per surah", "Rata-rata kata per ayat (proxy kesulitan)"],
            ["rata_huruf_per_ayat", "mean(huruf) per surah", "Rata-rata huruf per ayat (proxy panjang)"],
          ],
          [2600, 3380, 3380],
        ),

        heading2("3.2 Fitur Progress (per siswa per surah \u2014 3 fitur)"),
        makeTable(
          ["Fitur", "Cara Hitung", "Arti"],
          [
            ["hari_ke", "cumcount per (siswa, surah) + 1", "Hari ke-berapa menghafal surah ini"],
            ["ayat_sudah_dihafal", "cumsum(jumlah_ayat), shift(1)", "Total ayat dihafal SEBELUM hari ini"],
            ["progress_persen", "(ayat_sudah / total_ayat) * 100", "Persentase penyelesaian surah"],
          ],
          [2600, 3380, 3380],
        ),

        heading2("3.3 Fitur Riwayat Kecepatan (per siswa \u2014 6 fitur)"),
        makeTable(
          ["Fitur", "Cara Hitung", "Arti"],
          [
            ["kecepatan_avg_sebelumnya", "expanding mean, shift(1)", "Rata-rata kecepatan dari SEMUA setoran sebelumnya"],
            ["lag_1", "shift(1) per siswa", "Jumlah ayat 1 setoran lalu"],
            ["lag_2", "shift(2) per siswa", "Jumlah ayat 2 setoran lalu"],
            ["lag_3", "shift(3) per siswa", "Jumlah ayat 3 setoran lalu"],
            ["rolling_mean_3", "rolling(3).mean(), shift(1)", "Rata-rata kecepatan 3 setoran terakhir"],
            ["total_setoran_sebelumnya", "cumcount per siswa", "Berapa kali sudah setor sebelumnya"],
          ],
          [2900, 3000, 3460],
        ),

        heading3("Visualisasi Lag Features"),
        // Lag visualization as table
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [1560, 1560, 1560, 1560, 1560, 1560],
          rows: [
            new TableRow({ children: ["3", "5", "2", "7", "4", "?"].map((v, i) => new TableCell({
              width: { size: 1560, type: WidthType.DXA },
              borders,
              margins: cellPad,
              shading: i === 5 ? { fill: ACCENT, type: ShadingType.CLEAR } : (i >= 2 && i <= 4 ? { fill: BG_LIGHT, type: ShadingType.CLEAR } : undefined),
              children: [new Paragraph({ alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: v, size: 22, font: "Arial", bold: true, color: i === 5 ? PRIMARY : BLACK })] })],
            })) }),
            new TableRow({ children: ["", "", "lag_3=2", "lag_2=7", "lag_1=4", "PREDIKSI"].map((v, i) => new TableCell({
              width: { size: 1560, type: WidthType.DXA },
              borders: noBorders,
              margins: cellPad,
              children: [new Paragraph({ alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: v, size: 16, font: "Arial", color: NEUTRAL, italics: true })] })],
            })) }),
          ],
        }),
        para("rolling_mean_3 = mean(4, 7, 2) = 4.33", { italic: true, color: NEUTRAL }),

        heading2("3.4 Data Leakage Audit"),
        para("Data leakage = fitur yang secara tidak sengaja bocor informasi dari masa depan. Semua fitur temporal menggunakan shift() \u2014 model HANYA melihat data yang sudah terjadi."),
        makeTable(
          ["Fitur", "Aman?", "Mekanisme Pencegahan"],
          [
            ["kecepatan_avg_sebelumnya", "\u2705 Ya", "expanding().mean().shift(1)"],
            ["lag_1, lag_2, lag_3", "\u2705 Ya", "shift(1/2/3) per siswa"],
            ["rolling_mean_3", "\u2705 Ya", "rolling(3).mean().shift(1)"],
            ["ayat_sudah_dihafal", "\u2705 Ya", "cumsum().shift(1)"],
            ["progress_persen", "\u2705 Ya", "Derived dari ayat_sudah_dihafal"],
            ["hari_ke, total_setoran", "\u2705 Ya", "cumcount (before current row)"],
            ["Fitur surah (3 fitur)", "\u2705 Ya", "Data statis dari CSV"],
          ],
          [3120, 1040, 5200],
        ),

        // ===== 4. ALGORITMA =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("4. Algoritma: Random Forest Regressor"),

        heading2("4.1 Apa itu Random Forest?"),
        richPara([
          { text: "Random Forest adalah " },
          { text: "ensemble", bold: true },
          { text: " (kumpulan) dari banyak Decision Tree yang bekerja bersama. Setiap tree dilatih dengan subset data dan fitur yang berbeda, lalu hasil prediksinya dirata-ratakan." },
        ]),

        // RF diagram
        heading3("Cara Kerja Random Forest"),
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [3120, 3120, 3120],
          rows: [
            new TableRow({ children: [
              new TableCell({ width: { size: 9360, type: WidthType.DXA }, borders: noBorders, columnSpan: 3,
                shading: { fill: PRIMARY, type: ShadingType.CLEAR }, margins: cellPad,
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "DATA TRAINING (586 rows, 12 fitur)", size: 20, font: "Arial", bold: true, color: WHITE })] })],
              }),
            ]}),
            new TableRow({ children: [
              new TableCell({ width: { size: 9360, type: WidthType.DXA }, borders: noBorders, columnSpan: 3,
                margins: { top: 40, bottom: 40, left: 0, right: 0 },
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "\u25BC          \u25BC          \u25BC", size: 20, font: "Arial", color: ACCENT })] })],
              }),
            ]}),
            new TableRow({ children: ["Tree 1\n(subset data A)\npred: 3.2", "Tree 2\n(subset data B)\npred: 4.1", "... Tree 200\n(subset data N)\npred: 3.8"].map(t =>
              new TableCell({ width: { size: 3120, type: WidthType.DXA }, borders,
                shading: { fill: BG_LIGHT, type: ShadingType.CLEAR }, margins: cellPad,
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: t, size: 18, font: "Arial", color: PRIMARY })] })],
              })
            ) }),
            new TableRow({ children: [
              new TableCell({ width: { size: 9360, type: WidthType.DXA }, borders: noBorders, columnSpan: 3,
                margins: { top: 40, bottom: 40, left: 0, right: 0 },
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "\u25BC RATA-RATA \u25BC", size: 20, font: "Arial", bold: true, color: ACCENT })] })],
              }),
            ]}),
            new TableRow({ children: [
              new TableCell({ width: { size: 9360, type: WidthType.DXA }, borders: noBorders, columnSpan: 3,
                shading: { fill: ACCENT, type: ShadingType.CLEAR }, margins: cellPad,
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "PREDIKSI AKHIR = 3.7 ayat/hari", size: 22, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
            ]}),
          ],
        }),

        heading2("4.2 Kenapa Random Forest?"),
        makeTable(
          ["Aspek", "Decision Tree", "Random Forest"],
          [
            ["Overfit", "Sangat mudah", "Jauh lebih tahan"],
            ["Stabilitas", "Prediksi loncat-loncat", "Lebih smooth (rata-rata 200 tree)"],
            ["Akurasi", "Oke", "Lebih baik (wisdom of crowds)"],
            ["Interpretasi", "Export jadi rules", "Feature importance bawaan"],
            ["Dataset kecil?", "Rawan overfit", "Aman dgn parameter konservatif"],
          ],
          [2080, 3640, 3640],
        ),

        heading2("4.3 Parameter yang Digunakan"),
        makeTable(
          ["Parameter", "Nilai", "Alasan"],
          [
            ["n_estimators", "200", "Cukup banyak untuk stabilitas"],
            ["max_depth", "8", "Mencegah tree terlalu dalam (overfit)"],
            ["min_samples_leaf", "5", "Setiap leaf minimal 5 sampel"],
            ["random_state", "42", "Reproducibility (hasil bisa diulang)"],
          ],
          [2340, 1560, 5460],
        ),

        // ===== 5. TRAINING PIPELINE =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("5. Training Pipeline"),

        heading2("5.1 Alur Training"),
        // Steps as colored boxes
        ...[
          { step: "STEP 1", title: "Load Data", desc: "Baca hafalan_log dari MySQL + data surah/ayat dari CSV" },
          { step: "STEP 2", title: "Fitur Surah", desc: "Gabungkan statistik surah (total ayat, rata-rata kata/huruf)" },
          { step: "STEP 3", title: "Feature Engineering", desc: "Hitung 12 fitur per baris. Semua pakai shift() untuk cegah leakage" },
          { step: "STEP 4", title: "Time-Based Split", desc: "80% train (Sep\u2013Okt), 20% test (Nov\u2013Mar). Cutoff: 27 Okt 2025" },
          { step: "STEP 5", title: "Train Model", desc: "RandomForest.fit(X_train, y_train) + evaluasi + cross-validation" },
          { step: "STEP 6", title: "Feature Importance", desc: "Ranking fitur berdasarkan kontribusi ke prediksi" },
          { step: "STEP 7", title: "Simpan Model", desc: "Simpan ke models/decision_tree.joblib (model + metadata)" },
          { step: "STEP 8", title: "Visualisasi", desc: "3 panel: Actual vs Predicted, Feature Importance, Distribusi Error" },
        ].map(s => new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [1200, 8160],
          rows: [new TableRow({ children: [
            new TableCell({ width: { size: 1200, type: WidthType.DXA }, borders: noBorders,
              shading: { fill: PRIMARY, type: ShadingType.CLEAR }, margins: cellPad,
              children: [new Paragraph({ alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: s.step, size: 16, font: "Arial", bold: true, color: WHITE })] })],
            }),
            new TableCell({ width: { size: 8160, type: WidthType.DXA }, borders: noBorders,
              shading: { fill: BG_LIGHT, type: ShadingType.CLEAR }, margins: cellPad,
              children: [
                new Paragraph({ children: [new TextRun({ text: s.title, size: 20, font: "Arial", bold: true, color: PRIMARY })] }),
                new Paragraph({ children: [new TextRun({ text: s.desc, size: 18, font: "Arial", color: NEUTRAL })] }),
              ],
            }),
          ]})],
        })),

        heading2("5.2 Time-Based Split vs Random Split"),
        // Comparison diagram
        makeTable(
          ["", "Random Split (SALAH)", "Time-Based Split (BENAR)"],
          [
            ["Train", "Jan, Mar, Feb, Apr (campur)", "Sep, Sep, Okt, Okt (masa lalu)"],
            ["Test", "Feb, May, Jan (campur)", "Nov, Des, Jan, Mar (masa depan)"],
            ["Masalah", "Temporal leakage!", "Mensimulasikan kondisi nyata"],
          ],
          [1200, 4080, 4080],
        ),

        heading2("5.3 Distribution Shift"),
        makeTable(
          ["Periode", "Rata-rata Kecepatan", "Keterangan"],
          [
            ["Train (Sep\u2013Okt)", "4.62 ayat/hari", "Siswa masih semangat, surah mudah"],
            ["Test (Nov\u2013Mar)", "2.10 ayat/hari", "Surah lebih sulit, motivasi turun"],
            ["Shift", "54.5%", "Perilaku siswa berubah drastis"],
          ],
          [2340, 3120, 3900],
        ),
        para("Dampak: R\u00B2 test lebih rendah dari train. Ini NORMAL dan EXPECTED \u2014 model tidak gagal, dunia memang berubah.", { italic: true }),

        // ===== 6. EVALUASI =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("6. Evaluasi Model"),

        heading2("6.1 MAE (Mean Absolute Error)"),
        codeBlock("MAE = rata-rata( |actual - predicted| )"),
        para("Artinya: rata-rata, prediksi meleset berapa ayat?"),
        makeTable(
          ["Set", "MAE", "Interpretasi"],
          [
            ["Train", "1.00", "Meleset ~1 ayat di data training"],
            ["Test", "0.95", "Meleset ~1 ayat di data baru"],
          ],
          [2080, 2080, 5200],
        ),
        richPara([
          { text: "MAE ~1 ayat itu bagus? ", bold: true },
          { text: "Target rata-rata = 4.12. Meleset 1 ayat = error ~24%. Untuk prediksi perilaku manusia, ini " },
          { text: "sangat reasonable", bold: true },
          { text: "." },
        ]),

        heading2("6.2 R\u00B2 (Koefisien Determinasi)"),
        codeBlock("R\u00B2 = 1 - (sum of squared errors / total variance)"),
        para("Artinya: berapa persen variasi data yang bisa dijelaskan model?"),
        makeTable(
          ["Set", "R\u00B2", "Interpretasi"],
          [
            ["Train", "0.84", "Model menjelaskan 84% variasi di data training"],
            ["Test", "0.37", "Model menjelaskan 37% variasi di data baru"],
            ["CV (rata-rata)", "0.56", "Rata-rata 56% di 5 fold cross-validation"],
          ],
          [2080, 2080, 5200],
        ),

        heading2("6.3 Feature Importance"),
        makeTable(
          ["Rank", "Fitur", "Importance", "Penjelasan"],
          [
            ["1", "kecepatan_avg_sebelumnya", "43.3%", "Riwayat kecepatan = prediktor #1"],
            ["2", "rolling_mean_3", "19.8%", "Performa 3 setoran terakhir"],
            ["3", "progress_persen", "8.6%", "Makin jauh progress, makin pelan"],
            ["4", "lag_1", "6.2%", "Setoran terakhir"],
            ["5", "total_ayat_surah", "5.1%", "Surah panjang = lebih lambat"],
            ["6", "rata_kata_per_ayat", "4.9%", "Ayat kompleks = lebih lambat"],
            ["7", "rata_huruf_per_ayat", "4.3%", "Ayat panjang = lebih lambat"],
            ["8\u201312", "lag_2, lag_3, dll", "<3%", "Kontribusi kecil tapi tetap berguna"],
          ],
          [780, 3120, 1560, 3900],
        ),
        richPara([
          { text: "Insight: ", bold: true },
          { text: "63% prediksi ditentukan oleh 2 fitur saja (kecepatan historis + performa terbaru). Ini masuk akal: kecepatan besok paling ditentukan oleh kecepatan kemarin." },
        ]),

        heading2("6.4 Grafik Evaluasi Model"),
        ...(evalChartBuffer ? [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 200 },
            children: [new ImageRun({
              type: "png",
              data: evalChartBuffer,
              transformation: { width: 620, height: 200 },
              altText: { title: "Evaluasi Model", description: "Grafik evaluasi model ML", name: "evaluasi_model" },
            })],
          }),
          para("Gambar: Actual vs Predicted, Feature Importance, dan Distribusi Error", { italic: true, color: NEUTRAL, align: AlignmentType.CENTER }),
        ] : [para("(Grafik evaluasi_model.png tidak ditemukan)", { italic: true, color: NEUTRAL })]),

        // ===== 7. POST-PROCESSING =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("7. Post-Processing & Prediksi Runtime"),

        para("Model ML memberikan angka mentah yang kadang terlalu optimis atau tidak realistis. Post-processing memperbaiki output supaya lebih bisa dipercaya user."),

        heading2("7.1 Pipeline Post-Processing"),
        // 3-step diagram
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [780, 2860, 5720],
          rows: [
            makeRow(["Step", "Nama", "Logic"], { header: true, widths: [780, 2860, 5720] }),
            new TableRow({ children: [
              new TableCell({ width: { size: 780, type: WidthType.DXA }, borders, margins: cellPad,
                shading: { fill: ACCENT, type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "1", size: 22, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
              new TableCell({ width: { size: 2860, type: WidthType.DXA }, borders, margins: cellPad,
                children: [new Paragraph({ children: [new TextRun({ text: "Blending", size: 20, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
              new TableCell({ width: { size: 5720, type: WidthType.DXA }, borders, margins: cellPad,
                children: [
                  new Paragraph({ children: [new TextRun({ text: "final = 0.7 * model + 0.3 * rolling_mean_3", size: 19, font: "Courier New" })] }),
                  new Paragraph({ children: [new TextRun({ text: "Model kadang overpredict, rolling_mean_3 = performa aktual terbaru", size: 17, font: "Arial", color: NEUTRAL })] }),
                ],
              }),
            ]}),
            new TableRow({ children: [
              new TableCell({ width: { size: 780, type: WidthType.DXA }, borders, margins: cellPad,
                shading: { fill: ACCENT, type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "2", size: 22, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
              new TableCell({ width: { size: 2860, type: WidthType.DXA }, borders, margins: cellPad,
                children: [new Paragraph({ children: [new TextRun({ text: "Context Adjust", size: 20, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
              new TableCell({ width: { size: 5720, type: WidthType.DXA }, borders, margins: cellPad,
                children: [
                  new Paragraph({ children: [new TextRun({ text: "Surah >100 ayat: -5%, >15 kata/ayat: -5%, >200 ayat: -5%", size: 19, font: "Courier New" })] }),
                  new Paragraph({ children: [new TextRun({ text: "Adjustment ringan (max -15%) untuk surah panjang/kompleks", size: 17, font: "Arial", color: NEUTRAL })] }),
                ],
              }),
            ]}),
            new TableRow({ children: [
              new TableCell({ width: { size: 780, type: WidthType.DXA }, borders, margins: cellPad,
                shading: { fill: ACCENT, type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "3", size: 22, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
              new TableCell({ width: { size: 2860, type: WidthType.DXA }, borders, margins: cellPad,
                children: [new Paragraph({ children: [new TextRun({ text: "Clamp", size: 20, font: "Arial", bold: true, color: PRIMARY })] })],
              }),
              new TableCell({ width: { size: 5720, type: WidthType.DXA }, borders, margins: cellPad,
                children: [
                  new Paragraph({ children: [new TextRun({ text: "Min=1, Max=2x rata-rata siswa (min 10)", size: 19, font: "Courier New" })] }),
                  new Paragraph({ children: [new TextRun({ text: "Batasi ke range realistis, max dinamis per siswa", size: 17, font: "Arial", color: NEUTRAL })] }),
                ],
              }),
            ]}),
          ],
        }),

        heading2("7.2 Contoh Lengkap"),
        // Example box
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [9360],
          rows: [new TableRow({ children: [
            new TableCell({ width: { size: 9360, type: WidthType.DXA },
              borders: { top: { style: BorderStyle.SINGLE, size: 3, color: PRIMARY }, bottom: { style: BorderStyle.SINGLE, size: 3, color: PRIMARY },
                         left: { style: BorderStyle.SINGLE, size: 3, color: PRIMARY }, right: { style: BorderStyle.SINGLE, size: 3, color: PRIMARY } },
              margins: { top: 120, bottom: 120, left: 200, right: 200 },
              shading: { fill: BG_LIGHT, type: ShadingType.CLEAR },
              children: [
                new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Input:", size: 20, font: "Arial", bold: true, color: PRIMARY })] }),
                new Paragraph({ spacing: { after: 40 }, indent: { left: 360 }, children: [new TextRun({ text: "Siswa: Ahmad  |  Surah: Al-Mulk (30 ayat)  |  Sudah dihafal: 12  |  Sisa: 18 ayat", size: 19, font: "Arial" })] }),
                new Paragraph({ spacing: { before: 120, after: 60 }, children: [new TextRun({ text: "Processing:", size: 20, font: "Arial", bold: true, color: PRIMARY })] }),
                new Paragraph({ spacing: { after: 40 }, indent: { left: 360 }, children: [new TextRun({ text: "Model prediksi: 4.1 ayat/hari  \u2192  Post-process: 3.8 ayat/hari", size: 19, font: "Arial" })] }),
                new Paragraph({ spacing: { before: 120, after: 60 }, children: [new TextRun({ text: "Output:", size: 20, font: "Arial", bold: true, color: PRIMARY })] }),
                new Paragraph({ spacing: { after: 40 }, indent: { left: 360 }, children: [new TextRun({ text: "Prediksi kecepatan: 3.8 ayat/hari", size: 20, font: "Arial", bold: true, color: PRIMARY })] }),
                new Paragraph({ spacing: { after: 40 }, indent: { left: 360 }, children: [new TextRun({ text: "Estimasi selesai: 5 hari  (range: 5\u20136 hari)", size: 20, font: "Arial", bold: true, color: PRIMARY })] }),
                new Paragraph({ indent: { left: 360 }, children: [new TextRun({ text: "Insight: \"Kecepatan hafalan cukup stabil.\"", size: 19, font: "Arial", italics: true, color: NEUTRAL })] }),
              ],
            }),
          ]})],
        }),

        // ===== 8. ARSITEKTUR =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("8. Arsitektur Sistem"),

        heading2("8.1 Tech Stack"),
        makeTable(
          ["Komponen", "Teknologi"],
          [
            ["Backend", "Python + FastAPI"],
            ["Database", "MySQL (XAMPP)"],
            ["Frontend", "Jinja2 Templates (server-side rendering)"],
            ["ML Library", "scikit-learn (RandomForestRegressor)"],
            ["Data Processing", "pandas, numpy"],
            ["Model Storage", "joblib (.joblib file)"],
          ],
          [3120, 6240],
        ),

        heading2("8.2 Alur Request Prediksi"),
        // Request flow as step boxes
        new Table({
          width: { size: TABLE_W, type: WidthType.DXA },
          columnWidths: [9360],
          rows: [
            ...[
              { label: "1. Browser", desc: "GET /api/prediksi?siswa_id=5&surah_id=67", color: NEUTRAL },
              { label: "2. FastAPI (main.py)", desc: "Route menerima request, panggil predictor", color: PRIMARY },
              { label: "3. predictor.py", desc: "get_surah_features() + get_siswa_history() + MODEL.predict()", color: "2D6A4F" },
              { label: "4. Post-processing", desc: "compute_final_speed() + generate_insight()", color: ACCENT },
              { label: "5. Response JSON", desc: '{ prediksi_ayat_per_hari: 3.8, estimasi_hari: 5, insight: "..." }', color: PRIMARY },
            ].map(s => new TableRow({ children: [
              new TableCell({ width: { size: 9360, type: WidthType.DXA }, borders: noBorders,
                margins: { top: 40, bottom: 40, left: 120, right: 120 },
                shading: { fill: s.color === ACCENT ? ACCENT : (s.color === NEUTRAL ? "E8E8E8" : BG_LIGHT), type: ShadingType.CLEAR },
                children: [new Paragraph({
                  children: [
                    new TextRun({ text: s.label + "  ", size: 19, font: "Arial", bold: true, color: s.color === ACCENT ? PRIMARY : PRIMARY }),
                    new TextRun({ text: s.desc, size: 18, font: "Arial", color: s.color === ACCENT ? PRIMARY : NEUTRAL }),
                  ],
                })],
              }),
            ]})),
          ],
        }),

        // ===== 9. PERTANYAAN SIDANG =====
        new Paragraph({ children: [new PageBreak()] }),
        heading1("9. Jawaban untuk Pertanyaan Sidang"),

        // Q&A format
        ...buildQA("Kenapa pakai Random Forest, bukan algoritma lain?", [
          "1. Tahan overfit di dataset kecil (586 rows). Random Forest menggunakan 200 tree dengan data dan fitur berbeda, lalu rata-ratakan hasilnya. Seperti bertanya ke 200 pakar lalu ambil konsensus.",
          "2. Menangkap hubungan non-linear. Siswa yang sudah hafal 80% surah bisa LEBIH LAMBAT (fatigue). Ridge Regression tidak bisa menangkap pola ini.",
          "3. Feature importance bawaan. Langsung bisa lihat fitur mana yang paling berpengaruh.",
          "Perbandingan: Ridge Regression menghasilkan R\u00B2 = -0.10 (lebih buruk dari menebak rata-rata). Random Forest: R\u00B2 = 0.37.",
        ]),
        ...buildQA("Kenapa R\u00B2 nya cuma 0.37? Itu kan rendah?", [
          "1. Distribution shift 54.5% \u2014 perilaku siswa berubah drastis antara training dan test period.",
          "2. Cross-validation R\u00B2 = 0.56 \u2014 lebih representatif karena melihat beberapa periode.",
          "3. MAE = 0.95 ayat \u2014 model hanya meleset ~1 ayat. Untuk estimasi waktu, ini sangat usable.",
          "4. Ini prediksi perilaku manusia, bukan fisika. Manusia tidak konsisten. R\u00B2 0.37 dengan shift >50% sudah bagus.",
        ]),
        ...buildQA("Apa itu data leakage dan bagaimana mencegahnya?", [
          "Data leakage = model melihat informasi masa depan saat training. Seperti ujian buka buku.",
          "Pencegahan: semua fitur temporal pakai shift() (hanya data sebelum hari yang diprediksi), time-based split, dan TimeSeriesSplit untuk CV.",
          "Audit leakage dilakukan untuk semua 12 fitur dan semuanya aman.",
        ]),
        ...buildQA("Kenapa pakai time-based split, bukan random split?", [
          "Data hafalan punya urutan waktu. Random split = model bisa lihat data Maret saat training dan prediksi Januari.",
          "Time-based split mensimulasikan kondisi nyata: data sampai Oktober, prediksi November ke depan.",
        ]),
        ...buildQA("Apa itu feature engineering dan kenapa penting?", [
          "Data mentah hanya siswa X, Y ayat, tanggal Z. Model tidak bisa langsung belajar.",
          "Feature engineering mengubah data mentah jadi sinyal bermakna: hari ke-berapa, rata-rata kecepatan, tren naik/turun.",
          "Fitur terpenting: kecepatan_avg_sebelumnya (43%) \u2014 kecepatan besok ditentukan kecepatan kemarin.",
        ]),
        ...buildQA("Kenapa ada post-processing?", [
          "Bukan karena model kurang bagus, tapi output perlu disesuaikan untuk production.",
          "Blending: 70% model + 30% data aktual = lebih stabil.",
          "Context: surah panjang/kompleks perlu koreksi ringan (max -15%).",
          "Clamp: prediksi tidak boleh keluar batas wajar.",
          "Ini praktik standar di industri ML.",
        ]),
        ...buildQA("Bagaimana estimasi hari dihitung?", [
          "Rumus: estimasi_hari = sisa_ayat / prediksi_kecepatan",
          "Contoh: Surah Al-Mulk, sisa 18 ayat, kecepatan 3.8 ayat/hari \u2192 18/3.8 = 5 hari.",
          "Ditambah range: 5\u20136 hari (90%\u2013120% dari estimasi).",
        ]),
        ...buildQA("Bagaimana kalau siswa baru?", [
          "Fitur riwayat diisi GLOBAL MEDIAN (3.0 ayat/hari) = prediksi siswa rata-rata.",
          "Setelah 3+ setoran, model mulai mempersonalisasi berdasarkan data aktual.",
          "Insight menampilkan: \"Data masih sedikit, estimasi akan lebih akurat setelah beberapa setoran.\"",
        ]),
        ...buildQA("Tools/library apa yang dipakai?", [
          "scikit-learn: RandomForestRegressor, TimeSeriesSplit, metrics",
          "pandas: manipulasi data tabular, feature engineering",
          "numpy: operasi numerik",
          "joblib: simpan/muat model",
          "matplotlib: visualisasi evaluasi",
          "FastAPI: web framework untuk serving prediksi",
          "PyMySQL: koneksi ke MySQL",
        ]),
      ],
    },
  ],
});

function buildQA(question, answers) {
  return [
    new Paragraph({
      spacing: { before: 240, after: 100 },
      shading: { fill: BG_LIGHT, type: ShadingType.CLEAR },
      indent: { left: 200, right: 200 },
      children: [
        new TextRun({ text: "Q: ", size: 21, font: "Arial", bold: true, color: PRIMARY }),
        new TextRun({ text: `\u201C${question}\u201D`, size: 21, font: "Arial", bold: true, color: PRIMARY }),
      ],
    }),
    ...answers.map(a => new Paragraph({
      numbering: { reference: "bullets", level: 0 },
      spacing: { after: 60 },
      children: [new TextRun({ text: a, size: 20, font: "Arial", color: BLACK })],
    })),
  ];
}

const OUTPUT = "/Users/muchtar/quran-ml/docs/DOKUMENTASI_ML_SIDANG.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT, buffer);
  console.log("Created:", OUTPUT);
  console.log("Size:", (buffer.length / 1024).toFixed(0), "KB");
});
