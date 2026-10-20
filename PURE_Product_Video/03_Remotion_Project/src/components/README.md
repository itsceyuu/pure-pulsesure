# Rencana Komponen

Daftar komponen visual yang direncanakan untuk mendukung scene video PURE.

- **PpgWaveform** — Menggambar sinyal PPG dan mengatur animasi progres waveform.
- **ArtifactOverlay** — Menandai rentang sinyal yang mengandung artefak beserta jenis atau tingkat keparahannya.
- **QualityGauge** — Menampilkan quality score dengan skala dan state visual yang konsisten.
- **ReliabilityBadge** — Menampilkan status `not_assessed`, `reliable`, `caution`, atau `unreliable`.
- **BpmDisplay** — Menampilkan nilai BPM ketika layak atau state withheld ketika hasil tidak cukup andal.
- **CorrectiveGuidance** — Menyajikan tindakan korektif singkat, misalnya memperbaiki posisi sensor atau mengurangi gerakan.
- **ArchitectureFlow** — Memvisualisasikan alur hardware, pemrosesan sinyal, AI, dan dashboard.
- **SceneTitle** — Menyeragamkan judul, subjudul, dan transisi heading antar-scene.

Dokumen ini hanya mendefinisikan tanggung jawab awal. Implementasi React/TypeScript belum dibuat.
