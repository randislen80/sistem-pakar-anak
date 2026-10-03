"""
Mesin inferensi Forward Chaining.

Modul ini sengaja ditulis dalam Python murni (tanpa Django) agar logika
penalaran mudah diuji, mudah dijelaskan di laporan skripsi, dan tidak
tergantung pada basis data.

Alur penalaran (data-driven / forward chaining):

    Fakta awal  : indikator (kemampuan) yang diamati sudah dimiliki anak
         |
         v
    Tahap 1 (R01, R02, ...) : menentukan STATUS setiap domain perkembangan
         |                    berdasarkan jumlah indikator yang terpenuhi
         v
    Tahap 2 (K01 - K04)     : menentukan KESIMPULAN UMUM dari seluruh status domain
         |
         v
    Tahap 3 (S01, S02, ...) : menurunkan REKOMENDASI STIMULASI tiap domain
                              sesuai status yang sudah disimpulkan

Setiap aturan yang terpicu dicatat di "jejak" (trace) sehingga pengguna dapat
melihat mengapa sistem sampai pada suatu kesimpulan.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable

# ---------------------------------------------------------------------------
# Status domain (nilai disimpan dalam huruf kecil agar cocok dengan data lama)
# ---------------------------------------------------------------------------
SESUAI = "sesuai"
PERLU_PERHATIAN = "perlu perhatian"
TERLAMBAT = "terlambat"
BELUM_TERLIHAT = "belum terlihat"

STATUS_URUT = [SESUAI, PERLU_PERHATIAN, TERLAMBAT, BELUM_TERLIHAT]
STATUS_BERMASALAH = {TERLAMBAT, BELUM_TERLIHAT}

STATUS_INFO = {
    SESUAI: {
        "label": "Sesuai",
        "kelas": "sesuai",
        "ikon": "bi-check-circle-fill",
        "warna": "#0ca30c",
        "keterangan": "Seluruh indikator pada domain ini sudah tercapai.",
    },
    PERLU_PERHATIAN: {
        "label": "Perlu Perhatian",
        "kelas": "perlu",
        "ikon": "bi-exclamation-circle-fill",
        "warna": "#fab219",
        "keterangan": "Sebagian besar indikator tercapai, tetapi belum seluruhnya.",
    },
    TERLAMBAT: {
        "label": "Terlambat",
        "kelas": "terlambat",
        "ikon": "bi-exclamation-triangle-fill",
        "warna": "#ec835a",
        "keterangan": "Baru sedikit indikator yang tercapai untuk usianya.",
    },
    BELUM_TERLIHAT: {
        "label": "Belum Terlihat",
        "kelas": "belum",
        "ikon": "bi-x-circle-fill",
        "warna": "#d03b3b",
        "keterangan": "Belum ada indikator pada domain ini yang terlihat.",
    },
}

# Ambang batas persentase indikator terpenuhi.
# Dengan 3 indikator per domain: 3 = Sesuai, 2 = Perlu Perhatian,
# 1 = Terlambat, 0 = Belum Terlihat (sama dengan aturan versi awal program).
BATAS_SESUAI = 100.0
BATAS_PERLU_PERHATIAN = 60.0

# ---------------------------------------------------------------------------
# Kesimpulan umum (tahap 2)
# ---------------------------------------------------------------------------
K_SESUAI_HARAPAN = "sesuai_harapan"
K_PENDAMPINGAN = "pendampingan"
K_STIMULASI_TERARAH = "stimulasi_terarah"
K_PERHATIAN_KHUSUS = "perhatian_khusus"

KESIMPULAN_URUT = [K_SESUAI_HARAPAN, K_PENDAMPINGAN, K_STIMULASI_TERARAH, K_PERHATIAN_KHUSUS]

KESIMPULAN_INFO = {
    K_SESUAI_HARAPAN: {
        "kode": "K01",
        "label": "Berkembang Sesuai Harapan",
        "kelas": "sesuai",
        "ikon": "bi-emoji-smile-fill",
        "warna": "#0ca30c",
        "jika": "semua domain berstatus Sesuai",
        "saran": (
            "Seluruh aspek perkembangan yang diamati sudah tercapai. Pertahankan "
            "stimulasi yang sudah berjalan dan berikan kegiatan pengayaan agar anak "
            "tetap tertantang."
        ),
    },
    K_PENDAMPINGAN: {
        "kode": "K02",
        "label": "Perlu Pendampingan",
        "kelas": "perlu",
        "ikon": "bi-hand-thumbs-up-fill",
        "warna": "#fab219",
        "jika": "tidak ada domain Terlambat/Belum Terlihat, tetapi ada domain Perlu Perhatian",
        "saran": (
            "Sebagian besar kemampuan sudah muncul, namun beberapa indikator belum "
            "tercapai. Dampingi anak dengan latihan ringan yang menyenangkan di "
            "sekolah maupun di rumah."
        ),
    },
    K_STIMULASI_TERARAH: {
        "kode": "K03",
        "label": "Perlu Stimulasi Terarah",
        "kelas": "terlambat",
        "ikon": "bi-bullseye",
        "warna": "#ec835a",
        "jika": "terdapat 1 - 2 domain berstatus Terlambat/Belum Terlihat",
        "saran": (
            "Ada aspek perkembangan yang tertinggal. Berikan stimulasi yang terjadwal "
            "pada aspek tersebut, libatkan orang tua, dan lakukan pengamatan ulang "
            "dalam 1 - 2 bulan."
        ),
    },
    K_PERHATIAN_KHUSUS: {
        "kode": "K04",
        "label": "Perlu Perhatian Khusus",
        "kelas": "belum",
        "ikon": "bi-heart-pulse-fill",
        "warna": "#d03b3b",
        "jika": "terdapat 3 domain atau lebih berstatus Terlambat/Belum Terlihat",
        "saran": (
            "Beberapa aspek perkembangan tertinggal sekaligus. Diskusikan hasil ini "
            "dengan orang tua dan pertimbangkan konsultasi ke tenaga profesional "
            "(dokter anak, psikolog anak, atau layanan tumbuh kembang di Puskesmas)."
        ),
    },
}


# ---------------------------------------------------------------------------
# Fungsi bantu
# ---------------------------------------------------------------------------
def hitung_persen(terpenuhi: int, total: int) -> float:
    if not total:
        return 0.0
    return round(terpenuhi / total * 100, 1)


def tentukan_status(terpenuhi: int, total: int) -> str:
    """Status domain berdasarkan jumlah indikator yang terpenuhi."""
    if total <= 0 or terpenuhi <= 0:
        return BELUM_TERLIHAT
    persen = terpenuhi / total * 100
    if persen >= BATAS_SESUAI:
        return SESUAI
    if persen >= BATAS_PERLU_PERHATIAN:
        return PERLU_PERHATIAN
    return TERLAMBAT


def tentukan_kesimpulan(daftar_status: Iterable[str]) -> str:
    """Kesimpulan umum dari status seluruh domain (tahap 2)."""
    daftar_status = list(daftar_status)
    bermasalah = sum(1 for s in daftar_status if s in STATUS_BERMASALAH)
    perlu = sum(1 for s in daftar_status if s == PERLU_PERHATIAN)
    if bermasalah >= 3:
        return K_PERHATIAN_KHUSUS
    if bermasalah >= 1:
        return K_STIMULASI_TERARAH
    if perlu >= 1:
        return K_PENDAMPINGAN
    return K_SESUAI_HARAPAN


def _rentang_jumlah(total: int, status: str) -> tuple[int, int] | None:
    """Rentang jumlah indikator (min, max) yang menghasilkan status tertentu."""
    if total <= 0:
        return None
    min_perlu = max(1, math.ceil(total * BATAS_PERLU_PERHATIAN / 100))
    if status == SESUAI:
        return (total, total)
    if status == PERLU_PERHATIAN:
        lo, hi = min_perlu, total - 1
    elif status == TERLAMBAT:
        lo, hi = 1, min(min_perlu - 1, total - 1)
    else:
        return (0, 0)
    return (lo, hi) if lo <= hi else None


def teks_kondisi(nama_domain: str, total: int, status: str) -> str:
    rentang = _rentang_jumlah(total, status)
    if rentang is None:
        return f"(tidak berlaku untuk {nama_domain} dengan {total} indikator)"
    lo, hi = rentang
    if status == BELUM_TERLIHAT:
        return f"tidak ada indikator {nama_domain} yang terpenuhi (0 dari {total})"
    if status == SESUAI:
        return f"seluruh indikator {nama_domain} terpenuhi ({total} dari {total})"
    jumlah = f"{lo}" if lo == hi else f"{lo}-{hi}"
    return f"indikator {nama_domain} terpenuhi {jumlah} dari {total}"


# ---------------------------------------------------------------------------
# Representasi aturan
# ---------------------------------------------------------------------------
@dataclass
class Aturan:
    kode: str
    tahap: int
    jika: str
    maka: str
    cocok: Callable[[dict], bool]
    aksi: Callable[[dict], str]
    berlaku: bool = True
    domain: str = ""

    def sebagai_dict(self) -> dict:
        return {"kode": self.kode, "tahap": self.tahap, "jika": self.jika,
                "maka": self.maka, "berlaku": self.berlaku}


def _aturan_status(no: int, domain: dict, status: str) -> Aturan:
    nama = domain["nama"]
    ids = {i["id"] for i in domain["indikator"]}
    total = len(ids)
    rentang = _rentang_jumlah(total, status)

    def cocok(wm, nama=nama, ids=ids, total=total, status=status):
        if nama in wm["status"]:
            return False
        terpenuhi = len(ids & wm["indikator"])
        return tentukan_status(terpenuhi, total) == status

    def aksi(wm, nama=nama, status=status):
        wm["status"][nama] = status
        return f"Status {nama} = {STATUS_INFO[status]['label']}"

    return Aturan(
        kode=f"R{no:02d}",
        tahap=1,
        jika=teks_kondisi(nama, total, status),
        maka=f"{nama} = {STATUS_INFO[status]['label']}",
        cocok=cocok,
        aksi=aksi,
        berlaku=rentang is not None,
        domain=nama,
    )


def _aturan_kesimpulan(kunci: str, jumlah_domain: int) -> Aturan:
    info = KESIMPULAN_INFO[kunci]

    def cocok(wm, kunci=kunci):
        if wm["kesimpulan"] is not None or len(wm["status"]) < jumlah_domain:
            return False
        return tentukan_kesimpulan(wm["status"].values()) == kunci

    def aksi(wm, kunci=kunci):
        wm["kesimpulan"] = kunci
        return f"Kesimpulan = {KESIMPULAN_INFO[kunci]['label']}"

    return Aturan(kode=info["kode"], tahap=2, jika=info["jika"],
                  maka=f"Kesimpulan = {info['label']}", cocok=cocok, aksi=aksi)


def _aturan_rekomendasi(no: int, domain: dict, rekomendasi: dict) -> Aturan:
    nama = domain["nama"]

    def cocok(wm, nama=nama):
        return nama in wm["status"] and nama not in wm["rekomendasi"]

    def aksi(wm, nama=nama):
        status = wm["status"][nama]
        daftar = pilih_rekomendasi(rekomendasi.get(nama, []), status)
        wm["rekomendasi"][nama] = daftar
        return f"{len(daftar)} rekomendasi untuk {nama} ({STATUS_INFO[status]['label']})"

    return Aturan(
        kode=f"S{no:02d}",
        tahap=3,
        jika=f"status {nama} sudah diketahui",
        maka=f"berikan rekomendasi stimulasi {nama} sesuai statusnya",
        cocok=cocok,
        aksi=aksi,
        domain=nama,
    )


def pilih_rekomendasi(daftar: list[dict], status: str) -> list[str]:
    """
    Pilih teks rekomendasi yang sesuai status.
    Rekomendasi dengan status kosong berlaku untuk semua status yang belum Sesuai.
    """
    hasil = []
    for r in daftar:
        s = (r.get("status") or "").strip()
        if s == status or (not s and status != SESUAI):
            hasil.append(r["teks"])
    return hasil


def susun_aturan(basis: list[dict], rekomendasi: dict | None = None) -> list[Aturan]:
    """Membangun basis aturan dari basis pengetahuan (domain + indikator)."""
    rekomendasi = rekomendasi or {}
    domain_aktif = [d for d in basis if d["indikator"]]
    aturan: list[Aturan] = []
    no = 1
    for d in domain_aktif:
        for status in STATUS_URUT:
            aturan.append(_aturan_status(no, d, status))
            no += 1
    for kunci in KESIMPULAN_URUT:
        aturan.append(_aturan_kesimpulan(kunci, len(domain_aktif)))
    for i, d in enumerate(domain_aktif, start=1):
        aturan.append(_aturan_rekomendasi(i, d, rekomendasi))
    return aturan


# ---------------------------------------------------------------------------
# Mesin inferensi
# ---------------------------------------------------------------------------
def forward_chaining(basis: list[dict], fakta: Iterable, rekomendasi: dict | None = None) -> dict:
    """
    Menjalankan forward chaining.

    basis       : [{"id", "kode", "nama", "indikator": [{"id", "kode", "deskripsi"}]}]
    fakta       : id indikator yang dipilih (kemampuan yang sudah dimiliki anak)
    rekomendasi : {nama_domain: [{"status": "", "teks": "..."}]}

    Mengembalikan dict berisi: hasil (per domain), kesimpulan, rata_rata,
    jejak (urutan aturan yang terpicu) dan fakta awal.
    """
    semua_id = {i["id"] for d in basis for i in d["indikator"]}
    fakta_id = {int(f) for f in fakta if f is not None and str(f).strip() != ""} & semua_id

    wm = {"indikator": fakta_id, "status": {}, "kesimpulan": None, "rekomendasi": {}}
    aturan = susun_aturan(basis, rekomendasi)

    jejak = []
    fakta_awal = []
    for d in basis:
        for i in d["indikator"]:
            if i["id"] in fakta_id:
                fakta_awal.append({"id": i["id"], "kode": i.get("kode") or "",
                                   "deskripsi": i["deskripsi"], "domain": d["nama"]})

    terpicu = set()
    iterasi = 0
    while True:
        iterasi += 1
        ada_yang_terpicu = False
        for a in aturan:
            if a.kode in terpicu or not a.berlaku:
                continue
            if a.cocok(wm):
                fakta_baru = a.aksi(wm)
                terpicu.add(a.kode)
                ada_yang_terpicu = True
                jejak.append({
                    "langkah": len(jejak) + 1,
                    "iterasi": iterasi,
                    "tahap": a.tahap,
                    "aturan": a.kode,
                    "domain": a.domain,
                    "jika": a.jika,
                    "maka": a.maka,
                    "fakta_baru": fakta_baru,
                })
        if not ada_yang_terpicu or iterasi > len(aturan) + 1:
            break

    aturan_per_domain = {j["domain"]: j["aturan"] for j in jejak if j["tahap"] == 1}

    hasil = []
    for d in basis:
        if not d["indikator"]:
            continue
        nama = d["nama"]
        terpenuhi = [i for i in d["indikator"] if i["id"] in fakta_id]
        belum = [i for i in d["indikator"] if i["id"] not in fakta_id]
        total = len(d["indikator"])
        hasil.append({
            "domain": nama,
            "kode": d.get("kode") or "",
            "total": total,
            "terpenuhi": len(terpenuhi),
            "persen": hitung_persen(len(terpenuhi), total),
            "status": wm["status"].get(nama, tentukan_status(len(terpenuhi), total)),
            "aturan": aturan_per_domain.get(nama, ""),
            "indikator_terpenuhi": [i["deskripsi"] for i in terpenuhi],
            "indikator_belum": [i["deskripsi"] for i in belum],
            "rekomendasi": wm["rekomendasi"].get(nama, []),
        })

    kesimpulan = wm["kesimpulan"] or tentukan_kesimpulan(h["status"] for h in hasil)
    return {
        "hasil": hasil,
        "kesimpulan": kesimpulan,
        "rata_rata": rata_rata_capaian(hasil),
        "jejak": jejak,
        "fakta": fakta_awal,
    }


def rata_rata_capaian(hasil: list[dict]) -> float:
    nilai = [float(h.get("persen") or 0) for h in hasil]
    return round(sum(nilai) / len(nilai), 1) if nilai else 0.0


def kesimpulan_dari_hasil(hasil: list[dict]) -> str:
    """Menghitung kesimpulan dari data hasil (dipakai untuk riwayat lama)."""
    return tentukan_kesimpulan(h.get("status", "") for h in hasil)
