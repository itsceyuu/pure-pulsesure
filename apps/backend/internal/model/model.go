// Package model berisi model dummy yang menghasilkan probabilitas artefak per sampel,
// serta post-processing untuk mengubahnya menjadi interval waktu.
package model

import (
	"encoding/json"
	"errors"
	"math"
	"os"
)

// Interval adalah rentang waktu artefak, dihitung dari awal window (detik).
type Interval struct {
	StartS float64 `json:"start_s"`
	EndS   float64 `json:"end_s"`
}

type DummyModel struct {
	ModelName      string  `json:"name"`
	ModelVersion   string  `json:"version"`
	Fs             float64 `json:"fs"`
	BaseProb       float64 `json:"base_prob"`
	HighProb       float64 `json:"high_prob"`
	SpikeStep      float64 `json:"spike_step"`
	FlatEps        float64 `json:"flat_eps"`
	FlatMinSamples int     `json:"flat_min_samples"`
	SpikeMargin    int     `json:"spike_margin"`
	ProbThreshold  float64 `json:"prob_threshold"`
}

// LoadDummy membaca konfigurasi model dari file JSON.
func LoadDummy(path string) (*DummyModel, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var m DummyModel
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	if m.Fs <= 0 || m.ProbThreshold <= 0 || m.ProbThreshold >= 1 {
		return nil, errors.New("konfigurasi model tidak valid (fs atau prob_threshold)")
	}
	return &m, nil
}

// Predict menghasilkan satu probabilitas artefak untuk setiap sampel.
// Aturan dummy: lonjakan besar dan bagian datar yang panjang dianggap artefak.
func (m *DummyModel) Predict(x []float64) []float64 {
	n := len(x)
	prob := make([]float64, n)
	for i := range prob {
		prob[i] = m.BaseProb
	}

	mark := func(a, b int) {
		for k := max(a, 0); k < min(b, n); k++ {
			prob[k] = m.HighProb
		}
	}

	// Lonjakan: selisih besar antar-sampel, beri margin di kiri dan kanan.
	for i := 1; i < n; i++ {
		if math.Abs(x[i]-x[i-1]) > m.SpikeStep {
			mark(i-m.SpikeMargin, i+m.SpikeMargin+1)
		}
	}

	// Datar: deretan selisih hampir nol yang cukup panjang.
	run := 0
	for i := 1; i < n; i++ {
		if math.Abs(x[i]-x[i-1]) < m.FlatEps {
			run++
			continue
		}
		if run >= m.FlatMinSamples {
			mark(i-run-1, i)
		}
		run = 0
	}
	if run >= m.FlatMinSamples {
		mark(n-run-1, n)
	}
	return prob
}

// Intervals mengubah probabilitas menjadi rentang waktu artefak.
// Rentang yang lebih pendek dari minSec dibuang.
func Intervals(prob []float64, fs, thr, minSec float64) []Interval {
	out := []Interval{}
	start := -1
	for i := 0; i <= len(prob); i++ {
		on := i < len(prob) && prob[i] >= thr
		if on && start < 0 {
			start = i
		}
		if !on && start >= 0 {
			s := float64(start) / fs
			e := float64(i) / fs
			if e-s >= minSec {
				out = append(out, Interval{StartS: roundTo(s, 100), EndS: roundTo(e, 100)})
			}
			start = -1
		}
	}
	return out
}

func roundTo(x, p float64) float64 {
	return math.Round(x*p) / p
}