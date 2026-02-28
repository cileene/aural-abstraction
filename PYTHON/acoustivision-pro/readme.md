---
title: Acoustivision Pro
emoji: 🐢
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.5.1
app_file: app.py
pinned: false
license: mit
short_description: Interactive suite for Room Impulse Response Visualization
---
<div align="center">

# 🔊 AcoustiVision Pro

### Interactive Room Impulse Response Analysis & Visualization Platform

**A flagship research tool for acoustic evaluation, auralization, and automated reporting**

[![Hugging Face](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/mandipgoswami/acoustivision-pro)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)

---

**Analyze, visualize, and experience real rooms through physics-based RIR processing**

🚀 Powered by **RIRmega** and **RIR-Gen**

[Launch Demo](#-quick-start) •
[Features](#-features) •
[Datasets](#-datasets) •
[Citation](#-citation)

</div>

---

## 📌 Overview

**AcoustiVision Pro** is a professional web-based platform for analyzing **Room Impulse Responses (RIRs)** and evaluating acoustic performance in real and simulated spaces.

It integrates advanced signal processing, 3D visualization, dataset search, and automated reporting into a single interactive environment.

### Key Goals

- Bridge acoustic theory with public accessibility
- Enable reproducible room analysis
- Support research, design, and education
- Serve as a flagship interface for RIRmega

---
## Paper Link 

Arxiv : [arxiv.org/abs/2602.12299]

## ✨ Core Features

### 🔬 Acoustic Analysis

- Energy Decay Curve (EDC) with EDT / T20 / T30
- Broadband and octave-band RT60
- Clarity (C80), Definition (D50), DRR
- Speech Transmission Index (STI, proxy)
- Inter-Aural Cross Correlation (IACC)
- Room mode analysis

### 🌐 Visualization

- Interactive 3D reflection paths
- Time-domain waveform
- Spectrogram & frequency response
- Waterfall decay plots
- Acoustic fingerprint radar chart

### 🎧 Auralization

- FFT-based real-time convolution
- Dry / Wet audio comparison
- Automatic resampling & normalization

### 📄 Reporting

- One-click professional PDF reports
- Embedded plots and metrics
- Exportable JSON/CSV data

### 🔎 Dataset Integration

- Search RIRmega by metadata
- Auto-load geometry & positions
- Direct HF dataset access

### 📊 Impact Tracking

- Privacy-safe usage analytics
- Anonymous adoption metrics
- Research impact reporting

---

## 🚀 Quick Start

### Option A — Load from RIRmega

1. Use **RIRmega Search**
2. Filter by volume / RT60 / absorption
3. Select a matching room
4. Geometry and RIR auto-load

### Option B — Upload Your Own RIR

1. Upload `.wav` RIR file
2. (Optional) Upload dry audio
3. Configure geometry
4. Run analysis

### Run

Click:

▶ Run Analysis


All metrics and visualizations execute automatically.

---

## 🧭 Workflow

RIR Input
↓
Signal Conditioning
↓
Schroeder Integration
↓
Metric Extraction
↓
Visualization Engine
↓
PDF / Audio Output


---

## 📏 Computed Metrics

### Reverberation

| Metric | Range | Description |
|--------|-------|-------------|
| EDT | 0–3 s | Early decay |
| T20 | 0–3 s | −5 to −25 dB |
| T30 | 0–3 s | −5 to −35 dB |

### Clarity & Definition

| Metric | Purpose |
|--------|----------|
| C80 | Music clarity |
| D50 | Speech definition |

### Intelligibility

| Metric | Range |
|--------|-------|
| STI | 0.0–1.0 |

Proxy estimate based on RT60 and SNR.

### Spatial Quality

| Metric | Requirement |
|--------|-------------|
| IACC | Stereo RIR |

### Wellness Score

Composite 0–100 rating combining:

- RT60
- STI
- D50
- C80
- Room volume

---

## ✅ Standards Alignment

| Standard | Application |
|----------|-------------|
| ISO 3382 | Performance spaces |
| ISO 3382-3 | Open offices |
| ANSI S12.60 | Classrooms |
| IEC 60268-16 | STI |

Automatic compliance checks are performed when applicable.

---

## 📊 Datasets

### RIRmega
**https://huggingface.co/datasets/mandipgoswami/rirmega**

- 100k+ simulated RIRs
- Pyroomacoustics image-source
- Full geometric metadata

### RIRmega Speech
**https://huggingface.co/datasets/mandipgoswami/rir-mega-speech**

- RIR-convolved speech
- ASR / intelligibility research

---

## 🏗️ Technical Architecture

### Stack

| Layer | Technology |
|-------|------------|
| UI | Gradio |
| Plotting | Plotly / Matplotlib |
| DSP | SciPy / Librosa |
| Audio | SoundFile |
| Storage | SQLite |
| Reports | ReportLab |
| Hub | huggingface_hub |
### Processing Pipeline
WAV → Normalize → Peak Detect
→ EDC → Regression
→ Bandpass Filtering
→ Metrics → Plots
→ Report / Audio
---
## 🎯 Use Cases
### Academic Research
- Model validation
- Dataset benchmarking
- Publication figures
### Architecture & Design
- Room evaluation
- Treatment comparison
- Compliance checks
### Healthcare & Education
- Speech intelligibility
- Noise mitigation
- Standard adherence
### Audio Engineering
- Studio characterization
- Listening room tuning
### Machine Learning
- Data augmentation
- ASR robustness testing
- Dereverberation training
---
## 💻 Local Installation
```bash
git clone https://huggingface.co/spaces/mandipgoswami/acoustivision-pro
cd acoustivision-pro
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
python app.py
Open: http://localhost:7860
📈 Privacy & Analytics
AcoustiVision Pro records:
Anonymous session IDs
Usage counts
Feature adoption
Geographic aggregates
No IP addresses, emails, or personal data are stored.
All analytics are used solely for research impact assessment.
🤝 Contributing
Contributions are welcome in:
Full IEC STI implementation
Binaural IACC
Treatment recommendation
Ambisonics support
Measurement integration
Workflow:
Fork
Feature branch
Commit
Pull request
📚 References
Schroeder (1965), JASA
Allen & Berkley (1979), JASA
Houtgast & Steeneken (1985), JASA
ISO 3382 Series
ANSI S12.60
📜 Citation
If you use AcoustiVision Pro, please cite: arxiv: [arxiv.org/abs/2602.12299]
@software{goswami_acoustivision_2024,
  title   = {AcoustiVision Pro: Interactive RIR Analysis Platform},
  author  = {Goswami, Mandip},
  year    = {2024},
  url     = {https://huggingface.co/spaces/mandipgoswami/acoustivision-pro}
}
📄 License
MIT License © 2024–2026 Mandip Goswami
🙏 Acknowledgments
RIRmega & RIRmega Speech
Hugging Face
Acoustical Society of America
Open-source DSP community
<div align="center">
Built for the global acoustics research community
⭐ If you find this useful, please like and share ⭐
https://huggingface.co/spaces/mandipgoswami/acoustivision-pro
</div> ```