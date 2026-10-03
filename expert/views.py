import datetime as dt

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from . import statistik as stat
from .ekspor import excel_statistik
from .engine import daftar_aturan, forward_chaining, muat_basis_pengetahuan, nama_domain_berurutan
from .forms import AnakForm, DiagnosisForm, KontakForm
from .inference import (
    BATAS_PERLU_PERHATIAN,
    BATAS_SESUAI,
    BELUM_TERLIHAT,
    KESIMPULAN_INFO,
    KESIMPULAN_URUT,
    SESUAI,
    STATUS_INFO,
    STATUS_URUT,
    PERLU_PERHATIAN,
    TERLAMBAT,
    pilih_rekomendasi,
)
from .laporan import pdf_hasil_diagnosis, pdf_perkembangan_anak
from .models import Anak, DomainPerkembangan, GaleriKegiatan, Indikator, RiwayatDiagnosa
from .usia import hitung_usia_bulan, kelompok_dari_usia, teks_usia

SYARAT_STATUS = {
    SESUAI: f"{BATAS_SESUAI:g}% indikator terpenuhi (seluruhnya)",
    PERLU_PERHATIAN: f"{BATAS_PERLU_PERHATIAN:g}% sampai kurang dari {BATAS_SESUAI:g}%",
    TERLAMBAT: f"lebih dari 0% dan kurang dari {BATAS_PERLU_PERHATIAN:g}%",
    BELUM_TERLIHAT: "0% (tidak ada indikator yang terpenuhi)",
}

KELOMPOK_LABEL = dict(Anak.KELOMPOK)
KELOMPOK_SINGKAT = {k: v.split(" (")[0] for k, v in Anak.KELOMPOK}   # "Kelompok A"
JK_LABEL = dict(Anak.JENIS_KELAMIN)


def guru_required(view):
    """Halaman berisi data anak hanya untuk guru yang login (lihat WAJIB_LOGIN di settings)."""
    if getattr(settings, "WAJIB_LOGIN", True):
        return login_required(view)
    return view


# ---------------------------------------------------------------------------
# Fungsi bantu
# ---------------------------------------------------------------------------
def ke_rekaman(r):
    """Mengubah objek RiwayatDiagnosa menjadi dict untuk modul statistik."""
    anak = r.anak
    nama = anak.nama if anak else " ".join((r.nama_anak or "").split())
    return {
        "id": r.id,
        "anak_key": f"a{r.anak_id}" if r.anak_id else "n:" + nama.lower(),
        "anak_id": r.anak_id,
        "nama": nama,
        "kelompok": anak.kelompok if anak else "",
        "jenis_kelamin": anak.jenis_kelamin if anak else "",
        "tanggal": timezone.localtime(r.tanggal).date(),
        "hasil": r.hasil if isinstance(r.hasil, list) else [],
        "kesimpulan": r.kesimpulan,
        "rata_rata": None,  # dihitung ulang dari hasil agar selalu konsisten
        "usia": r.usia,
    }


def waktu_pengamatan(tanggal):
    """Tanggal pengamatan -> datetime aware. Hari ini memakai jam sekarang."""
    if tanggal == timezone.localdate():
        return timezone.now()
    return timezone.make_aware(dt.datetime.combine(tanggal, dt.time(9, 0)))


def perkiraan_usia_bulan(anak, tanggal):
    """Usia saat pengamatan; bila tanggal lahir kosong, diperkirakan dari riwayat terakhir."""
    bulan = hitung_usia_bulan(anak.tanggal_lahir, tanggal)
    if bulan is not None:
        return bulan
    lalu = anak.riwayat.exclude(usia_bulan__isnull=True).order_by("-tanggal").first()
    if lalu is None:
        return None
    t_lalu = timezone.localtime(lalu.tanggal).date()
    selisih = (tanggal.year - t_lalu.year) * 12 + (tanggal.month - t_lalu.month)
    return max(lalu.usia_bulan + max(selisih, 0), 0)


