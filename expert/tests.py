"""
Uji integrasi halaman (memakai basis data uji Django).

Jalankan dengan:
    python manage.py test expert
"""

import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Anak, DomainPerkembangan, Indikator, PesanKontak, Rekomendasi, RiwayatDiagnosa


class UjiBasisPengetahuan(TestCase):
    def test_migrasi_mengisi_basis_pengetahuan(self):
        self.assertEqual(DomainPerkembangan.objects.count(), 6)
        self.assertEqual(Indikator.objects.count(), 18)
        self.assertTrue(Rekomendasi.objects.exists())
        self.assertEqual(DomainPerkembangan.objects.first().kode, "D01")
        self.assertTrue(Indikator.objects.filter(kode="G18").exists())


class UjiHalaman(TestCase):
    def setUp(self):
        self.guru = get_user_model().objects.create_user("guru", password="rahasia-123")
        self.client.login(username="guru", password="rahasia-123")
        self.anak = Anak.objects.create(nama="Maria Yikwa", jenis_kelamin="P",
                                        tanggal_lahir=dt.date(2021, 5, 10), kelompok="A")

    def _diagnosa(self, indikator, tanggal):
        return self.client.post(reverse("diagnosis"), {
            "mode": "terdaftar",
            "anak": self.anak.pk,
            "tanggal": tanggal.isoformat(),
            "indikator": [str(i) for i in indikator],
            "catatan": "uji",
        })

    def test_halaman_umum(self):
        for nama in ["index", "basis_pengetahuan", "galeri", "kontak"]:
            self.assertEqual(self.client.get(reverse(nama)).status_code, 200, nama)

    def test_wajib_login(self):
        self.client.logout()
        resp = self.client.get(reverse("statistik"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("masuk"), resp["Location"])

    def test_diagnosis_dan_hasil(self):
        semua = list(Indikator.objects.values_list("id", flat=True))
        resp = self._diagnosa(semua[:3], timezone.localdate())
        self.assertEqual(resp.status_code, 302)
        r = RiwayatDiagnosa.objects.get()
        self.assertEqual(r.anak, self.anak)
        self.assertEqual(r.hasil[0]["status"], "sesuai")
        self.assertEqual(r.kesimpulan, "perhatian_khusus")
        self.assertTrue(r.jejak)
        self.assertTrue(r.usia)
        detail = self.client.get(resp["Location"])
        self.assertContains(detail, "Perlu Perhatian Khusus")
        self.assertContains(detail, "Jejak penalaran")
        pdf = self.client.get(reverse("riwayat_pdf", args=[r.pk]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_diagnosis_anak_baru(self):
        resp = self.client.post(reverse("diagnosis"), {
            "mode": "baru", "nama_baru": "  Petrus   Wanimbo ", "jenis_kelamin_baru": "L",
            "tanggal_lahir_baru": "2020-08-01", "tanggal": timezone.localdate().isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        anak = Anak.objects.get(nama="Petrus Wanimbo")
        self.assertEqual(anak.kelompok, "B")
        self.assertEqual(anak.riwayat.count(), 1)

    def test_diagnosis_tidak_valid(self):
        resp = self.client.post(reverse("diagnosis"), {"mode": "terdaftar", "tanggal": "2026-01-01"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(RiwayatDiagnosa.objects.exists())

    def test_statistik_perkembangan(self):
        semua = list(Indikator.objects.values_list("id", flat=True))
        hari_ini = timezone.localdate()
        self._diagnosa(semua[:6], hari_ini - dt.timedelta(days=60))
        self._diagnosa(semua[:15], hari_ini)
        profil = self.client.get(reverse("anak_detail", args=[self.anak.pk]))
        self.assertEqual(profil.status_code, 200)
        self.assertContains(profil, "Perkembangan capaian dari waktu ke waktu")
        self.assertEqual(profil.context["p"]["jumlah"], 2)
        self.assertGreater(profil.context["p"]["selisih_total"], 0)

        stat = self.client.get(reverse("statistik"), {"periode": "6bulan", "kelompok": "A"})
        self.assertEqual(stat.status_code, 200)
        self.assertEqual(stat.context["s"]["jumlah_anak"], 1)
        self.assertEqual(stat.context["s"]["perubahan"]["naik"], 1)

        excel = self.client.get(reverse("statistik_excel"))
        self.assertEqual(excel.status_code, 200)
        self.assertTrue(excel.content.startswith(b"PK"))
        laporan = self.client.get(reverse("anak_pdf", args=[self.anak.pk]))
        self.assertTrue(laporan.content.startswith(b"%PDF"))

    def test_daftar_dan_crud_anak(self):
        self.assertContains(self.client.get(reverse("anak_list")), "Maria Yikwa")
        self.assertContains(self.client.get(reverse("riwayat_list")), "Riwayat Diagnosis")
        resp = self.client.post(reverse("anak_tambah"), {
            "nama": "Yohana Itlay", "jenis_kelamin": "P", "tanggal_lahir": "2020-03-03", "aktif": "on",
        })
        self.assertEqual(resp.status_code, 302)
        baru = Anak.objects.get(nama="Yohana Itlay")
        self.client.post(reverse("anak_hapus", args=[baru.pk]))
        self.assertFalse(Anak.objects.filter(pk=baru.pk).exists())

    def test_kontak(self):
        self.client.post(reverse("kontak"), {"nama": "Orang Tua", "handphone": "0812", "pesan": "Halo"})
        self.assertEqual(PesanKontak.objects.count(), 1)


@override_settings(WAJIB_LOGIN=True)
class UjiTanpaLogin(TestCase):
    def test_beranda_tanpa_login(self):
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("ringkas", resp.context)
