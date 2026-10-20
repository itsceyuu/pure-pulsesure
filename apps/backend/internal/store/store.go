// Package store membaca data sesi dari folder data.
package store

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
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

type Store struct {
	sessions map[string]Session
}

// NewFromSessions dipakai di tes.
func NewFromSessions(list ...Session) *Store {
	st := &Store{sessions: map[string]Session{}}
	for _, s := range list {
		st.sessions[s.ID] = s
	}
	return st
}

// Load membaca semua file session_*.json di folder dir.
func Load(dir string) (*Store, error) {
	files, err := filepath.Glob(filepath.Join(dir, "session_*.json"))
	if err != nil {
		return nil, err
	}
	st := &Store{sessions: map[string]Session{}}
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			return nil, err
		}
		var s Session
		if err := json.Unmarshal(b, &s); err != nil {
			return nil, fmt.Errorf("%s: %w", f, err)
		}
		st.sessions[s.ID] = s
	}
	return st, nil
}

func (s *Store) List() []string {
	ids := make([]string, 0, len(s.sessions))
	for id := range s.sessions {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func (s *Store) Get(id string) (Session, bool) {
	v, ok := s.sessions[id]
	return v, ok
}