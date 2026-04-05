import os
import csv
import numpy as np
import librosa
import scipy.signal as signal
import pandas as pd
from scipy.stats import linregress

def load_ir(path):
    ir, sr = librosa.load(path, sr=None, mono=True)
    ir = ir / np.max(np.abs(ir))
    return ir, sr
def compute_edc(ir): #compute energy decay curve using the formula from the report
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


if __name__ == "__main__": # only run when playing in this file

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

            result = {
                "file": file,
                "T20": rt20,
                "T30": rt30,
                "EDT": EDT,
                "C50": C50,
                "C80": C80,
                "D50": D50,
                "D80": D80,
            }

            results.append(result)

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv("IR_Extraction_results.csv", index=False)
