from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .inference import KESIMPULAN_INFO, STATUS_INFO, STATUS_URUT, kesimpulan_dari_hasil
from .usia import hitung_usia_bulan, teks_usia

STATUS_CHOICES = [(s, STATUS_INFO[s]["label"]) for s in STATUS_URUT]


# ---------------------------------------------------------------------------
# Basis pengetahuan
# ---------------------------------------------------------------------------
class DomainPerkembangan(models.Model):
    kode = models.CharField(max_length=10, blank=True, help_text="Contoh: D01")
    nama = models.CharField(max_length=100)
    deskripsi = models.TextField(blank=True)
    urutan = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["urutan", "id"]
        verbose_name = "domain perkembangan"
        verbose_name_plural = "domain perkembangan"

    def __str__(self):
        return self.nama


class Indikator(models.Model):
    domain = models.ForeignKey(DomainPerkembangan, on_delete=models.CASCADE, related_name="indikator")
    kode = models.CharField(max_length=10, blank=True, help_text="Contoh: G01")
    deskripsi = models.CharField(max_length=255)
    urutan = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["domain__urutan", "domain_id", "urutan", "id"]
        verbose_name = "indikator"
        verbose_name_plural = "indikator"

    def __str__(self):
        return f"{self.domain.nama} - {self.deskripsi}"


class Rekomendasi(models.Model):
    domain = models.ForeignKey(DomainPerkembangan, on_delete=models.CASCADE, related_name="rekomendasi")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, blank=True,
        help_text="Kosongkan agar berlaku untuk semua status yang belum Sesuai.",
    )
    teks = models.TextField()

    class Meta:
        ordering = ["domain__urutan", "domain_id", "status", "id"]
        verbose_name = "rekomendasi"
        verbose_name_plural = "rekomendasi"

    def __str__(self):
        return f"Rekomendasi {self.domain.nama}"


# ---------------------------------------------------------------------------
# Data anak & riwayat diagnosis
# ---------------------------------------------------------------------------
class Anak(models.Model):
    JENIS_KELAMIN = [("L", "Laki-laki"), ("P", "Perempuan")]
    KELOMPOK = [("A", "Kelompok A (4-5 tahun)"), ("B", "Kelompok B (5-6 tahun)")]

    nama = models.CharField(max_length=100)
    nomor_induk = models.CharField(max_length=30, blank=True)
    jenis_kelamin = models.CharField(max_length=1, choices=JENIS_KELAMIN, blank=True)
    tanggal_lahir = models.DateField(null=True, blank=True)
    kelompok = models.CharField(max_length=1, choices=KELOMPOK, blank=True)
    nama_orang_tua = models.CharField(max_length=100, blank=True)
    kontak_orang_tua = models.CharField(max_length=30, blank=True)
    catatan = models.TextField(blank=True)
    aktif = models.BooleanField(default=True, help_text="Hilangkan centang jika anak sudah lulus atau pindah.")
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nama"]
        verbose_name = "anak"
        verbose_name_plural = "data anak"

    def __str__(self):
        return self.nama

    def get_absolute_url(self):
        return reverse("anak_detail", args=[self.pk])

    def usia_bulan(self, pada=None):
        return hitung_usia_bulan(self.tanggal_lahir, pada or timezone.localdate())

    @property
    def usia_teks(self):
        return teks_usia(self.usia_bulan()) or "-"

    @property
    def inisial(self):
        bagian = [b for b in self.nama.split() if b]
        return "".join(b[0] for b in bagian[:2]).upper() or "?"


class RiwayatDiagnosa(models.Model):
    anak = models.ForeignKey(Anak, on_delete=models.CASCADE, null=True, blank=True, related_name="riwayat")
    nama_anak = models.CharField(max_length=100)
    usia = models.CharField(max_length=20, blank=True)
    usia_bulan = models.PositiveIntegerField(null=True, blank=True)
    tanggal = models.DateTimeField(default=timezone.now)
    hasil = models.JSONField()   # status tiap domain
    indikator_terpilih = models.JSONField(default=list, blank=True)
    jejak = models.JSONField(default=list, blank=True)   # jejak penalaran forward chaining
    kesimpulan = models.CharField(max_length=30, blank=True)
    rata_rata = models.FloatField(default=0)
    catatan = models.TextField(blank=True)
    pemeriksa = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="diagnosa",
    )

    class Meta:
        ordering = ["-tanggal", "-id"]
        verbose_name = "riwayat diagnosa"
        verbose_name_plural = "riwayat diagnosa"

    def __str__(self):
        return f"{self.nama_anak} - {self.tanggal:%d-%m-%Y}"

    def get_absolute_url(self):
        return reverse("riwayat_detail", args=[self.pk])

    @property
    def kunci_kesimpulan(self):
        return self.kesimpulan or kesimpulan_dari_hasil(self.hasil or [])

    @property
    def kesimpulan_info(self):
        return KESIMPULAN_INFO.get(self.kunci_kesimpulan, {})


# ---------------------------------------------------------------------------
# Konten sekolah
# ---------------------------------------------------------------------------
class GaleriKegiatan(models.Model):
    judul_kegiatan = models.CharField(max_length=200, blank=True, null=True)
    foto = models.ImageField(upload_to='galeri/')
    tanggal = models.DateField()
    keterangan = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.judul_kegiatan}'


class PesanKontak(models.Model):
    nama = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    handphone = models.CharField(max_length=20, blank=True, null=True)
    pesan = models.TextField(blank=True, null=True)
    tanggal = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.nama}'
