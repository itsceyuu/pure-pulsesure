package api

import (
	"bytes"
	"encoding/json"
	"math"
	"net/http"
	"net/http/httptest"
	"testing"

	"pulsesure/backend/internal/history"
	"pulsesure/backend/internal/model"
	"pulsesure/backend/internal/store"
)

func pulsaUji(n int) []float64 {
	x := make([]float64, n)
	for i := range x {
		ph := math.Mod(float64(i)/64*72/60, 1)
		x[i] = math.Exp(-math.Pow(ph-0.2, 2)/0.005) + math.Sin(float64(i)*12.9898)*0.01
	}
	return x
}

func serverUji(t *testing.T) http.Handler {
	t.Helper()
	spike := pulsaUji(1920)
	spike[640] += 2.5

	st := store.NewFromSessions(store.Session{
		ID: "t", Fs: 64,
		Windows: []store.Window{
			{ID: 0, Samples: pulsaUji(1920)},
			{ID: 1, Samples: spike},
		},
	})
	mdl := &model.DummyModel{
		ModelName: "dummy-artifact", ModelVersion: "0.1", Fs: 64,
		BaseProb: 0.05, HighProb: 0.95, SpikeStep: 0.8, FlatEps: 0.0001,
		FlatMinSamples: 32, SpikeMargin: 16, ProbThreshold: 0.5,
	}
	return NewServer(st, mdl, history.NewMemory(), []string{"http://localhost:5173"})
}

func kirim(h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	var buf bytes.Buffer
	if body != nil {
		_ = json.NewEncoder(&buf).Encode(body)
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	rec := kirim(serverUji(t), http.MethodGet, "/api/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestSensorGagalDitolak(t *testing.T) {
	body := map[string]any{
		"session_id": "t", "window_id": 5, "fs": 64,
		"samples": []float64{}, "source": "sensor", "sensor_ok": false,
	}
	rec := kirim(serverUji(t), http.MethodPost, "/api/measurements", body)
	var out history.Record
	_ = json.Unmarshal(rec.Body.Bytes(), &out)
	if out.Status != "UNRELIABLE" || !out.HRWithheld || out.HRBpm != nil {
		t.Fatalf("pengukuran sensor gagal harus ditolak, dapat %+v", out)
	}
}

func TestMPU6050MotionWithholdsHeartRate(t *testing.T) {
	body := map[string]any{
		"session_id": "t", "window_id": 6, "fs": 64,
		"samples": pulsaUji(640), "source": "sensor", "sensor_ok": true,
		"motion": map[string]any{
			"available": true, "sample_rate_hz": 100, "samples": 1000,
			"accel_std_g": 0.2, "gyro_rms_dps": 55.0,
			"accel_peak_delta_g": 0.7, "motion_fraction": 0.4,
		},
	}
	rec := kirim(serverUji(t), http.MethodPost, "/api/measurements", body)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var out history.Record
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if !out.MotionDetected || out.Status != "UNRELIABLE" || !out.HRWithheld || out.HRBpm != nil {
		t.Fatalf("strong MPU6050 motion must withhold HR, got %+v", out)
	}
	if out.AccelStdG != 0.2 || out.GyroRMSDPS != 55 || out.MotionFraction != 0.4 {
		t.Fatalf("motion metrics not preserved: %+v", out)
	}
}

func TestInvalidMPU6050SummaryRejected(t *testing.T) {
	body := map[string]any{
		"session_id": "t", "window_id": 7, "fs": 64,
		"samples": pulsaUji(640), "source": "sensor", "sensor_ok": true,
		"motion": map[string]any{
			"available": true, "sample_rate_hz": 100, "samples": 1000,
			"accel_std_g": 0.01, "gyro_rms_dps": 1.0,
			"accel_peak_delta_g": 0.02, "motion_fraction": 1.5,
		},
	}
	rec := kirim(serverUji(t), http.MethodPost, "/api/measurements", body)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
}

func TestAnalyzeMenyimpanRiwayat(t *testing.T) {
	h := serverUji(t)
	rec := kirim(h, http.MethodPost, "/api/sessions/t/analyze", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var out AnalyzeResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if out.Summary.Windows != 2 || out.Summary.Reliable != 2 {
		t.Fatalf("ringkasan tidak sesuai: %+v", out.Summary)
	}
	if out.Windows[0].HRBpm == nil {
		t.Fatal("window bersih harus menampilkan HR")
	}

	hist := kirim(h, http.MethodGet, "/api/history?session_id=t&limit=10", nil)
	var recs []history.Record
	_ = json.Unmarshal(hist.Body.Bytes(), &recs)
	if len(recs) != 2 {
		t.Fatalf("riwayat harus berisi 2 hasil, dapat %d", len(recs))
	}
}
