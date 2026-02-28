# app.py
# AcoustiVision Pro — Full Featured

import base64
import hashlib
import tempfile
from collections import Counter
import ast
import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files

import shutil
import os
import io
import json
import sqlite3
import datetime as dt
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, List

import numpy as np
import soundfile as sf
import librosa
import librosa.display
from scipy.signal import fftconvolve, butter, sosfilt

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import gradio as gr
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ═══════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════
ANALYTICS_DB = "impact_tracker.sqlite"
ANALYTICS_SALT = os.environ.get("ACOUSTIVISION_ANALYTICS_SALT", "change_this")
APP_TITLE = "AcoustiVision Pro"
IMPACT_DB_PATH = os.environ.get("ACOUSTIVISION_IMPACT_DB", "impact_tracker.sqlite")
MAX_AUDIO_SECONDS = float(os.environ.get("ACOUSTIVISION_MAX_AUDIO_SECONDS", "30"))
DEFAULT_SR = int(os.environ.get("ACOUSTIVISION_DEFAULT_SR", "48000"))
EPS = 1e-12

# Matplotlib colors (proper RGBA tuples)
MPL_BORDER = (136 / 255, 176 / 255, 226 / 255, 0.15)
MPL_GRID = (143 / 255, 163 / 255, 190 / 255, 0.10)
MPL_TICK = "#5e7490"
MPL_LABEL = "#8fa3be"
MPL_TITLE = "#e8edf4"
MPL_LINE = "#5b8def"
MPL_GUIDE = (143 / 255, 163 / 255, 190 / 255, 0.20)
MPL_GUIDE_TEXT = "#5e7490"
MPL_BG_FIG = "#0c1219"
MPL_BG_AX = "#111923"
MPL_BBOX_EDGE = (91 / 255, 141 / 255, 239 / 255, 0.20)
MPL_BBOX_FACE = "#111923"

# Standards database
STANDARDS = {
    "Classroom (ANSI S12.60)": {"RT60_max": 0.6, "STI_min": 0.60},
    "Open Office (ISO 3382-3)": {"RT60_max": 0.8, "STI_min": 0.50},
    "Private Office": {"RT60_max": 0.6, "STI_min": 0.55},
    "Hospital Ward": {"RT60_max": 0.8, "STI_min": 0.60},
    "Concert Hall": {"RT60_min": 1.5, "RT60_max": 2.5},
    "Lecture Hall": {"RT60_max": 1.0, "STI_min": 0.55},
    "Recording Studio": {"RT60_max": 0.4},
    "Worship Space": {"RT60_min": 1.2, "RT60_max": 3.0},
    "Restaurant": {"RT60_max": 0.9},
    "Conference Room": {"RT60_max": 0.7, "STI_min": 0.55},
}


# ═══════════════════════════════════════════
#  ANALYTICS + DB
# ═══════════════════════════════════════════
def analytics_init():
    con = sqlite3.connect(ANALYTICS_DB);
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS usage_events
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       ts_utc
                       TEXT
                       NOT
                       NULL,
                       user_hash
                       TEXT
                       NOT
                       NULL,
                       event_type
                       TEXT
                       NOT
                       NULL,
                       country
                       TEXT,
                       use_case
                       TEXT
                   )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user ON usage_events(user_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ts ON usage_events(ts_utc)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event ON usage_events(event_type)")
    con.commit();
    con.close()


def copy_to_app_temp(src_path):
    dst = os.path.join(tempfile.gettempdir(), os.path.basename(src_path))
    shutil.copy2(src_path, dst);
    return dst


def hash_user_id(raw_id):
    return hashlib.sha256(f"{ANALYTICS_SALT}:{raw_id}".encode()).hexdigest()


def now_utc(): return dt.datetime.utcnow().isoformat() + "Z"


def log_event(user_hash, event_type, country="Unknown", use_case=""):
    try:
        con = sqlite3.connect(ANALYTICS_DB);
        cur = con.cursor()
        cur.execute("INSERT INTO usage_events (ts_utc,user_hash,event_type,country,use_case) VALUES(?,?,?,?,?)",
                    (now_utc(), user_hash, event_type, country, use_case))
        con.commit();
        con.close()
    except Exception:
        pass


def _safe_literal(x):
    if x is None: return None
    if isinstance(x, (dict, list)): return x
    if not isinstance(x, str): return None
    try:
        return ast.literal_eval(x)
    except:
        return None


def _room_volume_from_size(rs):
    if not rs or len(rs) != 3: return None
    try:
        return float(rs[0]) * float(rs[1]) * float(rs[2])
    except:
        return None


def impact_init(db_path=IMPACT_DB_PATH):
    con = sqlite3.connect(db_path);
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS report_events
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       ts_utc
                       TEXT
                       NOT
                       NULL,
                       kind
                       TEXT
                       NOT
                       NULL,
                       meta_json
                       TEXT
                   )""")
    con.commit();
    con.close()


def impact_log(kind, meta=None, db_path=IMPACT_DB_PATH):
    impact_init(db_path);
    con = sqlite3.connect(db_path);
    cur = con.cursor()
    cur.execute("INSERT INTO report_events(ts_utc,kind,meta_json) VALUES(?,?,?)",
                (dt.datetime.utcnow().isoformat() + "Z", kind, json.dumps(meta or {})))
    con.commit();
    con.close()


def impact_count(kind="pdf_report", db_path=IMPACT_DB_PATH):
    impact_init(db_path);
    con = sqlite3.connect(db_path);
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM report_events WHERE kind=?", (kind,))
    n = int(cur.fetchone()[0] or 0);
    con.close();
    return n


# ═══════════════════════════════════════════
#  DATA STRUCTURES + HF
# ═══════════════════════════════════════════
@dataclass
class RIRData:
    y: np.ndarray;
    sr: int;
    name: str = "RIR"


@dataclass
class AudioData:
    y: np.ndarray;
    sr: int;
    name: str = "Audio"


def resolve_hf_wav_path(repo_id, wav_path_from_csv):
    wav_path_from_csv = (wav_path_from_csv or "").lstrip("/")
    files = list_repo_files(repo_id=repo_id, repo_type="dataset")
    if wav_path_from_csv in files: return wav_path_from_csv
    for c in [wav_path_from_csv.replace("\\", "/"), f"data/{wav_path_from_csv}",
              f"audio/{wav_path_from_csv}", f"wavs/{os.path.basename(wav_path_from_csv)}",
              f"train/wavs/{os.path.basename(wav_path_from_csv)}",
              f"val/wavs/{os.path.basename(wav_path_from_csv)}",
              f"test/wavs/{os.path.basename(wav_path_from_csv)}"]:
        if c in files: return c
    base = os.path.basename(wav_path_from_csv)
    hits = sorted([f for f in files if f.endswith("/" + base) or f == base], key=len)
    if hits: return hits[0]
    raise FileNotFoundError(f"Could not resolve `{wav_path_from_csv}` in `{repo_id}`.")


# ═══════════════════════════════════════════
#  AUDIO UTILS
# ═══════════════════════════════════════════
def _ensure_mono(y):
    if y.ndim == 1: return y
    if y.shape[0] < y.shape[-1] and y.shape[0] in (2, 3, 4): y = y.T
    return np.mean(y, axis=1)


def _normalize_audio(y): return y / (np.max(np.abs(y)) + EPS)


def load_wav(file_obj, target_sr=None, limit_seconds=None):
    if file_obj is None: raise ValueError("No file.")
    path = file_obj if isinstance(file_obj, str) else file_obj.name
    y, sr = sf.read(path, always_2d=False)
    y = _ensure_mono(np.asarray(y, dtype=np.float32))
    if limit_seconds:
        mx = int(limit_seconds * sr)
        if y.shape[0] > mx: y = y[:mx]
    if target_sr and sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr);
        sr = target_sr
    return AudioData(y=np.asarray(y, dtype=np.float32), sr=sr, name=os.path.basename(path))


def load_rir(file_obj, target_sr=DEFAULT_SR):
    a = load_wav(file_obj, target_sr=target_sr)
    y = a.y;
    thr = 1e-4 * (np.max(np.abs(y)) + EPS)
    idx = np.argmax(np.abs(y) > thr) if np.any(np.abs(y) > thr) else 0
    if idx > 0: y = y[idx:]
    if y.shape[0] > int(10 * a.sr): y = y[:int(10 * a.sr)]
    return RIRData(y=_normalize_audio(y), sr=a.sr, name=a.name)


# ═══════════════════════════════════════════
#  CORE ACOUSTICS
# ═══════════════════════════════════════════
def schroeder_edc(rir):
    e = rir.astype(np.float64) ** 2
    edc = np.flip(np.cumsum(np.flip(e)))
    return 10.0 * np.log10(edc / (np.max(edc) + EPS) + EPS)


def rt_from_edc(t, edc_db):
    out = {"EDT": None, "T20": None, "T30": None}

    def fit(lo, hi):
        idx = np.where((edc_db <= lo) & (edc_db >= hi))[0]
        if idx.size < 10: return None
        A = np.vstack([t[idx], np.ones(idx.size)]).T
        m, b = np.linalg.lstsq(A, edc_db[idx], rcond=None)[0]
        if abs(m) < 1e-9: return None
        t60 = (-60.0 - b) / m;
        return float(t60) if t60 > 0 else None

    out["EDT"] = fit(0, -10);
    out["T20"] = fit(-5, -25);
    out["T30"] = fit(-5, -35)
    return out


def clarity_definition(rir, sr):
    e = rir.astype(np.float64) ** 2
    i80 = int(min(len(rir), max(1, round(0.080 * sr))))
    i50 = int(min(len(rir), max(1, round(0.050 * sr))))
    c80 = 10.0 * np.log10((np.sum(e[:i80]) + EPS) / (np.sum(e[i80:]) + EPS))
    d50 = float((np.sum(e[:i50]) + EPS) / (np.sum(e) + EPS))
    return {"C80_dB": float(c80), "D50": d50}


def iacc_proxy(rir_stereo, sr, window_ms=80.0, max_lag_ms=1.0):
    if rir_stereo.ndim != 2 or rir_stereo.shape[1] != 2: return None
    n = int(min(rir_stereo.shape[0], round(window_ms / 1000 * sr)))
    x = rir_stereo[:n, 0].astype(np.float64);
    y = rir_stereo[:n, 1].astype(np.float64)
    x -= np.mean(x);
    y -= np.mean(y)
    denom = np.linalg.norm(x) * np.linalg.norm(y) + EPS
    ml = int(round(max_lag_ms / 1000 * sr));
    best = 0.0
    for lag in range(-ml, ml + 1):
        if lag < 0:
            xx, yy = x[-lag:], y[:len(x) + lag]
        elif lag > 0:
            xx, yy = x[:-lag], y[lag:]
        else:
            xx, yy = x, y
        if len(xx) < 8: continue
        best = max(best, abs(float(np.dot(xx, yy) / denom)))
    return float(best)


def sti_proxy(rt60_s, snr_db=20.0):
    if rt60_s is None or not np.isfinite(rt60_s): return None
    rt_term = 1.0 / (1.0 + (rt60_s / 0.8) ** 1.6)
    snr_term = 1.0 / (1.0 + 10 ** (-(snr_db - 15.0) / 10.0))
    return float(np.clip(0.15 + 0.85 * (0.65 * rt_term + 0.35 * snr_term), 0, 1))


# ═══════════════════════════════════════════
#  NEW FEATURE 1: OCTAVE-BAND RT60
# ═══════════════════════════════════════════
OCTAVE_CENTERS = [125, 250, 500, 1000, 2000, 4000]


def octave_band_rt60(rir, sr):
    results = {}
    for fc in OCTAVE_CENTERS:
        low = fc / np.sqrt(2)
        high = min(fc * np.sqrt(2), sr / 2 - 1)
        if low >= high:
            results[fc] = {"EDT": None, "T20": None, "T30": None}
            continue
        try:
            sos = butter(4, [low, high], btype='band', fs=sr, output='sos')
            filtered = sosfilt(sos, rir).astype(np.float64)
            edc_db = schroeder_edc(filtered)
            t = np.arange(len(edc_db)) / sr
            results[fc] = rt_from_edc(t, edc_db)
        except Exception:
            results[fc] = {"EDT": None, "T20": None, "T30": None}
    return results


def plot_octave_rt60(octave_data):
    freqs = list(octave_data.keys())
    labels = [f"{f}" if f < 1000 else f"{f // 1000}k" for f in freqs]
    t30 = [octave_data[f]["T30"] or 0 for f in freqs]
    t20 = [octave_data[f]["T20"] or 0 for f in freqs]
    edt = [octave_data[f]["EDT"] or 0 for f in freqs]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=t30, name="T30", marker_color="#5b8def"))
    fig.add_trace(go.Bar(x=labels, y=t20, name="T20", marker_color="#3ecf8e"))
    fig.add_trace(go.Bar(x=labels, y=edt, name="EDT", marker_color="#f0b429"))
    _apply_dark(fig)
    fig.update_layout(barmode="group", title="RT60 by Octave Band",
                      xaxis_title="Frequency (Hz)", yaxis_title="Time (s)")
    return fig


# ═══════════════════════════════════════════
#  NEW FEATURE 2: RIR WAVEFORM
# ═══════════════════════════════════════════
def plot_rir_waveform(rir, sr):
    t = np.arange(len(rir)) / sr
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t, y=rir, mode="lines", line=dict(width=1, color="#5b8def"),
        name="RIR",
        hovertemplate="Time: %{x:.4f}s<br>Amp: %{y:.4f}<extra></extra>"))

    peak_idx = np.argmax(np.abs(rir))
    fig.add_trace(go.Scatter(
        x=[t[peak_idx]], y=[rir[peak_idx]], mode="markers",
        marker=dict(size=10, color="#e74c3c", line=dict(width=1, color="white")),
        name=f"Direct ({t[peak_idx] * 1000:.1f}ms)"))

    fig.add_vline(x=0.050, line=dict(color="#f0b429", dash="dash", width=1),
                  annotation_text="50ms (D50)", annotation_position="top left",
                  annotation_font_color="#f0b429", annotation_font_size=10)
    fig.add_vline(x=0.080, line=dict(color="#3ecf8e", dash="dash", width=1),
                  annotation_text="80ms (C80)", annotation_position="top right",
                  annotation_font_color="#3ecf8e", annotation_font_size=10)

    _apply_dark(fig)
    fig.update_layout(title="Room Impulse Response Waveform",
                      xaxis_title="Time (s)", yaxis_title="Amplitude",
                      xaxis=dict(rangeslider=dict(visible=True, thickness=0.05)))
    return fig


# ═══════════════════════════════════════════
#  NEW FEATURE 3: STANDARDS COMPLIANCE
# ═══════════════════════════════════════════
def check_standards(rt60, sti, c80=None, d50=None):
    rows = []
    for name, limits in STANDARDS.items():
        checks = []
        if "RT60_max" in limits:
            val = rt60
            ok = val is not None and val <= limits["RT60_max"]
            checks.append(("RT60≤", f"{limits['RT60_max']}s",
                           f"{val:.2f}s" if val else "—", ok, val is not None))
        if "RT60_min" in limits:
            val = rt60
            ok = val is not None and val >= limits["RT60_min"]
            checks.append(("RT60≥", f"{limits['RT60_min']}s",
                           f"{val:.2f}s" if val else "—", ok, val is not None))
        if "STI_min" in limits:
            val = sti
            ok = val is not None and val >= limits["STI_min"]
            checks.append(("STI≥", f"{limits['STI_min']:.2f}",
                           f"{val:.2f}" if val else "—", ok, val is not None))

        for metric, req, actual, passed, has_val in checks:
            if has_val:
                icon = "<span style='color:#3ecf8e;font-weight:700;'>✓ PASS</span>" if passed else "<span style='color:#ef5350;font-weight:700;'>✗ FAIL</span>"
            else:
                icon = "<span style='color:var(--text-muted);'>—</span>"
            rows.append(f"""<tr>
                <td data-label="Standard" style="padding:6px 10px;border-bottom:1px solid var(--border);">{name}</td>
                <td data-label="Check" style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">{metric}</td>
                <td data-label="Required" style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">{req}</td>
                <td data-label="Measured" style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">{actual}</td>
                <td data-label="Result" style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">{icon}</td>
            </tr>""")

    return f"""
    <div style="overflow-x:auto;">
    <table class="av-std-table" style="width:100%;font-size:12px;border-collapse:collapse;color:var(--text-primary);">
      <thead>
        <tr style="border-bottom:2px solid var(--border);background:var(--bg-surface);">
          <th style="padding:8px 10px;text-align:left;color:var(--text-muted);font-size:11px;text-transform:uppercase;letter-spacing:0.05em;">Standard</th>
          <th style="padding:8px 10px;text-align:center;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Check</th>
          <th style="padding:8px 10px;text-align:center;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Required</th>
          <th style="padding:8px 10px;text-align:center;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Measured</th>
          <th style="padding:8px 10px;text-align:center;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Result</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    </div>"""


