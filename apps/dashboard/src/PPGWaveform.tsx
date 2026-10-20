import { useMemo, useState } from "react"
import { Activity, ScanLine } from "lucide-react"

type Props = {
  samples: number[] | null      // sampel asli dari backend, 1.920 nilai
  fs: number                    // 64 Hz
  intervals: [number, number][] // interval artefak dalam detik
  analyzed: boolean             // sudah ada hasil analisis untuk window ini
  simulated: boolean            // inference_type === "simulated"
  overlay: boolean
  loading: boolean
  connected: boolean
}

const DURASI = 30
const LEBAR = 1000
const TINGGI = 195
const GARIS_TENGAH = 145

export default function PPGWaveform({
  samples,
  fs,
  intervals,
  analyzed,
  simulated,
  overlay,
  loading,
  connected,
}: Props) {
  const [hover, setHover] = useState<number | null>(null)

  const skala = useMemo(() => {
    if (!samples || samples.length === 0) return null
    let lo = Infinity
    let hi = -Infinity
    for (const v of samples) {
      if (v < lo) lo = v
      if (v > hi) hi = v
    }
    return { lo, span: hi - lo || 1 }
  }, [samples])

  const points = useMemo(() => {
    if (!samples || !skala) return ""
    return samples
      .map((v, i) => {
        const x = ((i / fs / DURASI) * LEBAR).toFixed(2)
        const y = (GARIS_TENGAH - ((v - skala.lo) / skala.span) * 98).toFixed(2)
        return `${x},${y}`
      })
      .join(" ")
  }, [samples, fs, skala])

  const idx =
    samples && hover !== null
      ? Math.min(samples.length - 1, Math.max(0, Math.round(hover * fs)))
      : -1
  const nilaiHover = samples && idx >= 0 ? samples[idx] : null
  const yHover =
    nilaiHover !== null && skala
      ? GARIS_TENGAH - ((nilaiHover - skala.lo) / skala.span) * 98
      : 0

  const dalamArtefak = (t: number) =>
    intervals.some(([s, e]) => t >= s && t <= e)

  return (
    <div className={`waveform ${!samples ? "is-empty" : ""}`}>
      <div className="chart-topline">
        <span>
          <span className={`dot ${analyzed ? "mint" : ""}`} />{" "}
          {analyzed
            ? simulated
              ? "SIMULATED PPG"
              : "PPG SIGNAL"
            : "SIGNAL PREVIEW"}
        </span>
        <span>
          30-second window <span className="chart-separator">/</span> Sample
          amplitude
        </span>
      </div>

      <div className="plot-wrap" onPointerLeave={() => setHover(null)}>
        <svg
          className="plot"
          viewBox={`0 0 ${LEBAR} ${TINGGI}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={
            samples
              ? analyzed
                ? "PPG waveform for the selected window"
                : "PPG signal preview, not yet analyzed"
              : "Signal placeholder. Select a window to view its signal."
          }
          onPointerMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect()
            setHover(
              Math.max(
                0,
                Math.min(DURASI, ((event.clientX - rect.left) / rect.width) * DURASI),
              ),
            )
          }}
        >
          <defs>
            <pattern
              id="grid"
              width="33.333"
              height="32.5"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 33.333 0 L 0 0 0 32.5"
                fill="none"
                stroke="#253e4b"
                strokeWidth="0.6"
              />
            </pattern>
          </defs>
          <rect width={LEBAR} height={TINGGI} fill="url(#grid)" />

          {analyzed &&
            overlay &&
            intervals.map(([start, end]) => (
              <g key={`${start}-${end}`}>
                <rect
                  x={(start / DURASI) * LEBAR}
                  y="0"
                  width={((end - start) / DURASI) * LEBAR}
                  height={TINGGI}
                  fill="#ed6868"
                  opacity="0.13"
                />
                <line
                  x1={(start / DURASI) * LEBAR}
                  x2={(start / DURASI) * LEBAR}
                  y1="0"
                  y2={TINGGI}
                  stroke="#ed6868"
                  strokeOpacity="0.4"
                  strokeDasharray="3 5"
                />
              </g>
            ))}

          <polyline
            points={points}
            fill="none"
            stroke="#35C4B5"
            strokeWidth="1.8"
            vectorEffect="non-scaling-stroke"
            opacity={analyzed ? 1 : 0.35}
            strokeLinejoin="round"
          />

          {samples && hover !== null && nilaiHover !== null && (
            <g>
              <line
                x1={(hover / DURASI) * LEBAR}
                x2={(hover / DURASI) * LEBAR}
                y1="0"
                y2={TINGGI}
                stroke="#93c9c4"
                strokeDasharray="4 4"
              />
              <circle
                cx={(hover / DURASI) * LEBAR}
                cy={yHover}
                r="4"
                fill="#35C4B5"
              />
            </g>
          )}
        </svg>

        {!samples && (
          <div className="chart-empty">
            <span className="chart-empty-icon">
              {loading ? (
                <Activity className="loading-icon" size={23} />
              ) : (
                <ScanLine size={23} />
              )}
            </span>
            <strong>
              {loading
                ? "Assessing signal quality…"
                : !connected
                  ? "Simulated sensor disconnected"
                  : "Loading signal…"}
            </strong>
            <span>
              {loading
                ? "Evaluating the selected window."
                : !connected
                  ? "Reconnect the simulated sensor to assess a window."
                  : "Waiting for the session from the backend."}
            </span>
          </div>
        )}

        {samples && hover !== null && nilaiHover !== null && (
          <div
            className="chart-tooltip"
            style={{
              left: `${Math.max(15, Math.min(79, (hover / DURASI) * 100))}%`,
            }}
          >
            <strong>{hover.toFixed(2)} s</strong>
            <span>Amplitude {nilaiHover.toFixed(2)} a.u.</span>
            <span>
              {dalamArtefak(hover) ? "Artifact detected" : "No detected artifact"}
            </span>
          </div>
        )}
      </div>

      <div className="chart-axis">
        {[0, 5, 10, 15, 20, 25, 30].map((n) => (
          <span key={n}>{n}s</span>
        ))}
      </div>

      <div className="chart-bottomline">
        <span>
          <i className="legend-line" /> PPG waveform
        </span>
        <span>
          <i className="legend-artifact" /> Detected artifact
          {overlay ? "" : " (hidden)"}
        </span>
        <span className="chart-note">
          {simulated
            ? "Simulated data · Not a patient observation"
            : "Measured data · Not a diagnosis"}
        </span>
      </div>
    </div>
  )
}