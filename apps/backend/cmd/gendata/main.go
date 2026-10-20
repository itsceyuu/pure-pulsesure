// Program gendata membuat data sesi dummy 30 detik untuk PulseSure Edge.
package main

import (
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"os"
)

const (
	fs      = 64.0
	panjang = 1920 // 30 detik x 64 Hz
	jumlah  = 10
)

type Window struct {
	ID       int       `json:"window_id"`
	StartMs  int       `json:"start_ms"`
	Samples  []float64 `json:"samples"`
	Scenario string    `json:"scenario"`
}

type Session struct {
	ID      string   `json:"id"`
	Fs      float64  `json:"fs"`
	Windows []Window `json:"windows"`
}

// ppg membuat bentuk gelombang PPG sederhana: satu puncak per siklus detak.
func ppg(t, bpm float64) float64 {
	ph := math.Mod(t*bpm/60, 1)
	return math.Exp(-math.Pow(ph-0.2, 2) / 0.005)
}

func bulat(x float64) float64 {
	return math.Round(x*1000) / 1000
}

func main() {
	rng := rand.New(rand.NewSource(7)) // seed tetap supaya hasil selalu sama
	s := Session{ID: "demo", Fs: fs}

	for w := 0; w < jumlah; w++ {
		bpm := 66 + rng.Float64()*12
		x := make([]float64, panjang)
		for i := range x {
			x[i] = ppg(float64(i)/fs, bpm) + rng.NormFloat64()*0.02
		}

		scenario := "clean"
		switch w {
		case 3:
			scenario = "heavy-motion"
			for i := 6 * 64; i < 26*64; i++ {
				x[i] += rng.NormFloat64() * 0.6
			}
		case 4:
			scenario = "poor-contact"
			for i := 5 * 64; i < 25*64; i++ {
				x[i] = x[5*64-1]
			}
		case 5:
			scenario = "weak-contact"
			for i := 15 * 64; i < 25*64; i++ {
				x[i] = x[15*64-1]
			}
		case 8:
			scenario = "brief-motion"
			for _, idx := range []int{10 * 64, 20 * 64} {
				x[idx] += 2.5
			}
		}

		for i := range x {
			x[i] = bulat(x[i])
		}
		s.Windows = append(s.Windows, Window{
			ID:       w,
			StartMs:  w * 30000,
			Samples:  x,
			Scenario: scenario,
		})
	}

	if err := os.MkdirAll("data", 0o755); err != nil {
		panic(err)
	}
	b, err := json.Marshal(s)
	if err != nil {
		panic(err)
	}
	if err := os.WriteFile("data/session_demo.json", b, 0o644); err != nil {
		panic(err)
	}
	fmt.Printf("Selesai: data/session_demo.json (%d window x 30 detik)\n", len(s.Windows))
}