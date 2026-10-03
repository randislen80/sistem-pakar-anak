"""
Uji unit untuk logika forward chaining dan statistik.

Tidak memerlukan basis data, sehingga dapat dijalankan dengan:
    python manage.py test expert
atau tanpa Django sama sekali:
    python -m unittest expert.tests_logika
"""

import unittest
from datetime import date

from .inference import (
    BELUM_TERLIHAT,
    K_PENDAMPINGAN,
    K_PERHATIAN_KHUSUS,
    K_SESUAI_HARAPAN,
    K_STIMULASI_TERARAH,
    PERLU_PERHATIAN,
    SESUAI,
    TERLAMBAT,
    forward_chaining,
    susun_aturan,
    tentukan_kesimpulan,
    tentukan_status,
)
from .statistik import perkembangan_anak, ringkasan_sekolah

NAMA_DOMAIN = ["Motorik Halus", "Motorik Kasar", "Bahasa", "Kognitif", "Sosial Emosional", "Kemandirian"]


def buat_basis():
    basis, no = [], 1
    for i, nama in enumerate(NAMA_DOMAIN, start=1):
        indikator = []
        for _ in range(3):
            indikator.append({"id": no, "kode": f"G{no:02d}", "deskripsi": f"{nama} indikator {no}"})
            no += 1
        basis.append({"id": i, "kode": f"D{i:02d}", "nama": nama, "indikator": indikator})
    return basis


REKOMENDASI = {
    "Motorik Halus": [
        {"status": "", "teks": "Bermain playdough"},
        {"status": SESUAI, "teks": "Pengayaan: melipat origami"},
    ],
}


class UjiStatus(unittest.TestCase):
    def test_ambang_tiga_indikator_sama_dengan_versi_awal(self):
        self.assertEqual(tentukan_status(3, 3), SESUAI)
        self.assertEqual(tentukan_status(2, 3), PERLU_PERHATIAN)
        self.assertEqual(tentukan_status(1, 3), TERLAMBAT)
        self.assertEqual(tentukan_status(0, 3), BELUM_TERLIHAT)

    def test_ambang_jumlah_indikator_lain(self):
        self.assertEqual(tentukan_status(3, 5), PERLU_PERHATIAN)
        self.assertEqual(tentukan_status(2, 5), TERLAMBAT)
        self.assertEqual(tentukan_status(1, 1), SESUAI)
        self.assertEqual(tentukan_status(0, 0), BELUM_TERLIHAT)

    def test_kesimpulan(self):
        self.assertEqual(tentukan_kesimpulan([SESUAI] * 6), K_SESUAI_HARAPAN)
        self.assertEqual(tentukan_kesimpulan([SESUAI] * 5 + [PERLU_PERHATIAN]), K_PENDAMPINGAN)
        self.assertEqual(tentukan_kesimpulan([SESUAI] * 4 + [TERLAMBAT, BELUM_TERLIHAT]), K_STIMULASI_TERARAH)
        self.assertEqual(tentukan_kesimpulan([TERLAMBAT] * 3 + [SESUAI] * 3), K_PERHATIAN_KHUSUS)


class UjiForwardChaining(unittest.TestCase):
    def setUp(self):
        self.basis = buat_basis()

    def test_jumlah_aturan(self):
        aturan = susun_aturan(self.basis)
        self.assertEqual(sum(1 for a in aturan if a.tahap == 1), 24)
        self.assertEqual(sum(1 for a in aturan if a.tahap == 2), 4)
        self.assertEqual(sum(1 for a in aturan if a.tahap == 3), 6)
        self.assertEqual(len({a.kode for a in aturan}), len(aturan))

    def test_semua_indikator_terpenuhi(self):
        semua = [i["id"] for d in self.basis for i in d["indikator"]]
        hasil = forward_chaining(self.basis, semua, REKOMENDASI)
        self.assertEqual(hasil["kesimpulan"], K_SESUAI_HARAPAN)
        self.assertEqual(hasil["rata_rata"], 100.0)
        self.assertTrue(all(h["status"] == SESUAI for h in hasil["hasil"]))
        mh = hasil["hasil"][0]
        self.assertEqual(mh["rekomendasi"], ["Pengayaan: melipat origami"])

    def test_sebagian_indikator(self):
        # Motorik Halus 2/3, Motorik Kasar 1/3, lainnya 0
        fakta = ["1", "2", 4, None, "", 999]
        hasil = forward_chaining(self.basis, fakta, REKOMENDASI)
        status = {h["domain"]: h["status"] for h in hasil["hasil"]}
        self.assertEqual(status["Motorik Halus"], PERLU_PERHATIAN)
        self.assertEqual(status["Motorik Kasar"], TERLAMBAT)
        self.assertEqual(status["Bahasa"], BELUM_TERLIHAT)
        self.assertEqual(hasil["kesimpulan"], K_PERHATIAN_KHUSUS)
        self.assertEqual(len(hasil["fakta"]), 3)
        mh = hasil["hasil"][0]
        self.assertEqual(mh["terpenuhi"], 2)
        self.assertEqual(mh["persen"], 66.7)
        self.assertEqual(mh["aturan"], "R02")
        self.assertEqual(mh["rekomendasi"], ["Bermain playdough"])
        self.assertEqual(len(mh["indikator_belum"]), 1)

    def test_jejak_berurutan_per_tahap(self):
        hasil = forward_chaining(self.basis, [1, 2, 3], REKOMENDASI)
        tahap = [j["tahap"] for j in hasil["jejak"]]
        self.assertEqual(tahap, sorted(tahap))
        self.assertEqual(tahap.count(1), 6)
        self.assertEqual(tahap.count(2), 1)
        self.assertEqual(tahap.count(3), 6)
        self.assertEqual(hasil["jejak"][0]["aturan"], "R01")


