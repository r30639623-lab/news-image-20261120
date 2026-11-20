#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Penyalin setia gambar berita 20 November — "satu gambar, seribu kabar, nol ubahan".

Skrip mungil ini hanya melakukan satu pekerjaan, dan melakukannya dengan
jujur: mengambil news.png yang sudah jadi di samping skrip ini, memeriksa
keasliannya sebentar, lalu menyalinnya mentah-mentah ke /output/entry.png.
Tidak ada piksel yang disentuh, tidak ada byte yang digeser, tidak ada
jaringan yang dibuka. Yang masuk, itulah yang keluar — seperti kurir yang
tidak pernah membuka paketnya.
"""

import struct
import sys
from pathlib import Path

# --- Tetapan yang sengaja ditulis terang-terangan di atas meja ---
NAMA_BERKAS_GAMBAR = "news.png"
FOLDER_KELUARAN = Path("/output")
NAMA_KELUARAN = "entry.png"
BATAS_BESAR_BYTE = 1_048_576  # 1 MiB, sesuai pagar harness program/v1
LEBAR_WAJIB = 1024
TINGGI_WAJIB = 1024
TANDA_TANGAN_PNG = b"\x89PNG\r\n\x1a\n"
KODE_IHDR = b"IHDR"


def mengeluh_lalu_mundur(pesan: str, kode: int = 1) -> "int":
    """Cetak keluhan ke stderr, lalu kembalikan kode keluar yang gagal."""
    print(f"main.py: GALAT — {pesan}", file=sys.stderr)
    return kode


def periksa_cap_png(data_mentah: bytes) -> str | None:
    """Periksa cap PNG + kotak IHDR; kembalikan pesan galat, atau None bila lolos."""
    if len(data_mentah) < 8:
        return "berkas terlalu pendek, bahkan cap PNG-nya tidak muat"
    if data_mentah[:8] != TANDA_TANGAN_PNG:
        return "8 byte pertama bukan tanda tangan PNG yang sah"
    if len(data_mentah) < 24:
        return "berkas terpotong sebelum kotak IHDR selesai dibaca"
    panjang_kotak = struct.unpack(">I", data_mentah[8:12])[0]
    if data_mentah[12:16] != KODE_IHDR:
        return "kotak pertama bukan IHDR, jadi ini bukan PNG yang wajar"
    if panjang_kotak < 13:
        return "kotak IHDR terlalu pendek untuk menyimpan lebar dan tinggi"
    lebar, tinggi = struct.unpack(">II", data_mentah[16:24])
    if lebar != LEBAR_WAJIB or tinggi != TINGGI_WAJIB:
        return (
            f"ukuran gambar {lebar}x{tinggi}, padahal harness meminta "
            f"{LEBAR_WAJIB}x{TINGGI_WAJIB}"
        )
    return None


def jalankan() -> int:
    """Titik masuk: baca, periksa, salin apa adanya, laporkan."""
    folder_sini = Path(__file__).resolve().parent
    jalan_masuk = folder_sini / NAMA_BERKAS_GAMBAR

    if not jalan_masuk.is_file():
        return mengeluh_lalu_mundur(f"tidak menemukan {jalan_masuk}")

    try:
        data_mentah = jalan_masuk.read_bytes()
    except OSError as salah:
        return mengeluh_lalu_mundur(f"tidak bisa membaca {jalan_masuk}: {salah}")

    if len(data_mentah) > BATAS_BESAR_BYTE:
        return mengeluh_lalu_mundur(
            f"ukuran {len(data_mentah)} byte melewati batas {BATAS_BESAR_BYTE} byte"
        )

    cacat = periksa_cap_png(data_mentah)
    if cacat is not None:
        return mengeluh_lalu_mundur(cacat)

    try:
        FOLDER_KELUARAN.mkdir(parents=True, exist_ok=True)
        jalan_keluar = FOLDER_KELUARAN / NAMA_KELUARAN
        jalan_keluar.write_bytes(data_mentah)
    except OSError as salah:
        return mengeluh_lalu_mundur(f"tidak bisa menulis {jalan_keluar}: {salah}")

    print(
        f"main.py: BERHASIL — menyalin {len(data_mentah)} byte "
        f"({LEBAR_WAJIB}x{TINGGI_WAJIB}) dari {jalan_masuk} ke {jalan_keluar} "
        f"tanpa satu byte pun diubah."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(jalankan())
