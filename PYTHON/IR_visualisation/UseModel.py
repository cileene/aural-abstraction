import joblib
import os
import pandas as pd
import IR_Extraction as IR

def extract_features_from_ir(path):
    ir, sr = IR.load_ir(path)

    edc_db = IR.compute_edc(ir)

    rt20 = IR.compute_rt(edc_db, sr, -5, -25)
    rt30 = IR.compute_rt(edc_db, sr, -5, -35)

    EDT = IR.compute_rt(edc_db, sr, 0, -10)

    c50, c80 = IR.compute_clarity(ir, sr)
    d50, d80 = IR.compute_definition(ir, sr)

    return {
        "RT20": rt20,
        "RT30": rt30,
        "EDT": EDT,
        "C50": c50,
        "C80": c80,
        "D50": d50,
        "D80": d80
    }

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
    df_features = df_features[[
        "RT20", "RT30", "EDT", "C50", "C80", "D50", "D80"
    ]]

    # Apply scaler and PCA
    X_scaled = scaler.transform(df_features)
    X_pca = pca.transform(X_scaled)

    # Predict model
    prediction = model.predict(X_pca)[0]

    # Store result
    result = {
        "file": file,
        "Size": prediction[0],
        "Texture": prediction[1],
        "Temp": prediction[2]
        }

    results.append(result)

    # Save predictions
    df = pd.DataFrame(results)
    df.to_csv("Predictions.csv", index=False)
