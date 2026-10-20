package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"strconv"
	"strings"
	"time"

	"pulsesure/backend/internal/ai"
	"pulsesure/backend/internal/dsp"
	"pulsesure/backend/internal/history"
	"pulsesure/backend/internal/model"
	"pulsesure/backend/internal/quality"
	"pulsesure/backend/internal/store"
)

const (
	minWindowSeconds = 10.0
	maxBodyBytes     = 4 << 20
	maxLimit         = 200
	motionAccelStdG  = 0.05
	motionGyroRMSDPS = 12.0
	severeAccelStdG  = 0.15
	severeGyroRMSDPS = 45.0
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
	SessionID string         `json:"session_id"`
	WindowID  int            `json:"window_id"`
	Fs        float64        `json:"fs"`
	Samples   []float64      `json:"samples"`
	Source    string         `json:"source"` // "replay" atau "sensor"
	SensorOK  bool           `json:"sensor_ok"`
	Motion    *MotionPayload `json:"motion,omitempty"`
}

// MotionPayload is a compact summary calculated from raw MPU6050 samples.
// Acceleration uses g and angular velocity uses degrees per second.
type MotionPayload struct {
	Available       bool    `json:"available"`
	SampleRateHz    float64 `json:"sample_rate_hz"`
	Samples         int     `json:"samples"`
	AccelStdG       float64 `json:"accel_std_g"`
	GyroRMSDPS      float64 `json:"gyro_rms_dps"`
	AccelPeakDeltaG float64 `json:"accel_peak_delta_g"`
	MotionFraction  float64 `json:"motion_fraction"`
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
	modelName := s.mdl.ModelName
	inferenceType := "simulated"
	if s.aiClient != nil {
		modelName = ai.ModelName
		inferenceType = "live"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":         "ok",
		"model":          modelName,
		"inference_type": inferenceType,
		"sessions":       len(s.store.List()),
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
	if err := validateMotion(p.Motion); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
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
	minSamples := int(math.Ceil(p.Fs * minWindowSeconds))
	if len(p.Samples) < minSamples {
		writeErr(w, http.StatusBadRequest, fmt.Sprintf("durasi sinyal kurang dari %.0f detik", minWindowSeconds))
		return
	}

	rec, err := s.measureWithMotion(p.SessionID, p.WindowID, p.Fs, p.Samples, p.Motion)
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

// measure menjalankan model V3 jika tersedia, lalu kembali ke dummy model jika
// service AI gagal. Hasil selalu disimpan satu kali setelah penilaian selesai.
func (s *Server) measure(sessionID string, windowID int, fs float64, x []float64) (history.Record, error) {
	return s.measureWithMotion(sessionID, windowID, fs, x, nil)
}

func (s *Server) measureWithMotion(sessionID string, windowID int, fs float64, x []float64, motion *MotionPayload) (history.Record, error) {
	mulai := time.Now()

	var rec history.Record
	if s.aiClient != nil {
		live, err := s.assessWithAI(sessionID, windowID, fs, x)
		if err == nil {
			rec = live
		} else {
			log.Printf("AI service failed, using dummy model: %v", err)
		}
	}
	if rec.InferenceType == "" {
		prob := s.mdl.Predict(x)
		ints := model.Intervals(prob, fs, s.mdl.ProbThreshold, 0.2)
		a := quality.Assess(x, prob, s.mdl.ProbThreshold, ints)
		rec = history.Record{
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
			ModelName:        s.mdl.ModelName,
			ModelVersion:     s.mdl.ModelVersion,
			InferenceType:    "simulated",
		}
		if a.Status == quality.Unreliable {
			rec.HRWithheld = true
		} else if bpm, ok := dsp.EstimateHR(x, fs); ok {
			rec.HRBpm = &bpm
		}
	}

	applyMotionGate(&rec, motion)
	rec.LatencyMs = round2(float64(time.Since(mulai).Microseconds()) / 1000)
	rec.CreatedAt = time.Now()
	if err := s.repo.Save(&rec); err != nil {
		return history.Record{}, err
	}
	return rec, nil
}

func validateMotion(m *MotionPayload) error {
	if m == nil || !m.Available {
		return nil
	}
	values := []float64{m.SampleRateHz, m.AccelStdG, m.GyroRMSDPS, m.AccelPeakDeltaG, m.MotionFraction}
	for _, value := range values {
		if math.IsNaN(value) || math.IsInf(value, 0) || value < 0 {
			return fmt.Errorf("ringkasan MPU6050 tidak valid")
		}
	}
	if m.SampleRateHz <= 0 || m.Samples <= 0 || m.MotionFraction > 1 {
		return fmt.Errorf("ringkasan MPU6050 tidak valid")
	}
	return nil
}

// applyMotionGate combines the optical model result with independent motion
// evidence from the MPU6050. The thresholds are prototype quality gates.
func applyMotionGate(rec *history.Record, m *MotionPayload) {
	if m == nil || !m.Available {
		return
	}
	rec.AccelStdG = round3(m.AccelStdG)
	rec.GyroRMSDPS = round2(m.GyroRMSDPS)
	rec.AccelPeakDeltaG = round3(m.AccelPeakDeltaG)
	rec.MotionFraction = round3(m.MotionFraction)

	motionDetected := m.AccelStdG >= motionAccelStdG ||
		m.GyroRMSDPS >= motionGyroRMSDPS || m.MotionFraction >= 0.10
	severeMotion := m.AccelStdG >= severeAccelStdG ||
		m.GyroRMSDPS >= severeGyroRMSDPS || m.MotionFraction >= 0.35 ||
		m.AccelPeakDeltaG >= 0.50
	rec.MotionDetected = motionDetected
	if !motionDetected {
		return
	}

	rec.Cause = "Motion detected by MPU6050 during the measurement."
	if severeMotion {
		rec.Status = quality.Unreliable
		rec.QualityScore = min(rec.QualityScore, 49)
		rec.Recommendation = "Keep your wrist still, adjust the sensor, and repeat the measurement."
	} else if rec.Status == quality.Reliable {
		rec.Status = quality.Caution
		rec.QualityScore = min(rec.QualityScore, 79)
		rec.Recommendation = "Keep your wrist still and repeat the measurement if motion continues."
	}
	rec.Decision = quality.Decision(rec.Status)
	rec.HRBpm = nil
	rec.HRWithheld = true
}

// assessWithAI adapts arbitrary sensor sampling rates to the model's fixed
// 10-second, 300-sample contract. Longer windows are evaluated per 10 seconds.
func (s *Server) assessWithAI(sessionID string, windowID int, fs float64, x []float64) (history.Record, error) {
	segmentSamples := int(math.Round(fs * ai.ExpectedWindowSecs))
	if fs <= 0 || segmentSamples < 2 || len(x) < segmentSamples {
		return history.Record{}, fmt.Errorf("AI model requires at least %.0f seconds of signal", ai.ExpectedWindowSecs)
	}
	segmentCount := len(x) / segmentSamples
	if len(x) != segmentCount*segmentSamples {
		return history.Record{}, fmt.Errorf("signal duration must be a multiple of %.0f seconds", ai.ExpectedWindowSecs)
	}

	status := quality.Reliable
	worstRank := 0
	allDisplayBPM := true
	scoreTotal := 0
	modelVersion := ""
	recommendation := "Display BPM and continue monitoring."
	intervals := []model.Interval{}

	for i := 0; i < segmentCount; i++ {
		start := i * segmentSamples
		segment := x[start : start+segmentSamples]
		resampled := resampleLinear(segment, ai.ExpectedSamples)

		var candidateBPM *float64
		if bpm, ok := dsp.EstimateHR(segment, fs); ok && bpm >= 30 && bpm <= 240 {
			candidateBPM = &bpm
		}
		deviceID := fmt.Sprintf("%s-window-%d-segment-%d", sessionID, windowID, i+1)
		result, err := s.aiClient.Predict(context.Background(), deviceID, resampled, candidateBPM)
		if err != nil {
			return history.Record{}, err
		}
		segmentStatus, rank, err := normalizeAIStatus(result.Status)
		if err != nil {
			return history.Record{}, err
		}
		if modelVersion != "" && modelVersion != result.ModelVersion {
			return history.Record{}, fmt.Errorf("AI model version changed during one measurement")
		}
		modelVersion = result.ModelVersion
		scoreTotal += result.QualityScore
		allDisplayBPM = allDisplayBPM && result.DisplayBPM
		if rank > worstRank {
			worstRank = rank
			status = segmentStatus
			recommendation = result.RecommendedAction
		}
		if segmentStatus != quality.Reliable {
			startS := float64(i) * ai.ExpectedWindowSecs
			intervals = append(intervals, model.Interval{
				StartS: startS,
				EndS:   startS + ai.ExpectedWindowSecs,
			})
		}
	}

	totalDuration := float64(segmentCount) * ai.ExpectedWindowSecs
	artifactDuration := float64(len(intervals)) * ai.ExpectedWindowSecs
	artifactRatio := artifactDuration / totalDuration * 100
	rec := history.Record{
		SessionID:        sessionID,
		WindowID:         windowID,
		QualityScore:     int(math.Round(float64(scoreTotal) / float64(segmentCount))),
		Status:           status,
		Decision:         quality.Decision(status),
		UsablePct:        round1(100 - artifactRatio),
		ArtifactRatio:    round1(artifactRatio),
		ArtifactDuration: round1(artifactDuration),
		Intervals:        intervals,
		Recommendation:   recommendation,
		ModelName:        ai.ModelName,
		ModelVersion:     modelVersion,
		InferenceType:    "live",
		HRWithheld:       true,
	}
	if status != quality.Reliable {
		rec.Cause = "Signal quality was below the model threshold in one or more 10-second segments."
	}
	if allDisplayBPM && status == quality.Reliable {
		if bpm, ok := dsp.EstimateHR(x, fs); ok {
			rec.HRBpm = &bpm
			rec.HRWithheld = false
		}
	}
	return rec, nil
}

func normalizeAIStatus(value string) (string, int, error) {
	switch strings.ToLower(value) {
	case "reliable":
		return quality.Reliable, 0, nil
	case "caution":
		return quality.Caution, 1, nil
	case "unreliable":
		return quality.Unreliable, 2, nil
	default:
		return "", 0, fmt.Errorf("AI service returned unknown status %q", value)
	}
}

// resampleLinear preserves the signal duration while converting a window to
// the model's 30 Hz grid. Sample j represents time j/30 seconds.
func resampleLinear(x []float64, outputLength int) []float64 {
	out := make([]float64, outputLength)
	if len(x) == 0 || outputLength == 0 {
		return out
	}
	if len(x) == 1 {
		for i := range out {
			out[i] = x[0]
		}
		return out
	}
	scale := float64(len(x)) / float64(outputLength)
	for i := range out {
		position := float64(i) * scale
		left := int(math.Floor(position))
		if left >= len(x)-1 {
			out[i] = x[len(x)-1]
			continue
		}
		fraction := position - float64(left)
		out[i] = x[left]*(1-fraction) + x[left+1]*fraction
	}
	return out
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

func round3(x float64) float64 {
	return math.Round(x*1000) / 1000
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
