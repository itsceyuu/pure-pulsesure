export type ApiStatus = "RELIABLE" | "CAUTION" | "UNRELIABLE"

export type ApiInterval = { start_s: number; end_s: number }

// Bentuk satu record dari backend (/api/measurements, /api/history).
export type ApiRecord = {
  id: number
  session_id: string
  window_id: number
  quality_score: number
  status: ApiStatus
  decision: string
  usable_signal: number
  artifact_ratio: number
  artifact_duration_seconds: number
  artifact_intervals: ApiInterval[]
  hr_bpm: number | null
  hr_withheld: boolean
  cause: string
  recommendation: string
  model_name: string
  model_version: string
  inference_type: "simulated" | "live" | "none"
  motion_detected: boolean
  accel_std_g: number
  gyro_rms_dps: number
  accel_peak_delta_g: number
  motion_fraction: number
  latency_ms: number
  created_at: string
}

export type ApiWindow = {
  window_id: number
  start_ms: number
  samples: number[]
}

export type ApiSession = {
  id: string
  fs: number
  windows: ApiWindow[]
}

export type MeasurementPayload = {
  session_id: string
  window_id: number
  fs: number
  samples: number[]
  source: "replay" | "sensor"
  sensor_ok: boolean
}

const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "")

async function panggil<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    throw new Error(body.detail || `Permintaan gagal (HTTP ${r.status})`)
  }
  return r.json() as Promise<T>
}

export const getSession = (id: string) =>
  panggil<ApiSession>(`/api/sessions/${id}`)

export const postMeasurement = (payload: MeasurementPayload) =>
  panggil<ApiRecord>("/api/measurements", {
    method: "POST",
    body: JSON.stringify(payload),
  })

export const getHistory = (sessionId: string, limit = 200) =>
  panggil<ApiRecord[]>(`/api/history?session_id=${sessionId}&limit=${limit}`)