def ambil_filter(request):
    """Filter periode, kelompok, dan jenis kelamin dari query string."""
    g = request.GET

    def tanggal(nama):
        try:
            return parse_date(g.get(nama) or "")
        except ValueError:
            return None

    dari, sampai = tanggal("dari"), tanggal("sampai")
    periode = g.get("periode", "")
    hari_ini = timezone.localdate()
    if not dari and not sampai:
        if periode == "tahun_ajaran":
            tahun = hari_ini.year if hari_ini.month >= 7 else hari_ini.year - 1
            dari, sampai = dt.date(tahun, 7, 1), dt.date(tahun + 1, 6, 30)
        elif periode == "6bulan":
            dari = hari_ini - dt.timedelta(days=182)
        elif periode == "30hari":
            dari = hari_ini - dt.timedelta(days=30)
        else:
            periode = ""
    else:
        periode = "kustom"
    kelompok = g.get("kelompok", "")
    jk = g.get("jk", "")
    return {
        "periode": periode,
        "dari": dari,
        "sampai": sampai,
        "kelompok": kelompok if kelompok in KELOMPOK_LABEL else "",
        "jk": jk if jk in JK_LABEL else "",
    }


def terapkan_filter(qs, f):
    if f["dari"]:
        qs = qs.filter(tanggal__date__gte=f["dari"])
    if f["sampai"]:
        qs = qs.filter(tanggal__date__lte=f["sampai"])
    if f["kelompok"]:
        qs = qs.filter(anak__kelompok=f["kelompok"])
    if f["jk"]:
        qs = qs.filter(anak__jenis_kelamin=f["jk"])
    return qs


def keterangan_filter(f):
    bagian = []
    if f["dari"] or f["sampai"]:
        bagian.append(f"Periode {stat.tanggal_indonesia(f['dari']) if f['dari'] else 'awal'}"
                      f" s.d. {stat.tanggal_indonesia(f['sampai']) if f['sampai'] else 'sekarang'}")
    else:
        bagian.append("Semua periode")
    bagian.append(KELOMPOK_LABEL.get(f["kelompok"], "Semua kelompok"))
    bagian.append(JK_LABEL.get(f["jk"], "Semua jenis kelamin"))
    return " | ".join(bagian)


def lengkapi_hasil(hasil, rekomendasi_map=None):
    """Menambahkan info status (label, warna) dan rekomendasi untuk riwayat lama."""
    keluaran = []
    for h in hasil if isinstance(hasil, list) else []:
        item = dict(h)
        item["info"] = STATUS_INFO.get(item.get("status"), {"label": item.get("status", "-"), "kelas": ""})
        if rekomendasi_map is not None and "indikator_belum" not in item and not item.get("rekomendasi"):
            # riwayat versi lama belum menyimpan rekomendasi -> ambil dari basis pengetahuan
            item["rekomendasi"] = pilih_rekomendasi(rekomendasi_map.get(item.get("domain"), []),
                                                    item.get("status", ""))
        keluaran.append(item)
    return keluaran


def riwayat_sebelumnya(r):
    if not r.anak_id:
        return None
    return (RiwayatDiagnosa.objects
            .filter(anak_id=r.anak_id)
            .filter(Q(tanggal__lt=r.tanggal) | Q(tanggal=r.tanggal, id__lt=r.id))
            .order_by("-tanggal", "-id").first())


def data_laporan_riwayat(r, hasil):
    anak = r.anak
    return {
        "sekolah": settings.SEKOLAH,
        "nama": anak.nama if anak else r.nama_anak,
        "jenis_kelamin": anak.get_jenis_kelamin_display() if anak else "",
        "kelompok": anak.get_kelompok_display() if anak else "",
        "tanggal_lahir": stat.tanggal_indonesia(anak.tanggal_lahir, pendek=False) if anak and anak.tanggal_lahir else "-",
        "orang_tua": anak.nama_orang_tua if anak else "",
        "usia": r.usia or "-",
        "tanggal": stat.tanggal_indonesia(timezone.localtime(r.tanggal).date(), pendek=False),
        "pemeriksa": (r.pemeriksa.get_full_name() or r.pemeriksa.username) if r.pemeriksa else "",
        "hasil": hasil,
        "rata_rata": stat.rata_rata_rekaman({"hasil": hasil, "rata_rata": None}),
        "kesimpulan": r.kesimpulan_info,
        "catatan": r.catatan,
    }


