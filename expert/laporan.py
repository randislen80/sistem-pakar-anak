"""
Pembuatan laporan PDF (ReportLab).

Fungsi di modul ini hanya menerima struktur data biasa (dict/list), sehingga
dapat diuji tanpa basis data.
"""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Warna mengikuti tampilan web
BIRU = colors.HexColor("#2a78d6")
TINTA = colors.HexColor("#1f2937")
ABU = colors.HexColor("#6b7280")
GARIS = colors.HexColor("#d9dee5")
LATAR = colors.HexColor("#f4f6f9")
WARNA_STATUS = {
    "sesuai": colors.HexColor("#0ca30c"),
    "perlu perhatian": colors.HexColor("#fab219"),
    "terlambat": colors.HexColor("#ec835a"),
    "belum terlihat": colors.HexColor("#d03b3b"),
}
LABEL_STATUS = {
    "sesuai": "Sesuai",
    "perlu perhatian": "Perlu Perhatian",
    "terlambat": "Terlambat",
    "belum terlihat": "Belum Terlihat",
}
# Warna kategori untuk garis tiap domain (urutan tetap)
WARNA_DOMAIN = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

LEBAR_ISI = A4[0] - 4 * cm


def _gaya():
    s = getSampleStyleSheet()
    return {
        "sekolah": ParagraphStyle("sekolah", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=13,
                                  leading=16, textColor=TINTA),
        "kecil": ParagraphStyle("kecil", parent=s["Normal"], fontSize=8.5, leading=11, textColor=ABU),
        "judul": ParagraphStyle("judul", parent=s["Title"], fontSize=14, leading=18, alignment=TA_CENTER,
                                spaceBefore=6, spaceAfter=10, textColor=TINTA),
        "sub": ParagraphStyle("sub", parent=s["Heading3"], fontSize=11, leading=14, spaceBefore=10,
                              spaceAfter=4, textColor=TINTA),
        "isi": ParagraphStyle("isi", parent=s["Normal"], fontSize=9.5, leading=13, textColor=TINTA),
        "sel": ParagraphStyle("sel", parent=s["Normal"], fontSize=8.5, leading=10.5, textColor=TINTA),
        "sel_tebal": ParagraphStyle("sel_tebal", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
                                    leading=10.5, textColor=TINTA),
        "butir": ParagraphStyle("butir", parent=s["Normal"], fontSize=9, leading=12, leftIndent=12,
                                bulletIndent=2, textColor=TINTA),
        "ttd": ParagraphStyle("ttd", parent=s["Normal"], fontSize=9.5, leading=13, alignment=TA_CENTER),
    }


def _p(teks, gaya):
    return Paragraph(escape(str(teks if teks not in (None, "") else "-")), gaya)


def _angka(v):
    if v is None:
        return "-"
    teks = f"{float(v):.1f}".rstrip("0").rstrip(".")
    return teks.replace(".", ",")


def _kop(sekolah, g, judul):
    alamat = " | ".join(x for x in [sekolah.get("alamat"), sekolah.get("telepon"), sekolah.get("email")] if x)
    return [
        _p(sekolah.get("nama", ""), g["sekolah"]),
        _p("Sistem Pakar Diagnosa Perkembangan Anak Usia Dini - Metode Forward Chaining", g["kecil"]),
        _p(alamat, g["kecil"]) if alamat else Spacer(1, 0),
        Table([[""]], colWidths=[LEBAR_ISI], rowHeights=[4],
              style=[("LINEBELOW", (0, 0), (-1, -1), 1.2, BIRU)]),
        Paragraph(escape(judul), g["judul"]),
    ]


