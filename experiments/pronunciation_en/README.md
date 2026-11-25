# Lexi Lang — EN lexicon + calibration R&D (isolated branch)

**Status: experimental source-based candidate builder, NOT an iOS inference engine, NOT a published pack.**

This directory is intentionally separate from the [public production pack registry](../../packs.json) and from Lexi Lang's approved app UI. It does not edit the production \`main\`, the ReaderKit, the curriculum, the existing Audio Recorder, Apple Speech, Kokoro or the private AssessmentKit's scoring protocol.

## What was found upstream (source-backed)

Audited GitHub sources:
- [Pronunciada at pinned commit](https://github.com/moglearn/pronunciada/tree/4619a298e5e2de927120122585683d18eda1f7c4)
- [Scoring-data inventory](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/pronunciada/data/LICENSES_SHIPPED.json)
- [English G2P implementation](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/pronunciada/text/en.py)
- [Source licensing audit](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/docs/LICENSING.md)
- [Upstream language bundle trace](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/scripts/build_language_bundles.py)

Upstream already provides:
- two English pronunciation lexicon files: \`lex/en.tsv.gz\` (CMUdict-derived phone variants with stress) and \`lex/en_lts.tsv.gz\` (out-of-vocabulary letter-to-sound fallbacks);
- 22 runtime-traced English scoring resources including ZIPA token names, acoustic adapter, native statistics, sound/word/sentence/prosody calibrations and the exported English sequence ONNX head;
- upstream benchmark/export scripts, including \`scripts/mobile_parity.py\` and \`scripts/export_sherpa_onnx.py\`.

**Important:** these are the existing upstream fitted data files, not new calibration trained by Lexi. Two shared stress assets (\`prosody/stress_v3.json\` and \`prosody/stress_v3.onnx\`) have outstanding license-classification questions according to the upstream inventory. The actual ZIPA backbone weights, runtime interpreter/ONNX bridge, text/number normalization, and coaching-only resources are NOT included in this initial 24-file scoring-resource candidate. No iPhone compatibility has been demonstrated.

## How to create the real candidate locally (Mac)

Prerequisites: Git, Python 3.9+, free disk space and an ordinary network connection to clone public upstream source. Do **not** commit any weights or private lesson content.

\`\`\`bash
# From the PUBLIC experimental branch checkout:
bash experiments/pronunciation_en/bootstrap_local.sh
\`\`\`

This runs the local unit tests, clones the pinned upstream revision, stages the **actual** 24 resources by SHA-256 under \`~/.cache/lexilang/en-pronunciation-experiment/\`, generates an immutable \`candidate_inventory.json\`, then independently verifies every file and its provenance. It never publishes a GitHub Release or modifies the app.

For a manual inspection of source data:

\`\`\`bash
python3 -m unittest discover -s experiments/pronunciation_en -p "test_*.py" -v
python3 experiments/pronunciation_en/verify_en_candidate.py \
  --candidate "$HOME/.cache/lexilang/en-pronunciation-experiment/candidate-4619a298e5e2de927120122585683d18eda1f7c4"
\`\`\`

## Lexi-specific lesson coverage

With local LexiPilot JSON, check what fraction of C1/C2 and other CEFR-level prompt words have exact dictionary entries:

\`\`\`bash
python3 experiments/pronunciation_en/lesson_lexicon_audit.py \
  --candidate "$HOME/.cache/lexilang/en-pronunciation-experiment/candidate-4619a298e5e2de927120122585683d18eda1f7c4" \
  --lessons-json /path/to/local/lexipilot/Native/Resources/LexiCurriculum_v3.json \
  --out /tmp/lexi-en-lesson-coverage.json
\`\`\`

The output reports exact-match dictionary coverage and OOV words, not sound quality or model accuracy. For out-of-vocabulary words the approved upstream G2P fallback must be verified on actual high-level lessons. No course IDs or saved learner drafts are rewritten.

## Recalibration — what it REALLY requires

We should **reuse upstream calibrated English scoring first**. If QA exposes poor scores/false positives on real C1/C2 recordings, train a separate adjustment only from expertly annotated speech, never from Apple Speech confidence.

\`recalibrate_expert_scores.py\` accepts a research CSV with these columns:

| Column | Meaning |
| --- | --- |
| \`sample_id\` | Globally unique sound/word/sentence observation identifier |
| \`speaker_id\` | Stable anonymized speaker group for leakage prevention |
| \`split\` | Explicit \`train\` or untouched \`test\` |
| \`unit\` | Exactly one of \`phone\`, \`word\`, \`sentence\`, \`prosody\` per calibration |
| \`raw_score\` | Actual acoustic engine probability in [0, 1] |
| \`human_accept\` | Human expert acceptability label (0/1) under an explicitly documented rubric |
| \`source_engine\` | Single pinned acoustic model + scoring configuration |

At least 300 labelled training examples across 25 distinct speakers and 100 held-out examples across 10 different speakers are required by the initial script; both classes must appear in both partitions. These are **minimum fail-safe input checks**, not proof the data is sufficient for production. Proper research requires larger speaker-disjoint tests, C1/C2 adults with different native languages, independent expert adjudication, perturbation/noise robustness and calibration plots.

\`\`\`bash
python3 experiments/pronunciation_en/recalibrate_expert_scores.py \
  --expert-labelled-csv /path/to/real-expert-acoustic-scores.csv \
  --out /tmp/lexi-platt-calibration-research.json
\`\`\`

The script produces coefficients plus held-out Brier/ECE metrics, but it marks **every output** as non-publishable. If held-out calibration worsens, it explicitly marks it \`rejected_holdout_regression\`. It does not overwrite Pronunciada's original \`.npz\` models, does not create a fake percentile and never updates \`packs.json\`.

### Quality/merge gates

- [ ] Run the local tests and actually build/verify the upstream resource candidate.
- [ ] Run official Pronunciada **full** vs **subset** parity scripts on labeled English recordings; inspect errors and offline extraction results.
- [ ] Clarify licenses for shared stress weights and all redistribution attributions.
- [ ] Implement the complete acoustic scorer for Apple in a separate adapter (16 kHz audio, fbank, ONNX, aligned phonemes, calibrated scores); compare byte-level outputs or tolerant numeric parity before UI integration.
- [ ] Reuse approved LexiAudio/Apple/Kokoro and \`LexiAcousticScorer\` protocol without changing the core architecture.
- [ ] Measure startup, RAM, latency and battery on real iPhone/iPad, including background and offline.
- [ ] Evaluate human-scored SpeechOcean762 on speaker-separated train/test and advanced C1/C2 adult samples.
- [ ] Approve safety, calibration, licensing and owner manual QA.
- [ ] **Only after all gates** publish an immutable signed-by-SHA GitHub Release and add real entries to \`packs.json\`.

**Not enough evidence?** Abandon this branch. No merge or production behavior changes are needed.
