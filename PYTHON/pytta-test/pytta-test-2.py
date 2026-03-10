import pytta
import matplotlib.pyplot as plt

# --- Load IR ---
# Replace with your actual mono IR wav file
ir = pytta.read_wav("dales_site1_1way_mono.wav")

print(f"Loaded IR: {ir.numSamples} samples @ {ir.samplingRate} Hz")
print(f"Duration: {ir.timeLength:.3f} s | Channels: {ir.numChannels}\n")

# --- Run RoomAnalysis ---
# nthOct=3 = 1/3 octave bands, nthOct=1 = full octave
analysis = pytta.RoomAnalysis(
    ir,
    nthOct=3,
    minFreq=100.0,
    maxFreq=10000.0,
    plotLundeby=False,       # set True to inspect Lundeby noise floor fitting
    bypassLundeby=False,     # set True if IR is clean and you want to skip it
    suppressWarnings=False,  # show warnings about IR quality
)

# --- Extract parameters ---
print("=== Reverberation Times ===")
edt  = analysis.EDT()
t20  = analysis.T20()
t30  = analysis.T30()

print("EDT  (bands):", edt.data)
print("T20  (bands):", t20.data)
print("T30  (bands):", t30.data)

print("\n=== Clarity & Definition ===")
c80 = analysis.C80()
d50 = analysis.D50()
ts  = analysis.Ts()

print("C80  (bands):", c80.data)
print("D50  (bands):", d50.data)
print("Ts   (bands):", ts.data)

print("\n=== Stage Parameters ===")
st_early = analysis.STearly()
st_late  = analysis.STlate()

print("STearly (bands):", st_early.data)
print("STlate  (bands):", st_late.data)

# --- Plot ---
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle("Room Acoustic Parameters", fontsize=14)

analysis.plot_EDT(axes=axes[0, 0])
analysis.plot_T20(axes=axes[0, 1])
analysis.plot_T30(axes=axes[1, 0])
analysis.plot_C80(axes=axes[1, 1])

plt.tight_layout()
plt.show()