import type { ApiRecord, ApiStatus } from "./api"

export type Reliability = "Reliable" | "Caution" | "Unreliable"

// Bentuk yang dipakai komponen tampilan. Semua nilainya berasal dari backend.
export type Scenario = {
  label: string
  score: number
  reliability: Reliability
  usable: number
  artifact: number
  durationS: number
  cause: string
  decision: string
  recommendation: string
  intervals: [number, number][]
  hrBpm: number | null
  withheld: boolean
  simulated: boolean
}

export type Assessment = {
  id: number
  window: number
  reviewed: boolean
  time: string
  previousId: number | null
  scenario: Scenario
}

const RELIABILITY: Record<ApiStatus, Reliability> = {
  RELIABLE: "Reliable",
  CAUTION: "Caution",
  UNRELIABLE: "Unreliable",
}

export function toScenario(r: ApiRecord): Scenario {
  return {
    label: `Window ${r.window_id + 1}`,
    score: r.quality_score,
    reliability: RELIABILITY[r.status],
    usable: r.usable_signal,
    artifact: r.artifact_ratio,
    durationS: r.artifact_duration_seconds,
    cause: r.cause || "No significant interference detected",
    decision: r.decision,
    recommendation: r.recommendation,
    intervals: r.artifact_intervals.map(
      (iv): [number, number] => [iv.start_s, iv.end_s],
    ),
    hrBpm: r.hr_bpm,
    withheld: r.hr_withheld,
    simulated: r.inference_type === "simulated",
  }
}

export function toAssessment(r: ApiRecord): Assessment {
  return {
    id: r.id,
    window: r.window_id,
    reviewed: false,
    previousId: null,
    time: new Date(r.created_at).toLocaleTimeString("en-GB", { hour12: false }),
    scenario: toScenario(r),
  }
}