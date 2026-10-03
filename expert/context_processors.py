from django.conf import settings
from django.utils import timezone

FILE_ASET = ["bootstrap.min.css", "bootstrap.bundle.min.js", "bootstrap-icons.min.css", "chart.umd.js"]


def _aset_lokal_tersedia():
    """True jika file Bootstrap & Chart.js sudah diunduh ke static/vendor (mode offline)."""
    folder = settings.BASE_DIR / "static" / "vendor"
    return all((folder / f).exists() for f in FILE_ASET)


def sekolah(request):
    """Data yang tersedia di semua template: identitas sekolah dan tahun berjalan."""
    return {
        "sekolah": getattr(settings, "SEKOLAH", {}),
        "year": timezone.localdate().year,
        "wajib_login": getattr(settings, "WAJIB_LOGIN", True),
        "aset_lokal": _aset_lokal_tersedia(),
    }