def _tabel_identitas(baris, g):
    data = [[_p(k, g["sel"]), _p(":", g["sel"]), _p(v, g["sel_tebal"])] for k, v in baris]
    t = Table(data, colWidths=[4.2 * cm, 0.4 * cm, LEBAR_ISI - 4.6 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _kotak_kesimpulan(kesimpulan, rata, g, catatan_tambahan=""):
    warna = colors.HexColor(kesimpulan.get("warna", "#2a78d6"))
    isi = [
        Paragraph(f"<b>Kesimpulan: {escape(kesimpulan.get('label', '-'))}</b>"
                  f"&nbsp;&nbsp;&nbsp;<font color='#6b7280'>Rata-rata capaian {_angka(rata)}%</font>",
                  g["isi"]),
        Spacer(1, 3),
        _p(kesimpulan.get("saran", ""), g["isi"]),
    ]
    if catatan_tambahan:
        isi += [Spacer(1, 3), Paragraph(catatan_tambahan, g["kecil"])]
    t = Table([[isi]], colWidths=[LEBAR_ISI])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LATAR),
        ("LINEBEFORE", (0, 0), (0, -1), 4, warna),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _grafik_batang(label, nilai):
    tinggi = 26 + 22 * len(label)
    d = Drawing(LEBAR_ISI, tinggi)
    c = HorizontalBarChart()
    c.x, c.y = 3.4 * cm, 18
    c.width, c.height = LEBAR_ISI - 3.4 * cm - 40, tinggi - 26
    c.data = [[float(v or 0) for v in reversed(nilai)]]
    c.categoryAxis.categoryNames = list(reversed(label))
    c.categoryAxis.labels.fontSize = 8
    c.categoryAxis.labels.fontName = "Helvetica"
    c.categoryAxis.labels.boxAnchor = "e"
    c.categoryAxis.labels.dx = -4
    c.categoryAxis.strokeColor = GARIS
    c.valueAxis.valueMin, c.valueAxis.valueMax, c.valueAxis.valueStep = 0, 100, 20
    c.valueAxis.labels.fontSize = 7.5
    c.valueAxis.labels.fontName = "Helvetica"
    c.valueAxis.labelTextFormat = "%d%%"
    c.valueAxis.strokeColor = GARIS
    c.valueAxis.visibleGrid = True
    c.valueAxis.gridStrokeColor = GARIS
    c.bars[0].fillColor = BIRU
    c.bars[0].strokeColor = None
    c.barWidth = 10
    c.groupSpacing = 8
    c.barLabelFormat = lambda v: f"{_angka(v)}%"
    c.barLabels.fontSize = 7.5
    c.barLabels.fontName = "Helvetica"
    c.barLabels.boxAnchor = "w"
    c.barLabels.dx = 3
    d.add(c)
    return d


def _grafik_garis(label, seri, domains):
    tinggi = 6.2 * cm
    d = Drawing(LEBAR_ISI, tinggi + 1.6 * cm)
    c = HorizontalLineChart()
    c.x, c.y = 1.2 * cm, 1.9 * cm
    c.width, c.height = LEBAR_ISI - 1.6 * cm, tinggi - 0.6 * cm
    data, dipakai = [], []
    for i, dom in enumerate(domains):
        nilai = seri.get(dom) or []
        if not any(v is not None for v in nilai):
            continue
        # ReportLab tidak menerima None -> pakai nilai sebelumnya/0 agar garis tetap tersambung
        isi, akhir = [], 0.0
        for v in nilai:
            akhir = float(v) if v is not None else akhir
            isi.append(akhir)
        data.append(isi)
        dipakai.append((dom, WARNA_DOMAIN[i % len(WARNA_DOMAIN)]))
    if not data:
        return Spacer(1, 0)
    c.data = data
    c.categoryAxis.categoryNames = label
    c.categoryAxis.labels.fontSize = 7
    c.categoryAxis.labels.fontName = "Helvetica"
    c.categoryAxis.labels.angle = 30 if len(label) > 4 else 0
    c.categoryAxis.labels.boxAnchor = "ne" if len(label) > 4 else "n"
    c.categoryAxis.strokeColor = GARIS
    c.valueAxis.valueMin, c.valueAxis.valueMax, c.valueAxis.valueStep = 0, 100, 20
    c.valueAxis.labels.fontSize = 7.5
    c.valueAxis.labels.fontName = "Helvetica"
    c.valueAxis.labelTextFormat = "%d%%"
    c.valueAxis.visibleGrid = True
    c.valueAxis.gridStrokeColor = GARIS
    c.valueAxis.strokeColor = GARIS
    for i, (_, warna) in enumerate(dipakai):
        c.lines[i].strokeColor = colors.HexColor(warna)
        c.lines[i].strokeWidth = 1.6
        c.lines[i].symbol = makeMarker("FilledCircle", size=4, fillColor=colors.HexColor(warna),
                                       strokeColor=colors.white, strokeWidth=0.8)
    c.joinedLines = 1
    d.add(c)
    lg = Legend()
    lg.x, lg.y = 1.2 * cm, 0.35 * cm
    lg.alignment = "right"
    lg.columnMaximum = 1
    lg.deltax = 2.55 * cm
    lg.fontSize = 7.5
    lg.fontName = "Helvetica"
    lg.dx = lg.dy = 7
    lg.colorNamePairs = [(colors.HexColor(w), n) for n, w in dipakai]
    d.add(lg)
    return d


def _tanda_tangan(sekolah, g, tanggal):
    kota = "Jayapura"
    kiri = [_p("Mengetahui,", g["ttd"]), _p("Orang Tua/Wali", g["ttd"]), Spacer(1, 42),
            _p("(.................................)", g["ttd"])]
    kanan = [_p(f"{kota}, {tanggal}", g["ttd"]), _p("Guru Kelas", g["ttd"]), Spacer(1, 42),
             _p("(.................................)", g["ttd"])]
    t = Table([[kiri, "", kanan]], colWidths=[6.5 * cm, LEBAR_ISI - 13 * cm, 6.5 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return KeepTogether([Spacer(1, 14), t])


def _halaman(sekolah):
    nama = sekolah.get("nama", "")

    def gambar(canvas, doc):
        canvas.saveState()
        # tanda air halus
        canvas.setFont("Helvetica-Bold", 30)
        canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.045))
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(40)
        canvas.drawCentredString(0, 0, nama)
        canvas.restoreState()
        # kaki halaman
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(ABU)
        canvas.drawString(2 * cm, 1.2 * cm, "Hasil sistem pakar ini adalah alat bantu pengamatan guru, "
                                            "bukan diagnosis medis.")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Halaman {doc.page}")
        canvas.restoreState()

    return gambar


def _dokumen(buffer, judul):
    return SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                             topMargin=1.6 * cm, bottomMargin=2 * cm, title=judul,
                             author="Sistem Pakar Perkembangan Anak")