# ---------------------------------------------------------------------------
# Beranda & halaman umum
# ---------------------------------------------------------------------------
TAMPILAN_DOMAIN = [
    ("bi-hand-index-thumb", "#e8f1fc", "#1c5cab"),
    ("bi-person-arms-up", "#fdebe3", "#b44a1c"),
    ("bi-chat-heart", "#e0f5ec", "#0f7a54"),
    ("bi-puzzle", "#fdf1d6", "#8a5a00"),
    ("bi-people", "#fce8f0", "#a33a67"),
    ("bi-stars", "#e1f1e1", "#086308"),
    ("bi-lightbulb", "#ece9fb", "#4a3aa7"),
    ("bi-heart", "#fbe3e3", "#a02727"),
]


def index(request):
    domains = []
    for i, d in enumerate(DomainPerkembangan.objects.annotate(jumlah=Count("indikator"))):
        ikon, bg, fg = TAMPILAN_DOMAIN[i % len(TAMPILAN_DOMAIN)]
        domains.append({"nama": d.nama, "deskripsi": d.deskripsi, "jumlah": d.jumlah,
                        "ikon": ikon, "bg": bg, "fg": fg})
    ctx = {
        "domains": domains,
        "jumlah_domain": len(domains),
        "jumlah_indikator": Indikator.objects.count(),
    }
    if request.user.is_authenticated or not settings.WAJIB_LOGIN:
        semua = list(RiwayatDiagnosa.objects.select_related("anak"))
        rekaman = [ke_rekaman(r) for r in semua]
        terbaru = stat.terbaru_per_anak(rekaman)
        awal_bulan = timezone.localdate().replace(day=1)
        ctx.update({
            "ringkas": {
                "anak": Anak.objects.filter(aktif=True).count(),
                "diagnosis": len(semua),
                "bulan_ini": sum(1 for x in rekaman if x["tanggal"] >= awal_bulan),
                "rata_rata": stat._rata(stat.rata_rata_rekaman(x) for x in terbaru),
            },
            "riwayat_terbaru": semua[:5],
            "perlu_perhatian": stat.anak_perlu_perhatian(terbaru)[:5],
        })
    return render(request, "index.html", ctx)


def basis_pengetahuan(request):
    aturan, basis = daftar_aturan()
    _, rekomendasi = muat_basis_pengetahuan()
    return render(request, "expert/basis_pengetahuan.html", {
        "basis": basis,
        "aturan_status": [a for a in aturan if a["tahap"] == 1],
        "aturan_kesimpulan": [a for a in aturan if a["tahap"] == 2],
        "aturan_rekomendasi": [a for a in aturan if a["tahap"] == 3],
        "rekomendasi": rekomendasi,
        "status_info": [dict(STATUS_INFO[s], kunci=s, syarat=SYARAT_STATUS[s]) for s in STATUS_URUT],
        "kesimpulan_info": [dict(KESIMPULAN_INFO[k], kunci=k) for k in KESIMPULAN_URUT],
        "jumlah_indikator": sum(len(d["indikator"]) for d in basis),
        "jumlah_aturan": len(aturan),
    })


def galeri(request):
    data = GaleriKegiatan.objects.all().order_by('-tanggal', '-id')
    return render(request, 'expert/galeri.html', {'data': data})


