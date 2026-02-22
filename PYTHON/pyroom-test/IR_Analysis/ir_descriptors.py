"""
ir_descriptors.py — minimal, dependency-stable IR descriptor module

Dependencies:
    numpy
    scipy (optional, only used for bandpass filtering; you can remove if not needed)

Implements (mono IR):
    - RT60 (Schroeder EDC regression, configurable dB range)
    - EDT (0 to -10 dB slope extrapolated to -60 dB)
    - C50 / C80 (clarity, dB)
    - DRR (direct-to-reverberant ratio, dB) with automatic direct-sound pick
    - Basic helpers: normalize, trim, detect direct sound, EDC

Notes:
    - Assumes IR is already deconvolved.
    - For consistent results, trim/align so the direct sound is near the start.
    - Standards often compute metrics per octave/third-octave band; this module is broadband by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import numpy as np

try:
    from scipy.signal import butter, sosfilt
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


@dataclass(frozen=True)
class IRDescriptors:
    rt60: Optional[float]      # seconds
    edt: Optional[float]       # seconds
    c50: Optional[float]       # dB
    c80: Optional[float]       # dB
    drr: Optional[float]       # dB
    direct_sample: Optional[int]
    fs: int


# ----------------------------
# Core helpers
# ----------------------------

def to_mono(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x)
    if x.ndim == 1:
        return x.astype(float)
    if x.ndim == 2:
        return x[:, 0].astype(float)
    raise ValueError("Audio must be 1D (mono) or 2D (channels).")


def normalize_peak(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    m = np.max(np.abs(x))
    if m < eps:
        return x
    return x / m


def trim_around_peak(x: np.ndarray, fs: int, pre_s: float = 0.01, post_s: float = 2.0) -> Tuple[np.ndarray, int]:
    """
    Trim around the largest absolute peak.
    Returns (trimmed_signal, peak_index_in_trimmed).
    """
    x = np.asarray(x, dtype=float)
    p = int(np.argmax(np.abs(x)))
    start = max(0, p - int(pre_s * fs))
    end = min(len(x), p + int(post_s * fs))
    xt = x[start:end]
    return xt, p - start


def detect_direct_sound(ir: np.ndarray, fs: int, search_ms: float = 50.0, rel_threshold: float = 0.2) -> int:
    """
    Detect direct sound onset as the first sample within the first `search_ms`
    that exceeds `rel_threshold` * max(abs(ir)).
    Returns sample index.
    """
    ir = np.asarray(ir, dtype=float)
    n = min(len(ir), int((search_ms / 1000.0) * fs))
    if n <= 0:
        return int(np.argmax(np.abs(ir)))
    seg = ir[:n]
    peak = np.max(np.abs(seg)) + 1e-12
    thr = rel_threshold * peak
    idx = np.argmax(np.abs(seg) >= thr)
    if np.abs(seg[idx]) >= thr:
        return int(idx)
    return int(np.argmax(np.abs(seg)))


def edc_schroeder(ir: np.ndarray) -> np.ndarray:
    """
    Energy Decay Curve via Schroeder integration.
    Returns linear EDC normalized to 1 at start.
    """
    ir = np.asarray(ir, dtype=float)
    e = ir * ir
    if not np.any(e):
        return np.zeros_like(e)
    edc = np.cumsum(e[::-1])[::-1]
    edc /= (np.max(edc) + 1e-12)
    return edc


def edc_db(edc_lin: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(edc_lin, 1e-12))


def _fit_decay_time(edc_db_curve: np.ndarray, fs: int, db_start: float, db_end: float) -> Optional[float]:
    """
    Fit a line to EDC dB curve between db_start and db_end (both negative or zero),
    then convert slope to RT60-style time: time for -60 dB.
    """
    y = np.asarray(edc_db_curve, dtype=float)
    t = np.arange(len(y), dtype=float) / float(fs)

    # region mask (y decreases from 0 downwards)
    lo = min(db_start, db_end)
    hi = max(db_start, db_end)
    mask = (y <= hi) & (y >= lo)

    idx = np.where(mask)[0]
    if idx.size < 10:
        return None

    # Use simple linear regression (least squares)
    tt = t[idx]
    yy = y[idx]
    A = np.vstack([tt, np.ones_like(tt)]).T
    slope, intercept = np.linalg.lstsq(A, yy, rcond=None)[0]

    if slope >= 0:
        return None

    return float(-60.0 / slope)


# ----------------------------
# Descriptor computations
# ----------------------------

def rt60(ir: np.ndarray, fs: int, db_start: float = -5.0, db_end: float = -35.0) -> Optional[float]:
    """
    RT60 estimate via Schroeder EDC regression.
    Default range (-5 to -35) corresponds to T30 extrapolated to -60 dB.
    Common alternatives:
        T20: db_start=-5, db_end=-25
        T30: db_start=-5, db_end=-35
    """
    edc = edc_schroeder(ir)
    y = edc_db(edc)
    return _fit_decay_time(y, fs, db_start, db_end)


def edt(ir: np.ndarray, fs: int) -> Optional[float]:
    """
    EDT: slope from 0 to -10 dB extrapolated to -60 dB.
    """
    edc = edc_schroeder(ir)
    y = edc_db(edc)
    return _fit_decay_time(y, fs, 0.0, -10.0)


def clarity(ir: np.ndarray, fs: int, t_ms: float) -> Optional[float]:
    """
    Clarity C_t = 10 log10 (E_early / E_late) with split at t_ms.
    For C50: t_ms=50
    For C80: t_ms=80
    """
    ir = np.asarray(ir, dtype=float)
    n_split = int((t_ms / 1000.0) * fs)
    n_split = np.clip(n_split, 1, len(ir) - 1)

    e = ir * ir
    e_early = np.sum(e[:n_split])
    e_late = np.sum(e[n_split:])

    if e_early <= 0 or e_late <= 0:
        return None
    return float(10.0 * np.log10(e_early / e_late))


def drr(ir: np.ndarray, fs: int, direct_idx: Optional[int] = None, direct_window_ms: float = 2.5) -> Optional[float]:
    """
    Direct-to-Reverberant Ratio (broadband):
        DRR = 10 log10 (E_direct / E_reverb)

    direct energy is computed in a short window around the direct sound.
    Default window is 2.5 ms (common-ish heuristic for broadband DRR).
    """
    ir = np.asarray(ir, dtype=float)
    if len(ir) < 10:
        return None

    if direct_idx is None:
        direct_idx = detect_direct_sound(ir, fs)

    w = int((direct_window_ms / 1000.0) * fs)
    w = max(1, w)
    start = max(0, direct_idx - w // 2)
    end = min(len(ir), start + w)

    e = ir * ir
    e_dir = np.sum(e[start:end])
    e_rev = np.sum(e[end:])  # reverberant tail after direct window

    if e_dir <= 0 or e_rev <= 0:
        return None
    return float(10.0 * np.log10(e_dir / e_rev))


# ----------------------------
# Optional: simple bandpass
# ----------------------------

def bandpass(ir: np.ndarray, fs: int, f_lo: float, f_hi: float, order: int = 4) -> np.ndarray:
    """
    Butterworth bandpass (requires SciPy). Useful if you want band-limited descriptors.
    """
    if not _HAVE_SCIPY:
        raise RuntimeError("SciPy not available. Install scipy or remove bandpass usage.")
    if f_lo <= 0 or f_hi >= fs / 2:
        raise ValueError("Band must be within (0, Nyquist).")
    sos = butter(order, [f_lo, f_hi], btype="bandpass", fs=fs, output="sos")
    return sosfilt(sos, ir)


# ----------------------------
# One-shot convenience
# ----------------------------

def compute_descriptors(
    ir: np.ndarray,
    fs: int,
    align_and_trim: bool = True,
    trim_pre_s: float = 0.01,
    trim_post_s: float = 2.0,
    rt_db_start: float = -5.0,
    rt_db_end: float = -35.0,
) -> IRDescriptors:
    """
    Compute a minimal set of broadband descriptors from an IR.
    """
    ir = to_mono(ir)
    ir = normalize_peak(ir)

    direct_sample = None

    if align_and_trim:
        ir, peak_in_trim = trim_around_peak(ir, fs, pre_s=trim_pre_s, post_s=trim_post_s)
        direct_sample = peak_in_trim
    else:
        direct_sample = detect_direct_sound(ir, fs)

    ir = normalize_peak(ir)

    return IRDescriptors(
        rt60=rt60(ir, fs, db_start=rt_db_start, db_end=rt_db_end),
        edt=edt(ir, fs),
        c50=clarity(ir, fs, 50.0),
        c80=clarity(ir, fs, 80.0),
        drr=drr(ir, fs, direct_idx=direct_sample),
        direct_sample=int(direct_sample) if direct_sample is not None else None,
        fs=int(fs),
    )


def as_dict(d: IRDescriptors) -> Dict[str, object]:
    return {
        "rt60": d.rt60,
        "edt": d.edt,
        "c50": d.c50,
        "c80": d.c80,
        "drr": d.drr,
        "direct_sample": d.direct_sample,
        "fs": d.fs,
    }