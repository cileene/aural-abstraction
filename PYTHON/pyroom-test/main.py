# Use this to capture an IR from you computers built in speakers and mic.

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.signal import fftconvolve

def log_sine_sweep(fs, duration, f_start=20.0, f_end=20000.0):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    K = duration / np.log(f_end / f_start)
    L = f_start * K
    sweep = np.sin(2 * np.pi * L * (np.exp(t / K) - 1.0))
    # fade in/out to reduce clicks
    fade_len = int(0.02 * fs)
    fade = np.ones_like(sweep)
    fade[:fade_len] *= np.linspace(0, 1, fade_len)
    fade[-fade_len:] *= np.linspace(1, 0, fade_len)
    sweep *= fade
    return sweep.astype(np.float32)

def inverse_sweep(sweep, fs, duration, f_start=20.0, f_end=20000.0):
    # Inverse filter for ESS: time-reversed sweep with amplitude correction
    t = np.linspace(0, duration, len(sweep), endpoint=False)
    K = duration / np.log(f_end / f_start)
    # amplitude correction term (approx)
    env = np.exp(t / K)
    inv = (sweep[::-1] / np.maximum(env, 1e-9)).astype(np.float32)
    # normalize
    inv /= np.max(np.abs(inv) + 1e-12)
    return inv

def main():
    fs = 48000
    duration = 4.0
    f_start, f_end = 50.0, 18000.0  # keep inside laptop capabilities

    sweep = log_sine_sweep(fs, duration, f_start, f_end)
    inv = inverse_sweep(sweep, fs, duration, f_start, f_end)

    # Add silence before/after to capture tail
    pre_sil = np.zeros(int(0.5 * fs), dtype=np.float32)
    post_sil = np.zeros(int(2.0 * fs), dtype=np.float32)
    play_sig = np.concatenate([pre_sil, sweep, post_sil])

    print("Recording... (stay quiet, keep laptop still)")
    rec = sd.playrec(play_sig, samplerate=fs, channels=1, dtype=np.float32)
    sd.wait()
    rec = rec[:, 0]

    sf.write("recording.wav", rec, fs)

    # Deconvolution (recording convolved with inverse sweep)
    ir = fftconvolve(rec, inv, mode="full")

    # Find main peak and trim around it
    peak = np.argmax(np.abs(ir))
    start = max(0, peak - int(0.01 * fs))
    end = min(len(ir), peak + int(2.0 * fs))
    ir_trim = ir[start:end]
    ir_trim /= np.max(np.abs(ir_trim) + 1e-12)

    sf.write("ir.wav", ir_trim.astype(np.float32), fs)
    print("Saved: recording.wav, ir.wav")

if __name__ == "__main__":
    main()