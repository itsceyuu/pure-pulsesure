# PURE Product Explainer — Locked Storyboard

**Duration:** 110 seconds  
**Format:** 16:9, 1920×1080, 30 fps  
**Language:** English  
**Narrator:** One consistent voice  
**Team name:** Team PURE  
**Team members:** Alexa, Grace, Jenni, and There

---

## Scene 1 — Team Introduction

**Time:** 0:00–0:05  
**Requirement:** Team name and team members

**Visual**

- PURE logo appears over an animated PPG waveform.
- Team member names fade in beneath the logo.
- Use the Midnight Navy and Signal Mint palette.

**On-screen text**

```text
TEAM PURE

Alexa • Grace • Jenni • There

Pulse Understanding & Reliability Engine
```

**Voice-over**

> We are Team PURE: Alexa, Grace, Jenni, and There.

---

## Scene 2 — Selected Problem Statement

**Time:** 0:05–0:13  
**Requirement:** Selected problem statement

**Visual**

- A bedside nurse looks at a heart-rate monitor.
- BPM appears normal, but the waveform begins showing subtle interference.
- The screen pauses before the BPM is accepted.

**On-screen text**

```text
SELECTED PROBLEM

How can bedside nurses verify whether
a PPG heart-rate reading is reliable
before displaying the number?
```

**Voice-over**

> How can we help bedside nurses verify whether a PPG heart-rate reading is reliable before displaying the number?

---

## Scene 3 — Problem Understanding

**Time:** 0:13–0:25  
**Requirement:** Problem understanding

**Visual**

- Show three causes of poor PPG quality:
  - patient movement;
  - unstable sensor contact;
  - weak signal or low perfusion.
- A plausible BPM remains visible despite the distorted waveform.
- Add a warning around the number.

**On-screen text**

```text
A plausible number
can still come from
an unreliable signal.
```

Supporting labels:

```text
Motion Artifact
Unstable Contact
Weak Signal
```

**Voice-over**

> PPG signals are highly sensitive to motion, unstable sensor contact, and low perfusion. These disturbances can produce a plausible heart-rate value even when the underlying signal is unreliable.

---

## Scene 4 — Proposed Solution

**Time:** 0:25–0:37  
**Requirement:** Proposed solution

**Visual**

- Insert PURE between the sensor and dashboard.
- Data passes through PURE before BPM reaches the monitor.
- Four PURE outputs appear:
  - artifact detection;
  - quality score;
  - reliability status;
  - corrective guidance.

**On-screen text**

```text
PURE

An AI-powered reliability layer
before the BPM is displayed
```

**Voice-over**

> PURE, the Pulse Understanding and Reliability Engine, adds an AI-powered reliability layer between the sensor and the dashboard. It assesses signal quality before releasing the BPM.

---

## Scene 5 — Innovation and Novelty

**Time:** 0:37–0:47  
**Requirement:** Innovation and novelty

**Visual**

Animate the Quality-to-Action workflow:

```text
Detect
  ↓
Score
  ↓
Decide
  ↓
Guide
```

The final stage should show an action such as:

```text
Check sensor placement
Repeat measurement
BPM can be displayed
```

**On-screen text**

```text
QUALITY-TO-ACTION

Not only detecting noise,
but deciding what happens next.
```

**Voice-over**

> Its novelty is a Quality-to-Action workflow: detect artifacts, quantify quality, decide reliability, and provide a corrective action—not merely flag noise.

---

## Scene 6 — Proposed Technology and AI Approach

**Time:** 0:47–1:01  
**Requirement:** Proposed technology and AI approach

**Visual**

Animate the AI pipeline:

```text
PPG + Motion Data
        ↓
Windowing & Preprocessing
        ↓
1D Time-Series AI Model
        ↓
Artifact Probability
        ↓
Calibrated Quality Score
        ↓
Reliability Gate
```

Do not name ResNet as the confirmed final model. Use:

```text
1D time-series model
selected through benchmarking
```

**On-screen output**

```text
Quality Score: 91
Status: Reliable
Decision: Display BPM
```

