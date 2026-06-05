import joblib
import os
import pandas as pd
import IR_Extraction as IR
import numpy as np
import socket
import struct


def extract_features_from_ir(path):
    # In UseModel.py, replace part of extract_features_from_ir:
    ir, sr = IR.load_ir(path)
    if ir.ndim > 1:
        ir = ir[0]  # use W channel only for B-format, or left channel for stereo
    ir = ir / np.max(np.abs(ir))

    peak_idx = np.argmax(np.abs(ir))
    ir_trimmed = ir[peak_idx:]

    edc_db = IR.compute_edc(ir)
    rt20 = IR.compute_rt(edc_db, sr, -5, -25)
    rt30 = IR.compute_rt(edc_db, sr, -5, -35)
    EDT = IR.compute_rt(edc_db, sr, 0, -10)

    # Use trimmed signal for clarity/definition like training did:
    c50, c80 = IR.compute_clarity(ir_trimmed, sr)
    d50, d80 = IR.compute_definition(ir_trimmed, sr)

    octave_T20_bands = IR.compute_T20_octave_band(ir, sr)

    extracted_features = {
        "RT20": rt20,
        "RT30": rt30,
        "EDT": EDT,
        "C50": c50,
        "C80": c80,
        "D50": d50,
        "D80": d80
    }
    extracted_features.update(octave_T20_bands)
    
    return extracted_features

if __name__ == "__main__":

    # Load trained tools
    scaler = joblib.load("scaler.pkl")
    pca = joblib.load("pca.pkl")
    model = joblib.load("model.pkl")

    results = [] #create list to store results

    file = os.listdir("IR_Deploy")[0]
    full_path = os.path.join("IR_Deploy", file)

    features = extract_features_from_ir(full_path) #extract the features

    # Convert to features dataframe for scaling and PCA
    df_features = pd.DataFrame([features])
    # make sure it's in the correct order for the model

    # Apply scaler and PCA
    X_scaled = scaler.transform(df_features)
    X_pca = pca.transform(X_scaled)
    print("pca.transform result (first PCs):", X_pca[0][:6])
    # Predict model
    prediction = model.predict(X_pca)[0]

    # Store result
    df = pd.DataFrame([{
        "filename": file,
        "color": prediction[0],
        "spaciality": prediction[1],
        "composition": prediction[2],
        "shape": prediction[3],
        "material": prediction[4],
    }])
    df.to_csv("Predictions.csv", index=False)

    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 5001

    data_to_send = [prediction[0], prediction[1], prediction[2], prediction[3], prediction[4]]
    packed_bytes = struct.pack("fffff", *data_to_send)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((SERVER_IP, SERVER_PORT))
            client.sendall(packed_bytes)
            print("data sent")
    except socket.error as e:
        print("Socket error")