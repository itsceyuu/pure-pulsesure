package dsp

import (
	"math"
	"testing"
)

func pulsa(n int, fs, bpm float64) []float64 {
	x := make([]float64, n)
	for i := range x {
		ph := math.Mod(float64(i)/fs*bpm/60, 1)
		x[i] = math.Exp(-math.Pow(ph-0.2, 2)/0.005) + math.Sin(float64(i)*12.9898)*0.01
	}
	return x
}

func TestEstimateHRSekitar72(t *testing.T) {
	hr, ok := EstimateHR(pulsa(1920, 64, 72), 64)
	if !ok {
		t.Fatal("HR tidak terdeteksi")
	}
	if math.Abs(hr-72) > 6 {
		t.Fatalf("HR = %.1f, seharusnya dekat 72", hr)
	}
}

func TestFlatRatioSinyalDatar(t *testing.T) {
	f := ExtractFeatures(make([]float64, 100))
	if f.FlatRatio != 1 {
		t.Fatalf("FlatRatio = %v, harus 1", f.FlatRatio)
	}
}