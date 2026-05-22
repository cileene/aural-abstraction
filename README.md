# Aural Abstraction

*From impulse responses to perceptual visualization.*

P4 project, Medialogy 4th semester, Aalborg University Copenhagen, 2026.

## About

This monorepo contains the full pipeline behind *Aural Abstraction*, which investigates:

> To what extent can standardized acoustic metrics extracted from a room impulse response be mapped, via a supervised ML model, to an abstract visualization that elicits a consistent perceptual vocabulary among non-expert listeners?

The work is grounded in Blesser and Salter's concept of *aural architecture* (2007) — the experiential consequence of how a space treats sound — and targets the gap between everyday listening and the technical vocabulary required to describe it.

## Repository layout

```
.
├── PYTHON/      # IR feature extraction, PCA, MLP training and deployment
└── aa_godot_viz/   # Godot 4.6 (C#) procedural tree visualization
```

## Pipeline

```
IR (.wav) → Feature extraction → Normalization → PCA → MLP regressor → 5 perceptual parameters → Godot visualization
```

**Acoustic features extracted** (ISO 3382 compliant): RT20, RT30, EDT, C50, C80, D50, D80, plus octave-band T30.

**Perceptual output parameters** (predicted by the MLP, normalized 0–1): Color, Spatiality, Composition, Shape, Material.

**Visualization**: a procedurally generated tree built from a recursive branching grammar. The five parameters drive tree structure (MaxDepth, LengthDecay, BranchAngle, Randomness), point cloud density and radius, surface shader properties, environment fog, lighting, and camera FOV. Identical parameter inputs always reproduce an identical tree (seeded RNGs).

## Requirements

**Python (`PYTHON/`)**
- Python 3.11+
- numpy, scipy, librosa, scikit-learn, joblib, pyfar (fractional octave band filter)

**Godot (`aa_godot_viz/`)**
- Godot 4.6.2 (.NET build)
- .NET 8 SDK



## Usage

```bash
# 1. Extract features from IRs
python PYTHON/IR_visualisation/IR_Extraction.py

# 2. Normalize and reduce dimensionality
python PYTHON/IR_visualisation/Normalize_and_PCA.py

# 3. Train the model
python PYTHON/IR_visualisation/ModelTraining.py

# 4. Run inference on a new IR
python PYTHON/IR_visualisation/UseModel.py path/to/new_ir.wav
```

Open `aa_godot_viz/project.godot` in Godot to run the visualization.

## Status

The supervised mapping could not be established under the conditions tested. The MLP returned a negative R² across all five perceptual parameters, performing worse than a mean-prediction baseline. Participants nonetheless reached perceptual congruence individually in the qualitative study, but the congruence was personal rather than shared. The project is documented as an exploratory proof of concept rather than a finalized perceptual visual language. See Section 8 of the report for the full discussion.

## Authors

[Camille H. Haarder](https://github.com/Calcium1000), [Ingrid Evertsen](https://github.com/IngridEvertsen), [Nick L. Jerlung](https://github.com/cileene), [Sandra E. Bach](https://github.com/HandySandy123), [Valdemar H. Wessing](https://github.com/ValdemarWessing).

Supervised by Razvan Paisa.

## References

Blesser, B., & Salter, L.-R. (2007). *Spaces speak, are you listening? Experiencing aural architecture*. MIT Press.

Godot Engine. (2026). *Godot 4.6 release: It's all about your flow*. https://godotengine.org/releases/4.6/

OpenAIR. (n.d.). *OpenAIR – Open Air Library*. University of York. https://openair.hosted.york.ac.uk/

Pyfar Developers. (2026). *pyrato*. https://pyrato.readthedocs.io/