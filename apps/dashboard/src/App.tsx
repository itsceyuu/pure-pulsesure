import { useEffect, useRef, useState } from "react"
import {
  Activity,
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BedDouble,
  Check,
  CheckCheck,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Clock3,
  Heart,
  Info,
  LayoutDashboard,
  LoaderCircle,
  Microscope,
  Radio,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  ShieldQuestion,
  Signal,
  Sparkles,
  TriangleAlert,
  Unplug,
  UserRound,
  X,
} from "lucide-react"

import PPGWaveform from "./PPGWaveform"
import {
  getHistory,
  getSession,
  postMeasurement,
  type ApiSession,
} from "./api"
import {
  toAssessment,
  type Assessment,
  type Reliability,
} from "./scenarios"

function StatusIcon({
  status,
  size = 16,
}: {
  status?: Reliability
  size?: number
}) {
  return status === "Reliable" ? (
    <CircleCheck size={size} />
  ) : status === "Caution" ? (
    <CircleAlert size={size} />
  ) : status === "Unreliable" ? (
    <TriangleAlert size={size} />
  ) : (
    <ShieldQuestion size={size} />
  )
}
function Badge({ status }: { status?: Reliability }) {
  return (
    <span className={`badge ${status?.toLowerCase() ?? "neutral"}`}>
      <StatusIcon status={status} size={13} />
      {status ?? "Not assessed"}
    </span>
  )
}

const SESSION_ID = "demo"
// Enable once the ESP32 is sending data to the backend.
const LIVE_MODE = import.meta.env.VITE_LIVE_MODE === "true"

