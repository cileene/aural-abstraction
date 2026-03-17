import numpy as np
import soundfile as sf
from math import gcd
from scipy.signal import fftconvolve, resample_poly


def to_mono(x: np.ndarray) -> np.ndarray:
    if x.ndim > 1:
        return x[:, 0]
    return x


def resample_if_needed(x: np.ndarray, fs_in: int, fs_target: int) -> np.ndarray:
    if fs_in == fs_target:
        return x

    g = gcd(fs_in, fs_target)
    up = fs_target // g
    down = fs_in // g
    return resample_poly(x, up, down)


# Load dry audio
dry, fs_dry = sf.read("voice.wav")

# Load impulse response
ir, fs_ir = sf.read("DrawingRoomDPA.wav")

# Ensure mono for simplicity
dry = to_mono(dry)
ir = to_mono(ir)

# Resample IR to match dry audio sample rate
ir = resample_if_needed(ir, fs_ir, fs_dry)

# Convolve
wet = fftconvolve(dry, ir, mode="full")

# Normalize to prevent clipping
peak = np.max(np.abs(wet))
if peak > 1e-12:
    wet = wet / peak

# Save result
sf.write("drawingRoomDPAWet.wav", wet.astype(np.float32), fs_dry)

print("Saved smallBWet.wav")