def kontak(request):
    if request.method == 'POST':
        form = KontakForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Terima kasih, pesan Anda sudah kami terima.")
            return redirect('kontak')
    else:
        form = KontakForm()
    return render(request, "expert/kontak.html", {"form": form})


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------
@guru_required
def diagnosis(request):
    basis, _ = muat_basis_pengetahuan()
    basis = [d for d in basis if d["indikator"]]

    if request.method == "POST":
        form = DiagnosisForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            tanggal = cd["tanggal"]
            if cd["mode"] == "baru":
                bulan_lahir = hitung_usia_bulan(cd["tanggal_lahir_baru"], timezone.localdate())
                anak = Anak.objects.create(
                    nama=cd["nama_baru"],
                    jenis_kelamin=cd["jenis_kelamin_baru"],
                    tanggal_lahir=cd["tanggal_lahir_baru"],
                    kelompok=cd["kelompok_baru"] or kelompok_dari_usia(bulan_lahir),
                )
            else:
                anak = cd["anak"]

            inferensi = forward_chaining([i.id for i in cd["indikator"]])
            bulan = perkiraan_usia_bulan(anak, tanggal)
            r = RiwayatDiagnosa.objects.create(
                anak=anak,
                nama_anak=anak.nama,
                usia=teks_usia(bulan),
                usia_bulan=bulan,
                tanggal=waktu_pengamatan(tanggal),
                hasil=inferensi["hasil"],
                indikator_terpilih=inferensi["fakta"],
                jejak=inferensi["jejak"],
                kesimpulan=inferensi["kesimpulan"],
                rata_rata=inferensi["rata_rata"],
                catatan=cd["catatan"],
                pemeriksa=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, f"Diagnosis {anak.nama} berhasil diproses dan disimpan.")
            return redirect("riwayat_detail", pk=r.pk)
    else:
        initial = {}
        anak_id = request.GET.get("anak", "")
        if anak_id.isdigit() and Anak.objects.filter(pk=anak_id, aktif=True).exists():
            initial["anak"] = int(anak_id)
        form = DiagnosisForm(initial=initial)

    nilai = form["indikator"].value() or []
    terpilih = {int(x) for x in nilai if str(x).isdigit()}

    # Info anak untuk panel samping & tombol "muat pilihan diagnosis terakhir"
    info_anak = {}
    for a in Anak.objects.filter(aktif=True).annotate(jumlah=Count("riwayat")):
        info_anak[str(a.id)] = {
            "usia": a.usia_teks,
            "kelompok": a.get_kelompok_display() or "-",
            "jumlah": a.jumlah,
            "terakhir": [],
            "tanggal_terakhir": "",
        }
    terakhir = (RiwayatDiagnosa.objects.filter(anak__aktif=True)
                .order_by("anak_id", "-tanggal", "-id"))
    sudah = set()
    for r in terakhir:
        key = str(r.anak_id)
        if key in sudah or key not in info_anak:
            continue
        sudah.add(key)
        info_anak[key]["tanggal_terakhir"] = stat.tanggal_indonesia(timezone.localtime(r.tanggal).date())
        info_anak[key]["terakhir"] = [f.get("id") for f in (r.indikator_terpilih or []) if isinstance(f, dict) and f.get("id")]

    return render(request, "expert/diagnosis.html", {
        "form": form,
        "basis": basis,
        "terpilih": terpilih,
        "total_indikator": sum(len(d["indikator"]) for d in basis),
        "info_anak": info_anak,
        "mode": form["mode"].value() or "terdaftar",
    })


# ---------------------------------------------------------------------------
# Riwayat diagnosis
# ---------------------------------------------------------------------------
@guru_required
def riwayat_list(request):
    f = ambil_filter(request)
    q = request.GET.get("q", "").strip()
    kesimpulan = request.GET.get("kesimpulan", "")
    qs = terapkan_filter(RiwayatDiagnosa.objects.select_related("anak", "pemeriksa"), f)
    if q:
        qs = qs.filter(Q(nama_anak__icontains=q) | Q(anak__nama__icontains=q))
    if kesimpulan in KESIMPULAN_INFO:
        qs = qs.filter(kesimpulan=kesimpulan)
    halaman = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "expert/riwayat_list.html", {
        "halaman": halaman,
        "filter": f,
        "q": q,
        "kesimpulan": kesimpulan,
        "pilihan_kesimpulan": [(k, KESIMPULAN_INFO[k]["label"]) for k in KESIMPULAN_URUT],
        "pilihan_kelompok": Anak.KELOMPOK,
        "total": qs.count(),
    })