# ═══════════════════════════════════════════
#  NEW FEATURE 4: FREQUENCY RESPONSE
# ═══════════════════════════════════════════
def plot_frequency_response(rir, sr):
    N = len(rir)
    freqs = np.fft.rfftfreq(N, d=1.0 / sr)
    mag = np.abs(np.fft.rfft(rir))
    mag_db = 20 * np.log10(mag + EPS)

    # Smooth with moving average for readability
    kernel_size = max(1, len(mag_db) // 500)
    if kernel_size > 1:
        kernel = np.ones(kernel_size) / kernel_size
        mag_smooth = np.convolve(mag_db, kernel, mode='same')
    else:
        mag_smooth = mag_db

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=freqs, y=mag_db, mode="lines",
        line=dict(width=0.5, color="rgba(91,141,239,0.3)"), name="Raw",
        hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=freqs, y=mag_smooth, mode="lines",
        line=dict(width=2, color="#5b8def"), name="Smoothed",
        hovertemplate="Freq: %{x:.0f} Hz<br>Level: %{y:.1f} dB<extra></extra>"))

    # Mark octave bands
    for fc in OCTAVE_CENTERS:
        label = f"{fc}" if fc < 1000 else f"{fc // 1000}k"
        fig.add_vline(x=fc, line=dict(color="rgba(143,163,190,0.15)", width=1),
                      annotation_text=label, annotation_position="top",
                      annotation_font_size=9, annotation_font_color="#5e7490")

    _apply_dark(fig)
    fig.update_layout(
        title="Frequency Response (Magnitude Spectrum)",
        xaxis_title="Frequency (Hz)", yaxis_title="Magnitude (dB)",
        xaxis_type="log",
        xaxis=dict(range=[np.log10(20), np.log10(min(sr / 2, 20000))]))
    return fig


# ═══════════════════════════════════════════
#  NEW FEATURE 5: WATERFALL PLOT
# ═══════════════════════════════════════════
def plot_waterfall(rir, sr, n_fft=2048, hop=512, n_slices=30, max_freq=4000):
    S = np.abs(librosa.stft(rir, n_fft=n_fft, hop_length=hop))
    S_db = librosa.amplitude_to_db(S, ref=np.max)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop)

    # Limit frequency range
    freq_mask = freqs <= max_freq
    freqs_cut = freqs[freq_mask]
    S_cut = S_db[freq_mask, :]

    # Downsample time for readability
    step = max(1, len(times) // n_slices)
    time_idx = np.arange(0, len(times), step)

    # Color scale based on time
    n_traces = len(time_idx)
    colors = [f"rgba(91,141,239,{0.3 + 0.7 * (1 - i / max(n_traces - 1, 1))})" for i in range(n_traces)]

    fig = go.Figure()
    for ci, i in enumerate(time_idx):
        fig.add_trace(go.Scatter3d(
            x=freqs_cut, y=[times[i]] * len(freqs_cut), z=S_cut[:, i],
            mode="lines", line=dict(width=3, color=colors[ci]),
            showlegend=False,
            hovertemplate=f"Time: {times[i]:.3f}s<br>" + "Freq: %{x:.0f}Hz<br>Level: %{z:.1f}dB<extra></extra>"))

    fig.update_layout(
        title=dict(text="Waterfall Plot (Frequency Decay Over Time)",
                   font=dict(size=14, color="#2d3436")),
        paper_bgcolor="white",
        font=dict(color="#636e72", size=11),
        scene=dict(
            xaxis=dict(title=dict(text="Frequency (Hz)", font=dict(color="#2d3436", size=11)),
                       backgroundcolor="rgba(230,235,245,0.6)",
                       gridcolor="rgba(180,190,210,0.4)", tickfont=dict(size=9)),
            yaxis=dict(title=dict(text="Time (s)", font=dict(color="#2d3436", size=11)),
                       backgroundcolor="rgba(225,230,245,0.6)",
                       gridcolor="rgba(180,190,210,0.4)", tickfont=dict(size=9)),
            zaxis=dict(title=dict(text="Level (dB)", font=dict(color="#2d3436", size=11)),
                       backgroundcolor="rgba(220,225,240,0.6)",
                       gridcolor="rgba(180,190,210,0.4)", tickfont=dict(size=9)),
            camera=dict(eye=dict(x=1.6, y=-1.4, z=0.7)),
            aspectmode="manual", aspectratio=dict(x=2, y=1.5, z=0.8)),
        margin=dict(l=0, r=0, t=40, b=0))
    return fig


# ═══════════════════════════════════════════
#  NEW FEATURE 7: CSV EXPORT
# ═══════════════════════════════════════════
def export_metrics_csv(metrics_ui, octave_data, room_modes_data):
    rows = []
    # Main metrics
    for k, v in metrics_ui.items():
        rows.append({"Category": "Main", "Metric": k, "Value": str(v)})
    # Octave band
    if octave_data:
        for freq, vals in octave_data.items():
            for param, val in vals.items():
                rows.append({"Category": "Octave",
                             "Metric": f"{param}_{freq}Hz",
                             "Value": f"{val:.4f}" if val else "—"})
    # Room modes
    if room_modes_data:
        for i, mode in enumerate(room_modes_data[:30]):
            rows.append({"Category": "RoomMode",
                         "Metric": f"Mode_{i + 1} ({mode['type']})",
                         "Value": f"{mode['freq']:.1f} Hz"})

    df = pd.DataFrame(rows)
    path = os.path.join(tempfile.gettempdir(), "acoustivision_metrics.csv")
    df.to_csv(path, index=False)
    return path


# ═══════════════════════════════════════════
#  NEW FEATURE 9: ROOM MODES
# ═══════════════════════════════════════════
def compute_room_modes(L, W, H, max_freq=500):
    c = 343.0
    modes = []
    for nx in range(0, 12):
        for ny in range(0, 12):
            for nz in range(0, 12):
                if nx == 0 and ny == 0 and nz == 0: continue
                f = (c / 2) * np.sqrt((nx / L) ** 2 + (ny / W) ** 2 + (nz / H) ** 2)
                if f <= max_freq:
                    order = sum([nx > 0, ny > 0, nz > 0])
                    modes.append({
                        "freq": float(f), "nx": nx, "ny": ny, "nz": nz,
                        "type": ["", "Axial", "Tangential", "Oblique"][order],
                        "label": f"({nx},{ny},{nz})"})
    return sorted(modes, key=lambda m: m["freq"])


def plot_room_modes(modes, max_freq=500):
    if not modes:
        fig = go.Figure()
        fig.add_annotation(text="No modes found", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    type_colors = {"Axial": "#5b8def", "Tangential": "#3ecf8e", "Oblique": "#f0b429"}

    fig = go.Figure()
    for mtype in ["Axial", "Tangential", "Oblique"]:
        mf = [m for m in modes if m["type"] == mtype]
        if not mf: continue
        fig.add_trace(go.Scatter(
            x=[m["freq"] for m in mf],
            y=[mtype] * len(mf),
            mode="markers+text",
            marker=dict(size=10, color=type_colors[mtype],
                        line=dict(width=1, color="rgba(255,255,255,0.3)")),
            text=[m["label"] for m in mf],
            textposition="top center",
            textfont=dict(size=8, color=type_colors[mtype]),
            name=f"{mtype} ({len(mf)})",
            hovertemplate="%{text}<br>%{x:.1f} Hz<extra></extra>"))

    # Density histogram on secondary y-axis
    all_freqs = [m["freq"] for m in modes]
    fig.add_trace(go.Histogram(
        x=all_freqs, nbinsx=int(max_freq / 10),
        marker_color="rgba(91,141,239,0.2)",
        yaxis="y2", name="Density", showlegend=False))

    _apply_dark(fig)
    fig.update_layout(
        title=f"Room Modes (up to {max_freq} Hz) — {len(modes)} total",
        xaxis=dict(title=dict(text="Frequency (Hz)")),
        yaxis=dict(title=dict(text="Mode Type")),
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            title=dict(text="Count", font=dict(color="#5b8def")),
            tickfont=dict(color="#5b8def"),
        ),
        height=350)
    return fig


# ═══════════════════════════════════════════
#  EXISTING VISUALIZATIONS (updated)
# ═══════════════════════════════════════════
PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(12,18,25,0.6)",
    font=dict(color="#8fa3be", family="Inter, sans-serif"),
    title_font=dict(color="#e8edf4", size=14),
    colorway=["#5b8def", "#3ecf8e", "#f0b429", "#ef5350", "#a78bfa", "#38bdf8", "#fb923c"])


def _apply_dark(fig):
    fig.update_layout(**PLOTLY_DARK, margin=dict(l=10, r=10, t=36, b=10),
                      legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(136,176,226,0.08)", font=dict(size=10)))
    fig.update_xaxes(gridcolor="rgba(136,176,226,0.06)", zerolinecolor="rgba(136,176,226,0.08)")
    fig.update_yaxes(gridcolor="rgba(136,176,226,0.06)", zerolinecolor="rgba(136,176,226,0.08)")
    return fig


def plot_3d_early_reflections(room_L, room_W, room_H, src, rec, n_rays=80):
    L, W, H = room_L, room_W, room_H;
    sx, sy, sz = src;
    rx, ry, rz = rec
    edges = [([0, L], [0, 0], [0, 0]), ([0, 0], [0, W], [0, 0]), ([0, 0], [0, 0], [0, H]),
             ([L, L], [0, W], [0, 0]), ([L, L], [0, 0], [0, H]), ([0, L], [W, W], [0, 0]),
             ([0, 0], [W, W], [0, H]), ([L, L], [W, W], [0, H]), ([0, L], [0, 0], [H, H]),
             ([0, L], [W, W], [H, H]), ([0, 0], [0, W], [H, H]), ([L, L], [0, W], [H, H])]
    fig = go.Figure()
    for i, (ex, ey, ez) in enumerate(edges):
        fig.add_trace(go.Scatter3d(x=ex, y=ey, z=ez, mode="lines",
                                   line=dict(width=3, color="rgba(0,200,180,0.7)"),
                                   showlegend=(i == 0), name="Room" if i == 0 else "", hoverinfo="skip"))
    fig.add_trace(go.Scatter3d(x=[sx, rx], y=[sy, ry], z=[sz, rz], mode="lines",
                               line=dict(width=6, color="#00c9a7"), name="Direct"))
    imgs = [(-sx, sy, sz), (2 * L - sx, sy, sz), (sx, -sy, sz), (sx, 2 * W - sy, sz), (sx, sy, -sz),
            (sx, sy, 2 * H - sz)]
    nms = ["x=0", f"x={L:.0f}", "y=0", f"y={W:.0f}", "floor", "ceil"]
    cls = ["#6c5ce7", "#fdcb6e", "#00b894", "#e17055", "#a8e6cf", "#ff6b81"]
    for (ix, iy, iz), nm, cl in zip(imgs, nms, cls):
        fig.add_trace(go.Scatter3d(x=[ix, rx], y=[iy, ry], z=[iz, rz], mode="lines",
                                   line=dict(width=3, dash="dot", color=cl), name=f"Refl {nm}"))
    rng = np.random.default_rng(42);
    pts = rng.random((n_rays, 3)) * np.array([L, W, H])
    fig.add_trace(go.Scatter3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="markers",
                               marker=dict(size=3.5, color="#f39c12", opacity=0.7), name="Sample rays"))
    fig.add_trace(go.Scatter3d(x=[sx], y=[sy], z=[sz], mode="markers+text",
                               marker=dict(size=12, color="#6c5ce7", symbol="circle",
                                           line=dict(width=1, color="white")),
                               text=["Source"], textposition="top center", textfont=dict(size=12, color="#6c5ce7"),
                               showlegend=False))
    fig.add_trace(go.Scatter3d(x=[rx], y=[ry], z=[rz], mode="markers+text",
                               marker=dict(size=12, color="#e74c3c", line=dict(width=1, color="white")),
                               text=["Receiver"], textposition="top center", textfont=dict(size=12, color="#e74c3c"),
                               showlegend=False))
    ax_common = dict(backgroundcolor="rgba(230,235,245,0.6)", gridcolor="rgba(180,190,210,0.4)",
                     zerolinecolor="rgba(180,190,210,0.5)", showbackground=True,
                     tickfont=dict(color="#636e72", size=10))
    fig.update_layout(
        title=dict(text="3D Reflections / Rays", font=dict(size=15, color="#2d3436")),
        paper_bgcolor="white", font=dict(color="#636e72", size=11),
        scene=dict(
            xaxis=dict(title=dict(text="x(m)", font=dict(color="#2d3436", size=12)), **ax_common),
            yaxis=dict(title=dict(text="y(m)", font=dict(color="#2d3436", size=12)), **ax_common),
            zaxis=dict(title=dict(text="z(m)", font=dict(color="#2d3436", size=12)), **ax_common),
            aspectmode="data",
            camera=dict(eye=dict(x=0.8, y=0.8, z=0.6), up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=-0.1))),
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5,
                    font=dict(size=11, color="#2d3436"), bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="rgba(200,200,200,0.5)", borderwidth=1),
        margin=dict(l=0, r=0, t=40, b=0))
    return fig


def _write_png_temp(png_bytes, prefix="plot_"):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".png");
    os.close(fd)
    with open(path, "wb") as f: f.write(png_bytes)
    return path


