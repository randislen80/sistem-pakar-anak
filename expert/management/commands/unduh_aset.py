"""
Mengunduh Bootstrap, Bootstrap Icons, dan Chart.js ke folder static/vendor
agar aplikasi tetap tampil lengkap tanpa koneksi internet (misalnya saat
presentasi/sidang skripsi atau dipakai di sekolah dengan internet terbatas).

Jalankan sekali saat komputer terhubung ke internet:
    python manage.py unduh_aset
"""

import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

CDN = "https://cdn.jsdelivr.net/npm/"
DAFTAR = [
    ("bootstrap@5.3.3/dist/css/bootstrap.min.css", "bootstrap.min.css"),
    ("bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js", "bootstrap.bundle.min.js"),
    ("bootstrap-icons@1.11.3/font/bootstrap-icons.min.css", "bootstrap-icons.min.css"),
    ("bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2", "fonts/bootstrap-icons.woff2"),
    ("bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff", "fonts/bootstrap-icons.woff"),
    ("chart.js@4.4.1/dist/chart.umd.js", "chart.umd.js"),
]


class Command(BaseCommand):
    help = "Unduh aset tampilan (Bootstrap, ikon, Chart.js) ke static/vendor untuk mode offline."

    def handle(self, *args, **options):
        folder = settings.BASE_DIR / "static" / "vendor"
        (folder / "fonts").mkdir(parents=True, exist_ok=True)
        for sumber, tujuan in DAFTAR:
            url = CDN + sumber
            self.stdout.write(f"Mengunduh {url}")
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    (folder / tujuan).write_bytes(resp.read())
            except OSError as exc:
                raise CommandError(f"Gagal mengunduh {url}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(
            f"Selesai. Aset tersimpan di {folder}. Aplikasi kini memakai file lokal secara otomatis."))
