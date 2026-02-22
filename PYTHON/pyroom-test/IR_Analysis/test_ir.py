import soundfile as sf
from ir_descriptors import compute_descriptors, as_dict

# Load your IR wav
ir, fs = sf.read("../ir.wav")

# If it's stereo, the module will take channel 0 automatically
desc = compute_descriptors(ir, fs)

print(as_dict(desc))