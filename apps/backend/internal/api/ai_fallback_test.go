package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
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

	// 1. AI service is up: the result must be "live" and use the AI model name.
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{
			"prob":          make([]float64, len(x)),
			"model_name":    "fake-ai",
			"model_version": "9",
		})
	}))
	defer ts.Close()

	s := &Server{mdl: mdl, repo: history.NewMemory(), aiClient: ai.NewClient(ts.URL, 2*time.Second)}
	rec, err := s.measure("demo", 1, 64, x)
	if err != nil || rec.InferenceType != "live" || rec.ModelName != "fake-ai" {
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