def rekaman(id_, anak, tgl, persen_list, kelompok="A", jk="L"):
    hasil = []
    for nama, p in zip(NAMA_DOMAIN, persen_list):
        if p is None:
            continue
        k = round(p / 100 * 3)
        hasil.append({"domain": nama, "persen": p, "terpenuhi": k, "total": 3,
                      "status": tentukan_status(k, 3)})
    return {"id": id_, "anak_key": str(anak), "anak_id": anak, "nama": f"Anak {anak}",
            "kelompok": kelompok, "jenis_kelamin": jk, "tanggal": tgl, "hasil": hasil,
            "kesimpulan": "", "rata_rata": None}


class UjiStatistik(unittest.TestCase):
    def setUp(self):
        self.data = [
            rekaman(1, 1, date(2026, 1, 10), [33.3, 33.3, 66.7, 33.3, 0, 33.3]),
            rekaman(2, 1, date(2026, 3, 10), [66.7, 66.7, 100, 66.7, 33.3, 66.7]),
            rekaman(3, 2, date(2026, 1, 12), [100] * 6, kelompok="B", jk="P"),
            rekaman(4, 3, date(2026, 3, 1), [100, None, 100, 100, 66.7, 100], kelompok="B"),
        ]
        self.kel = {"A": "Kelompok A", "B": "Kelompok B"}
        self.jk = {"L": "Laki-laki", "P": "Perempuan"}

    def test_ringkasan(self):
        r = ringkasan_sekolah(self.data, NAMA_DOMAIN, self.kel, self.jk)
        self.assertEqual(r["jumlah_diagnosis"], 4)
        self.assertEqual(r["jumlah_anak"], 3)
        self.assertEqual(r["jumlah_sesuai_harapan"], 1)
        # Anak 1 (terakhir: Sosial Emosional 33.3 -> Terlambat) masuk daftar perhatian
        self.assertEqual([a["anak_id"] for a in r["perlu_perhatian"]], [1])
        # Motorik Kasar: anak 3 tidak punya data -> rata dari 2 anak
        mk = next(x for x in r["rata_domain"] if x["domain"] == "Motorik Kasar")
        self.assertEqual(mk["n"], 2)
        self.assertEqual(r["tren"]["label"], ["Jan 2026", "Mar 2026"])
        self.assertEqual(r["perubahan"]["naik"], 1)
        self.assertEqual(len(r["per_kelompok"]), 2)

    def test_perkembangan_anak(self):
        p = perkembangan_anak([self.data[1], self.data[0]], NAMA_DOMAIN)
        self.assertTrue(p["ada_data"])
        self.assertEqual(p["jumlah"], 2)
        self.assertEqual(p["seri"]["Bahasa"], [66.7, 100.0])
        self.assertGreater(p["selisih_total"], 0)
        # baris terbaru di atas, dengan selisih terhadap diagnosis sebelumnya
        self.assertEqual(p["baris"][0]["sel"][0]["selisih"], 33.4)
        self.assertEqual(p["terkuat"][0], "Bahasa")

    def test_tanpa_data(self):
        self.assertFalse(perkembangan_anak([], NAMA_DOMAIN)["ada_data"])
        r = ringkasan_sekolah([], NAMA_DOMAIN, self.kel, self.jk)
        self.assertEqual(r["jumlah_anak"], 0)
        self.assertIsNone(r["rata_rata"])


if __name__ == "__main__":
    unittest.main()
