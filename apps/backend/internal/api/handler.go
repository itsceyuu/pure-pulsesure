package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"strconv"
	"time"

	"pulsesure/backend/internal/ai"
	"pulsesure/backend/internal/dsp"
	"pulsesure/backend/internal/history"
	"pulsesure/backend/internal/model"
	"pulsesure/backend/internal/quality"
	"pulsesure/backend/internal/store"
)

const (
	minSamples   = 640 // 10 detik pada 64 Hz
	maxBodyBytes = 4 << 20
	maxLimit     = 200
)

type Server struct {
	store    *store.Store
	mdl      *model.DummyModel
	repo     history.Repo
	origins  []string
	aiClient *ai.Client // nil = use the dummy model only
}

// MeasurementPayload: satu window dari sensor atau replay.
type MeasurementPayload struct {
	SessionID string    `json:"session_id"`
	WindowID  int       `json:"window_id"`
	Fs        float64   `json:"fs"`
	Samples   []float64 `json:"samples"`
	Source    string    `json:"source"` // "replay" atau "sensor"
	SensorOK  bool      `json:"sensor_ok"`
}

type Summary struct {
	Windows           int     `json:"windows"`
	Reliable          int     `json:"reliable"`
	Caution           int     `json:"caution"`
	Unreliable        int     `json:"unreliable"`
	HRWithheld        int     `json:"hr_withheld"`
	MonitoringSeconds float64 `json:"monitoring_seconds"`
	UsableSeconds     float64 `json:"usable_seconds"`
}

type AnalyzeResponse struct {
	SessionID string           `json:"session_id"`
	Summary   Summary          `json:"summary"`
	Windows   []history.Record `json:"windows"`
}

func NewServer(st *store.Store, mdl *model.DummyModel, repo history.Repo, origins []string) http.Handler {
	return NewServerWithAI(st, mdl, repo, origins, nil)
}

// NewServerWithAI is like NewServer, plus an optional AI service client (may be nil).
func NewServerWithAI(st *store.Store, mdl *model.DummyModel, repo history.Repo, origins []string, aiClient *ai.Client) http.Handler {
	s := &Server{store: st, mdl: mdl, repo: repo, origins: origins, aiClient: aiClient}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", s.health)
	mux.HandleFunc("GET /api/sessions", s.listSessions)
	mux.HandleFunc("GET /api/sessions/{id}", s.getSession)
	mux.HandleFunc("POST /api/sessions/{id}/analyze", s.analyzeSession)
	mux.HandleFunc("POST /api/measurements", s.postMeasurement)
	mux.HandleFunc("GET /api/history", s.getHistory)
	return s.withCORS(mux)
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"status":   "ok",
		"model":    s.mdl.ModelName,
		"sessions": len(s.store.List()),
	})
}

func (s *Server) listSessions(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.store.List())
}

func (s *Server) getSession(w http.ResponseWriter, r *http.Request) {
	sess, ok := s.store.Get(r.PathValue("id"))
	if !ok {
		writeErr(w, http.StatusNotFound, "sesi tidak ditemukan")
		return
	}
	writeJSON(w, http.StatusOK, sess)
}

// analyzeSession menilai semua window dalam satu sesi dan menyimpannya ke riwayat.
func (s *Server) analyzeSession(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	sess, ok := s.store.Get(id)
	if !ok {
		writeErr(w, http.StatusNotFound, "sesi tidak ditemukan")
		return
	}
	if len(sess.Windows) == 0 {
		writeErr(w, http.StatusBadRequest, "sesi tidak memiliki window")
		return
	}

	results := make([]history.Record, 0, len(sess.Windows))
	for _, win := range sess.Windows {
		rec, err := s.measure(id, win.ID, sess.Fs, win.Samples)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "gagal menyimpan hasil: "+err.Error())
			return
		}
		results = append(results, rec)
	}

	winSec := float64(len(sess.Windows[0].Samples)) / sess.Fs
	writeJSON(w, http.StatusOK, AnalyzeResponse{
		SessionID: id,
		Summary:   summarize(results, winSec),
		Windows:   results,
	})
}

// postMeasurement menilai satu window dari sensor atau replay.
func (s *Server) postMeasurement(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)

	var p MeasurementPayload
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		writeErr(w, http.StatusBadRequest, "JSON tidak valid")
		return
	}
	if p.SessionID == "" {
		writeErr(w, http.StatusBadRequest, "session_id wajib diisi")
		return
	}

	// Sensor gagal: pengukuran ditolak, tidak ada HR yang ditampilkan.
	if !p.SensorOK {
		rec := rejected(p.SessionID, p.WindowID, "sensor tidak mengirim data")
		if err := s.repo.Save(&rec); err != nil {
			writeErr(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, rec)
		return
	}

	if p.Fs <= 0 {
		writeErr(w, http.StatusBadRequest, "fs harus lebih dari 0")
		return
	}
	if len(p.Samples) < minSamples {
		writeErr(w, http.StatusBadRequest, "jumlah sampel kurang dari 640 (10 detik)")
		return
	}

	rec, err := s.measure(p.SessionID, p.WindowID, p.Fs, p.Samples)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "gagal menyimpan hasil: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, rec)
}

