# Lexi Lang — offline English Writing / GEC experiment

**Research only. No model release, no merge into main, no UI integration.**

## Which correction engine?

The current private `AssessmentKit` has a deterministic fallback and a `LexiWritingModel` interface. No trained model has been shipped. This branch tests [DeepQuill GECToR ONNX](https://huggingface.co/deepquillapp/gector-grammar) for precise English grammar edits, instead of repurposing the pronunciation scorer. The upstream model card declares Apache-2.0 and describes four required files: `model.onnx`, `tokenizer.json`, `labels.json`, `verb-form-vocab.txt`. Upstream repository size is about 264 MB; this is not a measured iPhone runtime footprint.

The GEC model produces edit tags like `$KEEP`, `$DELETE`, `$REPLACE_*`, `$APPEND_*`, `$TRANSFORM_VERB_*`. It does not automatically produce accurate Russian/Spanish explanations, assess content, or assign a reliable C1/C2 essay grade. For higher-level coherence/style, [Qwen3.5-0.8B GGUF](https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF) can be researched separately; **do not download that second model as part of this first experiment**.

The four model resources do not require archive extraction. After approval they can be published as separate assets in ONE versioned public GitHub Release and installed together with the existing `LexiModelPackManager` (HTTPS + SHA-256 + complete atomic activation). The private app, lesson source IDs and saved Writing drafts are not modified.

## Download, verify and stage locally on a Mac

Requires Python 3.9+ and internet access; do not commit the model binary or any private lesson content.

~~~bash
git clone https://github.com/NatNeuralPivot/lexilang-offline-models.git
cd lexilang-offline-models
git switch experiment/offline-writing-gec

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade huggingface_hub
python3 -m unittest discover -s experiments/writing_en -p 'test_*.py' -v

python3 experiments/writing_en/build_gec_candidate.py \
  --out "$HOME/.cache/lexilang/writing-gec-test/v1"
python3 experiments/writing_en/verify_gec_candidate.py \
  --candidate "$HOME/.cache/lexilang/writing-gec-test/v1"
~~~

The downloader reads Hugging Face metadata, pins every file to the same exact 40-character upstream commit, records byte size and SHA-256, and stages an immutable `candidate_inventory.json`. On the next run supply `--revision EXACT_COMMIT_SHA`. All QA gates are deliberately false. This is NOT installation into the Lexi app.

## Real inference, not just file checks

The upstream card specifies the model interface: byte-level RoBERTa BPE, pre-tokenized original words and a `$START` anchor; ONNX inputs `input_ids`, `attention_mask`; outputs `label_probs`, `error_probs`. Decode the tag at the first sub-token of each word, with upstream threshold 0.6 for both edit and error probabilities. Apply transforms using its verb-form-vocab and labels; reject unsupported tags.

Codex must obtain **real ONNX outputs**, not make up example results. Compare suggestions on the 20 [A1–C2 smoke cases](writing_smoke_cases.jsonl), including valid inverted clauses, UK spelling, names, Unicode and stylistic alternatives. Save output JSONL of `{"id":"...","original":"...","revised_text":"..."}`. Then:

~~~bash
python3 experiments/writing_en/evaluate_writing_smoke.py \
  --actual-predictions /path/to/actual-onnx-predictions.jsonl \
  --report /tmp/lexi-writing-gec-smoke-report.json
~~~

This reports only changed/preserved cases. A changed grammatical error can still be corrected incorrectly. Human review and an independent expert-labeled learner dataset are required.

In the private [experimental writing branch](https://github.com/NatNeuralPivot/lexipilot/tree/experiment/offline-writing-gec), `GECProposalGuard.swift` is a pure safety boundary for original-text UTF-16 offsets, probability thresholding, overlapping edits, Unicode and no whole-essay rewrite. It does not run ONNX inference or connect to SwiftUI.

## Release blockers

- [ ] Mac Python unit tests executed
- [ ] Full 4-file source revision downloaded, SHA-256 checked
- [ ] Licenses, copyright notices and commercial use independently verified
- [ ] Functional Mac ONNX inference + real predictions
- [ ] Apple iPhone/iPad runtime adapter and offline memory/latency benchmark
- [ ] Human-reviewed CEFR A1–C2 learner examples; accepted variants preserved
- [ ] RU/ES/EN localized grammar explanations, select/accept/reject each edit
- [ ] Explicit user download consent; entitlement and cancellation tested
- [ ] Only then publish a GitHub Release and update `packs.json`

**If weak or incompatible, do not merge.** Keep the accepted Lexi Lang UI and deterministic fallback untouched.
