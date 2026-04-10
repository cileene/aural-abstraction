from pyfar.dsp.filter import fractional_octave_bands as fob

def nth_octave_band(nth_root, lower_freq, upper_freq):
    center_freqs = []
    x = lower_freq
    while x < upper_freq:
        center_freqs.append(x)
        x = x * (2 ** (1/nth_root))
    center_freqs = [round(freq, 4) for freq in center_freqs]
    return center_freqs

center_freqs = nth_octave_band(3, 31.5, 20000)