def plot_edc_matplotlib(edc_db, sr):
    t = np.arange(len(edc_db)) / sr;
    rt = rt_from_edc(t, edc_db)
    with plt.style.context("dark_background"):
        fig, ax = plt.subplots(figsize=(9, 4), dpi=150)
        fig.patch.set_facecolor(MPL_BG_FIG);
        ax.set_facecolor(MPL_BG_AX)
        ax.plot(t, edc_db, color=MPL_LINE, linewidth=1.8)
        ax.set_title("Energy Decay Curve", fontsize=13, color=MPL_TITLE, pad=10)
        ax.set_xlabel("Time (s)", color=MPL_LABEL);
        ax.set_ylabel("EDC (dB)", color=MPL_LABEL)
        ax.set_ylim(-80, 5);
        ax.grid(True, alpha=0.1, color=MPL_LABEL);
        ax.tick_params(colors=MPL_TICK)
        for sp in ax.spines.values(): sp.set_color(MPL_BORDER)
        for lev, lab in zip([0, -5, -10, -25, -35, -60], ["0dB", "-5", "-10", "-25", "-35", "-60dB"]):
            ax.axhline(lev, lw=0.8, color=MPL_GUIDE, ls="--")
            ax.text(t[-1] * 0.98, lev + 1.2, lab, fontsize=7, color=MPL_GUIDE_TEXT, ha="right")
        parts = [f"{k}={rt[k]:.2f}s" if rt[k] else f"{k}=—" for k in ("EDT", "T20", "T30")]
        ax.text(0.02, 0.06, "  ·  ".join(parts), transform=ax.transAxes, fontsize=9, color=MPL_LINE,
                bbox=dict(facecolor=MPL_BBOX_FACE, edgecolor=MPL_BBOX_EDGE, boxstyle="round,pad=0.4"))
        fig.tight_layout();
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor="none");
        plt.close(fig);
        buf.seek(0)
    return buf.getvalue(), "  ·  ".join(parts)


def plot_melspec_matplotlib(y, sr, n_mels=128):
    S_db = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, fmax=sr / 2), ref=np.max)
    with plt.style.context("dark_background"):
        fig, ax = plt.subplots(figsize=(9, 4), dpi=150)
        fig.patch.set_facecolor(MPL_BG_FIG);
        ax.set_facecolor(MPL_BG_AX)
        img = librosa.display.specshow(S_db, sr=sr, x_axis="time", y_axis="mel", ax=ax, cmap="magma")
        ax.set_title("Mel Spectrogram", fontsize=13, color=MPL_TITLE, pad=10)
        cb = fig.colorbar(img, ax=ax, format="%+2.0f dB", pad=0.02)
        cb.ax.yaxis.set_tick_params(color=MPL_TICK);
        cb.outline.set_edgecolor(MPL_BORDER)
        plt.setp(plt.getp(cb.ax, "yticklabels"), color=MPL_LABEL)
        ax.tick_params(colors=MPL_TICK)
        for sp in ax.spines.values(): sp.set_color(MPL_BORDER)
        fig.tight_layout();
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor="none");
        plt.close(fig);
        buf.seek(0)
    return buf.getvalue()


def radar_fingerprint_plot(metrics):
    c80, d50, iacc, sti = metrics.get("C80_dB"), metrics.get("D50"), metrics.get("IACC"), metrics.get("STI_proxy")
    nc = lambda x: None if x is None or not np.isfinite(x) else float(np.clip((x + 5) / 15, 0, 1))
    nd = lambda x: None if x is None or not np.isfinite(x) else float(np.clip(x, 0, 1))
    ni = lambda x: None if x is None or not np.isfinite(x) else float(np.clip(1 - (x - 0.2) / 0.8, 0, 1))
    axes = ["Clarity(C80)", "Definition(D50)", "Spatial(IACC)", "Intelligibility(STI)"]
    vals = [nc(c80), nd(d50), ni(iacc), nd(sti)];
    pv = [v if v else 0.0 for v in vals]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=pv + [pv[0]], theta=axes + [axes[0]], fill="toself",
                                  fillcolor="rgba(91,141,239,0.12)", line=dict(color="#5b8def", width=2),
                                  marker=dict(size=6, color="#5b8def"), name="Fingerprint"))
    fig.update_layout(polar=dict(bgcolor="rgba(12,18,25,0.6)",
                                 radialaxis=dict(visible=True, range=[0, 1], gridcolor="rgba(136,176,226,0.08)",
                                                 tickfont=dict(size=8, color="#5e7490")),
                                 angularaxis=dict(gridcolor="rgba(136,176,226,0.08)",
                                                  tickfont=dict(size=10, color="#8fa3be"))),
                      showlegend=False)
    _apply_dark(fig);
    fig.update_layout(title="Acoustic Fingerprint")
    return fig


# ═══════════════════════════════════════════
#  WELLNESS + CONVOLUTION
# ═══════════════════════════════════════════
def wellness_score(room_volume_m3, rt60_s, sti, c80_db, d50):
    rt = rt60_s if rt60_s and np.isfinite(rt60_s) else 1.2
    sv = sti if sti and np.isfinite(sti) else 0.5
    c = c80_db if c80_db and np.isfinite(c80_db) else 0.0
    dv = d50 if d50 and np.isfinite(d50) else 0.5
    raw = (0.45 / (1 + (rt / 0.9) ** 1.8) + 0.25 * np.clip(sv, 0, 1) + 0.20 * np.clip(dv, 0, 1) + 0.10 * np.clip(
        (c + 2) / 10, 0, 1))
    raw *= 1.0 / (1 + max(0, (room_volume_m3 - 300)) / 800)
    score = int(np.round(100 * np.clip(raw, 0, 1)));
    suit = []
    if rt < 0.8 and sv >= 0.6 and dv >= 0.5: suit.append("Classroom")
    if rt < 0.7 and sv >= 0.65: suit.append("Hospital/Clinical")
    if 0.6 <= rt <= 1.2: suit.append("Office/Meeting")
    if rt >= 1.2 and c < 0: suit.append("Reverberant space")
    if rt >= 1.0 and c <= 0: suit.append("Music rehearsal")
    if rt < 0.6 and c > 2: suit.append("Broadcast/Studio")
    if not suit: suit = ["General-purpose"]
    return {"score": score, "suitability": suit,
            "rationale": "Combines RT60, STI proxy, D50, C80 with volume adjustment."}


def convolve_dry_with_rir(dry, rir):
    if dry.sr != rir.sr:
        y = librosa.resample(dry.y, orig_sr=dry.sr, target_sr=rir.sr)
        dry = AudioData(y=y.astype(np.float32), sr=rir.sr, name=dry.name)
    y = fftconvolve(dry.y.astype(np.float32), rir.y.astype(np.float32), mode="full").astype(np.float32)
    return AudioData(y=_normalize_audio(y) * 0.95, sr=dry.sr, name=f"conv_{dry.name}")


# ═══════════════════════════════════════════
#  PDF REPORT (updated with new features)
# ═══════════════════════════════════════════
def _png_to_ir(b): return ImageReader(io.BytesIO(b))


def generate_pdf_report(out_path, title, rir_name, dry_name, metrics, wellness,
                        edc_png, spec_png, fingerprint_fig, reflections_fig):
    c = canvas.Canvas(out_path, pagesize=letter);
    W, H = letter
    c.setFont("Helvetica-Bold", 18);
    c.drawString(0.75 * inch, H - 0.85 * inch, title)
    c.setFont("Helvetica", 10);
    c.setFillGray(0.5)
    c.drawString(0.75 * inch, H - 1.1 * inch, f"Generated: {dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    c.setFillGray(0)
    c.setFont("Helvetica-Bold", 12);
    c.drawString(0.75 * inch, H - 1.45 * inch, "Inputs")
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, H - 1.65 * inch, f"RIR: {rir_name}");
    c.drawString(0.75 * inch, H - 1.82 * inch, f"Dry: {dry_name or '—'}")
    c.setFont("Helvetica-Bold", 12);
    c.drawString(0.75 * inch, H - 2.15 * inch, "Key Metrics")
    c.setFont("Helvetica", 10)
    for i, (k, v) in enumerate([("EDT", metrics.get("EDT_s")), ("T20", metrics.get("T20_s")),
                                ("T30", metrics.get("T30_s")), ("C80", f"{metrics.get('C80_dB')} dB"),
                                ("D50", metrics.get("D50")), ("IACC", metrics.get("IACC")),
                                ("STI", metrics.get("STI_proxy"))]):
        c.drawString(0.9 * inch, H - 2.35 * inch - i * 0.16 * inch, f"{k}: {v}")
    c.setFont("Helvetica-Bold", 12);
    c.drawString(0.75 * inch, H - 3.65 * inch, "Wellness")
    c.setFont("Helvetica", 10)
    c.drawString(0.9 * inch, H - 3.85 * inch, f"Score: {wellness.get('score')}/100")
    c.drawString(0.9 * inch, H - 4.02 * inch, f"Suggested: {', '.join(wellness.get('suitability', []))}")
    c.showPage()
    c.setFont("Helvetica-Bold", 16);
    c.drawString(0.75 * inch, H - 0.85 * inch, "Plots")
    if edc_png: c.drawImage(_png_to_ir(edc_png), 0.75 * inch, H - 4.3 * inch, width=7 * inch, height=3.2 * inch,
                            preserveAspectRatio=True, mask="auto")
    if spec_png: c.drawImage(_png_to_ir(spec_png), 0.75 * inch, H - 7.8 * inch, width=7 * inch, height=3.2 * inch,
                             preserveAspectRatio=True, mask="auto")
    c.showPage()
    try:
        import plotly.io as pio
        fp = pio.to_image(fingerprint_fig, format="png", scale=2);
        rp = pio.to_image(reflections_fig, format="png", scale=2)
        c.drawImage(_png_to_ir(fp), 0.75 * inch, H - 4.2 * inch, width=3.4 * inch, height=3 * inch,
                    preserveAspectRatio=True, mask="auto")
        c.drawImage(_png_to_ir(rp), 4.35 * inch, H - 7.2 * inch, width=3.4 * inch, height=6 * inch,
                    preserveAspectRatio=True, mask="auto")
    except:
        c.setFont("Helvetica", 10);
        c.drawString(0.75 * inch, H - 1.15 * inch, "Install kaleido for chart export.")
    c.save()


# ═══════════════════════════════════════════
#  HF SEARCH
# ═══════════════════════════════════════════
def hf_search_rirmega(dataset_name, volume_range, rt60_range, absorption_range,
                      split_filter="any", metadata_filename="metadata.csv", limit=12):
    try:
        local_csv = hf_hub_download(repo_id=dataset_name, repo_type="dataset", filename=metadata_filename)
    except Exception as e:
        return (f"<div class='av-status warn'>⚠ {e}</div>", [])
    try:
        df = pd.read_csv(local_csv)
    except Exception as e:
        return (f"<div class='av-status warn'>⚠ CSV: {e}</div>", [])
    df["room_size_parsed"] = df["room_size"].apply(_safe_literal)
    df["volume_m3"] = df["room_size_parsed"].apply(_room_volume_from_size)
    df["metrics_parsed"] = df["metrics"].apply(_safe_literal)
    gm = lambda d, k: d.get(k) if isinstance(d, dict) else None
    df["rt60"] = df["metrics_parsed"].apply(lambda d: gm(d, "rt60"))
    df["drr_db"] = df["metrics_parsed"].apply(lambda d: gm(d, "drr_db"))
    df["c80_db"] = df["metrics_parsed"].apply(lambda d: gm(d, "c80_db"))
    vmin, vmax = map(float, volume_range);
    rmin, rmax = map(float, rt60_range);
    amin, amax = map(float, absorption_range)
    ir = lambda x, a, b: a <= float(x) <= b if x is not None else False
    mask = df["volume_m3"].apply(lambda x: ir(x, vmin, vmax))
    mask &= df["rt60"].apply(lambda x: ir(x, rmin, rmax))
    mask &= df["absorption"].apply(lambda x: ir(x, amin, amax))
    if split_filter in ("train", "test", "val"): mask &= df["wav"].astype(str).str.startswith(f"{split_filter}/")
    hits = df[mask].copy()
    if hits.empty: return ("<div class='av-status warn'>No matches.</div>", [])
    vm, rm, am = (vmin + vmax) / 2, (rmin + rmax) / 2, (amin + amax) / 2
    hits["score"] = (hits["volume_m3"] - vm).abs().fillna(1e9) + 200 * (hits["rt60"] - rm).abs().fillna(1e9) + 50 * (
            hits["absorption"] - am).abs().fillna(1e9)
    hits = hits.sort_values("score").head(int(limit))
    choices = []
    for _, r in hits.iterrows():
        wav = str(r.get("wav", ""))
        f_ = lambda x, n=2: f"{float(x):.{n}f}" if x is not None else "—"
        label = f"{os.path.basename(wav)} · V={f_(r.get('volume_m3'), 1)}m³ RT60={f_(r.get('rt60'), 2)}s DRR={f_(r.get('drr_db'), 1)}dB C80={f_(r.get('c80_db'), 1)}dB abs={f_(r.get('absorption'), 2)}"
        blob = {"wav": wav, "fs": r.get("fs"), "volume_m3": r.get("volume_m3"),
                "room_size": r.get("room_size_parsed"), "absorption": r.get("absorption"),
                "max_order": r.get("max_order"), "source": _safe_literal(r.get("source")),
                "microphone": _safe_literal(r.get("microphone")), "metrics": r.get("metrics_parsed")}
        choices.append((label, json.dumps(blob)))
    return (f"<div class='av-status success'>✓ <b>{len(choices)}</b> matches</div>", choices)


