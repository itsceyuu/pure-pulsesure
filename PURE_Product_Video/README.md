# PURE Product Video

Workspace ini menampung proses produksi video explainer produk PURE dengan Remotion, mulai dari perencanaan hingga paket final. Struktur folder memisahkan aset mentah, aset yang telah disetujui, sumber proyek Remotion, hasil review, dan hasil akhir agar status setiap berkas mudah ditelusuri.

## Fungsi folder utama

| Folder | Fungsi |
| --- | --- |
| `00_Project_Planning/` | Storyboard, naskah voice-over, referensi teknis dan eksternal, serta catatan review. |
| `01_Raw_Assets/` | Semua aset sumber yang belum disetujui. Simpan versi asli dan informasi sumber/lisensinya di sini. |
| `02_Approved_Assets/` | Salinan aset yang telah lolos review dan siap dipakai dalam produksi. |
| `03_Remotion_Project/` | Area proyek Remotion: aset publik, rencana source code, dan output render lokal. Belum berisi implementasi React/TypeScript. |
| `04_Review_Exports/` | Preview scene, video draft, umpan balik, dan preview yang sudah disetujui. |
| `05_Final_Delivery/` | Master video, versi terkompresi, caption, thumbnail, dan dokumen penyerahan. |

## Alur aset

1. Masukkan materi asli ke `01_Raw_Assets/` dan catat di `asset_manifest.csv`.
2. Review kualitas, hak penggunaan, dan kesesuaian teknis aset.
3. Salin aset yang disetujui ke kategori yang sesuai di `02_Approved_Assets/`.
4. Salin hanya aset produksi yang diperlukan ke `03_Remotion_Project/public/`.
5. Simpan hasil review di `04_Review_Exports/` dan hasil final di `05_Final_Delivery/`.

Gunakan aturan nama `category_asset-status_version.ext`. Detail format, resolusi, dan penamaan tersedia di `01_Raw_Assets/ASSET_GUIDE.md`.
