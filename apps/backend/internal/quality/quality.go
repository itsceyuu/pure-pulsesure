// Package quality berisi quality gate: skor, status, keputusan, dan rekomendasi.
package quality

import (
	"math"

	"pulsesure/backend/internal/dsp"
	"pulsesure/backend/internal/model"
)

const (
	Reliable   = "RELIABLE"
	Caution    = "CAUTION"
	Unreliable = "UNRELIABLE"
)

// Assessment adalah hasil penilaian satu window.
type Assessment struct {
	QualityScore     int
	Status           string
	UsablePct        float64
	ArtifactRatio    float64
	ArtifactDuration float64
	Cause            string
	Recommendation   string
}

// Assess menilai satu window berdasarkan probabilitas artefak.
func Assess(x, prob []float64, thr float64, ints []model.Interval) Assessment {
	n := len(x)
	if n == 0 || len(prob) != n {
		return Assessment{
			Status:         Unreliable,
			Cause:          "invalid signal data",
			Recommendation: "Repeat the measurement.",
		}
	}

	bad := 0
	for _, p := range prob {
		if p >= thr {
			bad++
		}
	}
	usable := float64(n-bad) / float64(n) * 100
	score := int(math.Floor(usable))

	dur := 0.0
	for _, iv := range ints {
		dur += iv.EndS - iv.StartS
	}

	st, rekom := status(score)
	return Assessment{
		QualityScore:     score,
		Status:           st,
		UsablePct:        round1(usable),
		ArtifactRatio:    round1(100 - usable),
		ArtifactDuration: round1(dur),
		Cause:            cause(dsp.ExtractFeatures(x), bad),
		Recommendation:   rekom,
	}
}

// status memetakan skor ke status dan rekomendasi.
func status(score int) (string, string) {
	switch {
	case score >= 80:
		return Reliable, "Heart rate results are suitable for use."
	case score >= 50:
		return Caution, "Results are displayed with a warning. Keep your hand still and adjust the sensor position."
	default:
		return Unreliable, "Keep your wrist still, adjust the sensor position, and repeat the measurement."
	}
}

// cause memperkirakan penyebab artefak dari ciri sinyal.
func cause(f dsp.Features, bad int) string {
	if bad == 0 {
		return ""
	}
	if f.FlatRatio > 0.1 {
		return "Poor sensor contact (flat signal)"
	}
	return "Motion detected (signal spikes)"
}

// Decision adalah keputusan yang ditampilkan ke pengguna.
func Decision(st string) string {
	switch st {
	case Reliable:
		return "MEASUREMENT RELIABLE"
	case Caution:
		return "MEASUREMENT CAUTION"
	default:
		return "MEASUREMENT UNRELIABLE"
	}
}

func round1(x float64) float64 {
	return math.Round(x*10) / 10
}