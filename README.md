# Sistem Pakar Diagnosa Perkembangan Anak Usia Dini
**TK YPPK Kristus Terang Dunia Waena — Metode Forward Chaining**

Aplikasi web (Django) untuk membantu guru menilai perkembangan anak usia dini pada
6 domain (Motorik Halus, Motorik Kasar, Bahasa, Kognitif, Sosial Emosional, Kemandirian),
memberi rekomendasi stimulasi, dan memantau statistik perkembangan anak dari waktu ke waktu.

---

## 1. Cara menjalankan

Butuh Python 3.12 atau lebih baru (Django 6).

```bash
cd sp_diagnosa_anak
python -m venv venv
# Windows: venv\Scripts\activate    |  Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate          # WAJIB: menambah tabel & data baru (lihat bagian 3)
python manage.py runserver
```

Buka http://127.0.0.1:8000 lalu klik **Masuk** (pojok kanan atas) memakai akun admin yang
sudah ada. Membuat akun baru untuk guru:

```bash
python manage.py createsuperuser        # akun admin baru
```
atau lewat **Admin → Users → Add user** (centang *Staff status* bila guru boleh mengubah
basis pengetahuan).

### Mode offline (disarankan untuk sidang/presentasi)
Tampilan memakai Bootstrap dan Chart.js dari internet. Agar tetap tampil lengkap tanpa
internet, jalankan sekali saat komputer sedang online:

```bash
python manage.py unduh_aset
```
File akan tersimpan di `static/vendor/` dan otomatis dipakai.

### Menguji program
```bash
python manage.py test expert
```
Terdapat uji untuk mesin forward chaining, statistik, dan semua halaman utama.

---

## 2. Fitur

| Menu | Kegunaan |
|---|---|
| **Beranda** | Ringkasan: jumlah anak, total diagnosis, rata-rata capaian, anak yang perlu perhatian, diagnosis terbaru. |
| **Diagnosis** | Pilih anak (atau daftarkan anak baru), centang kemampuan yang terlihat per domain, lalu proses. Bisa memuat centang dari diagnosis terakhir dan mengisi tanggal pengamatan lampau. |
| **Hasil diagnosis** | Kesimpulan umum, grafik capaian per domain (dibanding diagnosis sebelumnya), indikator yang belum tampak, rekomendasi stimulasi, **jejak penalaran forward chaining**, unduh PDF, cetak. |
| **Data Anak** | Data anak (tanggal lahir, jenis kelamin, kelompok A/B, orang tua). Usia dihitung otomatis. |
| **Perkembangan anak** | Statistik per anak: grafik garis capaian tiap domain dari waktu ke waktu, perubahan sejak diagnosis pertama, domain terkuat/terlemah, perbandingan dengan teman sekelompok, tabel riwayat, laporan perkembangan PDF. |
| **Statistik** | Dasbor sekolah dengan filter periode/kelompok/jenis kelamin: rata-rata capaian per domain, sebaran status per domain, sebaran kesimpulan, tren bulanan, perbandingan Kelompok A vs B, perubahan capaian, daftar anak yang perlu perhatian, **ekspor Excel**. Setiap grafik punya tombol *Tabel*. |
| **Basis Pengetahuan** | Menampilkan domain, indikator (G01–G18), seluruh aturan (R01–R24, K01–K04, S01–S06), dan rekomendasi. Berguna untuk BAB IV. |
| **Galeri, Kontak** | Tetap ada, dengan tampilan baru dan validasi formulir. |
| **Admin** | Kelola domain, indikator, rekomendasi, data anak, riwayat, galeri, dan pesan. |

---

## 3. Mesin inferensi forward chaining

File: `expert/inference.py` (Python murni, mudah dijelaskan dan diuji).

**Fakta awal**: indikator yang dicentang guru.

**Tahap 1 — status domain (R01–R24, 4 aturan per domain)**

| Persentase indikator terpenuhi | Status | Untuk 3 indikator |
|---|---|---|
| 100% | Sesuai | 3 dari 3 |
| ≥ 60% dan < 100% | Perlu Perhatian | 2 dari 3 |
| > 0% dan < 60% | Terlambat | 1 dari 3 |
| 0% | Belum Terlihat | 0 dari 3 |