# ═══════════════════════════════════════════
#  MAIN ANALYSIS PIPELINE (expanded)
# ═══════════════════════════════════════════
def analyze_rir_and_build_outputs(rir_file, dry_file, room_L, room_W, room_H,
                                  src_x, src_y, src_z, rec_x, rec_y, rec_z,
                                  heatmap_material, heatmap_strength, assumed_snr_db, user_id_raw, use_case):
    user_hash = hash_user_id(user_id_raw or "unknown")
    log_event(user_hash=user_hash, event_type="run_analysis", use_case=use_case)
    if rir_file is None: raise gr.Error("Upload or select an RIR .wav first.")

    rir = load_rir(rir_file, target_sr=DEFAULT_SR)

    # IACC
    iacc_val = None
    try:
        path = rir_file if isinstance(rir_file, str) else rir_file.name
        y2, sr2 = sf.read(path, always_2d=True)
        if y2.shape[1] >= 2:
            if sr2 != rir.sr:
                yL = librosa.resample(y2[:, 0].astype(np.float32), orig_sr=sr2, target_sr=rir.sr)
                yR = librosa.resample(y2[:, 1].astype(np.float32), orig_sr=sr2, target_sr=rir.sr)
                iacc_val = iacc_proxy(np.stack([yL, yR], axis=1), rir.sr)
            else:
                iacc_val = iacc_proxy(y2.astype(np.float32), sr2)
    except:
        pass

    # Core metrics
    edc_db = schroeder_edc(rir.y);
    t = np.arange(len(edc_db)) / rir.sr
    rt = rt_from_edc(t, edc_db);
    cd = clarity_definition(rir.y, rir.sr)
    rt_for_sti = rt["T30"] or rt["T20"] or rt["EDT"]
    sti = sti_proxy(rt_for_sti, snr_db=float(assumed_snr_db))
    room_volume = float(room_L) * float(room_W) * float(room_H)
    well = wellness_score(room_volume, rt_for_sti, sti, cd["C80_dB"], cd["D50"])

    # NEW: Octave band RT60
    octave_data = octave_band_rt60(rir.y, rir.sr)
    octave_fig = plot_octave_rt60(octave_data)

    # NEW: RIR waveform
    waveform_fig = plot_rir_waveform(rir.y, rir.sr)

    # NEW: Standards compliance
    standards_html = check_standards(rt_for_sti, sti, cd["C80_dB"], cd["D50"])

    # NEW: Frequency response
    freq_resp_fig = plot_frequency_response(rir.y, rir.sr)

    # NEW: Waterfall
    waterfall_fig = plot_waterfall(rir.y, rir.sr)

    # NEW: Room modes
    rL, rW, rH = float(room_L), float(room_W), float(room_H)
    modes_data = compute_room_modes(rL, rW, rH, max_freq=500)
    modes_fig = plot_room_modes(modes_data, max_freq=500)

    # 3D reflections
    reflections = plot_3d_early_reflections(rL, rW, rH,
                                            (float(src_x), float(src_y), float(src_z)),
                                            (float(rec_x), float(rec_y), float(rec_z)))

    # Spectrogram
    S_db = librosa.power_to_db(librosa.feature.melspectrogram(y=rir.y, sr=rir.sr, n_mels=128, fmax=rir.sr / 2),
                               ref=np.max)
    mats = {"None (raw)": 0, "Concrete (low absorption)": 0.15, "Painted drywall (mid)": 0.35,
            "Curtains (high high-freq)": 0.65, "Carpet (mid/high)": 0.55, "Acoustic panels (broadband)": 0.75}
    base = mats.get(heatmap_material, 0.0);
    strength = float(heatmap_strength)
    tilt = (np.linspace(0, 1, S_db.shape[0])[:, None] ** 1.3) * base * strength * 18.0;
    S_vis = S_db - tilt
    spec_fig = go.Figure(data=go.Heatmap(z=S_vis, x=np.linspace(0, len(rir.y) / rir.sr, S_vis.shape[1]),
                                         y=np.arange(S_vis.shape[0]), colorscale="Magma",
                                         colorbar=dict(title="dB", tickfont=dict(color="#8fa3be")),
                                         hovertemplate="T:%{x:.3f}s Mel:%{y} dB:%{z:.1f}<extra></extra>"))
    _apply_dark(spec_fig);
    spec_fig.update_layout(title="Mel Spectrogram", xaxis_title="Time(s)", yaxis_title="Mel")

    # Fingerprint
    fingerprint = radar_fingerprint_plot({"C80_dB": cd["C80_dB"], "D50": cd["D50"], "IACC": iacc_val, "STI_proxy": sti})

    # EDC + spec PNG for report
    edc_png, edc_txt = plot_edc_matplotlib(edc_db, rir.sr)
    edc_path = _write_png_temp(edc_png, prefix="edc_")
    spec_png = plot_melspec_matplotlib(rir.y, rir.sr)

    # Auralization
    dry_audio_out = wet_audio_out = None;
    dry_name = None
    if dry_file is not None:
        dry = load_wav(dry_file, target_sr=rir.sr, limit_seconds=MAX_AUDIO_SECONDS)
        wet = convolve_dry_with_rir(dry, rir)
        dry_audio_out = (dry.sr, dry.y);
        wet_audio_out = (wet.sr, wet.y);
        dry_name = dry.name

    def fmt(x, n=3):
        if x is None or (isinstance(x, float) and not np.isfinite(x)): return "—"
        return f"{x:.{n}f}"

    metrics_ui = {
        "EDT_s": fmt(rt["EDT"], 2), "T20_s": fmt(rt["T20"], 2), "T30_s": fmt(rt["T30"], 2),
        "C80_dB": fmt(cd["C80_dB"], 2), "D50": fmt(cd["D50"], 3),
        "IACC": fmt(iacc_val, 3) if iacc_val else "— (stereo)",
        "STI_proxy": fmt(sti, 3) if sti else "—",
        "RoomVolume_m3": fmt(room_volume, 1),
        "WellnessScore": str(well["score"]),
        "SuggestedUse": ", ".join(well["suitability"])}

    ws = well["score"];
    w_class = "low" if ws < 40 else ("mid" if ws < 70 else "")

    kpi_html = f"""
    <div class="av-kpi-grid">
      <div class="av-kpi-card"><div class="av-kpi-label">RT60 (T30)</div><div class="av-kpi-value">{metrics_ui["T30_s"]}<span class="av-kpi-unit">s</span></div></div>
      <div class="av-kpi-card"><div class="av-kpi-label">EDT</div><div class="av-kpi-value">{metrics_ui["EDT_s"]}<span class="av-kpi-unit">s</span></div></div>
      <div class="av-kpi-card"><div class="av-kpi-label">T20</div><div class="av-kpi-value">{metrics_ui["T20_s"]}<span class="av-kpi-unit">s</span></div></div>
      <div class="av-kpi-card"><div class="av-kpi-label">C80</div><div class="av-kpi-value">{metrics_ui["C80_dB"]}<span class="av-kpi-unit">dB</span></div></div>
      <div class="av-kpi-card"><div class="av-kpi-label">D50</div><div class="av-kpi-value">{metrics_ui["D50"]}</div></div>
      <div class="av-kpi-card"><div class="av-kpi-label">STI</div><div class="av-kpi-value">{metrics_ui["STI_proxy"]}</div></div>
    </div>
    <div class="av-wellness-wrap {w_class}">
      <div class="av-wellness-score {w_class}">{well['score']}</div>
      <div class="av-wellness-detail">
        <div class="av-wellness-label">Wellness / 100</div>
        <div class="av-wellness-uses"><b>Suggested:</b> {', '.join(well['suitability'])}</div>
        <div class="av-wellness-note">{well['rationale']}</div>
      </div>
    </div>
    <div class="av-muted" style="margin-top:4px;">IACC: {metrics_ui["IACC"]} · Vol: {metrics_ui["RoomVolume_m3"]}m³</div>"""

    state = {"rir_name": rir.name, "dry_name": dry_name, "metrics": metrics_ui, "wellness": well,
             "edc_png_b64": base64.b64encode(edc_png).decode("ascii"),
             "spec_png_b64": base64.b64encode(spec_png).decode("ascii"),
             "fingerprint_json": fingerprint.to_json(), "reflections_json": reflections.to_json(),
             "octave_data": {str(k): v for k, v in octave_data.items()},
             "room_modes": [{"freq": m["freq"], "type": m["type"], "label": m["label"]} for m in modes_data[:30]]}

    # Return all 15 outputs
    return (
        kpi_html,  # 1: KPI cards
        reflections,  # 2: 3D plot
        edc_path,  # 3: EDC image
        spec_fig,  # 4: Spectrogram
        fingerprint,  # 5: Fingerprint radar
        waveform_fig,  # 6: NEW: RIR waveform
        octave_fig,  # 7: NEW: Octave RT60
        freq_resp_fig,  # 8: NEW: Frequency response
        waterfall_fig,  # 9: NEW: Waterfall
        modes_fig,  # 10: NEW: Room modes
        standards_html,  # 11: NEW: Standards compliance
        dry_audio_out,  # 12: Dry audio
        wet_audio_out,  # 13: Wet audio
        json.dumps(metrics_ui, indent=2),  # 14: JSON
        state,  # 15: State for PDF
    )


# ═══════════════════════════════════════════
#  CSV EXPORT WRAPPER
# ═══════════════════════════════════════════
def export_csv_from_state(state_json):
    if not state_json:
        raise gr.Error("Run analysis first.")
    metrics = state_json.get("metrics", {})
    octave_raw = state_json.get("octave_data", {})
    # Convert string keys back to int
    octave_data = {}
    for k, v in octave_raw.items():
        try:
            octave_data[int(k)] = v
        except:
            octave_data[k] = v
    modes_data = state_json.get("room_modes", [])
    return export_metrics_csv(metrics, octave_data, modes_data)


# ═══════════════════════════════════════════
#  PDF BUILDER
# ═══════════════════════════════════════════
def build_pdf_from_state(state_json, user_id_raw, use_case):
    user_hash = hash_user_id(user_id_raw or "unknown")
    log_event(user_hash=user_hash, event_type="pdf_report", use_case=use_case)
    if not state_json: raise gr.Error("Run analysis first.")
    os.makedirs("reports", exist_ok=True)
    out_path = os.path.join("reports", f"report_{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf")
    generate_pdf_report(out_path, f"{APP_TITLE} Report",
                        state_json.get("rir_name", "RIR"), state_json.get("dry_name"),
                        state_json.get("metrics", {}), state_json.get("wellness", {}),
                        base64.b64decode(state_json["edc_png_b64"]) if state_json.get("edc_png_b64") else b"",
                        base64.b64decode(state_json["spec_png_b64"]) if state_json.get("spec_png_b64") else b"",
                        go.Figure(json.loads(state_json["fingerprint_json"])),
                        go.Figure(json.loads(state_json["reflections_json"])))
    impact_log("pdf_report", meta={"app": APP_TITLE});
    sync_impact_ledger_if_due(every_n_events=10)  # uploads on every 10 events
    # or force=True to upload on every PDF:
    # sync_impact_ledger_if_due(force=True)

    return out_path


def get_impact_stats_md():
    return f"<span class='av-impact'><b>{impact_count('pdf_report')}</b> reports · anon</span>"


def get_analytics_summary():
    con = sqlite3.connect(ANALYTICS_DB);
    cur = con.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_hash) FROM usage_events");
    users = cur.fetchone()[0]
    cur.execute("SELECT country,COUNT(*) FROM usage_events GROUP BY country");
    countries = cur.fetchall()
    cur.execute("SELECT substr(ts_utc,1,7),COUNT(*) FROM usage_events GROUP BY 1 ORDER BY 1");
    growth = cur.fetchall()
    cur.execute("SELECT event_type,COUNT(*) FROM usage_events GROUP BY event_type");
    events = cur.fetchall()
    cur.execute("SELECT use_case,COUNT(*) FROM usage_events GROUP BY use_case");
    use_cases = cur.fetchall()
    con.close()
    return {"unique_users": users, "countries": dict(countries), "growth": dict(growth),
            "events": dict(events), "use_cases": dict(use_cases)}


