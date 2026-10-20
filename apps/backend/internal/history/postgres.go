package history

import (
	"database/sql"
	"encoding/json"
	"fmt"

	_ "github.com/jackc/pgx/v5/stdlib" // driver PostgreSQL
)

const schema = `
CREATE TABLE IF NOT EXISTS measurements (
    id                BIGSERIAL PRIMARY KEY,
    session_id        TEXT NOT NULL,
    window_id         INT NOT NULL,
    quality_score     INT NOT NULL,
    status            TEXT NOT NULL,
    decision          TEXT NOT NULL,
    usable_pct        DOUBLE PRECISION NOT NULL,
    artifact_ratio    DOUBLE PRECISION NOT NULL,
    artifact_duration DOUBLE PRECISION NOT NULL,
    intervals         JSONB NOT NULL,
    hr_bpm            DOUBLE PRECISION NULL,
    hr_withheld       BOOLEAN NOT NULL,
    cause             TEXT NOT NULL,
    recommendation    TEXT NOT NULL,
    model_name        TEXT NOT NULL,
    model_version     TEXT NOT NULL,
    inference_type    TEXT NOT NULL,
	motion_detected   BOOLEAN NOT NULL DEFAULT FALSE,
	accel_std_g       DOUBLE PRECISION NOT NULL DEFAULT 0,
	gyro_rms_dps      DOUBLE PRECISION NOT NULL DEFAULT 0,
	accel_peak_delta_g DOUBLE PRECISION NOT NULL DEFAULT 0,
	motion_fraction   DOUBLE PRECISION NOT NULL DEFAULT 0,
    latency_ms        DOUBLE PRECISION NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS motion_detected BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS accel_std_g DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS gyro_rms_dps DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS accel_peak_delta_g DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS motion_fraction DOUBLE PRECISION NOT NULL DEFAULT 0;`

type Postgres struct {
	db *sql.DB
}

// OpenPostgres membuka koneksi dan membuat tabel jika belum ada.
func OpenPostgres(dsn string) (*Postgres, error) {
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("tidak bisa terhubung ke database (sudah jalankan docker compose up -d?): %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		return nil, fmt.Errorf("gagal membuat tabel: %w", err)
	}
	return &Postgres{db: db}, nil
}

func (p *Postgres) Save(r *Record) error {
	ivs, err := json.Marshal(r.Intervals)
	if err != nil {
		return err
	}
	var hr sql.NullFloat64
	if r.HRBpm != nil {
		hr = sql.NullFloat64{Float64: *r.HRBpm, Valid: true}
	}
	return p.db.QueryRow(`
		INSERT INTO measurements (session_id, window_id, quality_score, status, decision,
			usable_pct, artifact_ratio, artifact_duration, intervals, hr_bpm, hr_withheld,
			cause, recommendation, model_name, model_version, inference_type, motion_detected,
			accel_std_g, gyro_rms_dps, accel_peak_delta_g, motion_fraction, latency_ms)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22)
		RETURNING id, created_at`,
		r.SessionID, r.WindowID, r.QualityScore, r.Status, r.Decision,
		r.UsablePct, r.ArtifactRatio, r.ArtifactDuration, string(ivs), hr, r.HRWithheld,
		r.Cause, r.Recommendation, r.ModelName, r.ModelVersion, r.InferenceType,
		r.MotionDetected, r.AccelStdG, r.GyroRMSDPS, r.AccelPeakDeltaG, r.MotionFraction, r.LatencyMs,
	).Scan(&r.ID, &r.CreatedAt)
}

func (p *Postgres) List(sessionID string, limit int) ([]Record, error) {
	rows, err := p.db.Query(`
		SELECT id, session_id, window_id, quality_score, status, decision,
			usable_pct, artifact_ratio, artifact_duration, intervals, hr_bpm, hr_withheld,
			cause, recommendation, model_name, model_version, inference_type, motion_detected,
			accel_std_g, gyro_rms_dps, accel_peak_delta_g, motion_fraction, latency_ms, created_at
		FROM measurements
		WHERE ($1 = '' OR session_id = $1)
		ORDER BY id DESC
		LIMIT $2`, sessionID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := []Record{}
	for rows.Next() {
		var r Record
		var ivs []byte
		var hr sql.NullFloat64
		if err := rows.Scan(&r.ID, &r.SessionID, &r.WindowID, &r.QualityScore, &r.Status, &r.Decision,
			&r.UsablePct, &r.ArtifactRatio, &r.ArtifactDuration, &ivs, &hr, &r.HRWithheld,
			&r.Cause, &r.Recommendation, &r.ModelName, &r.ModelVersion, &r.InferenceType,
			&r.MotionDetected, &r.AccelStdG, &r.GyroRMSDPS, &r.AccelPeakDeltaG, &r.MotionFraction,
			&r.LatencyMs, &r.CreatedAt); err != nil {
			return nil, err
		}
		if hr.Valid {
			v := hr.Float64
			r.HRBpm = &v
		}
		if err := json.Unmarshal(ivs, &r.Intervals); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}
