package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"pulsesure/backend/internal/ai"
	"pulsesure/backend/internal/history"
	"pulsesure/backend/internal/model"
)

// Tests the AI path: "live" when the AI service is up, "simulated" when it is down.
func TestPredictLiveAndFallback(t *testing.T) {
	mdl, err := model.LoadDummy("../../models/dummy_model.json")
	if err != nil {
		t.Fatal(err)
	}
	x := make([]float64, 640)
	for i := range x {
		x[i] = 0.5
	}

	// 1. AI service is up: the result must be "live" and use the V3 model.
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/signal-quality" {
			t.Fatalf("unexpected AI path %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"device_id":                "demo-window-1-segment-1",
			"model_version":            "9",
			"quality_score":            90,
			"good_quality_probability": 0.9,
			"status":                   "reliable",
			"display_bpm":              true,
			"heart_rate_bpm":           nil,
			"recommended_action":       "Continue monitoring.",
			"branch_probabilities":     map[string]float64{"waveform": 0.9, "stft": 0.9, "sqi": 0.9},
			"processing_ms":            4.2,
		})
	}))
	defer ts.Close()

	s := &Server{mdl: mdl, repo: history.NewMemory(), aiClient: ai.NewClient(ts.URL, 2*time.Second)}
	rec, err := s.measure("demo", 1, 64, x)
	if err != nil || rec.InferenceType != "live" || rec.ModelName != ai.ModelName || rec.ModelVersion != "9" {
		t.Fatalf("expected live, got %+v (err=%v)", rec, err)
	}

	// 2. AI service is down: must fall back to the dummy model and still save the result.
	dead := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "boom", http.StatusInternalServerError)
	}))
	dead.Close()

	s2 := &Server{mdl: mdl, repo: history.NewMemory(), aiClient: ai.NewClient(dead.URL, 500*time.Millisecond)}
	rec2, err := s2.measure("demo", 2, 64, x)
	if err != nil || rec2.InferenceType != "simulated" {
		t.Fatalf("expected simulated (fallback), got %+v (err=%v)", rec2, err)
	}
}

func TestPredictSplitsThirtySecondWindow(t *testing.T) {
	mdl, err := model.LoadDummy("../../models/dummy_model.json")
	if err != nil {
		t.Fatal(err)
	}
	var calls atomic.Int32
	statuses := []string{"reliable", "caution", "reliable"}
	scores := []int{90, 40, 80}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		index := int(calls.Add(1)) - 1
		var body struct {
			SamplingRateHz float64   `json:"sampling_rate_hz"`
			PPG            []float64 `json:"ppg"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Fatal(err)
		}
		if body.SamplingRateHz != 30 || len(body.PPG) != 300 {
			t.Fatalf("unexpected model input: fs=%v samples=%d", body.SamplingRateHz, len(body.PPG))
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"device_id":                "demo",
			"model_version":            "v3-test",
			"quality_score":            scores[index],
			"good_quality_probability": float64(scores[index]) / 100,
			"status":                   statuses[index],
			"display_bpm":              statuses[index] == "reliable",
			"recommended_action":       "Reacquire the signal.",
			"branch_probabilities":     map[string]float64{"waveform": 0.5, "stft": 0.5, "sqi": 0.5},
			"processing_ms":            1,
		})
	}))
	defer ts.Close()

	x := make([]float64, 1920)
	s := &Server{mdl: mdl, repo: history.NewMemory(), aiClient: ai.NewClient(ts.URL, 2*time.Second)}
	rec, err := s.measure("demo", 1, 64, x)
	if err != nil {
		t.Fatal(err)
	}
	if calls.Load() != 3 || rec.Status != "CAUTION" || rec.QualityScore != 70 {
		t.Fatalf("unexpected aggregate: calls=%d record=%+v", calls.Load(), rec)
	}
	if len(rec.Intervals) != 1 || rec.Intervals[0].StartS != 10 || rec.Intervals[0].EndS != 20 {
		t.Fatalf("unexpected intervals: %+v", rec.Intervals)
	}
	if !rec.HRWithheld || rec.ArtifactDuration != 10 || rec.ArtifactRatio != 33.3 {
		t.Fatalf("unexpected quality gate: %+v", rec)
	}
}
