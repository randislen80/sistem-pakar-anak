"""Fungsi bantu perhitungan usia anak (Python murni)."""

from __future__ import annotations

import re
from datetime import date


def hitung_usia_bulan(tanggal_lahir: date | None, pada: date | None) -> int | None:
    """Usia dalam bulan penuh pada tanggal tertentu."""
    if not tanggal_lahir or not pada:
        return None
    bulan = (pada.year - tanggal_lahir.year) * 12 + (pada.month - tanggal_lahir.month)
    if pada.day < tanggal_lahir.day:
        bulan -= 1
    return max(bulan, 0)


def teks_usia(bulan: int | None) -> str:
    """48 -> '4 tahun', 51 -> '4 tahun 3 bulan'."""
    if bulan is None:
        return ""
    tahun, sisa = divmod(int(bulan), 12)
    if tahun and sisa:
        return f"{tahun} tahun {sisa} bulan"
    if tahun:
        return f"{tahun} tahun"
    return f"{sisa} bulan"


def baca_usia_teks(teks: str | None) -> int | None:
    """Membaca isian usia bebas versi lama ('4', '4 tahun', '4,5') menjadi bulan."""
    if not teks:
        return None
    cocok = re.search(r"\d+(?:[.,]\d+)?", str(teks))
    if not cocok:
        return None
    angka = float(cocok.group(0).replace(",", "."))
    if "bulan" in str(teks).lower() and "tahun" not in str(teks).lower():
        return int(round(angka))
    return int(round(angka * 12))


def kelompok_dari_usia(bulan: int | None) -> str:
    """Saran kelompok TK: A untuk 4-5 tahun, B untuk 5-6 tahun."""
    if bulan is None:
        return ""
    if bulan < 60:
        return "A"
    return "B"
