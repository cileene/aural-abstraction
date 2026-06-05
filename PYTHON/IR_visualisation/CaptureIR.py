import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.signal import fftconvolve
import os


USE_IPHONE_MIC = True


def main(output_path="ir.wav"):
    fs = 48000
    duration = 4.0
    f_start, f_end = 50.0, 18000.0

    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    K = duration / np.log(f_end / f_start)

    sweep = np.sin(2 * np.pi * f_start * K * (np.exp(t / K) - 1.0)).astype(np.float32)
    fade_len = int(0.02 * fs)
    sweep[:fade_len] *= np.linspace(0, 1, fade_len)
    sweep[-fade_len:] *= np.linspace(1, 0, fade_len)

    inv = (sweep[::-1] / np.maximum(np.exp(t / K), 1e-9)).astype(np.float32)
    inv /= np.max(np.abs(inv)) + 1e-12

    play_sig = np.concatenate([
        np.zeros(int(0.5 * fs), dtype=np.float32),
        sweep,
        np.zeros(int(2.0 * fs), dtype=np.float32),
    ])
    input_device = sd.default.device[0]
    if USE_IPHONE_MIC:
        devices = sd.query_devices()
        match = next((d["index"] for d in devices if "iphone" in d["name"].lower()), None)
        if match is None:
            raise RuntimeError("iPhone microphone not found — check Continuity Camera is connected")
        input_device = match

    print("Recording... (stay quiet, keep laptop still)")
    rec = sd.playrec(play_sig, samplerate=fs, channels=1, dtype=np.float32, device=(input_device, sd.default.device[1]))
    sd.wait()
    rec = rec[:, 0]

    sf.write("recording.wav", rec, fs)

    ir = fftconvolve(rec, inv, mode="full")
    peak = np.argmax(np.abs(ir))
    ir_trim = ir[max(0, peak - int(0.01 * fs)):peak + int(2.0 * fs)]
    ir_trim = (ir_trim / (np.max(np.abs(ir_trim)) + 1e-12)).astype(np.float32)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, ir_trim, fs)
    print(f"Saved: recording.wav, {output_path}")


if __name__ == "__main__":
    main()