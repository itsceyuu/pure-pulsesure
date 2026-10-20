package model

import (
	"math"
	"testing"
)

func modelUji() *DummyModel {
	return &DummyModel{
		ModelName: "dummy-artifact", ModelVersion: "0.1", Fs: 64,
		BaseProb: 0.05, HighProb: 0.95, SpikeStep: 0.8, FlatEps: 0.0001,
		FlatMinSamples: 32, SpikeMargin: 16, ProbThreshold: 0.5,
	}
}

func sinyalBersih(n int) []float64 {
	x := make([]float64, n)
	for i := range x {
		ph := math.Mod(float64(i)/64*72/60, 1)
		x[i] = math.Exp(-math.Pow(ph-0.2, 2)/0.005) + math.Sin(float64(i)*12.9898)*0.01
	}
	return x
}

func TestBersihTanpaArtefak(t *testing.T) {
	m := modelUji()
	ints := Intervals(m.Predict(sinyalBersih(1920)), 64, 0.5, 0.2)
	if len(ints) != 0 {
		t.Fatalf("sinyal bersih tidak boleh punya artefak, dapat %v", ints)
	}
}

func TestLonjakanMenjadiInterval(t *testing.T) {
	m := modelUji()
	x := sinyalBersih(1920)
	x[640] += 2.5
	ints := Intervals(m.Predict(x), 64, 0.5, 0.2)
	if len(ints) == 0 {
		t.Fatal("lonjakan harus menghasilkan interval artefak")
	}
	if ints[0].StartS > 10.1 || ints[0].EndS < 10.0 {
		t.Fatalf("interval %+v tidak mencakup detik 10", ints[0])
	}
}

func TestBagianDatarMenjadiInterval(t *testing.T) {
	m := modelUji()
	x := sinyalBersih(1920)
	for i := 320; i < 960; i++ {
		x[i] = x[319]
	}
	ints := Intervals(m.Predict(x), 64, 0.5, 0.2)
	if len(ints) == 0 {
		t.Fatal("bagian datar harus menghasilkan interval artefak")
	}
}