Aturan ini sama hasilnya dengan program versi awal untuk 3 indikator, tetapi kini berbasis
persentase sehingga tetap benar bila jumlah indikator per domain diubah di Admin.

**Tahap 2 — kesimpulan umum (K01–K04)**

| Aturan | JIKA | MAKA |
|---|---|---|
| K01 | semua domain Sesuai | Berkembang Sesuai Harapan |
| K02 | tidak ada domain Terlambat/Belum Terlihat, ada Perlu Perhatian | Perlu Pendampingan |
| K03 | 1–2 domain Terlambat/Belum Terlihat | Perlu Stimulasi Terarah |
| K04 | ≥ 3 domain Terlambat/Belum Terlihat | Perlu Perhatian Khusus |

**Tahap 3 — rekomendasi (S01–S06)**: status tiap domain menurunkan saran kegiatan dari tabel
Rekomendasi (status kosong = berlaku untuk semua status yang belum Sesuai; status *Sesuai* =
kegiatan pengayaan).

Setiap diagnosis menyimpan fakta awal, urutan aturan yang terpicu, kesimpulan, dan rata-rata
capaian, sehingga proses penalaran dapat ditampilkan kembali.

---

## 4. Perubahan dari versi sebelumnya

- **Model baru `Anak`** dan relasi riwayat → anak, sehingga perkembangan tiap anak bisa dilacak.
  Riwayat lama otomatis dibuatkan data anaknya oleh migrasi `0006_data_awal`
  (tanggal lahir anak lama perlu dilengkapi lewat menu Data Anak).
- Kode domain (D01–D06) dan indikator (G01–G18), urutan tampil, dan deskripsi domain.
- **Rekomendasi stimulasi bawaan** diisi otomatis (sebelumnya tabel rekomendasi kosong sehingga
  saran tidak pernah muncul), bisa diubah di Admin.
- Perbaikan logika status: urutan keparahan yang konsisten dan berbasis persentase.
- Diagnosis memakai pola *Post/Redirect/Get* (tidak tersimpan ganda saat halaman dimuat ulang),
  validasi formulir, dan pesan kesalahan yang jelas.
- Semua halaman memakai satu tata letak (sebelumnya halaman riwayat berdiri sendiri tanpa menu).
- Login guru untuk halaman yang berisi data anak (atur `WAJIB_LOGIN` di `settings.py`).
- Bahasa Indonesia dan zona waktu WIT (`Asia/Jayapura`).
- PDF hasil diagnosis lebih lengkap (grafik, rincian, rekomendasi, tanda tangan) dan laporan
  perkembangan anak; ekspor statistik ke Excel.
- Admin lebih rapi: pencarian, filter, inline indikator & rekomendasi.
- File contoh yang tidak dipakai (`index2.html`, `result.html`) dihapus; file sistem macOS
  (`._*`, `.DS_Store`) dan `__pycache__` dibersihkan. Gambar dibuat versi ringan (`*-web.jpg`).

---

## 5. Pengaturan penting (`sp_diagnosa_anak/settings.py`)

- `SEKOLAH` — nama, alamat, telepon, email sekolah (tampil di kontak, footer, dan PDF).
  **Lengkapi telepon dan email sekolah.**
- `WAJIB_LOGIN` — `True` (disarankan) atau `False` untuk demo tanpa login.
- `TIME_ZONE = 'Asia/Jayapura'`, `LANGUAGE_CODE = 'id'`.
- Untuk dipasang di server: set environment `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=...`,
  `DJANGO_ALLOWED_HOSTS=nama-domain`, lalu `python manage.py collectstatic`.

## 6. Struktur penting

```
expert/
  inference.py      mesin forward chaining (aturan R, K, S + jejak)
  statistik.py      perhitungan statistik sekolah & per anak
  engine.py         penghubung basis data -> mesin inferensi
  rules.py          basis pengetahuan & rekomendasi bawaan
  laporan.py        pembuatan PDF
  ekspor.py         ekspor Excel
  usia.py           perhitungan usia
  views.py, forms.py, models.py, admin.py, urls.py
  templates/expert/ halaman aplikasi
  tests.py, tests_logika.py   pengujian
templates/          main.html (tata letak), index.html, login
static/css/app.css, static/js/grafik.js
```

> Catatan: hasil sistem pakar ini adalah alat bantu pengamatan guru, bukan diagnosis medis.
