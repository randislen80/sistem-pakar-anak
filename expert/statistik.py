"""
Perhitungan statistik perkembangan anak.

Ditulis dalam Python murni (tanpa Django) agar mudah diuji. View cukup
mengubah objek RiwayatDiagnosa menjadi dict "rekaman" dengan kunci:

    id, anak_key, anak_id, nama, kelompok, jenis_kelamin,
    tanggal (datetime.date), hasil (list per domain), kesimpulan, rata_rata
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from datetime import date

from .inference import (
    KESIMPULAN_INFO,
    KESIMPULAN_URUT,
    STATUS_BERMASALAH,
    STATUS_INFO,
    STATUS_URUT,
    kesimpulan_dari_hasil,
    rata_rata_capaian,
)

NAMA_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
NAMA_BULAN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
                      "Agustus", "September", "Oktober", "November", "Desember"]


def _rata(nilai):
    nilai = [v for v in nilai if v is not None]
    return round(sum(nilai) / len(nilai), 1) if nilai else None


def tanggal_indonesia(tgl: date | None, pendek: bool = True) -> str:
    if not tgl:
        return "-"
    nama = NAMA_BULAN if pendek else NAMA_BULAN_PANJANG
    return f"{tgl.day} {nama[tgl.month - 1]} {tgl.year}"


def peta_hasil(hasil: list[dict]) -> dict:
    """{nama_domain: item_hasil} untuk pencarian cepat."""
    return {h.get("domain"): h for h in (hasil or []) if h.get("domain")}


def kesimpulan_rekaman(r: dict) -> str:
    return r.get("kesimpulan") or kesimpulan_dari_hasil(r.get("hasil") or [])


def rata_rata_rekaman(r: dict) -> float:
    if r.get("rata_rata") not in (None, ""):
        return float(r["rata_rata"])
    return rata_rata_capaian(r.get("hasil") or [])


# ---------------------------------------------------------------------------
# Kumpulan rekaman
# ---------------------------------------------------------------------------
def urutkan(rekaman: list[dict]) -> list[dict]:
    return sorted(rekaman, key=lambda r: (r["tanggal"], r.get("id") or 0))


def kelompokkan_per_anak(rekaman: list[dict]) -> "OrderedDict[str, list[dict]]":
    per_anak: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in urutkan(rekaman):
        per_anak.setdefault(r["anak_key"], []).append(r)
    return per_anak


def terbaru_per_anak(rekaman: list[dict]) -> list[dict]:
    """Diagnosis terakhir tiap anak (agar satu anak tidak terhitung berkali-kali)."""
    return [daftar[-1] for daftar in kelompokkan_per_anak(rekaman).values()]


# ---------------------------------------------------------------------------
# Statistik per domain
# ---------------------------------------------------------------------------
def rata_rata_domain(rekaman: list[dict], domains: list[str]) -> list[dict]:
    keluaran = []
    for d in domains:
        nilai = []
        for r in rekaman:
            h = peta_hasil(r["hasil"]).get(d)
            if h is not None:
                nilai.append(float(h.get("persen") or 0))
        keluaran.append({"domain": d, "rata": _rata(nilai), "n": len(nilai)})
    return keluaran


def sebaran_status(rekaman: list[dict], domains: list[str]) -> list[dict]:
    """Jumlah anak per status untuk setiap domain."""
    keluaran = []
    for d in domains:
        hitung = OrderedDict((s, 0) for s in STATUS_URUT)
        for r in rekaman:
            h = peta_hasil(r["hasil"]).get(d)
            if h is not None and h.get("status") in hitung:
                hitung[h["status"]] += 1
        total = sum(hitung.values())
        keluaran.append({
            "domain": d,
            "total": total,
            "jumlah": dict(hitung),
            "persen": {s: (round(v / total * 100, 1) if total else 0.0) for s, v in hitung.items()},
            "bermasalah": sum(hitung[s] for s in STATUS_BERMASALAH),
        })
    return keluaran


def sebaran_kesimpulan(rekaman: list[dict]) -> list[dict]:
    hitung = OrderedDict((k, 0) for k in KESIMPULAN_URUT)
    for r in rekaman:
        k = kesimpulan_rekaman(r)
        if k in hitung:
            hitung[k] += 1
    total = sum(hitung.values())
    return [{
        "kunci": k,
        "label": KESIMPULAN_INFO[k]["label"],
        "kode": KESIMPULAN_INFO[k]["kode"],
        "warna": KESIMPULAN_INFO[k]["warna"],
        "kelas": KESIMPULAN_INFO[k]["kelas"],
        "jumlah": v,
        "persen": round(v / total * 100, 1) if total else 0.0,
    } for k, v in hitung.items()]


def tren_bulanan(rekaman: list[dict], domains: list[str]) -> dict:
    """Rata-rata capaian per bulan (seluruh diagnosis pada bulan tersebut)."""
    per_bulan: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in rekaman:
        t = r["tanggal"]
        per_bulan[(t.year, t.month)].append(r)
    kunci = sorted(per_bulan)
    label = [f"{NAMA_BULAN[m - 1]} {y}" for y, m in kunci]
    keseluruhan = [_rata(rata_rata_rekaman(r) for r in per_bulan[k]) for k in kunci]
    per_domain = OrderedDict()
    for d in domains:
        seri = []
        for k in kunci:
            nilai = [float(peta_hasil(r["hasil"])[d].get("persen") or 0)
                     for r in per_bulan[k] if d in peta_hasil(r["hasil"])]
            seri.append(_rata(nilai))
        per_domain[d] = seri
    return {
        "label": label,
        "keseluruhan": keseluruhan,
        "per_domain": per_domain,
        "jumlah": [len(per_bulan[k]) for k in kunci],
    }


def per_kelompok(rekaman: list[dict], domains: list[str], kelompok_label: dict) -> list[dict]:
    """Rata-rata capaian per domain untuk tiap kelompok kelas."""
    keluaran = []
    for kode, label in kelompok_label.items():
        anggota = [r for r in rekaman if (r.get("kelompok") or "") == kode]
        if not anggota:
            continue
        keluaran.append({
            "kode": kode,
            "label": label,
            "n": len(anggota),
            "rata": [x["rata"] for x in rata_rata_domain(anggota, domains)],
            "rata_keseluruhan": _rata(rata_rata_rekaman(r) for r in anggota),
        })
    return keluaran


def per_jenis_kelamin(rekaman: list[dict], jk_label: dict) -> list[dict]:
    keluaran = []
    for kode, label in jk_label.items():
        anggota = [r for r in rekaman if (r.get("jenis_kelamin") or "") == kode]
        keluaran.append({
            "kode": kode,
            "label": label,
            "n": len(anggota),
            "rata": _rata(rata_rata_rekaman(r) for r in anggota),
        })
    return keluaran


def perubahan_capaian(rekaman: list[dict], domains: list[str]) -> dict:
    """
    Membandingkan diagnosis pertama dan terakhir setiap anak yang sudah
    didiagnosis minimal dua kali pada periode terpilih.
    """
    naik = tetap = turun = 0
    selisih_domain: dict[str, list[float]] = {d: [] for d in domains}
    selisih_total = []
    detail = []
    for daftar in kelompokkan_per_anak(rekaman).values():
        if len(daftar) < 2:
            continue
        awal, akhir = daftar[0], daftar[-1]
        s = round(rata_rata_rekaman(akhir) - rata_rata_rekaman(awal), 1)
        selisih_total.append(s)
        if s > 0:
            naik += 1
        elif s < 0:
            turun += 1
        else:
            tetap += 1
        pa, pb = peta_hasil(awal["hasil"]), peta_hasil(akhir["hasil"])
        for d in domains:
            if d in pa and d in pb:
                selisih_domain[d].append(float(pb[d].get("persen") or 0) - float(pa[d].get("persen") or 0))
        detail.append({
            "anak_key": akhir["anak_key"], "anak_id": akhir.get("anak_id"), "nama": akhir["nama"],
            "awal": rata_rata_rekaman(awal), "akhir": rata_rata_rekaman(akhir), "selisih": s,
            "jumlah_diagnosis": len(daftar),
        })
    detail.sort(key=lambda x: x["selisih"], reverse=True)
    return {
        "jumlah_anak": naik + tetap + turun,
        "naik": naik,
        "tetap": tetap,
        "turun": turun,
        "rata_selisih": _rata(selisih_total),
        "per_domain": [{"domain": d, "selisih": _rata(selisih_domain[d]), "n": len(selisih_domain[d])}
                       for d in domains],
        "detail": detail,
    }


def anak_perlu_perhatian(terbaru: list[dict]) -> list[dict]:
    """Anak yang pada diagnosis terakhirnya memiliki domain Terlambat/Belum Terlihat."""
    daftar = []
    for r in terbaru:
        bermasalah = [h for h in r["hasil"] if h.get("status") in STATUS_BERMASALAH]
        perlu = [h for h in r["hasil"] if h.get("status") == "perlu perhatian"]
        if not bermasalah:
            continue
        daftar.append({
            "id": r.get("id"),
            "anak_id": r.get("anak_id"),
            "nama": r["nama"],
            "kelompok": r.get("kelompok") or "",
            "tanggal": r["tanggal"],
            "rata_rata": rata_rata_rekaman(r),
            "kesimpulan": kesimpulan_rekaman(r),
            "domain_bermasalah": [{"domain": h["domain"], "status": h["status"],
                                   "label": STATUS_INFO[h["status"]]["label"],
                                   "kelas": STATUS_INFO[h["status"]]["kelas"]} for h in bermasalah],
            "jumlah_perlu": len(perlu),
        })
    daftar.sort(key=lambda x: (-len(x["domain_bermasalah"]), x["rata_rata"], x["nama"]))
    return daftar


# ---------------------------------------------------------------------------
# Ringkasan untuk dasbor statistik sekolah
# ---------------------------------------------------------------------------
def ringkasan_sekolah(rekaman: list[dict], domains: list[str], kelompok_label: dict,
                      jk_label: dict) -> dict:
    rekaman = urutkan(rekaman)
    terbaru = terbaru_per_anak(rekaman)
    rata_domain = rata_rata_domain(terbaru, domains)
    kes = sebaran_kesimpulan(terbaru)
    perhatian = anak_perlu_perhatian(terbaru)

    ada_nilai = [x for x in rata_domain if x["rata"] is not None]
    terlemah = min(ada_nilai, key=lambda x: x["rata"]) if ada_nilai else None
    terkuat = max(ada_nilai, key=lambda x: x["rata"]) if ada_nilai else None
    jumlah_sesuai = next((k["jumlah"] for k in kes if k["kunci"] == "sesuai_harapan"), 0)

    return {
        "jumlah_diagnosis": len(rekaman),
        "jumlah_anak": len(terbaru),
        "rata_rata": _rata(rata_rata_rekaman(r) for r in terbaru),
        "jumlah_sesuai_harapan": jumlah_sesuai,
        "persen_sesuai_harapan": round(jumlah_sesuai / len(terbaru) * 100, 1) if terbaru else 0.0,
        "jumlah_perlu_perhatian": len(perhatian),
        "rata_domain": rata_domain,
        "domain_terlemah": terlemah,
        "domain_terkuat": terkuat,
        "sebaran_status": sebaran_status(terbaru, domains),
        "sebaran_kesimpulan": kes,
        "tren": tren_bulanan(rekaman, domains),
        "per_kelompok": per_kelompok(terbaru, domains, kelompok_label),
        "per_jenis_kelamin": per_jenis_kelamin(terbaru, jk_label),
        "perubahan": perubahan_capaian(rekaman, domains),
        "perlu_perhatian": perhatian,
    }


# ---------------------------------------------------------------------------
# Statistik perkembangan satu anak
# ---------------------------------------------------------------------------
def perkembangan_anak(rekaman: list[dict], domains: list[str]) -> dict:
    """
    Linimasa perkembangan seorang anak: seri capaian per domain, tabel
    riwayat dengan selisih terhadap diagnosis sebelumnya, serta domain
    terkuat/terlemah pada diagnosis terakhir.
    """
    rekaman = urutkan(rekaman)
    if not rekaman:
        return {"ada_data": False, "jumlah": 0}

    label = [tanggal_indonesia(r["tanggal"]) for r in rekaman]
    seri = OrderedDict()
    for d in domains:
        seri[d] = [(float(peta_hasil(r["hasil"])[d].get("persen") or 0)
                    if d in peta_hasil(r["hasil"]) else None) for r in rekaman]
    keseluruhan = [rata_rata_rekaman(r) for r in rekaman]

    baris = []
    sebelumnya = None
    for r in rekaman:
        p = peta_hasil(r["hasil"])
        q = peta_hasil(sebelumnya["hasil"]) if sebelumnya else {}
        sel = []
        for d in domains:
            h = p.get(d)
            if h is None:
                sel.append(None)
                continue
            persen = float(h.get("persen") or 0)
            selisih = None
            if d in q:
                selisih = round(persen - float(q[d].get("persen") or 0), 1)
            status = h.get("status", "")
            sel.append({
                "persen": persen,
                "status": status,
                "label": STATUS_INFO.get(status, {}).get("label", status),
                "kelas": STATUS_INFO.get(status, {}).get("kelas", ""),
                "selisih": selisih,
            })
        rata = rata_rata_rekaman(r)
        baris.append({
            "id": r.get("id"),
            "tanggal": r["tanggal"],
            "tanggal_teks": tanggal_indonesia(r["tanggal"]),
            "usia": r.get("usia") or "",
            "sel": sel,
            "rata_rata": rata,
            "selisih_rata": (round(rata - rata_rata_rekaman(sebelumnya), 1) if sebelumnya else None),
            "kesimpulan": kesimpulan_rekaman(r),
        })
        sebelumnya = r

    terakhir = rekaman[-1]
    p_akhir = peta_hasil(terakhir["hasil"])
    nilai_akhir = [(d, float(p_akhir[d].get("persen") or 0)) for d in domains if d in p_akhir]
    terkuat = max(nilai_akhir, key=lambda x: x[1]) if nilai_akhir else None
    terlemah = min(nilai_akhir, key=lambda x: x[1]) if nilai_akhir else None

    fokus = [{"domain": d, "status": p_akhir[d]["status"],
              "label": STATUS_INFO[p_akhir[d]["status"]]["label"],
              "kelas": STATUS_INFO[p_akhir[d]["status"]]["kelas"],
              "persen": float(p_akhir[d].get("persen") or 0)}
             for d in domains if d in p_akhir and p_akhir[d].get("status") in STATUS_INFO
             and p_akhir[d]["status"] != "sesuai"]

    return {
        "ada_data": True,
        "jumlah": len(rekaman),
        "label": label,
        "seri": seri,
        "keseluruhan": keseluruhan,
        "baris": list(reversed(baris)),
        "terakhir": terakhir,
        "rata_terakhir": keseluruhan[-1],
        "selisih_terakhir": baris[-1]["selisih_rata"],
        "selisih_total": (round(keseluruhan[-1] - keseluruhan[0], 1) if len(keseluruhan) > 1 else None),
        "terkuat": terkuat,
        "terlemah": terlemah,
        "fokus": fokus,
        "kesimpulan_terakhir": kesimpulan_rekaman(terakhir),
    }
