package quality

import (
	"testing"

	"pulsesure/backend/internal/model"
)

func TestStatusBatas(t *testing.T) {
	cases := []struct {
		skor int
		want string
	}{
		{100, Reliable}, {80, Reliable},
		{79, Caution}, {50, Caution},
		{49, Unreliable}, {0, Unreliable},
	}
	for _, c := range cases {
		got, _ := status(c.skor)
		if got != c.want {
			t.Errorf("status(%d) = %s, harus %s", c.skor, got, c.want)
		}
	}
}

func TestAssessSkorDariProbabilitas(t *testing.T) {
	x := make([]float64, 100)
	prob := make([]float64, 100)
	for i := 0; i < 15; i++ {
		prob[i] = 0.9 // 15 sampel artefak, 85 bersih
	}
	a := Assess(x, prob, 0.5, []model.Interval{{StartS: 0, EndS: 0.2}})
	if a.QualityScore != 85 || a.Status != Reliable {
		t.Fatalf("skor = %d status = %s, must 85 RELIABLE", a.QualityScore, a.Status)
	}
}

func TestDecisionSesuaiStatus(t *testing.T) {
	if Decision(Reliable) != "MEASUREMENT RELIABLE" {
		t.Fatal("decision RELIABLE wrong")
	}
	if Decision(Unreliable) != "MEASUREMENT UNRELIABLE" {
		t.Fatal("decision UNRELIABLE wrong")
	}
}