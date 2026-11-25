# Codex handoff — 7 additional EN acoustic recordings (10 total)

**Approved scope:** one local, quota-conscious Pronunciada smoke-test expansion on the **existing** experimental branches. This is an instruction, not proof the test has run.

## Starting point

- Previous real inference: [QA_ACOUSTIC_REPORT.md](QA_ACOUSTIC_REPORT.md), 3 distinct SpeechOcean762 recordings succeeded.
- Candidate manifest: [qa_acoustic/expansion-candidates.json](qa_acoustic/expansion-candidates.json). Exactly seven adult **test** examples, seven distinct speakers, excluding previous three speakers; selected before examining model outputs.
- Existing runner: [run_acoustic_smoke.py](run_acoustic_smoke.py). Its `CLIPS` constant contains the old three audio paths and fixed hashes; **do not pretend it already accepts arbitrary WAV files**. Extend it via an **optional, separate** `--clips-manifest` mode, or create a separate `run_expansion_smoke.py` that reuses its pinned-model guards and inference logic. Preserve the original three-clip runner unchanged if possible.
- Local model directory (already downloaded, DO NOT download again): `~/.cache/lexilang/en-pronunciation-acoustic-qa/zipa-small-int8-dfe87c97662606fa6db90ad06f627d4363314744/`
- Model `model.int8.onnx`: 70,677,672 bytes; SHA-256 `d0e28b68164e8b1fbd6105100c01798828aa0855000ce9bbbd1a2cec233adf13`
- Model pinned HF revision `dfe87c97662606fa6db90ad06f627d4363314744`; Pronunciada pinned source `4619a298e5e2de927120122585683d18eda1f7c4`.
- Prior working runtime: `Scorer("en", precision="int8", threads=4, strictness=0.5, cache_size=1)`. **Do NOT set cache_size=0**: an upstream KeyError has been observed. Maintain the input normalization, balanced coaching and all calibrations.
- Previously downloaded runtime dependencies live in the separate QA virtual environment (see previous report). No Xcode build needed.

## Exactly seven new recordings

Read IDs, speaker IDs, relative source paths, pinned revision, URLs and HEAD byte counts from `qa_acoustic/expansion-candidates.json`. Do not substitute samples or move between train/test:

1. `001200015` — speaker `0120`
2. `001570024` — speaker `0157`
3. `003060002` — speaker `0306`
4. `004570010` — speaker `0457`
5. `004610037` — speaker `0461`
6. `005630017` — speaker `0563`
7. `005670043` — speaker `0567`

### Step 1 — locate exact human-reference labels before inference

Use the official, pinned `jimbozhang/speechocean762` revision `613968e3b0b789fc33936fb5eba1973176ba7d11`. Find each sample's precise reference transcript and word/phone-level human annotations in the official test manifest. Validate each file's split and speaker ID against the manifest. Avoid reliance on a guessed transcript, any language-model reconstruction or the Pronunciada predictions themselves. If real annotations are missing or ambiguous, mark that comparison **BLOCKED**, do not invent a human label or change the chosen samples without owner consent.

### Step 2 — download locally, verify and freeze inputs

Download **only these seven WAV files**, not the whole corpus, into a temporary local QA cache **outside Git**. Validate HTTP success, actual WAV decode, declared sample rate/channel count/duration, finite audio samples, exact local byte lengths and SHA-256. Persist a local `input-manifest.json` listing original pinned URLs, bytes, hashes, source revision, speaker, split, transcript, and available human labels. HEAD=200 from the previous check is not proof of WAV content. Do not modify any original audio or source repository files.

### Step 3 — seven real acoustic inference runs

Use the **already cached** ZIPA INT8 ONNX (check its SHA again); do not redownload weights or create a second ~71 MB artifact unless necessary for runtime compatibility. Use the same pinned Pronunciada source and `cache_size=1`. Score each WAV only once in the successful run, with full audio → 16 kHz mono → fbank → ZIPA → phoneme alignment → calibrated phone/word/sentence/stress → balanced coaching. Disable network access **during inference**, after the WAV downloads have finished. No fake acoustic results, no Apple Speech confidence, no transcript-only scoring, no synthesized TTS to simulate learner audio.

Persist each individual raw output and coaching flags as JSON with original audio hash. Flag non-finite values, missing timings, failed audio quality gates, repeated audio or unexpectedly identical results. Keep exact output counts for sound, word, syllable, stress, score and coaching records.

### Step 4 — quality-focused comparison

Where genuine expert labels exist, compare **at the same word/phone/stress units**: human-reported errors versus model flags, missed errors and false warnings on accepted speech. Differentiate confidence scales, raw phoneme probabilities and coaching error thresholds; count distinct flagged events, not every duplicate word/sound item as an independent mistake. Report concrete examples and potential false positives for manual review. Do **not** call the 10 recordings a statistically validated accuracy, precision, recall, F1, ECE/Brier or CEFR study. All seven new speakers are Mandarin-L1; they do not cover diverse accents or advanced adult C1/C2 performance.

Measure first-call/warm latency, model-only inference, full scoring time, per-clip duration and process peak RSS on the actual Mac. Note which network-dependent operations occurred **before** the offline inference session.

### Output and stopping condition

Create **new** evidence files and `experiments/pronunciation_en/QA_10_CLIP_REPORT.md` in **the same public experimental branch**, then a brief private report under `AssessmentKit/Experiments/PronunciationEN/` in the existing private experimental branch. Keep privately derived lesson/personal material out of the public repo. Include:

- PASS / FAIL / BLOCKED per step and **exactly how many of the seven** were actually scored.
- The original 3 + new 7 separately, with total `n=10` **only if all seven pass**.
- URLs/revisions/byte sizes/SHA-256; separate real expert labels from predictions.
- Sound/word/stress/coaching examples; clear false-positive/false-negative *case notes* where labels permit.
- Time, memory, failure logs and any license/provenance issues.
- **GO / HOLD / REJECT strictly for further local research**, not for release/merge/app integration.
- Preserve a machine-readable SHA256 inventory of *textual* evidence; do not push WAV or ONNX files.

**Limits:** no new branches, no changes to `main`, no merger, no GitHub Releases, no app/Xcode/SwiftUI/ReaderKit/Curriculum modifications, no native iPhone port, no full QA regression, no retraining or large downloads, no background tasks. Maximum two small script-fix iterations; stop if unable to obtain verified labels or more than a small subset. After committing the reports, **stop**. Reserve Codex budget for the separate Writing GEC and eventual full Lexi Lang regression.