func (s *Server) getHistory(w http.ResponseWriter, r *http.Request) {
	sid := r.URL.Query().Get("session_id")
	limit, err := strconv.Atoi(r.URL.Query().Get("limit"))
	if err != nil || limit <= 0 {
		limit = 20
	}
	if limit > maxLimit {
		limit = maxLimit
	}
	recs, err := s.repo.List(sid, limit)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, recs)
}

// measure adalah alur utama: model -> interval -> quality gate -> HR (jika boleh) -> simpan.
func (s *Server) measure(sessionID string, windowID int, fs float64, x []float64) (history.Record, error) {
	mulai := time.Now()

	prob, modelName, modelVersion, jenis := s.predict(x, fs)
	ints := model.Intervals(prob, fs, s.mdl.ProbThreshold, 0.2)
	a := quality.Assess(x, prob, s.mdl.ProbThreshold, ints)

	rec := history.Record{
		SessionID:        sessionID,
		WindowID:         windowID,
		QualityScore:     a.QualityScore,
		Status:           a.Status,
		Decision:         quality.Decision(a.Status),
		UsablePct:        a.UsablePct,
		ArtifactRatio:    a.ArtifactRatio,
		ArtifactDuration: a.ArtifactDuration,
		Intervals:        ints,
		Cause:            a.Cause,
		Recommendation:   a.Recommendation,
		ModelName:        modelName,
		ModelVersion:     modelVersion,
		InferenceType:    jenis,
		LatencyMs:        round2(float64(time.Since(mulai).Microseconds()) / 1000),
		CreatedAt:        time.Now(),
	}

	// Quality gate: HR hanya ditampilkan jika sinyal tidak ditolak.
	if a.Status == quality.Unreliable {
		rec.HRWithheld = true
	} else if bpm, ok := dsp.EstimateHR(x, fs); ok {
		rec.HRBpm = &bpm
	}

	if err := s.repo.Save(&rec); err != nil {
		return history.Record{}, err
	}
	return rec, nil
}

// predict uses the AI service when available. If it fails, it falls back to the
// dummy model so the measurement is still recorded. Type "live" = real AI, "simulated" = dummy.
func (s *Server) predict(x []float64, fs float64) ([]float64, string, string, string) {
	if s.aiClient != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		res, err := s.aiClient.Predict(ctx, x, fs)
		if err == nil && len(res.Prob) != len(x) {
			err = fmt.Errorf("probability count %d does not match sample count %d", len(res.Prob), len(x))
		}
		if err == nil {
			return res.Prob, res.ModelName, res.ModelVersion, "live"
		}
		log.Printf("AI service failed, using dummy model: %v", err)
	}
	return s.mdl.Predict(x), s.mdl.ModelName, s.mdl.ModelVersion, "simulated"
}

// rejected membuat hasil untuk pengukuran yang tidak bisa dinilai.
func rejected(sessionID string, windowID int, penyebab string) history.Record {
	return history.Record{
		SessionID:      sessionID,
		WindowID:       windowID,
		QualityScore:   0,
		Status:         quality.Unreliable,
		Decision:       quality.Decision(quality.Unreliable),
		Intervals:      []model.Interval{},
		HRWithheld:     true,
		Cause:          penyebab,
		Recommendation: "Periksa kontak sensor, lalu ulangi pengukuran.",
		ModelName:      "-",
		ModelVersion:   "-",
		InferenceType:  "none",
		CreatedAt:      time.Now(),
	}
}

func summarize(rs []history.Record, winSec float64) Summary {
	var s Summary
	s.Windows = len(rs)
	for _, r := range rs {
		switch r.Status {
		case quality.Reliable:
			s.Reliable++
		case quality.Caution:
			s.Caution++
		default:
			s.Unreliable++
		}
		if r.HRWithheld {
			s.HRWithheld++
		}
		s.UsableSeconds += r.UsablePct / 100 * winSec
	}
	s.MonitoringSeconds = float64(len(rs)) * winSec
	s.UsableSeconds = round1(s.UsableSeconds)
	return s
}

func round1(x float64) float64 {
	return math.Round(x*10) / 10
}

func round2(x float64) float64 {
	return math.Round(x*100) / 100
}

func (s *Server) withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		for _, o := range s.origins {
			if origin != "" && origin == o {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			}
		}
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// writeErr memakai field "detail" supaya cocok dengan penanganan error di frontend.
func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"detail": msg})
}