"""
Basis pengetahuan awal (data bawaan).

Data ini dimasukkan ke basis data secara otomatis oleh migrasi
0006_data_awal saat `python manage.py migrate` dijalankan pada basis data
yang masih kosong. Setelah itu, basis pengetahuan dikelola lewat halaman
Admin (menu Domain perkembangan, Indikator, dan Rekomendasi) sehingga pakar
dapat menambah atau mengubah indikator tanpa mengubah kode program.

Aturan (rule) forward chaining dibangkitkan otomatis dari data ini oleh
modul expert/inference.py.
"""

from .inference import SESUAI

# Urutan domain juga menentukan kode D01..D06 dan kode indikator G01..G18.
KNOWLEDGE_BASE = {
    "Motorik Halus": [
        "Dapat menyusun menara dari 6-8 kubus",
        "Dapat mengancingkan baju sendiri",
        "Dapat memegang pensil dengan benar (3 jari)",
    ],
    "Motorik Kasar": [
        "Dapat melompat dengan dua kaki",
        "Dapat menangkap bola dengan kedua tangan",
        "Dapat naik turun tangga tanpa bantuan",
    ],
    "Bahasa": [
        "Dapat menyebutkan nama lengkap sendiri",
        "Dapat mengucapkan kalimat dengan 4-6 kata",
        "Dapat menyanyikan lagu anak-anak sederhana",
    ],
    "Kognitif": [
        "Dapat menyebutkan 4 warna utama",
        "Dapat menghitung benda hingga angka 5",
        "Dapat menyelesaikan puzzle 4-6 keping",
    ],
    "Sosial Emosional": [
        "Mau berbagi mainan dengan teman",
        "Dapat bermain bersama teman (kooperatif)",
        "Dapat mengungkapkan perasaan (sedih/senang) dengan kata-kata",
    ],
    "Kemandirian": [
        "Dapat membereskan mainan setelah bermain",
        "Dapat makan dan minum sendiri tanpa tumpah",
        "Dapat membersihkan diri (cuci tangan) dengan bantuan",
    ],
}

DESKRIPSI_DOMAIN = {
    "Motorik Halus": "Kemampuan menggunakan otot-otot kecil jari dan tangan serta koordinasi mata-tangan.",
    "Motorik Kasar": "Kemampuan menggunakan otot-otot besar untuk bergerak, melompat, dan menjaga keseimbangan.",
    "Bahasa": "Kemampuan memahami dan mengungkapkan bahasa secara lisan.",
    "Kognitif": "Kemampuan berpikir, mengenal konsep warna, bilangan, dan memecahkan masalah sederhana.",
    "Sosial Emosional": "Kemampuan berinteraksi dengan teman serta mengenali dan mengungkapkan perasaan.",
    "Kemandirian": "Kemampuan merawat diri dan melakukan kegiatan sehari-hari tanpa banyak bantuan.",
}

# Rekomendasi stimulasi. Status kosong ("") = berlaku untuk semua status yang
# belum Sesuai; status SESUAI = kegiatan pengayaan bagi anak yang sudah mampu.
REKOMENDASI_AWAL = {
    "Motorik Halus": [
        ("", "Ajak anak meremas dan membentuk plastisin/playdough 10-15 menit setiap hari untuk menguatkan otot jari."),
        ("", "Latih koordinasi jari lewat kegiatan meronce manik-manik besar, menjepit benda dengan jepitan baju, dan menyusun balok."),
        ("", "Biasakan memegang krayon atau pensil dengan tiga jari saat mewarnai dan menebalkan garis; beri contoh dan pujian."),
        ("", "Beri kesempatan mengancingkan baju sendiri setiap hari, dimulai dari kancing yang besar."),
        (SESUAI, "Pengayaan: menggunting mengikuti pola, melipat kertas (origami sederhana), dan menganyam kertas."),
    ],
    "Motorik Kasar": [
        ("", "Ajak anak bermain lompat dua kaki, misalnya melompat ke dalam lingkaran simpai atau engklek sederhana, 10-15 menit setiap hari."),
        ("", "Latih melempar dan menangkap bola besar yang lunak dari jarak dekat, lalu jauhkan jaraknya secara bertahap."),
        ("", "Latih naik-turun tangga sambil berpegangan, kemudian dengan pendampingan tanpa berpegangan di area yang aman."),
        (SESUAI, "Pengayaan: senam irama, berjalan di atas papan titian, dan permainan tradisional seperti lompat tali."),
    ],
    "Bahasa": [
        ("", "Bacakan buku cerita bergambar setiap hari dan ajak anak menceritakan kembali isi gambar dengan kata-katanya sendiri."),
        ("", "Ajak bercakap-cakap dengan pertanyaan terbuka (apa, siapa, mengapa) dan bantu anak melengkapi kalimatnya menjadi 4-6 kata."),
        ("", "Nyanyikan lagu anak-anak bersama sambil bergerak, dan latih anak menyebutkan nama lengkap serta nama orang tuanya."),
        (SESUAI, "Pengayaan: kegiatan bercerita di depan teman (show and tell), tebak kata, dan mengenal huruf awal nama benda."),
    ],
    "Kognitif": [
        ("", "Kenalkan warna dengan mengelompokkan benda sehari-hari (mainan, buah, balok) berdasarkan warnanya."),
        ("", "Ajak anak menghitung benda nyata (kancing, sendok, jari) sambil menunjuk satu per satu, dimulai dari 1 sampai 5."),
        ("", "Berikan puzzle sederhana 2-4 keping, lalu naikkan jumlah kepingnya secara bertahap."),
        (SESUAI, "Pengayaan: permainan pola (merah-biru-merah), mencocokkan bentuk geometri, dan membandingkan banyak-sedikit."),
    ],
    "Sosial Emosional": [
        ("", "Libatkan anak dalam permainan kelompok kecil yang mengharuskan bergiliran, misalnya estafet atau bermain peran."),
        ("", "Kenalkan nama-nama perasaan (senang, sedih, marah, takut) memakai gambar ekspresi wajah, lalu ajak anak menyebutkan perasaannya."),
        ("", "Beri pujian yang spesifik saat anak mau berbagi atau membantu teman, dan tunjukkan contoh perilaku berbagi."),
        (SESUAI, "Pengayaan: beri tanggung jawab kecil di kelas (membagikan alat, memimpin doa) dan kegiatan membuat karya bersama."),
    ],
    "Kemandirian": [
        ("", "Buat rutinitas membereskan mainan setelah bermain dengan lagu atau hitungan agar terasa menyenangkan."),
        ("", "Beri kesempatan makan dan minum sendiri dengan peralatan yang mudah dipegang; maklumi bila masih tumpah."),
        ("", "Tempel gambar urutan cuci tangan pakai sabun di dekat wastafel dan dampingi anak sampai terbiasa."),
        (SESUAI, "Pengayaan: libatkan anak menyiapkan tas sekolah sendiri, memakai sepatu, dan merapikan tempat makannya."),
    ],
}
