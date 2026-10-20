# Dataset Information

PURE uses the Brno University of Technology Smartphone PPG Database (BUT PPG)
version 2.0.0 for the signal-quality baseline.

- Source: https://physionet.org/content/butppg/2.0.0/
- License: Creative Commons Attribution 4.0 International
- Content: 3,888 ten-second PPG recordings from 50 subjects
- Sampling rate: 30 Hz for PPG
- Labels: record-level binary quality and reference heart rate
- Additional signals: reference ECG for all records and ACC for later records

Raw and processed measurement files are intentionally excluded from Git. Place
the downloaded dataset at:

```text
data/raw/but-ppg-2.0.0/
```

Then run:

```bash
python3 scripts/prepare_but_ppg.py
```

For the waveform model, run:

```bash
python3 scripts/prepare_but_ppg_waveforms.py
```

This V2 export selects `PPG_R` for RGB records because the dataset's quality
annotations were created from the red channel. It writes three aligned model
views per record: robust-scaled raw PPG, a zero-phase 0.5-5 Hz Butterworth
band-pass signal, and the normalized first derivative.

The preparation script creates subject-disjoint train, validation, and test
splits. The first three digits of each record ID identify the subject, so
records from one person never appear in more than one split.

## Important limitations

The quality annotation is binary and covers a complete recording. It is not a
sample-level artifact mask. PURE's three user-facing states will therefore be
defined later from two validation-set thresholds around the model probability:

- Reliable: high confidence that the signal is usable;
- Caution: uncertain intermediate region;
- Unreliable: high confidence that the signal is unsuitable.

These thresholds are prototype decisions and are not clinical standards.
The database was acquired through smartphone cameras; it is not a substitute
for validation using the proposed MAX30102 hardware.

## Required attribution

Nemcova, A., Smisek, R., Vargova, E., Marsanova, L., Vitek, M., Smital, L.,
Filipenska, M., Sikorova, P., and Galik, P. (2024). Brno University of
Technology Smartphone PPG Database (version 2.0.0). PhysioNet.
https://doi.org/10.13026/tn53-8153
