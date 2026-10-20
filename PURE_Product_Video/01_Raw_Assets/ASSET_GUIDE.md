# Panduan Aset PURE Product Video

Panduan ini berlaku untuk aset yang masuk ke `01_Raw_Assets/`. Jangan mengubah atau menghapus sumber asli; buat versi baru saat aset direvisi dan catat setiap aset di `../asset_manifest.csv`.

## Aset yang perlu disiapkan

- **Brand:** logo utama dan alternatif, palet warna, serta font beserta bukti lisensi.
- **PPG:** waveform bersih dan berartefak, preview visual, anotasi artefak, output model AI, dan skor kualitas/reliabilitas.
- **Dashboard:** tangkapan layar untuk status `not_assessed`, `reliable`, `caution`, dan `unreliable`; keadaan BPM ditampilkan atau ditahan; corrective guidance; screen recording; serta user flow.
- **Hardware:** foto atau render MAX30102, ESP32-C3, MPU6050, wearable prototype, dan rekaman sensor yang relevan.
- **Architecture:** diagram alur perangkat, pemrosesan sinyal, AI, dan dashboard.
- **Icons:** ikon sensor, konektivitas, AI, kualitas/reliabilitas, dashboard, dan tindakan korektif.
- **Audio:** voice-over final dan take alternatif, musik latar, serta sound effects.
- **Sources dan licenses:** referensi klaim, atribusi, bukti lisensi, izin, dan ketentuan penggunaan.
- **Disclaimer:** teks batasan produk dan pernyataan bahwa tampilan atau hasil bukan pengganti diagnosis medis, sesuai keputusan tim produk/legal.

## Format file yang diterima

| Jenis aset | Format utama | Format tambahan/catatan |
| --- | --- | --- |
| Logo, ikon, diagram | `.svg` | `.png` transparan untuk fallback; hindari teks yang belum diubah menjadi path jika font tidak ikut tersedia. |
| Palet warna | `.json`, `.ase` | Sertakan nilai HEX/RGB dalam dokumen `.md` bila perlu. |
| Font | `.woff2` | `.woff`, `.ttf`, atau `.otf`; wajib disertai informasi lisensi. |
| Waveform dan data sensor | `.csv`, `.json` | Cantumkan sampling rate, unit, timestamp, label, dan definisi field. |
| Screenshot dan gambar | `.png` | `.jpg` untuk foto tanpa transparansi; gunakan kualitas tinggi. |
| Video/screen recording | `.mp4` (H.264) | Frame rate konstan 30 fps; `.mov` ProRes dapat dipakai sebagai master bila tersedia. |
| Voice-over dan sound effects | `.wav` | PCM 48 kHz, 24-bit disarankan; `.mp3` hanya untuk preview. |
| Musik | `.wav` | PCM 48 kHz, 24-bit disarankan; sertakan lisensi dan versi instrumental jika ada. |
| Dokumen sumber/lisensi | `.pdf`, `.md`, `.txt` | Simpan URL, penulis/penerbit, tanggal akses, dan batas penggunaan. |

Untuk CSV, gunakan UTF-8, baris header, delimiter koma, dan titik sebagai pemisah desimal. Untuk JSON, gunakan UTF-8 dan nama field yang konsisten.

## Spesifikasi resolusi

- Target video utama: **1920 × 1080 px (16:9)** pada **30 fps**.
- Screenshot dashboard: minimal **1920 × 1080 px** atau resolusi native perangkat; jangan melakukan upscale.
- Preview waveform, diagram, dan raster overlay: **1920 × 1080 px**; gunakan latar transparan bila akan ditumpuk di komposisi.
- Foto atau render hardware: sisi terpanjang minimal **3000 px**, fokus tajam, dan ruang kosong cukup untuk cropping.
- Logo dan ikon: utamakan SVG; fallback PNG minimal **1024 px** pada sisi terpanjang dan transparan.
- Screen recording: **1920 × 1080 px**, 30 fps konstan, tanpa notifikasi atau data pribadi.
- Color space gambar/video: **sRGB / Rec.709** agar hasil konsisten saat render.

## Aturan penamaan file

Gunakan format berikut:

```text
category_asset-status_version.ext
```

Aturannya:

1. Gunakan huruf kecil ASCII tanpa spasi.
2. Pisahkan bagian utama dengan underscore (`_`) dan kata di dalam bagian dengan hyphen (`-`).
3. Gunakan kategori folder, misalnya `brand`, `ppg`, `dashboard`, `hardware`, `architecture`, `icons`, atau `audio`.
4. Gunakan status `draft`, `review`, atau `approved`.
5. Gunakan versi berurutan `v1`, `v2`, dan seterusnya; jangan memakai kata `final`, `latest`, atau tanggal sebagai pengganti versi.
6. Pertahankan ekstensi asli yang paling sesuai dan buat file baru jika status atau versi berubah.

Contoh:

```text
brand_pure-logo_approved_v1.svg
ppg_heavy-artifact_draft_v1.json
hardware_max30102-render_approved_v1.png
dashboard_unreliable_approved_v1.png
```

Sebelum aset dipindahkan ke `02_Approved_Assets/`, pastikan status pada nama file dan `asset_manifest.csv` sudah `approved`, sumber atau lisensi tercatat, dan tidak ada data pribadi/sensitif yang tertinggal.
