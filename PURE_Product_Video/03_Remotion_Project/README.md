# PURE Product Video V0.3 — Refined V0.2 Visual Direction

V0.3 final mempertahankan gaya, scene, dan animasi V0.2 yang dipilih pengguna. Seluruh label internal produksi telah dihapus sehingga video tampil sebagai presentasi final, bukan animatic atau pre-deployment review.

Komposisi `PUREExplainer` berukuran 1920×1080, 30 fps, 3300 frame, dan berdurasi 110 detik. Video sengaja tidak memiliki audio stream karena voice-over dan musik akan ditambahkan pengguna saat external editing.

## Perubahan final

- Mengembalikan sembilan scene programmatic dari V0.2.
- Menghapus badge `ANIMATIC V0.2`, `PRE-DEPLOYMENT REVIEW`, dan `NO AUDIO`.
- Menghapus teks internal seperti `placeholder`, `review asset`, dan catatan development lain dari layar.
- Menggunakan SVG simbol resmi yang diberikan pengguna pada opening dan sebagai brand mark di kanan atas setiap scene (`public/brand/brand_pure-logo-symbol_approved_v1.svg`).
- Memperbaiki kontras teks yang sebelumnya mewarisi warna terlalu gelap.
- Mempertahankan Reliable, Caution, Unreliable, quality score, BPM gate, dan corrective guidance karena semuanya merupakan bagian dari produk.
- Mempertahankan label `SIMULATED DATA` untuk membedakan demonstrasi dari data pasien nyata.
- Memperjelas AI pipeline sebagai preprocessing → artifact context → model benchmarking → quality state.

## Timeline

| Scene | Time |
| --- | ---: |
| Team Introduction | 0:00–0:05 |
| Problem Statement | 0:05–0:13 |
| Problem Understanding | 0:13–0:25 |
| Proposed Solution | 0:25–0:37 |
| Innovation | 0:37–0:47 |
| AI Approach | 0:47–1:01 |
| Proposed Prototype Implementation | 1:01–1:23 |
| Dashboard Demo | 1:23–1:38 |
| Impact & Closing | 1:38–1:50 |

## Menjalankan proyek

```bash
npm run qa:assets
npm run typecheck
npm run dev
npm run render
```

Output utama:

- `../05_Final_Delivery/master_video/PUREExplainer-v0.3-final-silent.mp4`
- `../05_Final_Delivery/compressed_video/PUREExplainer-v0.3-final-silent-compressed.mp4`

## Audio

- Tidak ada komponen audio di composition.
- Kedua MP4 hanya memiliki satu H.264 video stream.
- Tambahkan voice-over, musik, dan SFX di editor pilihan dengan timeline 30 fps tanpa mengubah durasi awal.
- Subtitle/cue bahasa Inggris siap diimpor ke CapCut dari `../05_Final_Delivery/subtitles/PUREExplainer-voiceover-en.srt`.

## Batasan

PURE tetap diposisikan sebagai measurement-reliability support system dan bukan alat diagnosis. Data pada demonstrasi dashboard bersifat sintetis. Tidak ada deployment, upload, atau publikasi eksternal yang dilakukan oleh proses render ini.
