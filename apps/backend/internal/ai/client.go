// Package ai calls the frozen PURE V3 inference service.
package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const (
	ModelName          = "pure-v3-ensemble"
	ExpectedSamples    = 300
	ExpectedSamplingHz = 30.0
	ExpectedWindowSecs = 10.0
)

// Client calls the AI service over HTTP.
type Client struct {
	baseURL string
	http    *http.Client
}

type BranchProbabilities struct {
	Waveform float64 `json:"waveform"`
	STFT     float64 `json:"stft"`
	SQI      float64 `json:"sqi"`
}

// Result is the response returned by POST /v1/signal-quality.
type Result struct {
	DeviceID               string              `json:"device_id"`
	ModelVersion           string              `json:"model_version"`
	QualityScore           int                 `json:"quality_score"`
	GoodQualityProbability float64             `json:"good_quality_probability"`
	Status                 string              `json:"status"`
	DisplayBPM             bool                `json:"display_bpm"`
	HeartRateBPM           *float64            `json:"heart_rate_bpm"`
	RecommendedAction      string              `json:"recommended_action"`
	BranchProbabilities    BranchProbabilities `json:"branch_probabilities"`
	ProcessingMS           float64             `json:"processing_ms"`
}

type predictRequest struct {
	DeviceID       string    `json:"device_id"`
	SamplingRateHz float64   `json:"sampling_rate_hz"`
	PPG            []float64 `json:"ppg"`
	CandidateBPM   *float64  `json:"candidate_bpm,omitempty"`
}

// NewClient creates a client with a timeout for each request.
func NewClient(baseURL string, timeout time.Duration) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: timeout},
	}
}

// Predict sends one 10-second, 30 Hz window to the frozen V3 model.
func (c *Client) Predict(ctx context.Context, deviceID string, samples []float64, candidateBPM *float64) (Result, error) {
	if len(samples) != ExpectedSamples {
		return Result{}, fmt.Errorf("AI request requires %d samples, got %d", ExpectedSamples, len(samples))
	}
	body, err := json.Marshal(predictRequest{
		DeviceID:       deviceID,
		SamplingRateHz: ExpectedSamplingHz,
		PPG:            samples,
		CandidateBPM:   candidateBPM,
	})
	if err != nil {
		return Result{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/v1/signal-quality", bytes.NewReader(body))
	if err != nil {
		return Result{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return Result{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		msg, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return Result{}, fmt.Errorf("AI service responded with HTTP %d: %s", resp.StatusCode, msg)
	}

	var out Result
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return Result{}, fmt.Errorf("invalid response from AI service: %w", err)
	}
	if out.ModelVersion == "" || out.QualityScore < 0 || out.QualityScore > 100 {
		return Result{}, fmt.Errorf("AI service returned an invalid result")
	}
	return out, nil
}
