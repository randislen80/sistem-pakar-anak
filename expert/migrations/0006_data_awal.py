# Migrasi data:
# 1. Mengisi basis pengetahuan bawaan jika basis data masih kosong.
# 2. Memberi kode (D01.., G01..) dan urutan pada domain & indikator.
# 3. Mengisi rekomendasi stimulasi bawaan untuk domain yang belum punya.
# 4. Membuat data Anak dari riwayat diagnosa lama dan menautkannya,
#    serta melengkapi usia (bulan), rata-rata capaian, dan kesimpulan.

import re

from django.db import migrations

BASIS_URUTAN = [
    "Motorik Halus", "Motorik Kasar", "Bahasa", "Kognitif", "Sosial Emosional", "Kemandirian",
]


def _kesimpulan(hasil):
    status = [h.get("status", "") for h in (hasil or []) if isinstance(h, dict)]
    bermasalah = sum(1 for s in status if s in ("terlambat", "belum terlihat"))
    perlu = sum(1 for s in status if s == "perlu perhatian")
    if bermasalah >= 3:
        return "perhatian_khusus"
    if bermasalah >= 1:
        return "stimulasi_terarah"
    if perlu >= 1:
        return "pendampingan"
    return "sesuai_harapan"


def _rata(hasil):
    nilai = []
    for h in hasil or []:
        if isinstance(h, dict):
            try:
                nilai.append(float(h.get("persen") or 0))
            except (TypeError, ValueError):
                pass
    return round(sum(nilai) / len(nilai), 1) if nilai else 0.0


def _usia_bulan(teks):
    if not teks:
        return None
    cocok = re.search(r"\d+(?:[.,]\d+)?", str(teks))
    if not cocok:
        return None
    angka = float(cocok.group(0).replace(",", "."))
    if "bulan" in str(teks).lower() and "tahun" not in str(teks).lower():
        return int(round(angka))
    return int(round(angka * 12))


def _teks_usia(bulan):
    if bulan is None:
        return ""
    tahun, sisa = divmod(int(bulan), 12)
    if tahun and sisa:
        return f"{tahun} tahun {sisa} bulan"
    if tahun:
        return f"{tahun} tahun"
    return f"{sisa} bulan"


def isi_data(apps, schema_editor):
    from expert.rules import DESKRIPSI_DOMAIN, KNOWLEDGE_BASE, REKOMENDASI_AWAL

    Domain = apps.get_model("expert", "DomainPerkembangan")
    Indikator = apps.get_model("expert", "Indikator")
    Rekomendasi = apps.get_model("expert", "Rekomendasi")
    Anak = apps.get_model("expert", "Anak")
    Riwayat = apps.get_model("expert", "RiwayatDiagnosa")

    # 1. Basis pengetahuan bawaan untuk instalasi baru
    if not Domain.objects.exists():
        for nama, daftar in KNOWLEDGE_BASE.items():
            d = Domain.objects.create(nama=nama)
            for teks in daftar:
                Indikator.objects.create(domain=d, deskripsi=teks)

    # 2. Kode dan urutan domain & indikator
    posisi = {n.lower(): i for i, n in enumerate(BASIS_URUTAN)}
    domains = sorted(Domain.objects.all(), key=lambda d: (posisi.get(d.nama.strip().lower(), 99), d.id))
    deskripsi_map = {k.lower(): v for k, v in DESKRIPSI_DOMAIN.items()}
    nomor_indikator = 1
    for i, d in enumerate(domains, start=1):
        if not d.urutan:
            d.urutan = i
        if not d.kode:
            d.kode = f"D{i:02d}"
        if not d.deskripsi:
            d.deskripsi = deskripsi_map.get(d.nama.strip().lower(), "")
        d.save()
        for j, ind in enumerate(Indikator.objects.filter(domain_id=d.id).order_by("id"), start=1):
            if not ind.urutan:
                ind.urutan = j
            if not ind.kode:
                ind.kode = f"G{nomor_indikator:02d}"
            ind.save()
            nomor_indikator += 1

    # 3. Rekomendasi bawaan
    rekom_map = {k.lower(): v for k, v in REKOMENDASI_AWAL.items()}
    for d in domains:
        if Rekomendasi.objects.filter(domain_id=d.id).exists():
            continue
        for status, teks in rekom_map.get(d.nama.strip().lower(), []):
            Rekomendasi.objects.create(domain_id=d.id, status=status, teks=teks)

    # 4. Riwayat lama -> data Anak
    anak_per_nama = {}
    for r in Riwayat.objects.filter(anak__isnull=True).order_by("tanggal", "id"):
        nama = " ".join((r.nama_anak or "").split()) or "Tanpa Nama"
        kunci = nama.lower()
        bulan = _usia_bulan(r.usia)
        anak = anak_per_nama.get(kunci)
        if anak is None:
            anak = Anak.objects.create(nama=nama)
            anak_per_nama[kunci] = anak
        if bulan is not None:
            # riwayat diproses urut waktu, jadi kelompok mengikuti usia terbaru
            anak.kelompok = "A" if bulan < 60 else "B"
            anak.save()
        r.anak_id = anak.id
        r.nama_anak = nama
        r.usia_bulan = bulan
        if bulan is not None:
            r.usia = _teks_usia(bulan)
        hasil = r.hasil if isinstance(r.hasil, list) else []
        r.rata_rata = _rata(hasil)
        if not r.kesimpulan:
            r.kesimpulan = _kesimpulan(hasil)
        r.save()


class Migration(migrations.Migration):

    dependencies = [
        ('expert', '0005_perluasan_sistem'),
    ]

    operations = [
        migrations.RunPython(isi_data, migrations.RunPython.noop),
    ]
