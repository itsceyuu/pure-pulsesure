// Package dsp berisi pemrosesan sinyal sederhana.
package dsp

import "math"

// Features adalah ciri sinyal mentah yang dipakai untuk menentukan penyebab artefak.
type Features struct {
	Std       float64 // simpangan baku amplitudo
	MaxStep   float64 // selisih antar-sampel terbesar (spike atau gerakan)
	FlatRatio float64 // proporsi sampel yang hampir tidak berubah (kontak sensor buruk)
}

// Normalize mengubah sinyal menjadi skor z.
func Normalize(x []float64) []float64 {
	out := make([]float64, len(x))
	if len(x) == 0 {
		return out
	}
	var mean float64
	for _, v := range x {
		mean += v
	}
	mean /= float64(len(x))

	var ss float64
	for _, v := range x {
		d := v - mean
		ss += d * d
	}
	std := math.Sqrt(ss / float64(len(x)))
	if std == 0 {
		return out
	}
	for i, v := range x {
		out[i] = (v - mean) / std
	}
	return out
}

// ExtractFeatures menghitung ciri kualitas dari sinyal mentah.
func ExtractFeatures(x []float64) Features {
	n := len(x)
	if n < 2 {
		return Features{}
	}
	var mean float64
	for _, v := range x {
		mean += v
	}
	mean /= float64(n)

	var ss float64
	for _, v := range x {
		d := v - mean
		ss += d * d
	}
	f := Features{Std: math.Sqrt(ss / float64(n))}

	flat := 0
	for i := 1; i < n; i++ {
		d := math.Abs(x[i] - x[i-1])
		if d > f.MaxStep {
			f.MaxStep = d
		}
		if d < 1e-4 {
			flat++
		}
	}
	f.FlatRatio = float64(flat) / float64(n-1)
	return f
}

// EstimateHR menghitung detak per menit dari puncak sinyal.
// Mengembalikan false jika puncak yang ditemukan kurang dari dua.
func EstimateHR(x []float64, fs float64) (float64, bool) {
	if fs <= 0 || len(x) < int(fs) {
		return 0, false
	}
	z := Normalize(x)
	refractory := int(0.3 * fs) // jarak minimum antar-detak: 0,3 detik
	peaks := 0
	last := -refractory
	for i := 1; i < len(z)-1; i++ {
		if z[i] > 0.5 && z[i] >= z[i-1] && z[i] > z[i+1] && i-last >= refractory {
			peaks++
			last = i
		}
	}
	durasi := float64(len(x)) / fs
	bpm := float64(peaks) / durasi * 60
	return math.Round(bpm*10) / 10, peaks >= 2
}