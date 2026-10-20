// Package history menyimpan hasil pengukuran. Ada dua implementasi:
// Memory (untuk tes) dan Postgres (untuk pemakaian biasa).
package history

import (
	"sync"
	"time"

	"pulsesure/backend/internal/model"
)

// Record adalah satu hasil pengukuran (satu window).
type Record struct {
	ID               int64            `json:"id"`
	SessionID        string           `json:"session_id"`
	WindowID         int              `json:"window_id"`
	QualityScore     int              `json:"quality_score"`
	Status           string           `json:"status"`
	Decision         string           `json:"decision"`
	UsablePct        float64          `json:"usable_signal"`
	ArtifactRatio    float64          `json:"artifact_ratio"`
	ArtifactDuration float64          `json:"artifact_duration_seconds"`
	Intervals        []model.Interval `json:"artifact_intervals"`
	HRBpm            *float64         `json:"hr_bpm"`
	HRWithheld       bool             `json:"hr_withheld"`
	Cause            string           `json:"cause"`
	Recommendation   string           `json:"recommendation"`
	ModelName        string           `json:"model_name"`
	ModelVersion     string           `json:"model_version"`
	InferenceType    string           `json:"inference_type"`
	LatencyMs        float64          `json:"latency_ms"`
	CreatedAt        time.Time        `json:"created_at"`
}

// Repo adalah kontrak penyimpanan riwayat.
type Repo interface {
	Save(r *Record) error
	List(sessionID string, limit int) ([]Record, error)
}

// Memory menyimpan riwayat di RAM. Hilang saat server berhenti.
type Memory struct {
	mu    sync.Mutex
	items []Record
	next  int64
}

func NewMemory() *Memory {
	return &Memory{}
}

func (m *Memory) Save(r *Record) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.next++
	r.ID = m.next
	m.items = append(m.items, *r)
	return nil
}

func (m *Memory) List(sessionID string, limit int) ([]Record, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := []Record{}
	for i := len(m.items) - 1; i >= 0 && len(out) < limit; i-- {
		if sessionID == "" || m.items[i].SessionID == sessionID {
			out = append(out, m.items[i])
		}
	}
	return out, nil
}