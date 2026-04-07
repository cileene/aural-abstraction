import os
import csv
import numpy as np
import librosa
import scipy.signal as signal
import scipy.fft as fft
import pandas as pd
from scipy.stats import linregress
import matplotlib.pyplot as plt


def load_ir(path): #Returns a normalized impulse response and its sampling rate from a given file path
    ir, sr = librosa.load(path, sr=None, mono=True)
    ir = ir / np.max(np.abs(ir))
    return ir, sr
def compute_edc(ir): #Compute energy decay curve using the formula from the report
    energy = ir**2
    edc = np.cumsum(energy[::-1])[::-1]
    edc = edc / np.max(edc)
    edc_db = 10 * np.log10(edc + 1e-12)
    return edc_db

def compute_rt(edc_db, sr, start_db, end_db): #find rt60 using t20 and t30
    decay_index = np.where((edc_db <= start_db) & (edc_db >= end_db))[0] #find samples between start and end dB for line fitting

    t = decay_index / sr  # time axis for the selected decay segment (in seconds)
    y = edc_db[decay_index]  # corresponding EDC values (dB) used for line fitting

    slope = linregress(t, y).slope #Linear fit using time and dB

    # Extrapolate to -60 dB
    rt60 = -60 / slope

    return rt60

def compute_clarity(ir, sr):
    energy = ir**2

    t50 = int(0.05 * sr)
    t80 = int(0.08 * sr)

    early_50 = np.sum(energy[:t50])
    late_50 = np.sum(energy[t50:])

    early_80 = np.sum(energy[:t80])
    late_80 = np.sum(energy[t80:])

    C50 = 10 * np.log10(early_50 / late_50)
    C80 = 10 * np.log10(early_80 / late_80)

    return C50, C80

def compute_definition(ir, sr):
    energy = ir**2
    t50 = int(0.05 * sr)
    t80 = int(0.08 * sr)
    early_50 = np.sum(energy[:t50])
    early_80 = np.sum(energy[:t80])

    total_energy = np.sum(energy)

    D50 = early_50 / total_energy
    D80 = early_80 / total_energy
    return D50, D80

def compute_mel_T20_bands(ir, sr, n_bands=40):
    n_fft = 2048 #Windows size for STFT
    hop_length = 512 #Hop length for STFT

    stft = np.abs(librosa.stft(ir, n_fft=n_fft, hop_length=hop_length))**2 #Power spectrogram
    mel_filter_bank = librosa.filters.mel(sr=sr, n_fft=n_fft, n_mels=n_bands) #Mel filter bank to map frequencies to mel scale
    mel_power_spectrogram = mel_filter_bank @ stft #Apply mel filter bank to power spectrogram using matrix multiplication
    results = {}
    frame_times = librosa.frames_to_time(np.arange(mel_power_spectrogram.shape[1]), sr=sr, hop_length=hop_length) #Time axis for frames

    for i, mel_band_energy in enumerate(mel_power_spectrogram):
        edc = np.cumsum(mel_band_energy[::-1])[::-1] #EDC for each mel band
        if np.max(edc) == 0:
            results[i] = np.nan
            continue

        edc = edc / np.max(edc) #Normalize EDC
        edc_db = 10 * np.log10(edc + 1e-12) #Convert to dB
        T20 = compute_rt(edc_db, {sr / hop_length}, -5, -25) #Compute T20 for the corresponding mel band

        results[f"mel_T20_band_{i}"] = T20

    return results


if __name__ == "__main__": # only run when playing in this file
    skippedIRs = 0

    results = [] #create list for rsults

    for file in os.listdir("IR"):
        if file.endswith(".wav"):
            path = "IR/" + file

            ir, sr = load_ir(path)
            edc_db = compute_edc(ir)
            rt20 = compute_rt(edc_db, sr, -5, -25)
            rt30 = compute_rt(edc_db, sr, -5, -35)
            EDT = compute_rt(edc_db, sr, 0, -10)
            C50, C80 = compute_clarity(ir, sr)
            D50, D80 = compute_definition(ir, sr)
            mel_T20_bands = compute_mel_T20_bands(ir, sr)

            result = {
                "file": file,
                "RT20": rt20,
                "RT30": rt30,
                "EDT": EDT,
                "C50": C50,
                "C80": C80,
                "D50": D50,
                "D80": D80,
            }
            result.update(mel_T20_bands)
            
            skip = False

            for k, v in result.items(): #for each key, check value, if file is naN skip row
                if k != "file":
                    if np.isnan(v):
                        skip = True
                        skippedIRs += 1
                        break
            if skip:
                continue

            results.append(result)

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv("IR_Extraction_results.csv", index=False)
    print(f"Finished extracting features. Skipped {skippedIRs} IRs due to NaN values.")