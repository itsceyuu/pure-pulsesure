// Package ai calls the Python inference service (FastAPI) that returns an
// artifact probability for every signal sample. Contract: POST /predict.
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

// Client calls the AI service over HTTP.
type Client struct {
	baseURL string
	http    *http.Client
}

// Result is the response returned by the AI service.
type Result struct {
	Prob         []float64 `json:"prob"`
	ModelName    string    `json:"model_name"`
	ModelVersion string    `json:"model_version"`
}

type predictRequest struct {
	Fs      float64   `json:"fs"`
	Samples []float64 `json:"samples"`
}

// NewClient creates a client with a timeout for each request.
func NewClient(baseURL string, timeout time.Duration) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: timeout},
	}
}

// Predict sends one signal window and returns the artifact probabilities.
func (c *Client) Predict(ctx context.Context, x []float64, fs float64) (Result, error) {
	body, err := json.Marshal(predictRequest{Fs: fs, Samples: x})
	if err != nil {
		return Result{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/predict", bytes.NewReader(body))
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
		msg, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		return Result{}, fmt.Errorf("AI service responded with HTTP %d: %s", resp.StatusCode, msg)
	}

	var out Result
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return Result{}, fmt.Errorf("invalid response from AI service: %w", err)
	}
	return out, nil
}