export default function App() {
  const [session, setSession] = useState<ApiSession | null>(null)
  const [records, setRecords] = useState<Assessment[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [windowIndex, setWindowIndex] = useState(0)
  const [overlay, setOverlay] = useState(true)
  const [connected, setConnected] = useState(true)
  const [loading, setLoading] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const [repeatPrevious, setRepeatPrevious] = useState<number | null>(null)
  const [notice, setNotice] = useState("")
  const [loadError, setLoadError] = useState("")
  const dialog = useRef<HTMLDialogElement>(null)
  const resetButton = useRef<HTMLButtonElement>(null)

  const active = records.find((r) => r.id === activeId)
  const result = active ? active.scenario : null
  const status: Reliability | undefined = result?.reliability
  const patientRecords = records
  const previous = records.find((r) => r.id === active?.previousId)
  const previousResult = previous ? previous.scenario : null
  const latestByWindow = Array.from({ length: 10 }, (_, i) =>
    [...records].reverse().find((r) => r.window === i),
  )
  const windowSamples = session?.windows[windowIndex]?.samples ?? null
  const fs = session?.fs ?? 64

  // Muat sesi dan riwayat dari backend saat halaman dibuka.
  useEffect(() => {
    let aktif = true
    Promise.all([getSession(SESSION_ID), getHistory(SESSION_ID)])
      .then(([sesi, riwayat]) => {
        if (!aktif) return
        setSession(sesi)
        // Backend mengirim terbaru di atas, sedangkan tampilan memakai urutan lama ke baru.
        setRecords([...riwayat].reverse().map(toAssessment))
      })
      .catch((e: Error) => {
        if (aktif) setLoadError(e.message)
      })
    return () => {
      aktif = false
    }
  }, [])

  useEffect(() => {
    if (resetOpen) dialog.current?.showModal()
    else if (dialog.current?.open) dialog.current.close()
  }, [resetOpen])

  function cancelAnalysis() {
    setLoading(false)
  }

  // Live mode: the ESP32 sends windows to the backend; this page reloads the history
  // every 2 seconds so sensor results appear without a manual refresh.
  useEffect(() => {
    if (!LIVE_MODE) return
    const timer = setInterval(() => {
      getHistory(SESSION_ID)
        .then((riwayat) => setRecords([...riwayat].reverse().map(toAssessment)))
        .catch(() => {})
    }, 2000)
    return () => clearInterval(timer)
  }, [])

  // Analisis window yang dipilih lewat backend. Hasilnya tersimpan di riwayat database.
  async function analyze() {
    if (loading || !connected || !session) return
    const w = session.windows[windowIndex]
    setLoading(true)
    setNotice("")
    try {
      const rec = await postMeasurement({
        session_id: SESSION_ID,
        window_id: w.window_id,
        fs: session.fs,
        samples: w.samples,
        source: "replay",
        sensor_ok: connected,
      })
      const item: Assessment = { ...toAssessment(rec), previousId: repeatPrevious }
      setRecords((old) => [...old, item])
      setActiveId(item.id)
      setRepeatPrevious(null)
      setNotice(
        `${item.scenario.reliability} assessment recorded for window ${String(
          windowIndex + 1,
        ).padStart(2, "0")}.`,
      )
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Analysis failed.")
    } finally {
      setLoading(false)
    }
  }

  function repeat() {
    if (!active) return
    setRepeatPrevious(active.id)
    setActiveId(null)
    const freeWindow = latestByWindow.findIndex((r, i) => !r && i > windowIndex)
    const anyFreeWindow = latestByWindow.findIndex((r) => !r)
    setWindowIndex(
      freeWindow >= 0
        ? freeWindow
        : anyFreeWindow >= 0
          ? anyFreeWindow
          : (windowIndex + 1) % 10,
    )
    setNotice("Previous assessment saved. Analyze the selected window again.")
  }

  function selectWindow(index: number) {
    cancelAnalysis()
    setWindowIndex(index)
    setActiveId(latestByWindow[index]?.id ?? null)
    setRepeatPrevious(null)
    setNotice("")
  }

  // Reset hanya membersihkan tampilan. Riwayat di database tidak dihapus.
  function reset() {
    cancelAnalysis()
    setRecords([])
    setActiveId(null)
    setWindowIndex(0)
    setOverlay(true)
    setConnected(true)
    setRepeatPrevious(null)
    setShowAll(false)
    setResetOpen(false)
    setNotice("View reset. Stored history in the database is unchanged.")
    resetButton.current?.focus()
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Activity size={25} strokeWidth={2.1} />
          </span>
          <span>
            Pulse<span className="brand-light">Sure</span>
            <span className="brand-period">.</span>
          </span>
        </div>
        <div className="sidebar-label">CLINICAL WORKSPACE</div>
        <a className="nav-item" href="#monitoring" aria-current="page">
          <LayoutDashboard size={18} />
          Clinical Monitoring
          <span className="nav-active-dot" />
        </a>
        <div className="sidebar-message">
          <div className="sidebar-line" />
          <ShieldCheck size={23} />
          <p>
            Trust the measurement.
            <br />
            <strong>Then trust the number.</strong>
          </p>
          <span>Clarity for every bedside decision.</span>
        </div>
        <div className="sidebar-bottom">
          <div className="prototype-pill">
            <span className="dot mint" />
            Prototype mode
          </div>
          <div className="research">
            <Microscope size={15} />
            <span>Research demonstration</span>
          </div>
          <p>
            Simulated signals.
            <br />
            Not for clinical use.
          </p>
          <div className="sidebar-version">
            <span>PULSESURE</span>
            <span>v1.0</span>
          </div>
        </div>
      </aside>
      <main id="monitoring">
        <header className="page-header">
          <div>
            <div className="eyebrow">
              BEDSIDE INTELLIGENCE <span>/</span> LIVE WORKSPACE
            </div>
            <h1>Patient Monitoring</h1>
            <p>PPG Signal Reliability Assessment</p>
          </div>
          <div className="header-actions">
            <span className="source-status">
              <span className={`dot ${connected ? "green" : "red"}`} />
              {connected ? "Demo source available" : "Demo source disconnected"}
            </span>
            <button
              className="button secondary reset-button"
              ref={resetButton}
              onClick={() => setResetOpen(true)}
            >
              <RotateCcw size={15} />
              Reset session
            </button>
          </div>
        </header>

        {loadError && (
          <p style={{ color: "crimson", margin: "8px 0" }}>
            Gagal memuat data dari backend: {loadError}
          </p>
        )}

        <section className="patient-context card" aria-label="Session context">
          <div className="patient-selector">
            <div className="patient-avatar">
              <UserRound size={23} />
            </div>
            <div>
              <label>MONITORING SESSION</label>
              <strong>Demo session · {SESSION_ID}</strong>
            </div>
          </div>
          <div className="patient-detail">
            <span>Session ID</span>
            <strong>{SESSION_ID}</strong>
          </div>
          <div className="patient-detail">
            <span>Windows</span>
            <strong>{session ? `${session.windows.length} × 30 s` : "—"}</strong>
          </div>

          <div className="patient-detail monitoring-detail">
            <span>Monitoring status</span>
            <strong>
              <span className={`dot ${connected ? "green" : "red"}`} />
              {!connected
                ? "Unavailable"
                : loading
                  ? "Assessing"
                  : active
                    ? "Assessment available"
                    : "Ready to assess"}
            </strong>
          </div>
          <div className="sensor-context">
            <button
              className={`sensor-button ${!connected ? "disconnected" : ""}`}
              title={
                connected
                  ? "Disconnect simulated sensor"
                  : "Reconnect simulated sensor"
              }
              aria-pressed={connected}
              onClick={() => {
                cancelAnalysis()
                setConnected(!connected)
                setActiveId(null)
                setRepeatPrevious(null)
                setNotice(
                  connected
                    ? "Simulated sensor disconnected. Reconnect to analyze a sample."
                    : "Simulated sensor connected. Select a sample to reassess.",
                )
              }}
            >
              {connected ? <Radio size={15} /> : <Unplug size={15} />}Simulated
              sensor {connected ? "connected" : "disconnected"}
            </button>
            <span>
              Demo data source <span className="tiny-divider">|</span> Fictional
              patient
            </span>
          </div>
        </section>

        <section
          className="kpi-grid"
          aria-label="Measurement overview"
          aria-live="polite"
        >
          <div className="card kpi">
            <div className="kpi-top">
              <span>Heart rate</span>
              <Heart size={18} />
            </div>
            <div className={`kpi-value ${result?.withheld ? "withheld" : ""}`}>
              {!result ? (
                <span className="empty-dash">—</span>
              ) : result.withheld || result.hrBpm === null ? (
                <>
                  <span className="withheld-dot" />
                  WITHHELD
                </>
              ) : (
                <>
                  {result.hrBpm} <span className="unit">BPM</span>
                </>
              )}
            </div>
            <p>
              {!result
                ? "Awaiting signal quality assessment"
                : result.withheld
                  ? "Estimate unavailable: insufficient signal quality."
                  : status === "Caution"
                    ? "Estimate shown with caution. Verify the signal before use."
                    : "Estimate from accepted signal"}
            </p>
          </div>
          <div className="card kpi">
            <div className="kpi-top">
              <span>Signal quality</span>
              <Signal size={18} />
            </div>
            <div className="quality-value-row">
              <div className="kpi-value">
                {result ? result.score : <span className="empty-dash">—</span>}
                <span className="unit"> / 100</span>
              </div>
              {result && (
                <span className={`quality-mini ${status?.toLowerCase()}`}>
                  <StatusIcon status={status} size={15} />
                </span>
              )}
            </div>
            <div className="quality-track">
              <div
                className={status?.toLowerCase()}
                style={{ width: `${result?.score ?? 0}%` }}
              />
            </div>
            <p>AI signal quality assessment</p>
          </div>
          <div
            className={`card kpi reliability-kpi ${status?.toLowerCase() ?? ""}`}
          >
            <div className="kpi-top">
              <span>Measurement reliability</span>
              <ShieldCheck size={18} />
            </div>
            <div className={`reliability-value ${status?.toLowerCase() ?? ""}`}>
              <StatusIcon status={status} size={25} />
              <span>{status?.toUpperCase() ?? "NOT ASSESSED"}</span>
            </div>
            <p>
              {!result
                ? "Analyze a sample to determine reliability."
                : status === "Reliable"
                  ? "Signal suitable for review."
                  : status === "Caution"
                    ? "Signal requires verification."
                    : "Measurement withheld."}
            </p>
          </div>
        </section>

        <div className="monitoring-grid">
          <section className="card monitoring-card" aria-labelledby="ppg-title">
            <div className="section-heading">
              <div>
                <h2 id="ppg-title">
                  <Activity size={18} />
                  PPG Signal Monitoring
                </h2>
                <p>Simulated signal. A clearer view of measurement quality.</p>
              </div>
              <span className="window-chip">
                <Clock3 size={13} />
                Window {String(windowIndex + 1).padStart(2, "0")}
              </span>
            </div>
            <div className="signal-controls">
              
              <button
                className="button primary analyze-button"
                disabled={loading || !connected}
                onClick={analyze}
              >
                {loading ? (
                  <LoaderCircle size={16} className="spin" />
                ) : (
                  <ScanLine size={16} />
                )}
                {loading ? "Assessing…" : `Analyze window ${String(windowIndex + 1).padStart(2, "0")}`}
              </button>
              <label className="overlay-control">
                <span>Artifact overlay</span>
                <button
                  role="switch"
                  type="button"
                  aria-checked={overlay}
                  aria-label="Artifact overlay"
                  className={`switch ${overlay ? "on" : ""}`}
                  onClick={() => setOverlay(!overlay)}
                >
                  <span />
                </button>
              </label>
            </div>
          
            <PPGWaveform
              samples={windowSamples}
              fs={fs}
              intervals={result ? result.intervals : []}
              analyzed={!!active}
              simulated={result ? result.simulated : true}
              overlay={overlay}
              loading={loading && !active}
              connected={connected}
            />
            <div className="waveform-footer">
              <Info size={13} />
              <span>
                {active
                ? `Showing recorded assessment · ${result?.label} · ${active.time}`
                  : "Results appear only after analysis. No physical sensor is connected."}
              </span>
            </div>
          </section>

          <section
            className={`card action-card ${status?.toLowerCase() ?? ""}`}
            aria-labelledby="action-title"
          >
            <div className="action-heading">
              <span className="section-icon">
                <ShieldCheck size={18} />
              </span>
              <h2 id="action-title">
                Measurement Decision
                <br />
                <span>& Nursing Action</span>
              </h2>
            </div>
            <div className={`decision-panel ${status?.toLowerCase() ?? ""}`}>
              <StatusIcon status={status} size={24} />
              <div>
                <span className="small-label">MEASUREMENT DECISION</span>
                <strong>{result?.decision ?? "Awaiting assessment"}</strong>
              </div>
            </div>
            <p className="decision-description">
              {!result
                ? "Assess signal quality before relying on a heart rate estimate."
                : status === "Reliable"
                  ? "Signal quality meets the prototype acceptance criteria."
                  : status === "Caution"
                    ? "Signal quality may affect measurement reliability."
                    : "Heart rate is hidden because signal quality is insufficient."}
            </p>
            <div className="recommended-action">
              <div className="small-label">
                {result ? "RECOMMENDED NEXT STEP" : "GET STARTED"}
              </div>
              <p>
                {result?.recommendation ?? "Select a demo sample to begin."}
              </p>
            </div>
            <div className="action-buttons">
              <button
                className={`button ${
                  status && status !== "Reliable" ? "primary" : "secondary"
                }`}
                disabled={!active || loading || !connected}
                onClick={repeat}
              >
                <RotateCcw size={15} />
                Repeat measurement
              </button>
              <button
                className={`button review-button ${
                  active?.reviewed ? "is-reviewed" : ""
                }`}
                disabled={!active || active.reviewed || loading}
                onClick={() => {
                  setRecords((old) =>
                    old.map((r) =>
                      r.id === activeId ? { ...r, reviewed: true } : r,
                    ),
                  )
                  setNotice(
                    "Assessment marked as reviewed. This does not confirm clinical verification.",
                  )
                }}
              >
                {active?.reviewed ? (
                  <CheckCheck size={16} />
                ) : (
                  <Check size={16} />
                )}
                {active?.reviewed ? "Reviewed" : "Mark as reviewed"}
              </button>
            </div>
            <div className="action-footnote">
              <Info size={12} />
              <span>
                Review records acknowledgement, not clinical verification.
              </span>
            </div>
          </section>
        </div>

        <section
          className="card assessment-card"
          aria-labelledby="assessment-title"
        >
          <div className="assessment-heading">
            <h2 id="assessment-title">
              <Sparkles size={17} />
              AI Reliability Assessment
            </h2>
            <span>Results from backend (MVP thresholds)</span>
          </div>
          <div className="assessment-metrics">
            <div className="assessment-metric">
              <span>Usable signal</span>
              <strong>{result ? `${result.usable}%` : "—"}</strong>
              <div className="mini-track">
                <div style={{ width: `${result?.usable ?? 0}%` }} />
              </div>
            </div>
            <div className="assessment-metric">
              <span>Artifact duration</span>
              <strong>
                {result ? result.durationS.toFixed(1) : "—"}
                <small> / 30 s</small>
              </strong>
              <span className="metric-hint">
                {result
                  ? `${result.artifact}% of measurement window`
                  : "No assessment available"}
              </span>
            </div>
            <div className="assessment-metric cause-metric">
              <span>Possible interference cause</span>
              <strong>{result?.cause ?? "Not yet assessed"}</strong>
              <span className="metric-hint">
                Signal interference assessment, not a diagnosis.
              </span>
            </div>
            <div className="assessment-note">
              <Info size={15} />
              <p>
                Reliability describes the <strong>signal</strong>,<br />
                not the patient’s clinical condition.
              </p>
            </div>
          </div>
        </section>

        <section className="card history-card" aria-labelledby="history-title">
          <div className="section-heading history-heading">
            <div>
              <h2 id="history-title">
                <Clock3 size={18} />
                Monitoring History
                <span className="count-pill">{patientRecords.length}</span>
              </h2>
              <p>A complete view of this patient’s assessment session.</p>
            </div>
            <span className="history-duration">
              10 windows <span>·</span> 30 s each <span>·</span> 5 minutes
            </span>
          </div>
          <div className="timeline-header">
            <span className="small-label">MEASUREMENT WINDOWS</span>
            <div className="timeline-legend">
              <span>
                <i className="dot green" />
                Reliable
              </span>
              <span>
                <i className="dot amber" />
                Caution
              </span>
              <span>
                <i className="dot red" />
                Unreliable
              </span>
              <span>
                <i className="dot" />
                Not analyzed
              </span>
            </div>
          </div>
          <div className="window-timeline">
            {latestByWindow.map((record, i) => {
              const scenario = record ? record.scenario : null
              return (
                <button
                  key={i}
                  className={`timeline-window ${scenario?.reliability.toLowerCase() ?? "unanalyzed"} ${
                    windowIndex === i ? "selected" : ""
                  }`}
                  aria-pressed={windowIndex === i}
                  aria-label={`Window ${i + 1}, ${
                    scenario
                      ? `${scenario.reliability}, quality ${scenario.score}`
                      : "not analyzed"
                  }`}
                  onClick={() => selectWindow(i)}
                >
                  <span>
                    W{String(i + 1).padStart(2, "0")}
                    {windowIndex === i && <span className="selected-marker" />}
                  </span>
                  <strong>
                    {scenario ? (
                      <>
                        <StatusIcon status={scenario.reliability} size={12} />
                        {scenario.score}
                        <small>/100</small>
                      </>
                    ) : (
                      "—"
                    )}
                  </strong>
                  <span className="window-time">
                    {i * 30}–{(i + 1) * 30}s
                  </span>
                </button>
              )
            })}
          </div>
          {previousResult && result && (
            <div className="recovery-comparison">
              <div className="recovery-icon">
                {result.score > previousResult.score ? (
                  <ArrowUpRight size={20} />
                ) : (
                  <ArrowRight size={20} />
                )}
              </div>
              <div>
                <span className="small-label">
                  REPEAT MEASUREMENT COMPARISON
                </span>
                <div className="comparison-values">
                  <strong>
                    {previousResult.score}/100{" "}
                    <span>{previousResult.reliability.toUpperCase()}</span>
                  </strong>
                  <ArrowRight size={17} />
                  <strong>
                    {result.score}/100{" "}
                    <span>{result.reliability.toUpperCase()}</span>
                  </strong>
                </div>
                <p>
                  {result.score > previousResult.score
                    ? "Signal quality improved after repeat measurement."
                    : result.score < previousResult.score
                      ? "Signal quality decreased. Follow the current assessment guidance."
                      : "Signal quality is unchanged after repeat measurement."}
                </p>
              </div>
            </div>
          )}
          <div className="records-title">
            <h3>Recent assessments</h3>
            <span>
              {patientRecords.length > 5 ? (
                <button
                  className="text-button"
                  onClick={() => setShowAll(!showAll)}
                >
                  {showAll
                    ? "Show latest 5"
                    : `View all ${patientRecords.length}`}
                  <ArrowDown size={13} />
                </button>
              ) : (
                "Latest 5 records"
              )}
            </span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>TIME</th>
                  <th>WINDOW</th>
                  <th>QUALITY</th>
                  <th>RELIABILITY</th>
                  <th>POSSIBLE CAUSE</th>
                  <th>REVIEW STATUS</th>
                </tr>
              </thead>
              <tbody>
                {[...patientRecords]
                  .reverse()
                  .slice(0, showAll ? undefined : 5)
                  .map((record) => (
                    <tr
                      key={record.id}
                      className={activeId === record.id ? "active-row" : ""}
                    >
                      <td>
                        <button
                          className="record-link"
                          onClick={() => {
                            cancelAnalysis()
                            setActiveId(record.id)
                            setWindowIndex(record.window)
                            setRepeatPrevious(null)
                          }}
                        >
                          {record.time}
                        </button>
                      </td>
                      <td>W{String(record.window + 1).padStart(2, "0")}</td>
                      <td>
                        <strong>{record.scenario.score}</strong>
                        <span className="table-unit"> /100</span>
                      </td>
                      <td>
                        <Badge status={record.scenario.reliability} />
                      </td>
                      <td className="cause-cell">
                        {record.scenario.cause}
                      </td>
                      <td>
                        <span
                          className={`review-status ${
                            record.reviewed ? "done" : ""
                          }`}
                        >
                          {record.reviewed ? (
                            <CheckCheck size={14} />
                          ) : (
                            <Clock3 size={13} />
                          )}
                          {record.reviewed ? "Reviewed" : "Not reviewed"}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {patientRecords.length === 0 && (
            <div className="history-empty">
              <span className="empty-history-icon">
                <Clock3 size={19} />
              </span>
              <div>
                <strong>Your monitoring session starts here</strong>
                <p>Select a window and analyze it to record your first assessment.</p>
              </div>
              <span className="session-only">
                <span className="dot" />
                Session only
              </span>
            </div>
          )}
          <div className="history-footer">
            <span>
              <Info size={12} />
              Records are kept in this session only.
            </span>
            <span>All timestamps reflect demonstration activity.</span>
          </div>
        </section>
        <footer className="page-footer">
          <span>
            <ShieldCheck size={14} />
            Designed to support measurement verification. Not a diagnostic
            system.
          </span>
          <span>
            SIMULATED DATA <i /> RESEARCH USE ONLY
          </span>
        </footer>
        <div className="clinical-note">
          <Info size={13} />
          <span>
            If monitoring is unavailable or clinical signs are concerning, use
            your institution’s standard assessment and escalation procedures.
          </span>
        </div>
        <div className="sr-only" role="status" aria-live="polite">
          {notice}
        </div>
      </main>
      <dialog
        ref={dialog}
        className="reset-dialog"
        onCancel={() => setResetOpen(false)}
        onClick={(e) => {
          if (e.target === e.currentTarget) setResetOpen(false)
        }}
      >
        <div className="dialog-header">
          <span className="dialog-icon">
            <RotateCcw size={22} />
          </span>
          <button
            className="icon-button"
            onClick={() => setResetOpen(false)}
            aria-label="Close confirmation"
          >
            <X size={19} />
          </button>
        </div>
        <h2>Reset this session?</h2>
        <p>
          This will clear all assessments, review statuses, and measurement
          history for every fictional patient. This action cannot be undone.
        </p>
        <div className="dialog-actions">
          <button
            className="button secondary"
            autoFocus
            onClick={() => setResetOpen(false)}
          >
            Keep session
          </button>
          <button className="button danger" onClick={reset}>
            <RotateCcw size={15} />
            Reset session
          </button>
        </div>
      </dialog>
    </div>
  )
}
