---
profile_id: flexible-curved-ultrasonic
version: "1.0"
title: Flexible curved-surface ultrasonic inspection
triggers:
  - flexible ultrasonic array
  - curved-surface ultrasonic inspection
  - conformal ultrasonic array
  - flexible phased array
  - 柔性曲面超声探测
  - 曲面超声成像
  - 柔性换能器
  - 曲面构件检测
status: active
---

# Project profile: flexible curved-surface ultrasonic inspection

Use this file to keep the review's scientific layers distinct. It is a routing
reference, not a substitute for reading the named source papers.

## Physical-to-inferential chain

Flexible probes interact with a curved surface through contact, coupling,
element pose, local normal, propagation velocity, attenuation, mode conversion,
and structural scattering. The instrument observes time-varying multichannel
signals; it does not observe defect size or material properties directly.

Keep this chain explicit:

```text
contact/propagation
-> A-scan or FMC observations
-> waveform, event, TOF, amplitude, phase
-> defect/features/learned representation
-> geometry, velocity, path, and delay calibration
-> baseline imaging (DAS/SAFT/TFM/PWI or method-specific baseline)
-> coherent/adaptive enhancement
-> visibility/localization/sizing/property-estimation candidate
-> uncertainty, domain shift, failure boundary
```

## Claim-level separations

- signal enhancement is not a sizing measurement;
- image sharpness is not localization accuracy;
- nominal resolution is not sizing error;
- a learned representation is not automatically a physical parameter;
- a method comparison is conditional on input, geometry, material, defect,
  frequency, calibration, threshold, truth definition, and data split;
- a review paper supports taxonomy or context, while an original experiment
  supports its own quantitative result.

## Minimum conditions for numerical claims

Record material, surface/curvature, probe and coupling, frequency/bandwidth,
defect type and depth, acquisition mode, algorithm settings, threshold,
reference/truth definition, metric, sample count, and train/test or validation
split whenever available. If a condition is missing, mark the claim for human
verification rather than filling it from intuition.

## Method comparison contract

Compare methods by input, output, assumptions, calibration burden, computation,
data requirement, failure modes, and evidence scope. Do not create a universal
winner or a cross-paper aggregate score unless the datasets and evaluation
protocol are genuinely comparable.