@guru_required
def riwayat_detail(request, pk):
    r = get_object_or_404(RiwayatDiagnosa.objects.select_related("anak", "pemeriksa"), pk=pk)
    _, rekomendasi = muat_basis_pengetahuan()
    hasil = lengkapi_hasil(r.hasil, rekomendasi)

    sebelumnya = riwayat_sebelumnya(r)
    peta_lalu = stat.peta_hasil(sebelumnya.hasil) if sebelumnya else {}
    for h in hasil:
        lalu = peta_lalu.get(h.get("domain"))
        h["selisih"] = (round(float(h.get("persen") or 0) - float(lalu.get("persen") or 0), 1)
                        if lalu is not None else None)

    grafik = {
        "label": [h.get("domain") for h in hasil],
        "sekarang": [h.get("persen") for h in hasil],
        "sebelumnya": [peta_lalu.get(h.get("domain"), {}).get("persen") for h in hasil] if sebelumnya else None,
        "tanggal_sebelumnya": (stat.tanggal_indonesia(timezone.localtime(sebelumnya.tanggal).date())
                               if sebelumnya else ""),
    }
    jejak = r.jejak if isinstance(r.jejak, list) else []
    rata = stat.rata_rata_rekaman({"hasil": hasil, "rata_rata": None})
    return render(request, "expert/riwayat_detail.html", {
        "r": r,
        "hasil": hasil,
        "rata_rata": rata,
        "selisih_rata": (round(rata - stat.rata_rata_rekaman({"hasil": sebelumnya.hasil, "rata_rata": None}), 1)
                         if sebelumnya else None),
        "kesimpulan": r.kesimpulan_info,
        "sebelumnya": sebelumnya,
        "grafik": grafik,
        "jejak_tahap": [
            ("Tahap 1 - Menentukan status tiap domain", [j for j in jejak if j.get("tahap") == 1]),
            ("Tahap 2 - Menentukan kesimpulan umum", [j for j in jejak if j.get("tahap") == 2]),
            ("Tahap 3 - Menurunkan rekomendasi stimulasi", [j for j in jejak if j.get("tahap") == 3]),
        ] if jejak else [],
        "fakta": r.indikator_terpilih if isinstance(r.indikator_terpilih, list) else [],
        "jumlah_indikator": sum(int(h.get("total") or 0) for h in hasil),
        "jumlah_terpenuhi": sum(int(h.get("terpenuhi") or 0) for h in hasil),
    })


@guru_required
def riwayat_pdf(request, pk):
    r = get_object_or_404(RiwayatDiagnosa.objects.select_related("anak", "pemeriksa"), pk=pk)
    _, rekomendasi = muat_basis_pengetahuan()
    hasil = lengkapi_hasil(r.hasil, rekomendasi)
    pdf = pdf_hasil_diagnosis(data_laporan_riwayat(r, hasil))
    nama_file = f"hasil-diagnosis-{slugify(r.nama_anak) or 'anak'}-{timezone.localtime(r.tanggal):%Y%m%d}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nama_file}"'
    return response


@guru_required
def riwayat_hapus(request, pk):
    r = get_object_or_404(RiwayatDiagnosa, pk=pk)
    if request.method == "POST":
        anak_id = r.anak_id
        r.delete()
        messages.success(request, "Riwayat diagnosis telah dihapus.")
        if anak_id and request.POST.get("kembali") == "anak":
            return redirect("anak_detail", pk=anak_id)
        return redirect("riwayat_list")
    return render(request, "expert/konfirmasi_hapus.html", {
        "judul": "Hapus riwayat diagnosis",
        "objek": f"diagnosis {r.nama_anak} tanggal {timezone.localtime(r.tanggal):%d-%m-%Y}",
        "batal_url": r.get_absolute_url(),
    })


# ---------------------------------------------------------------------------
# Data anak
# ---------------------------------------------------------------------------
@guru_required
def anak_list(request):
    q = request.GET.get("q", "").strip()
    kelompok = request.GET.get("kelompok", "")
    status = request.GET.get("status", "aktif")
    qs = Anak.objects.annotate(jumlah=Count("riwayat"), terakhir=Max("riwayat__tanggal"))
    if q:
        qs = qs.filter(Q(nama__icontains=q) | Q(nomor_induk__icontains=q) | Q(nama_orang_tua__icontains=q))
    if kelompok in KELOMPOK_LABEL:
        qs = qs.filter(kelompok=kelompok)
    if status == "aktif":
        qs = qs.filter(aktif=True)
    elif status == "nonaktif":
        qs = qs.filter(aktif=False)
    halaman = Paginator(qs.order_by("nama"), 20).get_page(request.GET.get("page"))

    # capaian dan kesimpulan diagnosis terakhir setiap anak di halaman ini
    ids = [a.id for a in halaman]
    terakhir = {}
    for r in RiwayatDiagnosa.objects.filter(anak_id__in=ids).order_by("anak_id", "-tanggal", "-id"):
        terakhir.setdefault(r.anak_id, r)
    for a in halaman:
        r = terakhir.get(a.id)
        a.rata_terakhir = stat.rata_rata_rekaman({"hasil": r.hasil, "rata_rata": None}) if r else None
        a.kesimpulan_terakhir = r.kesimpulan_info if r else None

    return render(request, "expert/anak_list.html", {
        "halaman": halaman, "q": q, "kelompok": kelompok, "status": status,
        "pilihan_kelompok": Anak.KELOMPOK,
    })