# ═══════════════════════════════════════════
#  CSS — VISUALLY RICH
# ═══════════════════════════════════════════
DARK_CSS = """
:root {
  --bg-base:#060a10;--bg-surface:#0c1219;--bg-card:#111923;--bg-card-hover:#151f2d;
  --bg-input:#0e151f;--text-primary:#e8edf4;--text-secondary:#8fa3be;--text-muted:#5e7490;
  --border:rgba(136,176,226,0.08);--border-focus:rgba(106,152,234,0.25);
  --accent:#5b8def;--accent-soft:rgba(91,141,239,0.12);--accent-glow:rgba(91,141,239,0.06);
  --success:#3ecf8e;--success-soft:rgba(62,207,142,0.10);
  --warning:#f0b429;--warning-soft:rgba(240,180,41,0.10);--danger:#ef5350;
  --purple:#a78bfa;--pink:#f472b6;--cyan:#38bdf8;--orange:#fb923c;--teal:#2dd4bf;
  --radius-sm:8px;--radius-md:12px;--radius-lg:16px;--radius-xl:20px;
  --shadow-card:0 1px 3px rgba(0,0,0,0.4),0 0 0 1px var(--border);
  --shadow-glow:0 0 20px rgba(91,141,239,0.15);
  --transition:0.18s cubic-bezier(.4,0,.2,1);
}
body,.gradio-container{background:var(--bg-base)!important;color:var(--text-primary)!important;
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important;-webkit-font-smoothing:antialiased;}
.gradio-container{max-width:1440px!important;margin:0 auto!important;padding:0 16px!important;}
.gradio-container .prose,.gradio-container label,.gradio-container span,
.gradio-container p,.gradio-container h1,.gradio-container h2,.gradio-container h3{color:var(--text-primary)!important;}
.gradio-container .block{border-radius:var(--radius-lg)!important;border:1px solid var(--border)!important;
  background:var(--bg-card)!important;box-shadow:var(--shadow-card)!important;transition:border-color var(--transition)!important;}
.gradio-container .block:hover{border-color:var(--border-focus)!important;}
.gradio-container .form,.gradio-container .panel,.gradio-container .tabitem,.gradio-container .tab-nav{background:transparent!important;}
.gradio-container input,.gradio-container textarea,.gradio-container select{
  background:var(--bg-input)!important;color:var(--text-primary)!important;border:1px solid var(--border)!important;
  border-radius:var(--radius-sm)!important;padding:6px 10px!important;font-size:13px!important;
  transition:border-color var(--transition),box-shadow var(--transition)!important;}
.gradio-container input:focus,.gradio-container textarea:focus,.gradio-container select:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 3px var(--accent-soft)!important;outline:none!important;}
.gradio-container label{font-size:12px!important;margin-bottom:2px!important;}
.gradio-container button{border-radius:var(--radius-sm)!important;font-weight:600!important;transition:all var(--transition)!important;}
.gradio-container button.primary{background:linear-gradient(135deg,#4a7de8,#5b8def)!important;
  border:1px solid rgba(91,141,239,0.3)!important;color:#fff!important;box-shadow:0 2px 8px rgba(91,141,239,0.25)!important;}
.gradio-container button.primary:hover{background:linear-gradient(135deg,#5b8def,#6e9ef5)!important;
  box-shadow:0 4px 16px rgba(91,141,239,0.35)!important;transform:translateY(-1px)!important;}
.gradio-container button.secondary{background:var(--bg-card)!important;border:1px solid var(--border)!important;color:var(--text-secondary)!important;}
.gradio-container .tab-nav button{background:transparent!important;border:none!important;
  border-bottom:2px solid transparent!important;color:var(--text-muted)!important;
  padding:8px 14px!important;font-size:12px!important;font-weight:500!important;border-radius:0!important;box-shadow:none!important;}
.gradio-container .tab-nav button.selected{color:var(--accent)!important;border-bottom-color:var(--accent)!important;background:var(--accent-glow)!important;}
.gradio-container .tab-nav button:hover:not(.selected){color:var(--text-secondary)!important;}
.gradio-container .tab-nav{border-bottom:1px solid var(--border)!important;margin-bottom:10px!important;}

/* ══════════════════════════════════════
   HERO — Full width with animated waveform
   ══════════════════════════════════════ */
.av-hero{
  position:relative;padding:32px 36px 28px;
  border:1px solid var(--border);border-radius:var(--radius-xl);
  background:linear-gradient(135deg,rgba(91,141,239,0.08) 0%,rgba(167,139,250,0.05) 40%,rgba(56,189,248,0.04) 70%,rgba(15,22,35,0) 100%),var(--bg-surface);
  margin-bottom:16px;overflow:hidden;
}
.av-hero::before{
  content:"";position:absolute;top:-40%;right:-10%;width:600px;height:600px;
  background:radial-gradient(circle,rgba(91,141,239,0.08),rgba(167,139,250,0.04) 40%,transparent 70%);
  pointer-events:none;animation:hero-glow 8s ease-in-out infinite alternate;
}
.av-hero::after{
  content:"";position:absolute;bottom:-30%;left:-5%;width:400px;height:400px;
  background:radial-gradient(circle,rgba(62,207,142,0.06),transparent 60%);
  pointer-events:none;animation:hero-glow 6s ease-in-out 2s infinite alternate;
}
@keyframes hero-glow{0%{opacity:0.5;transform:scale(1);}100%{opacity:1;transform:scale(1.1);}}

.av-hero-content{position:relative;z-index:1;display:flex;align-items:center;gap:28px;}
.av-hero-text{flex:1;}
.av-hero-title{
  font-size:28px;font-weight:800;letter-spacing:-0.5px;
  background:linear-gradient(135deg,#e8edf4 0%,#8fb0e0 50%,#a78bfa 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 6px;
}
.av-hero-sub{color:var(--text-secondary);font-size:13px;line-height:1.5;margin:0 0 12px;}
.av-hero-badges{display:flex;gap:8px;flex-wrap:wrap;}
.av-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 12px;
  border:1px solid var(--border);border-radius:999px;font-size:11px;font-weight:500;
  color:var(--text-secondary);background:var(--accent-soft);transition:all var(--transition);}
.av-badge:hover{border-color:var(--accent);background:rgba(91,141,239,0.18);}
.av-badge .dot{width:5px;height:5px;border-radius:50%;background:var(--success);animation:pulse 2s infinite;}
.av-badge.purple{background:rgba(167,139,250,0.10);border-color:rgba(167,139,250,0.15);}
.av-badge.cyan{background:rgba(56,189,248,0.10);border-color:rgba(56,189,248,0.15);}
.av-badge.teal{background:rgba(45,212,191,0.10);border-color:rgba(45,212,191,0.15);}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}

/* Animated SVG waveform in hero */
.av-hero-viz{flex-shrink:0;width:200px;height:80px;position:relative;}
.av-hero-viz svg{width:100%;height:100%;}
.av-wave-line{animation:wave-draw 3s ease-in-out infinite;stroke-dasharray:600;stroke-dashoffset:600;}
@keyframes wave-draw{0%{stroke-dashoffset:600;}50%{stroke-dashoffset:0;}100%{stroke-dashoffset:-600;}}

/* ══════════════════════════════════════
   FEATURE CARDS — colorful grid
   ══════════════════════════════════════ */
.av-features{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:8px;margin:0 0 16px;
}
.av-feat-card{
  padding:12px 14px;border-radius:var(--radius-md);
  border:1px solid var(--border);
  background:var(--bg-surface);
  transition:all var(--transition);
  cursor:default;position:relative;overflow:hidden;
}
.av-feat-card::before{
  content:"";position:absolute;top:0;left:0;right:0;height:3px;
  border-radius:var(--radius-md) var(--radius-md) 0 0;
}
.av-feat-card:hover{transform:translateY(-2px);box-shadow:var(--shadow-glow);border-color:var(--border-focus);}
.av-feat-card .icon{font-size:20px;margin-bottom:4px;}
.av-feat-card .label{font-size:11px;font-weight:600;color:var(--text-secondary);line-height:1.3;}
.av-feat-card .value{font-size:10px;color:var(--text-muted);margin-top:2px;}

/* Card color variants */
.av-feat-card.blue::before{background:linear-gradient(90deg,#5b8def,#38bdf8);}
.av-feat-card.green::before{background:linear-gradient(90deg,#3ecf8e,#2dd4bf);}
.av-feat-card.purple::before{background:linear-gradient(90deg,#a78bfa,#f472b6);}
.av-feat-card.orange::before{background:linear-gradient(90deg,#fb923c,#f0b429);}
.av-feat-card.pink::before{background:linear-gradient(90deg,#f472b6,#ef5350);}
.av-feat-card.cyan::before{background:linear-gradient(90deg,#38bdf8,#2dd4bf);}

/* ══════════════════════════════════════
   SECTION TITLES — colorful icons
   ══════════════════════════════════════ */
.av-section-title{
  font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;
  color:var(--text-muted);margin:0 0 8px;padding-bottom:6px;
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:8px;
}
.av-section-icon{
  width:20px;height:20px;border-radius:6px;
  display:inline-flex;align-items:center;justify-content:center;
  font-size:11px;flex-shrink:0;
}
.av-section-icon.blue{background:rgba(91,141,239,0.15);color:#5b8def;}
.av-section-icon.green{background:rgba(62,207,142,0.15);color:#3ecf8e;}
.av-section-icon.purple{background:rgba(167,139,250,0.15);color:#a78bfa;}
.av-section-icon.orange{background:rgba(251,146,60,0.15);color:#fb923c;}

/* ══════════════════════════════════════
   KPI CARDS — gradient borders
   ══════════════════════════════════════ */
.av-kpi-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:6px 0 12px;}
.av-kpi-card{
  background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-md);
  padding:10px 12px;transition:all var(--transition);position:relative;overflow:hidden;
}
.av-kpi-card::after{
  content:"";position:absolute;bottom:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--accent),var(--cyan));opacity:0;
  transition:opacity var(--transition);
}
.av-kpi-card:hover{border-color:var(--border-focus);background:var(--bg-card-hover);}
.av-kpi-card:hover::after{opacity:1;}
.av-kpi-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);margin:0 0 4px;}
.av-kpi-value{font-size:18px;font-weight:700;color:var(--text-primary);margin:0;line-height:1.1;}
.av-kpi-unit{font-size:11px;font-weight:500;color:var(--text-secondary);margin-left:2px;}

/* ══════════════════════════════════════
   WELLNESS — animated gradient
   ══════════════════════════════════════ */
.av-wellness-wrap{
  display:flex;align-items:center;gap:16px;padding:14px 18px;margin:8px 0;
  background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-lg);
  position:relative;overflow:hidden;
}
.av-wellness-wrap::before{
  content:"";position:absolute;top:0;left:0;bottom:0;width:4px;
  background:linear-gradient(180deg,var(--success),var(--accent));border-radius:4px 0 0 4px;
}
.av-wellness-wrap.mid::before{background:linear-gradient(180deg,var(--warning),var(--orange));}
.av-wellness-wrap.low::before{background:linear-gradient(180deg,var(--danger),var(--pink));}
.av-wellness-score{font-size:36px;font-weight:800;line-height:1;padding-left:8px;
  background:linear-gradient(135deg,var(--success),#5befa0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.av-wellness-score.mid{background:linear-gradient(135deg,var(--warning),#f5d060);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.av-wellness-score.low{background:linear-gradient(135deg,var(--danger),#f08080);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.av-wellness-detail{flex:1;}
.av-wellness-label{font-size:11px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;}
.av-wellness-uses{font-size:12px;color:var(--text-secondary);margin-top:4px;line-height:1.3;}
.av-wellness-note{font-size:10px;color:var(--text-muted);margin-top:4px;font-style:italic;line-height:1.2;}

/* ══════════════════════════════════════
   STATUS + MISC
   ══════════════════════════════════════ */
.av-status{padding:8px 12px;border-radius:var(--radius-sm);font-size:12px;line-height:1.3;}
.av-status.info{background:var(--accent-soft);color:var(--accent);border:1px solid rgba(91,141,239,0.15);}
.av-status.success{background:var(--success-soft);color:var(--success);border:1px solid rgba(62,207,142,0.15);}
.av-status.warn{background:var(--warning-soft);color:var(--warning);border:1px solid rgba(240,180,41,0.15);}

.av-impact{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:999px;
  background:var(--accent-soft);border:1px solid rgba(91,141,239,0.12);font-size:11px;color:var(--text-secondary);}
.av-impact b{color:var(--accent);}

.av-sep{border:none;border-top:1px solid var(--border);margin:14px 0;}
.av-muted{color:var(--text-muted)!important;font-size:11px!important;line-height:1.3!important;}

/* ══════════════════════════════════════
   RUN BUTTON BAR — gradient glow
   ══════════════════════════════════════ */
.av-run-bar{
  padding:14px 20px;margin:10px 0;
  background:linear-gradient(135deg,rgba(91,141,239,0.08),rgba(62,207,142,0.05),rgba(167,139,250,0.04));
  border:1px solid var(--border);border-radius:var(--radius-lg);
  position:relative;overflow:hidden;
}
.av-run-bar::before{
  content:"";position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--accent),var(--success),var(--purple),var(--cyan));
  animation:run-bar-shimmer 3s linear infinite;
  background-size:200% 100%;
}
@keyframes run-bar-shimmer{0%{background-position:200% 0;}100%{background-position:-200% 0;}}

/* ══════════════════════════════════════
   TAB CONTENT HEADERS
   ══════════════════════════════════════ */
.av-tab-header{
  display:flex;align-items:center;gap:10px;
  padding:8px 14px;margin-bottom:8px;
  background:linear-gradient(90deg,rgba(91,141,239,0.06),transparent);
  border-radius:var(--radius-sm);border-left:3px solid var(--accent);
}
.av-tab-header.green{background:linear-gradient(90deg,rgba(62,207,142,0.06),transparent);border-left-color:var(--success);}
.av-tab-header.purple{background:linear-gradient(90deg,rgba(167,139,250,0.06),transparent);border-left-color:var(--purple);}
.av-tab-header.orange{background:linear-gradient(90deg,rgba(251,146,60,0.06),transparent);border-left-color:var(--orange);}
.av-tab-header.pink{background:linear-gradient(90deg,rgba(244,114,182,0.06),transparent);border-left-color:var(--pink);}
.av-tab-header.cyan{background:linear-gradient(90deg,rgba(56,189,248,0.06),transparent);border-left-color:var(--cyan);}
.av-tab-header.teal{background:linear-gradient(90deg,rgba(45,212,191,0.06),transparent);border-left-color:var(--teal);}
.av-tab-header .icon{font-size:16px;}
.av-tab-header .text{font-size:12px;color:var(--text-secondary);line-height:1.3;}

.av-compact-radio .wrap{max-height:260px;overflow-y:auto;scrollbar-width:thin;}

/* Scrollbar */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--bg-base);}
::-webkit-scrollbar-thumb{background:rgba(136,176,226,0.15);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:rgba(136,176,226,0.25);}

.gradio-container .gradio-accordion{border:1px solid var(--border)!important;border-radius:var(--radius-md)!important;background:var(--bg-surface)!important;}
.gradio-container .file-preview,.gradio-container .upload-button{
  background:var(--bg-input)!important;border:1px dashed var(--border)!important;border-radius:var(--radius-md)!important;}
.js-plotly-plot .plotly .modebar{background:transparent!important;}

/* ══════════════════════════════════════
   STANDARDS TABLE — colorful
   ══════════════════════════════════════ */
.av-std-pass{color:#3ecf8e;font-weight:700;}
.av-std-fail{color:#ef5350;font-weight:700;}
.av-std-table{width:100%;font-size:12px;border-collapse:collapse;color:var(--text-primary);}
.av-std-table thead tr{border-bottom:2px solid var(--border);background:var(--bg-surface);}
.av-std-table th{padding:8px 10px;text-align:left;color:var(--text-muted);font-size:11px;text-transform:uppercase;letter-spacing:0.05em;}
.av-std-table td{padding:6px 10px;border-bottom:1px solid var(--border);}
.av-std-table tr:hover td{background:rgba(91,141,239,0.03);}

/* ══════════════════════════════════════
   EXPORT ROW — styled
   ══════════════════════════════════════ */
.av-export-row{
  display:flex;gap:8px;align-items:center;
  padding:12px 16px;
  background:var(--bg-surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);margin-top:8px;
}

/* ══════════════════════════════════════
   HERO POWERED BY SECTION
   ══════════════════════════════════════ */
.av-hero-powered{
  margin-top:14px;padding-top:12px;
  border-top:1px solid var(--border);
  font-size:11px;color:var(--text-muted);
}
.av-hero-powered a{
  color:var(--accent);text-decoration:none;
  font-weight:500;transition:all var(--transition);
  border-bottom:1px solid transparent;
}
.av-hero-powered a:hover{
  color:#7aa5f7;border-bottom-color:rgba(91,141,239,0.4);
}

/* ══════════════════════════════════════
   FOOTER
   ══════════════════════════════════════ */
.av-footer{
  margin-top:24px;padding:16px 0;
  border-top:1px solid var(--border);
}
.av-footer-content{
  display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:12px;
}
.av-footer-left,.av-footer-center,.av-footer-right{
  display:flex;align-items:center;gap:8px;
}
.av-footer-brand{
  font-size:12px;font-weight:600;
  background:linear-gradient(135deg,#e8edf4,#8fb0e0);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.av-footer-sep{color:var(--border);font-size:10px;}
.av-footer-text{font-size:11px;color:var(--text-muted);}
.av-footer-powered{
  font-size:11px;color:var(--text-muted);
  display:flex;align-items:center;gap:6px;
}
.av-footer-powered a{
  color:var(--accent);text-decoration:none;
  font-weight:500;display:inline-flex;align-items:center;gap:4px;
  padding:3px 8px;border-radius:6px;
  background:var(--accent-soft);border:1px solid rgba(91,141,239,0.1);
  transition:all var(--transition);
}
.av-footer-powered a:hover{
  background:rgba(91,141,239,0.18);border-color:rgba(91,141,239,0.25);
  transform:translateY(-1px);
}
.av-hf-logo{
  width:14px;height:14px;vertical-align:middle;
}
.av-footer-credit{
  font-size:10px;color:var(--text-muted);
  opacity:0.7;font-style:italic;
}

/* ══════════════════════════════════════
   RESPONSIVE FOOTER
   ══════════════════════════════════════ */
@media (max-width:768px){
  .av-footer-content{flex-direction:column;text-align:center;}
  .av-footer-left,.av-footer-center,.av-footer-right{justify-content:center;}
}
/* ══════════════════════════════════════
   HELP ACCORDION — styled like a feature card
   ══════════════════════════════════════ */
.av-help-accordion{
  margin:0 0 16px!important;
  border:1px solid var(--border)!important;
  border-radius:var(--radius-lg)!important;
  background:linear-gradient(135deg,rgba(91,141,239,0.06),rgba(62,207,142,0.04))!important;
  overflow:hidden;
}
.av-help-accordion > .label-wrap{
  padding:12px 16px!important;
  background:transparent!important;
  cursor:pointer;
  transition:all var(--transition);
  display:flex;
  align-items:center;
  gap:8px;
}
.av-help-accordion > .label-wrap:hover{
  background:rgba(91,141,239,0.08)!important;
}
.av-help-accordion .label-wrap span{
  font-size:13px!important;
  font-weight:600!important;
  color:var(--text-primary)!important;
}
/* ══════════════════════════════════════
   MOBILE RESPONSIVE
   ══════════════════════════════════════ */

/* Tablets and below (≤ 1024px) */
@media (max-width:1024px){
  .gradio-container{padding:0 12px!important;}
  .av-hero{padding:24px 20px 20px;}
  .av-hero-content{flex-direction:column;gap:16px;}
  .av-hero-viz{width:100%;height:60px;}
  .av-hero-title{font-size:24px;}
  .av-features{grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:6px;}
  .av-kpi-grid{grid-template-columns:repeat(3,1fr);gap:6px;}
  .av-feat-card{padding:10px 12px;}
}

/* Mobile phones (≤ 768px) */
@media (max-width:768px){
  .gradio-container{padding:0 8px!important;}

  /* Hero */
  .av-hero{padding:20px 16px 16px;margin-bottom:12px;}
  .av-hero-title{font-size:20px;margin:0 0 4px;}
  .av-hero-sub{font-size:12px;margin:0 0 8px;}
  .av-hero-badges{gap:6px;}
  .av-badge{padding:2px 10px;font-size:10px;}
  .av-hero-powered{font-size:10px;margin-top:10px;padding-top:8px;}

  /* Features */
  .av-features{grid-template-columns:repeat(3,1fr);gap:4px;margin:0 0 12px;}
  .av-feat-card{padding:8px 6px;}
  .av-feat-card .icon{font-size:16px;margin-bottom:3px;}
  .av-feat-card .label{font-size:9px;}
  .av-feat-card .value{font-size:8px;margin-top:1px;}

  /* Help accordion */
  .av-help-accordion > .label-wrap{padding:10px 12px!important;}
  .av-help-accordion .label-wrap span{font-size:12px!important;}

  /* Two-column layout → stack */
  .gradio-container .row{flex-direction:column!important;}
  .gradio-container .column{width:100%!important;min-width:100%!important;}

  /* Section titles */
  .av-section-title{font-size:11px;margin:0 0 6px;padding-bottom:4px;}
  .av-section-icon{width:16px;height:16px;font-size:10px;}

  /* KPI cards */
  .av-kpi-grid{grid-template-columns:repeat(2,1fr);gap:6px;margin:6px 0 10px;}
  .av-kpi-card{padding:8px 10px;}
  .av-kpi-label{font-size:9px;margin:0 0 3px;}
  .av-kpi-value{font-size:16px;}
  .av-kpi-unit{font-size:10px;}

  /* Wellness */
  .av-wellness-wrap{flex-direction:column;align-items:flex-start;padding:12px 14px;gap:10px;}
  .av-wellness-score{font-size:28px;padding-left:6px;}
  .av-wellness-label{font-size:10px;}
  .av-wellness-uses{font-size:11px;margin-top:3px;}
  .av-wellness-note{font-size:9px;margin-top:3px;}

  /* Run button bar */
  .av-run-bar{padding:12px 14px;margin:8px 0;}
  .av-run-bar .row{flex-direction:column!important;gap:8px!important;}
  .av-run-bar button{width:100%!important;}
  .av-run-bar .av-muted{display:none;} /* Hide long text on mobile */

  /* Tabs */
  .gradio-container .tab-nav{overflow-x:auto;white-space:nowrap;scrollbar-width:thin;}
  .gradio-container .tab-nav button{font-size:11px!important;padding:7px 10px!important;}

  /* Tab headers */
  .av-tab-header{padding:6px 10px;margin-bottom:6px;gap:8px;}
  .av-tab-header .icon{font-size:14px;}
  .av-tab-header .text{font-size:11px;}

  /* Form inputs */
  .gradio-container input,.gradio-container textarea,.gradio-container select{
    font-size:14px!important;padding:8px 10px!important;
  }
  .gradio-container label{font-size:11px!important;}

  /* Buttons */
  .gradio-container button{
    font-size:13px!important;
    padding:10px 14px!important;
    min-height:44px; /* Touch-friendly */
  }

  /* File upload */
  .gradio-container .file-preview,.gradio-container .upload-button{
    min-height:80px!important;
  }

  /* Accordions */
  .gradio-container .accordion .label-wrap{
    padding:10px 12px!important;
    font-size:12px!important;
  }

  /* Audio players */
  .gradio-container audio{width:100%!important;}

  /* Images and plots */
  .gradio-container img,.gradio-container .plot-container{
    max-width:100%!important;
    height:auto!important;
  }

  /* Report & Export row */
  .av-export-row{
    flex-direction:column!important;
    padding:10px 12px;
    gap:6px!important;
  }
  .av-export-row button,.av-export-row .file{
    width:100%!important;
  }

  /* Footer */
  .av-footer{margin-top:16px;padding:12px 0;}
  .av-footer-content{flex-direction:column;text-align:center;gap:8px;}
  .av-footer-left,.av-footer-center,.av-footer-right{
    flex-direction:column;gap:6px;width:100%;
  }
  .av-footer-brand{font-size:11px;}
  .av-footer-text,.av-footer-powered,.av-footer-credit{font-size:10px;}
  .av-footer-sep{display:none;}

  /* Status messages */
  .av-status{padding:6px 10px;font-size:11px;}

  /* Impact stats */
  .av-impact{padding:3px 10px;font-size:10px;}

  /* Standards table */
  .av-std-table,.av-std-table thead,.av-std-table tbody,.av-std-table tr,.av-std-table td,.av-std-table th{
    display:block!important;
  }
  .av-std-table thead{display:none!important;} /* Hide headers on mobile */
  .av-std-table tr{
    border:1px solid var(--border)!important;
    border-radius:var(--radius-sm)!important;
    margin-bottom:8px!important;
    padding:8px!important;
  }
  .av-std-table td{
    border:none!important;
    padding:4px 0!important;
    text-align:left!important;
  }
  .av-std-table td:before{
    content:attr(data-label);
    font-weight:600;
    color:var(--text-muted);
    display:inline-block;
    width:80px;
    font-size:10px;
  }

  /* Help content */
  .av-help-accordion h3{font-size:14px!important;}
  .av-help-accordion ul,.av-help-accordion ol{padding-left:16px!important;}
  .av-help-accordion li{font-size:12px!important;margin-bottom:6px!important;}
  .av-help-accordion table{font-size:11px!important;}
  .av-help-accordion td,.av-help-accordion th{padding:4px 6px!important;}
}

/* Very small phones (≤ 480px) */
@media (max-width:480px){
  .av-hero-title{font-size:18px;}
  .av-features{grid-template-columns:repeat(2,1fr);}
  .av-kpi-grid{grid-template-columns:repeat(2,1fr);gap:4px;}
  .av-kpi-value{font-size:14px;}
  .av-wellness-score{font-size:24px;}
  .gradio-container .tab-nav button{font-size:10px!important;padding:6px 8px!important;}
}

/* Landscape orientation fixes */
@media (max-height:600px) and (orientation:landscape){
  .av-hero{padding:16px 20px;}
  .av-hero-title{font-size:18px;}
  .av-hero-viz{display:none;} /* Hide decorative viz */
  .av-features{margin:0 0 8px;}
}

/* Touch-friendly improvements */
@media (hover:none) and (pointer:coarse){
  /* Larger tap targets */
  .gradio-container button{
    min-height:48px!important;
    min-width:48px!important;
  }

  /* Remove hover effects on touch devices */
  .av-feat-card:hover{transform:none!important;}
  .av-kpi-card:hover{background:var(--bg-surface)!important;}

  /* Better spacing for fat fingers */
  .gradio-container .tab-nav button{
    padding:10px 14px!important;
    margin:0 2px!important;
  }
}

/* Prevent horizontal scroll */
*{
  max-width:100%;
  box-sizing:border-box;
}

/* Better overflow handling */
.gradio-container{
  overflow-x:hidden!important;
}

/* Ensure plots are responsive */
.js-plotly-plot{
  width:100%!important;
  height:auto!important;
  min-height:300px!important;
}

/* Fix for small screen scrolling */
@media (max-width:768px){
  .gradio-container .tabitem{
    min-height:300px;
    overflow-x:auto;
  }
}
"""

