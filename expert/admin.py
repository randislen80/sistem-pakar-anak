from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .inference import KESIMPULAN_INFO
from .models import (
    Anak,
    DomainPerkembangan,
    GaleriKegiatan,
    Indikator,
    PesanKontak,
    Rekomendasi,
    RiwayatDiagnosa,
)


# ---------------------------------------------------------------------------
# Basis pengetahuan
# ---------------------------------------------------------------------------
class IndikatorInline(admin.TabularInline):
    model = Indikator
    extra = 1
    fields = ("kode", "deskripsi", "urutan")


class RekomendasiInline(admin.TabularInline):
    model = Rekomendasi
    extra = 1
    fields = ("status", "teks")


@admin.register(DomainPerkembangan)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama", "urutan", "jumlah_indikator", "jumlah_rekomendasi")
    list_display_links = ("kode", "nama")
    search_fields = ("nama", "kode")
    inlines = [IndikatorInline, RekomendasiInline]

    @admin.display(description="Indikator")
    def jumlah_indikator(self, obj):
        return obj.indikator.count()

    @admin.display(description="Rekomendasi")
    def jumlah_rekomendasi(self, obj):
        return obj.rekomendasi.count()


@admin.register(Indikator)
class IndikatorAdmin(admin.ModelAdmin):
    list_display = ("kode", "deskripsi", "domain", "urutan")
    list_display_links = ("kode", "deskripsi")
    list_filter = ("domain",)
    search_fields = ("deskripsi", "kode")


@admin.register(Rekomendasi)
class RekomendasiAdmin(admin.ModelAdmin):
    list_display = ("domain", "status_tampil", "teks")
    list_filter = ("domain", "status")
    search_fields = ("teks",)

    @admin.display(description="Berlaku untuk status", ordering="status")
    def status_tampil(self, obj):
        return obj.get_status_display() or "Semua status yang belum Sesuai"


# ---------------------------------------------------------------------------
# Data anak & riwayat
# ---------------------------------------------------------------------------
class RiwayatInline(admin.TabularInline):
    model = RiwayatDiagnosa
    extra = 0
    fields = ("tanggal", "usia", "rata_rata", "kesimpulan")
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Anak)
class AnakAdmin(admin.ModelAdmin):
    list_display = ("nama", "jenis_kelamin", "kelompok", "tanggal_lahir", "nama_orang_tua", "aktif",
                    "jumlah_diagnosis")
    list_filter = ("kelompok", "jenis_kelamin", "aktif")
    search_fields = ("nama", "nomor_induk", "nama_orang_tua")
    inlines = [RiwayatInline]

    @admin.display(description="Jumlah diagnosis")
    def jumlah_diagnosis(self, obj):
        return obj.riwayat.count()


@admin.register(RiwayatDiagnosa)
class RiwayatAdmin(admin.ModelAdmin):
    list_display = ("nama_anak", "tanggal", "usia", "rata_rata", "kesimpulan_tampil", "pemeriksa")
    list_filter = ("kesimpulan", "anak__kelompok", "tanggal")
    search_fields = ("nama_anak", "anak__nama")
    date_hierarchy = "tanggal"
    autocomplete_fields = ("anak",)
    readonly_fields = ("hasil_tampil", "jejak_tampil", "rata_rata", "kesimpulan", "pemeriksa")
    exclude = ("hasil", "jejak", "indikator_terpilih")

    # Diagnosis baru dibuat lewat halaman Diagnosis agar forward chaining dijalankan.
    def has_add_permission(self, request):
        return False

    @admin.display(description="Kesimpulan", ordering="kesimpulan")
    def kesimpulan_tampil(self, obj):
        return KESIMPULAN_INFO.get(obj.kunci_kesimpulan, {}).get("label", "-")

    @admin.display(description="Hasil per domain")
    def hasil_tampil(self, obj):
        baris = format_html_join(
            "", "<tr><td>{}</td><td>{} / {}</td><td>{}%</td><td>{}</td></tr>",
            ((h.get("domain", ""), h.get("terpenuhi", ""), h.get("total", ""), h.get("persen", ""),
              h.get("status", "")) for h in (obj.hasil or []) if isinstance(h, dict)),
        )
        return format_html(
            "<table><tr><th>Domain</th><th>Terpenuhi</th><th>Persen</th><th>Status</th></tr>{}</table>",
            baris,
        )

    @admin.display(description="Jejak forward chaining")
    def jejak_tampil(self, obj):
        if not obj.jejak:
            return "-"
        baris = format_html_join(
            "", "<li><b>{}</b>: JIKA {} MAKA {}</li>",
            ((j.get("aturan", ""), j.get("jika", ""), j.get("maka", "")) for j in obj.jejak if isinstance(j, dict)),
        )
        return format_html("<ol>{}</ol>", baris)


# ---------------------------------------------------------------------------
# Konten sekolah
# ---------------------------------------------------------------------------
@admin.register(GaleriKegiatan)
class GaleriAdmin(admin.ModelAdmin):
    list_display = ("judul_kegiatan", "tanggal")
    date_hierarchy = "tanggal"


@admin.register(PesanKontak)
class PesanKontakAdmin(admin.ModelAdmin):
    list_display = ("nama", "email", "handphone", "tanggal", "pesan")
    search_fields = ("nama", "email", "pesan")
    readonly_fields = ("tanggal",)