**Voice-over**

> PPG and accelerometer data are segmented and preprocessed. A benchmarked one-dimensional time-series model estimates artifact probability, produces a calibrated quality score, and feeds a reliability gate that decides whether BPM can be displayed.

---

## Scene 7 — Proposed Prototype Implementation

**Time:** 1:01–1:23  
**Requirement:** Brief implementation plan

**Visual Part A — Wearable Assembly**

Show an exploded wearable prototype containing:

```text
ESP32-C3 Mini
MAX30102
MPU6050
LiPo Battery
3D-Printed TPU Casing
```

**Visual Part B — Connectivity**

Animate the data path:

```text
PPG + Motion Sensors
        ↓
ESP32-C3 Mini
        ↓ Wi-Fi / MQTT
Mosquitto Broker
```

**Visual Part C — Processing**

Continue the data flow:

```text
Backend
   ↓
AI Signal Analysis
   ↓
Quality Gate
   ↓
Storage
   ↓
Dashboard
```

**On-screen phase labels**

```text
PHASE 1
Assemble & Capture

PHASE 2
Transmit & Analyze

PHASE 3
Gate, Store & Display
```

**Voice-over**

> During implementation, we will assemble a wearable prototype using an ESP32-C3 Mini, MAX30102, MPU6050, LiPo battery, and custom TPU casing. It will transmit PPG and motion data over Wi-Fi using MQTT to a Mosquitto broker, then to the backend for AI analysis, quality gating, storage, and dashboard delivery.

---

## Scene 8 — Dashboard Prototype Demo

**Time:** 1:23–1:38  
**Requirement:** Demonstration of the proposed solution

**Visual sequence**

1. Clean PPG waveform appears.
2. Quality score is high.
3. Status displays `Reliable`.
4. BPM is visible.
5. Motion is introduced.
6. Waveform becomes distorted.
7. Quality score falls.
8. Status changes to `Unreliable`.
9. BPM changes to `WITHHELD`.
10. Corrective guidance appears.
11. Signal stabilizes.
12. BPM becomes visible again.

**Dashboard states**

```text
RELIABLE
BPM displayed
```

```text
CAUTION
Check sensor placement
```

```text
UNRELIABLE
BPM withheld
Repeat measurement
```

**Voice-over**

> On the dashboard, reliable signals reveal BPM. If motion degrades the waveform, the quality score falls, PURE withholds the heart rate, and recommends checking the sensor. Once the signal recovers, BPM returns.

---

## Scene 9 — Expected Impact and Closing

**Time:** 1:38–1:50  
**Requirement:** Expected impact

**Visual**

Show three impact statements:

```text
More Reliable Measurements

Faster Corrective Action

Greater Monitoring Confidence
```

Then display the non-diagnostic disclaimer, followed by the PURE logo and tagline.

**On-screen disclaimer**

```text
PURE supports signal-quality assessment
and does not provide a medical diagnosis.
```

**Closing text**

```text
PURE

Trust the Signal.
Before the Number.
```

**Voice-over**

> PURE reduces uncertainty and unnecessary rechecks while supporting more confident monitoring. It supports measurement decisions—it does not diagnose patients. Trust the Signal. Before the Number.

---

# Requirement Coverage

| Required content | Scene |
|---|---:|
| Team name | 1 |
| Team members | 1 |
| Selected problem statement | 2 |
| Problem understanding | 3 |
| Proposed solution | 4 |
| Innovation and novelty | 5 |
| Proposed technology and AI approach | 6 |
| Brief implementation plan | 7 |
| Expected impact | 9 |
| Prototype demonstration | 8 |

# Claim and Prototype Rules

- Use **Proposed Prototype Implementation** until the hardware works end-to-end.
- Change it to **Working Prototype** only after successful testing.
- Do not present literature metrics as PURE performance.
- Do not state that ResNet is the final model before benchmarking.
- Clearly show that AI inference takes place in the backend.
- Heart rate must be withheld during the Unreliable state.
- PURE must consistently be described as non-diagnostic.