def _gaya_tabel_data(jumlah_baris):
    gaya = [
        ("BACKGROUND", (0, 0), (-1, 0), BIRU),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GARIS),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(2, jumlah_baris, 2):
        gaya.append(("BACKGROUND", (0, i), (-1, i), LATAR))
    return gaya


# ---------------------------------------------------------------------------
# Laporan hasil satu kali diagnosis
# ---------------------------------------------------------------------------
def pdf_hasil_diagnosis(data: dict) -> bytes:
    """
    data: sekolah, nama, jenis_kelamin, kelompok, tanggal_lahir, orang_tua, usia,
          tanggal, pemeriksa, hasil (list per domain), rata_rata, kesimpulan (dict), catatan
    """
    g = _gaya()
    sekolah = data.get("sekolah") or {}
    buffer = BytesIO()
    doc = _dokumen(buffer, f"Hasil Diagnosis {data.get('nama', '')}")
    isi = _kop(sekolah, g, "LAPORAN HASIL DIAGNOSIS PERKEMBANGAN ANAK")

    isi.append(_tabel_identitas([
        ("Nama anak", data.get("nama")),
        ("Jenis kelamin", data.get("jenis_kelamin")),
        ("Tanggal lahir", data.get("tanggal_lahir")),
        ("Usia saat pengamatan", data.get("usia")),
        ("Kelompok", data.get("kelompok")),
        ("Nama orang tua/wali", data.get("orang_tua")),
        ("Tanggal pengamatan", data.get("tanggal")),
        ("Guru pengamat", data.get("pemeriksa")),
    ], g))
    isi.append(Spacer(1, 10))
    isi.append(_kotak_kesimpulan(data.get("kesimpulan") or {}, data.get("rata_rata"), g))

    hasil = data.get("hasil") or []
    isi.append(Paragraph("Capaian per domain perkembangan", g["sub"]))
    isi.append(_grafik_batang([h.get("domain", "") for h in hasil], [h.get("persen") for h in hasil]))

    tabel = [["No", "Domain perkembangan", "Indikator terpenuhi", "Capaian", "Status"]]
    for i, h in enumerate(hasil, start=1):
        tabel.append([str(i), _p(h.get("domain"), g["sel"]), f"{h.get('terpenuhi', 0)} dari {h.get('total', 0)}",
                      f"{_angka(h.get('persen'))}%", LABEL_STATUS.get(h.get("status"), h.get("status", "-"))])
    t = Table(tabel, colWidths=[1 * cm, 5.6 * cm, 3.6 * cm, 2.4 * cm, LEBAR_ISI - 12.6 * cm], repeatRows=1)
    gaya = _gaya_tabel_data(len(tabel))
    gaya += [("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (2, 0), (3, -1), "CENTER")]
    for i, h in enumerate(hasil, start=1):
        warna = WARNA_STATUS.get(h.get("status"))
        if warna:
            gaya += [("LINEBEFORE", (4, i), (4, i), 4, warna), ("FONTNAME", (4, i), (4, i), "Helvetica-Bold")]
    t.setStyle(TableStyle(gaya))
    isi.append(Spacer(1, 6))
    isi.append(t)

    # Rincian indikator & rekomendasi
    isi.append(Paragraph("Rincian dan rekomendasi stimulasi", g["sub"]))
    for h in hasil:
        blok = [Paragraph(f"<b>{escape(h.get('domain', ''))}</b> - "
                          f"{escape(LABEL_STATUS.get(h.get('status'), h.get('status', '')))}", g["isi"])]
        belum = h.get("indikator_belum")
        if belum:
            blok.append(_p("Kemampuan yang belum tampak:", g["kecil"]))
            blok += [Paragraph(escape(x), g["butir"], bulletText="-") for x in belum]
        rek = h.get("rekomendasi") or []
        if rek:
            blok.append(_p("Saran kegiatan:", g["kecil"]))
            blok += [Paragraph(escape(x), g["butir"], bulletText="•") for x in rek]
        if len(blok) == 1:
            blok.append(_p("Seluruh indikator tercapai.", g["kecil"]))
        blok.append(Spacer(1, 6))
        isi.append(KeepTogether(blok))

    if data.get("catatan"):
        isi.append(Paragraph("Catatan guru", g["sub"]))
        isi.append(_p(data["catatan"], g["isi"]))

    isi.append(_tanda_tangan(sekolah, g, data.get("tanggal", "")))
    doc.build(isi, onFirstPage=_halaman(sekolah), onLaterPages=_halaman(sekolah))
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Laporan perkembangan anak dari waktu ke waktu
# ---------------------------------------------------------------------------
def pdf_perkembangan_anak(data: dict) -> bytes:
    """
    data: sekolah, nama, jenis_kelamin, kelompok, tanggal_lahir, usia, orang_tua,
          domains, p (hasil statistik.perkembangan_anak), kesimpulan (dict),
          fokus (list domain + rekomendasi), dicetak
    """
    g = _gaya()
    sekolah = data.get("sekolah") or {}
    p = data["p"]
    domains = data.get("domains") or []
    buffer = BytesIO()
    doc = _dokumen(buffer, f"Laporan Perkembangan {data.get('nama', '')}")
    isi = _kop(sekolah, g, "LAPORAN PERKEMBANGAN ANAK")

    isi.append(_tabel_identitas([
        ("Nama anak", data.get("nama")),
        ("Jenis kelamin", data.get("jenis_kelamin")),
        ("Tanggal lahir", data.get("tanggal_lahir")),
        ("Usia sekarang", data.get("usia")),
        ("Kelompok", data.get("kelompok")),
        ("Nama orang tua/wali", data.get("orang_tua")),
        ("Jumlah diagnosis", f"{p['jumlah']} kali"),
    ], g))
    isi.append(Spacer(1, 10))

    tambahan = []
    if p.get("selisih_total") is not None:
        tanda = "+" if p["selisih_total"] > 0 else ""
        tambahan.append(f"Perubahan sejak diagnosis pertama: <b>{tanda}{_angka(p['selisih_total'])} poin</b>.")
    if p.get("terkuat"):
        tambahan.append(f"Domain terkuat: <b>{escape(p['terkuat'][0])}</b> ({_angka(p['terkuat'][1])}%).")
    if p.get("terlemah") and p["terlemah"] != p.get("terkuat"):
        tambahan.append(f"Domain yang perlu difokuskan: <b>{escape(p['terlemah'][0])}</b> "
                        f"({_angka(p['terlemah'][1])}%).")
    isi.append(_kotak_kesimpulan(data.get("kesimpulan") or {}, p.get("rata_terakhir"), g, " ".join(tambahan)))

    if p["jumlah"] > 1:
        isi.append(Paragraph("Grafik capaian per domain dari waktu ke waktu", g["sub"]))
        isi.append(_grafik_garis(p["label"], p["seri"], domains))
    else:
        isi.append(Paragraph("Capaian per domain (diagnosis terakhir)", g["sub"]))
        peta = {h.get("domain"): h for h in p["terakhir"]["hasil"]}
        dom = [d for d in domains if d in peta]
        isi.append(_grafik_batang(dom, [peta[d].get("persen") for d in dom]))

    # Tabel riwayat: baris = diagnosis, kolom = domain
    isi.append(Paragraph("Riwayat capaian (%)", g["sub"]))
    kepala_gaya = ParagraphStyle("kepala", parent=g["sel_tebal"], fontSize=7.5, leading=9)
    kepala = [_p("Tanggal", kepala_gaya)] + [_p(d, kepala_gaya) for d in domains] + [_p("Rata-rata", kepala_gaya)]
    baris_data = [kepala]
    for b in reversed(p["baris"]):  # urut dari yang terlama
        baris = [b["tanggal_teks"]]
        for sel in b["sel"]:
            baris.append("-" if sel is None else f"{_angka(sel['persen'])}")
        baris.append(_angka(b["rata_rata"]))
        baris_data.append(baris)
    lebar_tgl = 2.4 * cm
    lebar_kol = (LEBAR_ISI - lebar_tgl) / (len(domains) + 1)
    t = Table(baris_data, colWidths=[lebar_tgl] + [lebar_kol] * (len(domains) + 1), repeatRows=1)
    gaya = _gaya_tabel_data(len(baris_data))
    gaya += [("ALIGN", (1, 1), (-1, -1), "CENTER"), ("BACKGROUND", (0, 0), (-1, 0), LATAR),
             ("TEXTCOLOR", (0, 0), (-1, 0), TINTA), ("LINEBELOW", (0, 0), (-1, 0), 1, BIRU),
             ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    t.setStyle(TableStyle(gaya))
    isi.append(t)

    fokus = data.get("fokus") or []
    if fokus:
        for nomor, f in enumerate(fokus):
            blok = [Paragraph("Fokus stimulasi berikutnya", g["sub"])] if nomor == 0 else []
            blok += [Paragraph(f"<b>{escape(f['domain'])}</b> - {escape(f['label'])} ({_angka(f['persen'])}%)",
                              g["isi"])]
            blok += [Paragraph(escape(x), g["butir"], bulletText="•") for x in f.get("rekomendasi", [])]
            blok.append(Spacer(1, 5))
            isi.append(KeepTogether(blok))

    isi.append(_tanda_tangan(sekolah, g, data.get("dicetak", "")))
    doc.build(isi, onFirstPage=_halaman(sekolah), onLaterPages=_halaman(sekolah))
    return buffer.getvalue()