# ═══════════════════════════════════════════
#  GRADIO UI
# ═══════════════════════════════════════════
impact_init()
analytics_init()

with gr.Blocks(css=DARK_CSS, theme=gr.themes.Base(), title="AcoustiVision Pro") as demo:
    # Hidden state
    user_id = gr.Textbox(visible=False, label="user_id")
    state = gr.State({})
    hf_hits_state = gr.State({})

    gr.HTML("""
    <script>
    (function(){
      const KEY="acoustivision_uid";
      function uuid(){return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,c=>{
        const r=Math.random()*16|0;return(c=="x"?r:(r&3|8)).toString(16);});}
      let id=localStorage.getItem(KEY);
      if(!id){id=uuid();localStorage.setItem(KEY,id);}
      setTimeout(()=>{document.querySelectorAll("input").forEach(el=>{
        if(el.getAttribute("aria-label")==="user_id"){el.value=id;el.dispatchEvent(new Event("input",{bubbles:true}));}
      });},600);
    })();
    </script>
    """)

    gr.HTML("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    """)

    # ── Hero with animated waveform + attribution ──
    gr.HTML("""
    <div class="av-hero">
      <div class="av-hero-content">
        <div class="av-hero-text">
          <div class="av-hero-title">AcoustiVision Pro</div>
          <p class="av-hero-sub">
            Professional room impulse response analysis with 12 visualization modes,
            standards compliance checking, and automated engineering reports.
          </p>
          <div class="av-hero-badges">
            <span class="av-badge"><span class="dot"></span> Live Analysis</span>
            <span class="av-badge purple">12 Visualizations</span>
            <span class="av-badge cyan">Standards Check</span>
            <span class="av-badge teal">PDF + CSV Export</span>
          </div>
          <div class="av-hero-powered">
            Powered by 
            <a href="https://huggingface.co/datasets/mandipgoswami/rirmega" target="_blank" rel="noopener">RIRMega</a>
            &amp;
            <a href="https://huggingface.co/datasets/mandipgoswami/rir-mega-speech" target="_blank" rel="noopener">RIRMega Speech</a>
            on 🤗 Hugging Face
          </div>
        </div>
        <div class="av-hero-viz">
          <svg viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="wg1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#5b8def;stop-opacity:0.8"/>
                <stop offset="50%" style="stop-color:#a78bfa;stop-opacity:0.6"/>
                <stop offset="100%" style="stop-color:#38bdf8;stop-opacity:0.3"/>
              </linearGradient>
              <linearGradient id="wg2" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#3ecf8e;stop-opacity:0.6"/>
                <stop offset="100%" style="stop-color:#2dd4bf;stop-opacity:0.2"/>
              </linearGradient>
            </defs>
            <path class="av-wave-line" d="M0,40 L8,40 L10,40 L12,8 L14,65 L16,20 L18,55 L20,30 L22,48 L24,35 L26,42 L28,38 L30,41 L35,40 L40,43 L45,38 L50,41 L55,39 L60,40.5 L70,40 L80,40.3 L90,39.8 L100,40 L120,40 L140,40 L160,40 L180,40 L200,40"
                  fill="none" stroke="url(#wg1)" stroke-width="2" stroke-linecap="round"/>
            <path d="M12,8 Q30,25 60,38 Q100,40 200,40" fill="none" stroke="url(#wg2)" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>
            <circle cx="12" cy="8" r="3" fill="#5b8def" opacity="0.9">
              <animate attributeName="r" values="3;4;3" dur="2s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.9;0.5;0.9" dur="2s" repeatCount="indefinite"/>
            </circle>
            <text x="12" y="78" font-size="7" fill="#5e7490" text-anchor="middle">Direct</text>
            <text x="50" y="78" font-size="7" fill="#5e7490" text-anchor="middle">Early</text>
            <text x="120" y="78" font-size="7" fill="#5e7490" text-anchor="middle">Late reverb</text>
            <line x1="30" y1="72" x2="30" y2="68" stroke="#3ecf8e" stroke-width="0.5" opacity="0.5"/>
            <text x="30" y="67" font-size="5" fill="#3ecf8e" text-anchor="middle" opacity="0.6">50ms</text>
            <line x1="40" y1="72" x2="40" y2="68" stroke="#f0b429" stroke-width="0.5" opacity="0.5"/>
            <text x="40" y="67" font-size="5" fill="#f0b429" text-anchor="middle" opacity="0.6">80ms</text>
          </svg>
        </div>
      </div>
    </div>
    """)

    # ── Feature highlight cards ──
    gr.HTML("""
    <div class="av-features">
      <div class="av-feat-card blue">
        <div class="icon">〰️</div>
        <div class="label">RIR Waveform</div>
        <div class="value">Interactive zoom</div>
      </div>
      <div class="av-feat-card green">
        <div class="icon">📉</div>
        <div class="label">Energy Decay</div>
        <div class="value">Schroeder EDC</div>
      </div>
      <div class="av-feat-card purple">
        <div class="icon">📊</div>
        <div class="label">Octave RT60</div>
        <div class="value">125–4000 Hz</div>
      </div>
      <div class="av-feat-card orange">
        <div class="icon">📈</div>
        <div class="label">Freq Response</div>
        <div class="value">20–20k Hz</div>
      </div>
      <div class="av-feat-card pink">
        <div class="icon">🌊</div>
        <div class="label">Waterfall 3D</div>
        <div class="value">Time-freq decay</div>
      </div>
      <div class="av-feat-card cyan">
        <div class="icon">🌐</div>
        <div class="label">3D Spatial</div>
        <div class="value">Image source</div>
      </div>
      <div class="av-feat-card blue">
        <div class="icon">🎯</div>
        <div class="label">Fingerprint</div>
        <div class="value">Radar chart</div>
      </div>
      <div class="av-feat-card green">
        <div class="icon">🏛️</div>
        <div class="label">Room Modes</div>
        <div class="value">Up to 500 Hz</div>
      </div>
      <div class="av-feat-card purple">
        <div class="icon">✅</div>
        <div class="label">Standards</div>
        <div class="value">ANSI / ISO</div>
      </div>
      <div class="av-feat-card orange">
        <div class="icon">🎧</div>
        <div class="label">Auralization</div>
        <div class="value">FFT convolve</div>
      </div>
      <div class="av-feat-card pink">
        <div class="icon">📄</div>
        <div class="label">PDF Report</div>
        <div class="value">Multi-page</div>
      </div>
      <div class="av-feat-card cyan">
        <div class="icon">📥</div>
        <div class="label">CSV Export</div>
        <div class="value">All metrics</div>
      </div>
    </div>

    """)
    # ── Help Section (collapsible) ──
    with gr.Accordion("❓ Help & Documentation", open=False, elem_classes=["av-help-accordion"]):
        gr.HTML("""
        <div style="padding:12px 16px;color:var(--text-primary);font-size:13px;line-height:1.7;">

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">🚀 Quick Start</h3>
          <ol style="padding-left:20px;margin:0 0 20px;">
            <li><b>Load an RIR</b> — Either <em>search</em> the RIRMega dataset (left panel) or <em>upload</em> your own <code>.wav</code> file.</li>
            <li><b>Set room geometry</b> — Open <em>⚙ Room Geometry &amp; Parameters</em> and enter dimensions, source/receiver positions. If you loaded from RIRMega these fill automatically.</li>
            <li><b>Click ▶ Run Full Analysis</b> — All 12 analyses run in one pass.</li>
            <li><b>Explore tabs</b> — Browse results across the visualization tabs below.</li>
            <li><b>Export</b> — Download a multi-page <em>PDF Report</em> or a <em>CSV</em> of all metrics.</li>
          </ol>

          <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">🔍 Searching RIRMega</h3>
          <ul style="padding-left:20px;margin:0 0 20px;">
            <li><b>Volume range</b> — Filter rooms by cubic-metre volume (Length × Width × Height).</li>
            <li><b>RT60 range</b> — Target reverberation time window in seconds.</li>
            <li><b>Absorption range</b> — Average absorption coefficient (0 = fully reflective, 1 = fully absorptive).</li>
            <li><b>Split</b> — Restrict to <code>train</code>, <code>val</code>, or <code>test</code> partition, or <code>any</code>.</li>
            <li>Click a result row to auto-load the RIR and populate room parameters.</li>
          </ul>

          <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📐 Room Geometry &amp; Parameters</h3>
          <ul style="padding-left:20px;margin:0 0 20px;">
            <li><b>L / W / H</b> — Room length, width and height in metres. Used for room-mode calculation and the 3D reflection view.</li>
            <li><b>Sx, Sy, Sz / Rx, Ry, Rz</b> — Source and receiver coordinates (metres). Shown in the 3D Spatial tab.</li>
            <li><b>Material &amp; Heatmap strength</b> — Applies a frequency-dependent absorption overlay to the spectrogram for visual comparison only (does not alter metrics).</li>
            <li><b>SNR (dB)</b> — Assumed signal-to-noise ratio used for the STI proxy calculation.</li>
          </ul>

          <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📏 Metric Definitions</h3>
          <table style="width:100%;border-collapse:collapse;font-size:12px;color:var(--text-primary);">
            <thead>
              <tr style="border-bottom:2px solid var(--border);background:var(--bg-surface);">
                <th style="padding:8px 10px;text-align:left;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Metric</th>
                <th style="padding:8px 10px;text-align:left;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Description</th>
                <th style="padding:8px 10px;text-align:center;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Typical Range</th>
              </tr>
            </thead>
            <tbody>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">EDT</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Early Decay Time — RT60 extrapolated from the first 10 dB of decay. Reflects perceived reverberance.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.2 – 3.0 s</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">T20</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Reverberation time from −5 to −25 dB decay range, extrapolated to −60 dB.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.2 – 3.0 s</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">T30</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Reverberation time from −5 to −35 dB decay range. Most robust broadband RT60 estimate.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.2 – 3.0 s</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">C80 (dB)</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Clarity — ratio of early energy (0–80 ms) to late energy. Higher = clearer for music.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">−5 to +10 dB</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">D50</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Definition — fraction of energy arriving within 50 ms. Higher = better speech intelligibility.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.3 – 0.8</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">STI (proxy)</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Speech Transmission Index estimate derived from RT60 and assumed SNR. Approximation only.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.0 – 1.0</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">IACC</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Inter-Aural Cross-Correlation (stereo RIRs only). Lower values → wider spatial impression.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.0 – 1.0</td></tr>
              <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">Wellness</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Composite score (0–100) combining RT60, STI, D50, C80 and room volume. Higher = better for speech-centric use.</td>
                  <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0 – 100</td></tr>
            </tbody>
          </table>

          <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📑 Feature Guide</h3>
          <table style="width:100%;border-collapse:collapse;font-size:12px;color:var(--text-primary);">
            <tbody>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">🌐 3D Spatial</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Image-source first-order reflections in an interactive 3D room view. Drag to orbit, scroll to zoom.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">〰️ Waveform</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Time-domain RIR with direct-sound marker and 50 ms / 80 ms boundary lines. Range slider for zoom.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">📉 EDC</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Schroeder backward-integrated energy decay curve with dB guide lines.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">📊 Octave RT60</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">EDT, T20 and T30 per octave band (125 Hz – 4 kHz) via 4th-order Butterworth bandpass filters.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">📈 Freq Response</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">FFT magnitude spectrum (raw + smoothed) on a log-frequency axis.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">🔥 Spectrogram</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Mel spectrogram with optional material-absorption tint for visual exploration.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">🌊 Waterfall</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">3D waterfall showing frequency-band energy decay over time. Drag to rotate.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">🎯 Fingerprint</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Radar chart normalizing C80, D50, IACC and STI onto a 0–1 scale for quick comparison.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">🏛️ Room Modes</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Axial, tangential and oblique standing-wave frequencies up to 500 Hz with density overlay.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">✅ Standards</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Pass/fail checks against ANSI S12.60, ISO 3382-3, and common room-type criteria.</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">🎧 Auralization</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Upload a dry recording to hear it convolved with the loaded RIR (FFT-based).</td></tr>
              <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;">📊 JSON</td>
                  <td style="padding:5px 10px;border-bottom:1px solid var(--border);">All computed metrics as JSON for copy-paste or programmatic use.</td></tr>
            </tbody>
          </table>

          <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">🎧 Auralization Tips</h3>
          <ul style="padding-left:20px;margin:0 0 20px;">
            <li>Upload a <b>mono, anechoic</b> <code>.wav</code> file (speech or music) as the <em>Dry Audio</em>.</li>
            <li>Audio is automatically resampled to match the RIR's sample rate and trimmed to 30 s max.</li>
            <li>The <em>Wet</em> output is the FFT convolution of your dry signal with the RIR — this simulates what a listener would hear in the room.</li>
          </ul>

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📄 Exporting</h3>
          <ul style="padding-left:20px;margin:0 0 20px;">
            <li><b>PDF Report</b> — Multi-page document with key metrics, wellness score, EDC, spectrogram and radar plots.</li>
            <li><b>CSV Export</b> — Flat file containing all main metrics, octave-band RT60 values and the first 30 room modes.</li>
            <li>Both require running the analysis first.</li>
          </ul>

          <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">⚠️ Limitations &amp; Notes</h3>
          <ul style="padding-left:20px;margin:0 0 16px;">
            <li>STI is a <em>proxy</em> based on RT60 and assumed SNR — not a full modulation-transfer-function computation.</li>
            <li>IACC requires a <b>stereo</b> RIR file; mono files will show "—".</li>
            <li>Room-mode calculation assumes a rectangular (shoebox) room.</li>
            <li>The material overlay on the spectrogram is for <em>visualization only</em> and does not affect computed metrics.</li>
            <li>Maximum audio duration is 30 seconds (configurable via environment variable).</li>
          </ul>

        </div>
        """)
    # ══════════════════════════════════════
    #  MAIN TWO-COLUMN LAYOUT
    # ══════════════════════════════════════
    with gr.Row(equal_height=False):

        # ━━━ LEFT COLUMN: Search ━━━
        with gr.Column(scale=2, min_width=360):
            gr.HTML("""<div class='av-section-title'>
                            <span class='av-section-icon blue'>🔍</span> Search RIRmega
                        </div>""")

            with gr.Row():
                ds_name = gr.Textbox(value="mandipgoswami/rirmega", label="Dataset", scale=3, max_lines=1)
                metadata_filename = gr.Textbox(value="metadata.csv", label="CSV", scale=2, max_lines=1)

            with gr.Row():
                vol_min = gr.Number(value=50, label="Vol min", precision=0)
                vol_max = gr.Number(value=600, label="Vol max", precision=0)
                rt60_min = gr.Number(value=0.10, label="RT min", precision=2)
                rt60_max = gr.Number(value=1.50, label="RT max", precision=2)

            with gr.Row():
                abs_min = gr.Number(value=0.00, label="Abs min", precision=2)
                abs_max = gr.Number(value=0.80, label="Abs max", precision=2)
                split_filter = gr.Dropdown(choices=["any", "train", "val", "test"], value="any", label="Split")

            hf_btn = gr.Button("🔎 Search RIRmega", variant="primary", size="sm")
            hf_status = gr.HTML("")

            gr.HTML("""<div class='av-section-title' style='margin-top:8px;'>
                            <span class='av-section-icon green'>📋</span> Results
                        </div>""")
            hf_choices = gr.Radio(choices=[], label="", interactive=True, elem_classes=["av-compact-radio"])

        # ━━━ RIGHT COLUMN: Upload + Run + Results ━━━
        with gr.Column(scale=3, min_width=520):
            # Upload
            gr.HTML("""<div class='av-section-title'>
                            <span class='av-section-icon purple'>📁</span> Upload / Loaded RIR
                        </div>""")
            with gr.Row():
                rir_file = gr.File(label="RIR WAV", file_types=[".wav"], height=70, scale=1)
                dry_file = gr.File(label="Dry Audio (opt)", file_types=[".wav"], height=70, scale=1)
            loaded_info = gr.HTML("<div class='av-status info'>No RIR loaded. Search or upload.</div>")

            # Room setup accordion
            with gr.Accordion("⚙ Room Geometry & Parameters", open=False):
                with gr.Row():
                    room_L = gr.Number(value=10.0, label="L(m)", precision=1)
                    room_W = gr.Number(value=8.0, label="W(m)", precision=1)
                    room_H = gr.Number(value=3.0, label="H(m)", precision=1)
                    src_x = gr.Number(value=2.0, label="Sx", precision=2)
                    src_y = gr.Number(value=2.0, label="Sy", precision=2)
                    src_z = gr.Number(value=1.5, label="Sz", precision=2)
                with gr.Row():
                    rec_x = gr.Number(value=7.0, label="Rx", precision=2)
                    rec_y = gr.Number(value=5.0, label="Ry", precision=2)
                    rec_z = gr.Number(value=1.5, label="Rz", precision=2)
                    heatmap_material = gr.Dropdown(
                        choices=["None (raw)", "Concrete (low absorption)", "Painted drywall (mid)",
                                 "Curtains (high high-freq)", "Carpet (mid/high)", "Acoustic panels (broadband)"],
                        value="None (raw)", label="Material", scale=2)
                with gr.Row():
                    heatmap_strength = gr.Slider(0, 1, value=0.6, step=0.05, label="Heatmap str")
                    assumed_snr_db = gr.Slider(0, 40, value=20, step=1, label="SNR(dB)")
                    use_case = gr.Dropdown(
                        choices=["Academic research", "Architecture", "Healthcare", "Industrial", "Education", "Other"],
                        value="Academic research", label="Use case")

            # ── RUN BUTTON ──
            with gr.Row(elem_classes=["av-run-bar"]):
                run_btn = gr.Button("▶  Run Full Analysis", variant="primary", size="lg", scale=1, min_width=220)
                gr.HTML("<span class='av-muted' style='align-self:center;padding-left:12px;'>"
                        "12 analyses: EDC · RT60 · Octave RT60 · C80 · D50 · STI · IACC · "
                        "Waveform · Freq Response · Waterfall · Room Modes · Standards</span>")

            # ── KPI ──
            kpi_html = gr.HTML("")

            # ── RESULT TABS (12 visualizations) ──
            # Inside the Tabs block, replace each tab's description:

            with gr.Tabs():
                with gr.TabItem("🌐 3D Spatial"):
                    gr.HTML("""<div class="av-tab-header cyan">
                        <span class="icon">🌐</span>
                        <span class="text">First-order reflections via image-source method. Drag to rotate, scroll to zoom.</span>
                    </div>""")
                    reflections_plot = gr.Plot(label="3D Reflections")

                with gr.TabItem("〰️ Waveform"):
                    gr.HTML("""<div class="av-tab-header">
                        <span class="icon">〰️</span>
                        <span class="text">RIR waveform with direct sound marker and C80/D50 boundaries. Use the range slider below to zoom in.</span>
                    </div>""")
                    waveform_plot = gr.Plot(label="RIR Waveform")

                with gr.TabItem("📉 EDC"):
                    gr.HTML("""<div class="av-tab-header green">
                        <span class="icon">📉</span>
                        <span class="text">Schroeder backward integration with regression guide lines for EDT, T20, T30.</span>
                    </div>""")
                    edc_img = gr.Image(label="Energy Decay Curve", height=420)

                with gr.TabItem("📊 Octave RT60"):
                    gr.HTML("""<div class="av-tab-header purple">
                        <span class="icon">📊</span>
                        <span class="text">RT60 (EDT / T20 / T30) at standard octave bands from 125 Hz to 4000 Hz via bandpass filtering.</span>
                    </div>""")
                    octave_plot = gr.Plot(label="Octave Band RT60")

                with gr.TabItem("📈 Freq Response"):
                    gr.HTML("""<div class="av-tab-header orange">
                        <span class="icon">📈</span>
                        <span class="text">Magnitude spectrum (raw + smoothed) on log scale with octave band markers.</span>
                    </div>""")
                    freq_resp_plot = gr.Plot(label="Frequency Response")

                with gr.TabItem("🔥 Spectrogram"):
                    gr.HTML("""<div class="av-tab-header pink">
                        <span class="icon">🔥</span>
                        <span class="text">Mel spectrogram with optional material absorption overlay visualization.</span>
                    </div>""")
                    spec_plot = gr.Plot(label="Mel Spectrogram")

                with gr.TabItem("🌊 Waterfall"):
                    gr.HTML("""<div class="av-tab-header cyan">
                        <span class="icon">🌊</span>
                        <span class="text">3D waterfall showing how each frequency band decays over time. Drag to rotate.</span>
                    </div>""")
                    waterfall_plot = gr.Plot(label="Waterfall Plot")

                with gr.TabItem("🎯 Fingerprint"):
                    gr.HTML("""<div class="av-tab-header purple">
                        <span class="icon">🎯</span>
                        <span class="text">Normalized radar chart of clarity, definition, spatial quality and intelligibility.</span>
                    </div>""")
                    fingerprint_plot = gr.Plot(label="Acoustic Fingerprint")

                with gr.TabItem("🏛️ Room Modes"):
                    gr.HTML("""<div class="av-tab-header teal">
                        <span class="icon">🏛️</span>
                        <span class="text">Axial, tangential and oblique room modes up to 500 Hz with density histogram overlay.</span>
                    </div>""")
                    modes_plot = gr.Plot(label="Room Modes")

                with gr.TabItem("✅ Standards"):
                    gr.HTML("""<div class="av-tab-header green">
                        <span class="icon">✅</span>
                        <span class="text">Compliance check against ANSI S12.60, ISO 3382-3 and industry standards for classrooms, offices, hospitals and more.</span>
                    </div>""")
                    standards_html_out = gr.HTML("")

                with gr.TabItem("🎧 Auralization"):
                    gr.HTML("""<div class="av-tab-header orange">
                        <span class="icon">🎧</span>
                        <span class="text">Upload dry speech or music audio to hear how it sounds in the analyzed room via FFT convolution.</span>
                    </div>""")
                    with gr.Row():
                        dry_player = gr.Audio(label="Dry", interactive=False)
                        wet_player = gr.Audio(label="Wet", interactive=False)

                with gr.TabItem("📊 JSON"):
                    gr.HTML("""<div class="av-tab-header">
                        <span class="icon">📊</span>
                        <span class="text">Full metrics in JSON format for programmatic use or integration with other tools.</span>
                    </div>""")
                    metrics_json = gr.Code(label="Metrics", language="json", lines=14)

                with gr.TabItem("❓ Help"):
                    gr.HTML("""
                    <div class="av-tab-header green">
                        <span class="icon">❓</span>
                        <span class="text">How to use AcoustiVision Pro — step-by-step guide, metric definitions and tab reference.</span>
                    </div>

                    <div style="padding:12px 16px;color:var(--text-primary);font-size:13px;line-height:1.7;">

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">🚀 Quick Start</h3>
                      <ol style="padding-left:20px;margin:0 0 20px;">
                        <li><b>Load an RIR</b> — Either <em>search</em> the RIRMega dataset (left panel) or <em>upload</em> your own <code>.wav</code> file.</li>
                        <li><b>Set room geometry</b> — Open <em>⚙ Room Geometry &amp; Parameters</em> and enter dimensions, source/receiver positions. If you loaded from RIRMega these fill automatically.</li>
                        <li><b>Click ▶ Run Full Analysis</b> — All 12 analyses run in one pass.</li>
                        <li><b>Explore tabs</b> — Browse results across the visualization tabs.</li>
                        <li><b>Export</b> — Download a multi-page <em>PDF Report</em> or a <em>CSV</em> of all metrics.</li>
                      </ol>

                      <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">🔍 Searching RIRMega</h3>
                      <ul style="padding-left:20px;margin:0 0 20px;">
                        <li><b>Volume range</b> — Filter rooms by cubic-metre volume (L × W × H).</li>
                        <li><b>RT60 range</b> — Target reverberation time window in seconds.</li>
                        <li><b>Absorption range</b> — Average absorption coefficient (0 = fully reflective, 1 = fully absorptive).</li>
                        <li><b>Split</b> — Restrict to <code>train</code>, <code>val</code>, or <code>test</code> partition, or <code>any</code>.</li>
                        <li>Click a result row to auto-load the RIR and populate room parameters.</li>
                      </ul>

                      <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📐 Room Geometry &amp; Parameters</h3>
                      <ul style="padding-left:20px;margin:0 0 20px;">
                        <li><b>L / W / H</b> — Room length, width and height in metres. Used for room-mode calculation and the 3D reflection view.</li>
                        <li><b>Sx, Sy, Sz / Rx, Ry, Rz</b> — Source and receiver coordinates (metres).</li>
                        <li><b>Material &amp; Heatmap strength</b> — Applies a frequency-dependent absorption overlay to the spectrogram for visual comparison only (does not alter metrics).</li>
                        <li><b>SNR (dB)</b> — Assumed signal-to-noise ratio used for the STI proxy calculation.</li>
                      </ul>

                      <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📏 Metric Definitions</h3>
                      <table style="width:100%;border-collapse:collapse;font-size:12px;color:var(--text-primary);">
                        <thead>
                          <tr style="border-bottom:2px solid var(--border);background:var(--bg-surface);">
                            <th style="padding:8px 10px;text-align:left;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Metric</th>
                            <th style="padding:8px 10px;text-align:left;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Description</th>
                            <th style="padding:8px 10px;text-align:center;color:var(--text-muted);font-size:11px;text-transform:uppercase;">Typical Range</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">EDT</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Early Decay Time — RT60 extrapolated from the first 10 dB of decay. Reflects perceived reverberance.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.2 – 3.0 s</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">T20</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Reverberation time from −5 to −25 dB decay range, extrapolated to −60 dB.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.2 – 3.0 s</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">T30</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Reverberation time from −5 to −35 dB decay range. Most robust broadband RT60 estimate.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.2 – 3.0 s</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">C80 (dB)</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Clarity — ratio of early energy (0–80 ms) to late energy. Higher = clearer for music.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">−5 to +10 dB</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">D50</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Definition — fraction of energy arriving within 50 ms. Higher = better speech intelligibility.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.3 – 0.8</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">STI (proxy)</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Speech Transmission Index estimate derived from RT60 and assumed SNR. Approximation only.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.0 – 1.0</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">IACC</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Inter-Aural Cross-Correlation (stereo RIRs only). Lower values → wider spatial impression.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0.0 – 1.0</td></tr>
                          <tr><td style="padding:6px 10px;border-bottom:1px solid var(--border);font-weight:600;">Wellness</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);">Composite score (0–100) combining RT60, STI, D50, C80 and room volume. Higher = better for speech-centric use.</td>
                              <td style="padding:6px 10px;border-bottom:1px solid var(--border);text-align:center;">0 – 100</td></tr>
                        </tbody>
                      </table>

                      <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📑 Tab Guide</h3>
                      <table style="width:100%;border-collapse:collapse;font-size:12px;color:var(--text-primary);">
                        <tbody>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">🌐 3D Spatial</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Image-source first-order reflections in an interactive 3D room view. Drag to orbit, scroll to zoom.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">〰️ Waveform</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Time-domain RIR with direct-sound marker and 50 ms / 80 ms boundary lines. Range slider for zoom.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">📉 EDC</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Schroeder backward-integrated energy decay curve with dB guide lines.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">📊 Octave RT60</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">EDT, T20 and T30 per octave band (125 Hz – 4 kHz) via 4th-order Butterworth bandpass filters.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">📈 Freq Response</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">FFT magnitude spectrum (raw + smoothed) on a log-frequency axis.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">🔥 Spectrogram</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Mel spectrogram with optional material-absorption tint for visual exploration.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">🌊 Waterfall</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">3D waterfall showing frequency-band energy decay over time. Drag to rotate.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">🎯 Fingerprint</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Radar chart normalizing C80, D50, IACC and STI onto a 0–1 scale for quick comparison.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">🏛️ Room Modes</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Axial, tangential and oblique standing-wave frequencies up to 500 Hz with density overlay.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">✅ Standards</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Pass/fail checks against ANSI S12.60, ISO 3382-3, and common room-type criteria.</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">🎧 Auralization</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">Upload a dry recording to hear it convolved with the loaded RIR (FFT-based).</td></tr>
                          <tr><td style="padding:5px 10px;border-bottom:1px solid var(--border);font-weight:600;white-space:nowrap;">📊 JSON</td>
                              <td style="padding:5px 10px;border-bottom:1px solid var(--border);">All computed metrics as JSON for copy-paste or programmatic use.</td></tr>
                        </tbody>
                      </table>

                      <hr style="border:none;border-top:1px solid var(--border);margin:16px 0;">

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">🎧 Auralization Tips</h3>
                      <ul style="padding-left:20px;margin:0 0 20px;">
                        <li>Upload a <b>mono, anechoic</b> <code>.wav</code> file (speech or music) as the <em>Dry Audio</em>.</li>
                        <li>Audio is automatically resampled to match the RIR's sample rate and trimmed to 30 s max.</li>
                        <li>The <em>Wet</em> output is the FFT convolution of your dry signal with the RIR — this simulates what a listener would hear in the room.</li>
                      </ul>

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">📄 Exporting</h3>
                      <ul style="padding-left:20px;margin:0 0 20px;">
                        <li><b>PDF Report</b> — Multi-page document with key metrics, wellness score, EDC, spectrogram and radar plots.</li>
                        <li><b>CSV Export</b> — Flat file containing all main metrics, octave-band RT60 values and the first 30 room modes.</li>
                        <li>Both require running the analysis first.</li>
                      </ul>

                      <h3 style="color:var(--accent);margin:0 0 12px;font-size:16px;">⚠️ Limitations &amp; Notes</h3>
                      <ul style="padding-left:20px;margin:0 0 16px;">
                        <li>STI is a <em>proxy</em> based on RT60 and assumed SNR — not a full modulation-transfer-function computation.</li>
                        <li>IACC requires a <b>stereo</b> RIR file; mono files will show "—".</li>
                        <li>Room-mode calculation assumes a rectangular (shoebox) room.</li>
                        <li>The material overlay on the spectrogram is for <em>visualization only</em> and does not affect computed metrics.</li>
                        <li>Maximum audio duration is 30 seconds (configurable via <code>ACOUSTIVISION_MAX_AUDIO_SECONDS</code> env var).</li>
                      </ul>

                    </div>
                    """)

            # ── Report + Export ──
            gr.HTML("<hr class='av-sep'/>")
            gr.HTML("""<div class='av-section-title'>
                            <span class='av-section-icon orange'>📄</span> Report & Export
                        </div>""")

            with gr.Row():
                make_pdf_btn = gr.Button("📄 PDF Report", variant="primary", scale=1)
                export_csv_btn = gr.Button("📥 Export CSV", variant="secondary", scale=1)
                pdf_file = gr.File(label="PDF", height=60, scale=1)
                csv_file = gr.File(label="CSV", height=60, scale=1)
                with gr.Column(scale=1, min_width=140):
                    stats_md = gr.HTML(get_impact_stats_md())
                    refresh_stats_btn = gr.Button("🔄", variant="secondary", size="sm")
                    stats_md2 = gr.HTML("")

            with gr.Accordion("⚙ Admin", open=False):
                summary_btn = gr.Button("Analytics Summary", variant="secondary", size="sm")
                summary_out = gr.Code(language="json", label="Analytics", lines=10)
    # ── Footer ──
    gr.HTML("""
    <div class="av-footer">
      <div class="av-footer-content">
        <div class="av-footer-left">
          <span class="av-footer-brand">AcoustiVision Pro</span>
          <span class="av-footer-sep">·</span>
          <span class="av-footer-text">Room acoustics analysis toolkit</span>
        </div>
        <div class="av-footer-center">
          <span class="av-footer-powered">
            Powered by
            <a href="https://huggingface.co/datasets/mandipgoswami/rirmega" target="_blank" rel="noopener">
              <img src="https://huggingface.co/front/assets/huggingface_logo-noborder.svg" alt="HF" class="av-hf-logo"/>
              RIRMega
            </a>
            &amp;
            <a href="https://huggingface.co/datasets/mandipgoswami/rir-mega-speech" target="_blank" rel="noopener">
              RIRMega Speech
            </a>
          </span>
        </div>
        <div class="av-footer-right">
          <span class="av-footer-credit">Developed by Mandip Goswami</span>
        </div>
      </div>
    </div>
    """)
    # ══════════════════════════════════════
    #  EVENT WIRING
    # ══════════════════════════════════════

    # --- Run analysis (15 outputs) ---
    run_btn.click(
        fn=analyze_rir_and_build_outputs,
        inputs=[rir_file, dry_file, room_L, room_W, room_H,
                src_x, src_y, src_z, rec_x, rec_y, rec_z,
                heatmap_material, heatmap_strength, assumed_snr_db,
                user_id, use_case],
        outputs=[
            kpi_html,  # 1
            reflections_plot,  # 2
            edc_img,  # 3
            spec_plot,  # 4
            fingerprint_plot,  # 5
            waveform_plot,  # 6
            octave_plot,  # 7
            freq_resp_plot,  # 8
            waterfall_plot,  # 9
            modes_plot,  # 10
            standards_html_out,  # 11
            dry_player,  # 12
            wet_player,  # 13
            metrics_json,  # 14
            state,  # 15
        ])


    # --- HF search ---
    def _hf_search(ds, mf, vmin, vmax, rmin, rmax, amin, amax, split):
        status, choices = hf_search_rirmega(
            dataset_name=ds, volume_range=(vmin, vmax),
            rt60_range=(rmin, rmax), absorption_range=(amin, amax),
            split_filter=split, metadata_filename=mf, limit=12)
        labels = [c[0] for c in choices]
        mapping = {}
        for label, blob_json in choices:
            try:
                mapping[label] = json.loads(blob_json)
            except:
                mapping[label] = {}
        return (status, gr.update(choices=labels, value=None, interactive=True), mapping)


    hf_btn.click(
        fn=_hf_search,
        inputs=[ds_name, metadata_filename, vol_min, vol_max,
                rt60_min, rt60_max, abs_min, abs_max, split_filter],
        outputs=[hf_status, hf_choices, hf_hits_state])


    # --- Apply HF selection ---
    def _extract_xyz(obj):
        if obj is None: return (None, None, None)
        if isinstance(obj, str):
            try:
                obj = ast.literal_eval(obj)
            except:
                return (None, None, None)
        if isinstance(obj, (list, tuple)) and len(obj) >= 3:
            try:
                return (float(obj[0]), float(obj[1]), float(obj[2]))
            except:
                return (None, None, None)
        if isinstance(obj, dict):
            if all(k in obj for k in ("x", "y", "z")):
                try:
                    return (float(obj["x"]), float(obj["y"]), float(obj["z"]))
                except:
                    return (None, None, None)
            for key in ("pos", "position", "xyz", "coords"):
                if key in obj and obj[key] is not None:
                    return _extract_xyz(obj[key])
        return (None, None, None)


    def _hf_apply_choice(selected_label, hf_map, ds):
        if not selected_label or not isinstance(hf_map, dict):
            return (gr.update(),) * 10 + ("",)
        blob = hf_map.get(selected_label, {}) or {}
        wav_path = blob.get("wav", "")
        try:
            resolved = resolve_hf_wav_path(ds, wav_path)
            hf_path = hf_hub_download(repo_id=ds, repo_type="dataset", filename=resolved)
            local_wav = copy_to_app_temp(hf_path)
        except Exception as e:
            raise gr.Error(f"Download failed: {e}")
        room_size = blob.get("room_size")
        if isinstance(room_size, str):
            try:
                room_size = ast.literal_eval(room_size)
            except:
                room_size = None
        L = W = H = None
        if isinstance(room_size, (list, tuple)) and len(room_size) == 3:
            L, W, H = room_size
        sx, sy, sz = _extract_xyz(blob.get("source"))
        rx, ry, rz = _extract_xyz(blob.get("microphone"))
        fname = os.path.basename(wav_path)
        mets = blob.get("metrics") or {}
        info_parts = [f"✓ <b>{fname}</b>"]
        if L and W and H: info_parts.append(f"Room: {L}×{W}×{H}m")
        vol = blob.get("volume_m3")
        if vol:
            try:
                info_parts.append(f"V={float(vol):.1f}m³")
            except:
                pass
        rt60_val = mets.get("rt60") if isinstance(mets, dict) else None
        if rt60_val:
            try:
                info_parts.append(f"RT60={float(rt60_val):.2f}s")
            except:
                pass
        info_html = f"<div class='av-status success'>{' · '.join(info_parts)}</div>"
        return (local_wav, L, W, H, sx, sy, sz, rx, ry, rz, info_html)


    hf_choices.change(
        fn=_hf_apply_choice,
        inputs=[hf_choices, hf_hits_state, ds_name],
        outputs=[rir_file, room_L, room_W, room_H,
                 src_x, src_y, src_z, rec_x, rec_y, rec_z, loaded_info])

    # --- PDF ---
    make_pdf_btn.click(fn=build_pdf_from_state, inputs=[state, user_id, use_case], outputs=[pdf_file])

    # --- CSV Export ---
    export_csv_btn.click(fn=export_csv_from_state, inputs=[state], outputs=[csv_file])
    from huggingface_hub import upload_file
    import tempfile, os, json, datetime as dt, sqlite3


    def sync_impact_ledger_if_due(db_path="impact_tracker.sqlite",
                                  repo_id="mandipgoswami/acoustivision-impact-ledger",
                                  every_n_events=25,
                                  force=False):
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            return  # no token, silently skip (safe for public Spaces)
        con = sqlite3.connect(db_path);
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM usage_events");
        total = int(cur.fetchone()[0] or 0)
        con.close()
        if (not force) and every_n_events and total % int(every_n_events) != 0:
            return
        summary = get_analytics_summary()  # <- you already added this earlier
        summary["updated_utc"] = dt.datetime.utcnow().isoformat() + "Z"
        tmp = tempfile.gettempdir()
        local = os.path.join(tmp, "summary.json")
        with open(local, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        upload_file(path_or_fileobj=local, path_in_repo="summary.json",
                    repo_id=repo_id, repo_type="dataset", token=token)


    # --- Stats ---
    def _refresh():
        h = get_impact_stats_md();
        return h, h


    refresh_stats_btn.click(fn=_refresh, inputs=[], outputs=[stats_md, stats_md2])


    # --- Admin ---
    def _get_summary():
        return json.dumps(get_analytics_summary(), indent=2)


    summary_btn.click(_get_summary, outputs=[summary_out])

# ─── Launch ───
if __name__ == "__main__":
    demo.queue()
    demo.launch(show_error=True, share=True)