@guru_required
def anak_tambah(request):
    lanjut = request.GET.get("next") or request.POST.get("next") or ""
    if request.method == "POST":
        form = AnakForm(request.POST)
        if form.is_valid():
            anak = form.save(commit=False)
            if not anak.kelompok:
                anak.kelompok = kelompok_dari_usia(anak.usia_bulan())
            anak.save()
            messages.success(request, f"Data {anak.nama} berhasil ditambahkan.")
            if lanjut == "diagnosis":
                return redirect(f"{reverse('diagnosis')}?anak={anak.pk}")
            return redirect(anak)
    else:
        form = AnakForm()
    return render(request, "expert/anak_form.html", {"form": form, "judul": "Tambah Data Anak", "next": lanjut})


@guru_required
def anak_ubah(request, pk):
    anak = get_object_or_404(Anak, pk=pk)
    if request.method == "POST":
        form = AnakForm(request.POST, instance=anak)
        if form.is_valid():
            form.save()
            messages.success(request, f"Data {anak.nama} berhasil diperbarui.")
            return redirect(anak)
    else:
        form = AnakForm(instance=anak)
    return render(request, "expert/anak_form.html", {"form": form, "judul": f"Ubah Data {anak.nama}", "anak": anak})


@guru_required
def anak_hapus(request, pk):
    anak = get_object_or_404(Anak, pk=pk)
    if request.method == "POST":
        nama = anak.nama
        anak.delete()
        messages.success(request, f"Data {nama} beserta seluruh riwayat diagnosisnya telah dihapus.")
        return redirect("anak_list")
    return render(request, "expert/konfirmasi_hapus.html", {
        "judul": "Hapus data anak",
        "objek": f"data {anak.nama} beserta {anak.riwayat.count()} riwayat diagnosisnya",
        "saran": "Jika anak sudah lulus atau pindah, sebaiknya cukup ubah datanya menjadi tidak aktif "
                 "agar riwayat perkembangannya tetap tersimpan.",
        "batal_url": anak.get_absolute_url(),
    })


def _data_perkembangan(anak):
    domains = nama_domain_berurutan()
    riwayat = list(anak.riwayat.select_related("anak").all())
    rekaman = [ke_rekaman(r) for r in riwayat]
    perkembangan = stat.perkembangan_anak(rekaman, domains)
    return domains, perkembangan


@guru_required
def anak_detail(request, pk):
    anak = get_object_or_404(Anak, pk=pk)
    domains, perkembangan = _data_perkembangan(anak)

    # Pembanding: rata-rata diagnosis terakhir anak lain di kelompok yang sama
    pembanding = None
    if anak.kelompok and perkembangan["ada_data"]:
        teman = (RiwayatDiagnosa.objects.select_related("anak")
                 .filter(anak__kelompok=anak.kelompok, anak__aktif=True).exclude(anak=anak))
        terbaru_teman = stat.terbaru_per_anak([ke_rekaman(r) for r in teman])
        if terbaru_teman:
            pembanding = {
                "label": f"Rata-rata {anak.get_kelompok_display().split(' (')[0]}",
                "n": len(terbaru_teman),
                "nilai": [x["rata"] for x in stat.rata_rata_domain(terbaru_teman, domains)],
            }

    grafik = None
    if perkembangan["ada_data"]:
        terakhir = stat.peta_hasil(perkembangan["terakhir"]["hasil"])
        grafik = {
            "domain": domains,
            "label": perkembangan["label"],
            "seri": perkembangan["seri"],
            "keseluruhan": perkembangan["keseluruhan"],
            "terakhir": [terakhir.get(d, {}).get("persen") for d in domains],
            "pembanding": pembanding,
        }
    return render(request, "expert/anak_detail.html", {
        "anak": anak,
        "domains": domains,
        "p": perkembangan,
        "grafik": grafik,
        "pembanding": pembanding,
        "kesimpulan_terakhir": KESIMPULAN_INFO.get(perkembangan.get("kesimpulan_terakhir"), {}),
        "status_legenda": [STATUS_INFO[s] for s in STATUS_URUT],
    })


