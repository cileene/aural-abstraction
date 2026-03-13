import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

# Load dry audio
dry, fs_dry = sf.read("voice.wav")

# Load impulse response
ir, fs_ir = sf.read("large.aif")

# Ensure mono for simplicity
if dry.ndim > 1:
    dry = dry[:, 0]
if ir.ndim > 1:
    ir = ir[:, 0]

# Resample if needed (optional but recommended if sample rates differ)
if fs_dry != fs_ir:
    raise ValueError("Sample rates must match")

# Convolve
wet = fftconvolve(dry, ir, mode="full")

# Normalize to prevent clipping
wet /= np.max(np.abs(wet) + 1e-12)

# Save result
sf.write("largeWet.wav", wet.astype(np.float32), fs_dry)

print("Saved wet.wav")