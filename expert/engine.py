"""
Penghubung antara basis data (Django ORM) dan mesin inferensi.

Mesin forward chaining sendiri ada di expert/inference.py (Python murni).
"""

from .inference import forward_chaining as _forward_chaining
from .inference import susun_aturan
from .models import DomainPerkembangan


def muat_basis_pengetahuan():
    """
    Membaca domain, indikator, dan rekomendasi dari basis data.
    Mengembalikan (basis, rekomendasi) dalam bentuk struktur data biasa.
    """
    domains = DomainPerkembangan.objects.prefetch_related("indikator", "rekomendasi").all()
    basis = []
    rekomendasi = {}
    for d in domains:
        basis.append({
            "id": d.id,
            "kode": d.kode,
            "nama": d.nama,
            "deskripsi": d.deskripsi,
            "indikator": [
                {"id": i.id, "kode": i.kode, "deskripsi": i.deskripsi}
                for i in d.indikator.all()
            ],
        })
        rekomendasi[d.nama] = [{"status": r.status, "teks": r.teks} for r in d.rekomendasi.all()]
    return basis, rekomendasi


def forward_chaining(indikator_terpilih):
    """Menjalankan diagnosis berdasarkan id indikator yang dipilih."""
    basis, rekomendasi = muat_basis_pengetahuan()
    return _forward_chaining(basis, indikator_terpilih, rekomendasi)


def daftar_aturan():
    """Daftar aturan untuk ditampilkan di halaman Basis Pengetahuan."""
    basis, rekomendasi = muat_basis_pengetahuan()
    return [a.sebagai_dict() for a in susun_aturan(basis, rekomendasi)], basis


def nama_domain_berurutan():
    return list(DomainPerkembangan.objects.values_list("nama", flat=True))