@guru_required
def anak_pdf(request, pk):
    anak = get_object_or_404(Anak, pk=pk)
    domains, perkembangan = _data_perkembangan(anak)
    if not perkembangan["ada_data"]:
        messages.warning(request, "Anak ini belum memiliki riwayat diagnosis untuk dilaporkan.")
        return redirect(anak)
    _, rekomendasi = muat_basis_pengetahuan()
    hasil_terakhir = lengkapi_hasil(perkembangan["terakhir"]["hasil"], rekomendasi)
    fokus = [{"domain": h.get("domain"), "label": h["info"].get("label", ""), "persen": h.get("persen"),
              "rekomendasi": h.get("rekomendasi") or []}
             for h in hasil_terakhir if h.get("status") != SESUAI]
    data = {
        "sekolah": settings.SEKOLAH,
        "fokus": fokus,
        "nama": anak.nama,
        "jenis_kelamin": anak.get_jenis_kelamin_display(),
        "kelompok": anak.get_kelompok_display(),
        "tanggal_lahir": stat.tanggal_indonesia(anak.tanggal_lahir, pendek=False) if anak.tanggal_lahir else "-",
        "usia": anak.usia_teks,
        "orang_tua": anak.nama_orang_tua,
        "domains": domains,
        "p": perkembangan,
        "kesimpulan": KESIMPULAN_INFO.get(perkembangan["kesimpulan_terakhir"], {}),
        "dicetak": stat.tanggal_indonesia(timezone.localdate(), pendek=False),
    }
    pdf = pdf_perkembangan_anak(data)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="laporan-perkembangan-{slugify(anak.nama) or "anak"}.pdf"')
    return response


# ---------------------------------------------------------------------------
# Statistik
# ---------------------------------------------------------------------------
def _statistik(request):
    f = ambil_filter(request)
    domains = nama_domain_berurutan()
    qs = terapkan_filter(RiwayatDiagnosa.objects.select_related("anak"), f)
    rekaman = [ke_rekaman(r) for r in qs]
    ringkasan = stat.ringkasan_sekolah(rekaman, domains, KELOMPOK_SINGKAT, JK_LABEL)
    return f, domains, rekaman, ringkasan


@guru_required
def statistik(request):
    f, domains, rekaman, ringkasan = _statistik(request)
    grafik = {
        "domain": domains,
        "rata_domain": [x["rata"] for x in ringkasan["rata_domain"]],
        "status": {
            "urutan": [{"kunci": s, "label": STATUS_INFO[s]["label"], "warna": STATUS_INFO[s]["warna"]}
                       for s in STATUS_URUT],
            "persen": {s: [x["persen"][s] for x in ringkasan["sebaran_status"]] for s in STATUS_URUT},
            "jumlah": {s: [x["jumlah"][s] for x in ringkasan["sebaran_status"]] for s in STATUS_URUT},
        },
        "tren": ringkasan["tren"],
        "kesimpulan": ringkasan["sebaran_kesimpulan"],
        "kelompok": ringkasan["per_kelompok"],
        "perubahan": ringkasan["perubahan"]["per_domain"],
    }
    query_ekspor = request.GET.copy()
    query_ekspor.pop("page", None)
    return render(request, "expert/statistik.html", {
        "f": f,
        "s": ringkasan,
        "grafik": grafik,
        "domains": domains,
        "keterangan": keterangan_filter(f),
        "pilihan_kelompok": Anak.KELOMPOK,
        "pilihan_jk": Anak.JENIS_KELAMIN,
        "query_ekspor": query_ekspor.urlencode(),
        "status_urut": [dict(STATUS_INFO[s], kunci=s) for s in STATUS_URUT],
        "anak_terdaftar": Anak.objects.filter(aktif=True).count(),
        "sesuai": SESUAI,
    })


@guru_required
def statistik_excel(request):
    f, domains, rekaman, ringkasan = _statistik(request)
    isi = excel_statistik(ringkasan, rekaman, domains, keterangan_filter(f), settings.SEKOLAH)
    response = HttpResponse(
        isi, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = (
        f'attachment; filename="statistik-perkembangan-anak-{timezone.localdate():%Y%m%d}.xlsx"')
    return response


@require_POST
def keluar(request):
    logout(request)
    messages.info(request, "Anda telah keluar.")
    return redirect("index")
