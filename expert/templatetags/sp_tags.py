"""Filter template untuk menampilkan status, kesimpulan, dan angka."""

from django import template

from ..inference import KESIMPULAN_INFO, STATUS_INFO

register = template.Library()


@register.filter
def status_label(status):
    return STATUS_INFO.get(status, {}).get("label", status or "-")


@register.filter
def status_kelas(status):
    return STATUS_INFO.get(status, {}).get("kelas", "")


@register.filter
def status_ikon(status):
    return STATUS_INFO.get(status, {}).get("ikon", "bi-dot")


@register.filter
def kesimpulan_info(kunci):
    return KESIMPULAN_INFO.get(kunci, {})


@register.filter
def ambil(data, kunci):
    """{{ dict|ambil:kunci }} untuk membaca dict dengan kunci variabel."""
    try:
        return data.get(kunci)
    except AttributeError:
        try:
            return data[kunci]
        except (IndexError, KeyError, TypeError):
            return None


def _angka(nilai, desimal=1):
    teks = f"{float(nilai):.{desimal}f}"
    if "." in teks:
        teks = teks.rstrip("0").rstrip(".")
    return teks.replace(".", ",")


@register.filter
def persen(nilai):
    """66.7 -> '66,7%', 100.0 -> '100%', None -> '-'."""
    if nilai is None or nilai == "":
        return "-"
    try:
        return _angka(nilai) + "%"
    except (TypeError, ValueError):
        return "-"


@register.filter
def selisih(nilai):
    """Selisih poin persentase bertanda: 33.4 -> '+33,4', -5 -> '-5', 0 -> '0'."""
    if nilai is None or nilai == "":
        return ""
    try:
        v = float(nilai)
    except (TypeError, ValueError):
        return ""
    if v == 0:
        return "0"
    return ("+" if v > 0 else "−") + _angka(abs(v))


@register.filter
def arah(nilai):
    """'naik', 'turun', atau 'tetap' untuk pewarnaan selisih."""
    try:
        v = float(nilai)
    except (TypeError, ValueError):
        return ""
    return "naik" if v > 0 else "turun" if v < 0 else "tetap"
