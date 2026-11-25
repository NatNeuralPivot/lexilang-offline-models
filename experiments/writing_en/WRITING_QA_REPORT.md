# Lexi Lang Writing GEC — QA report

25 November 2026, Europe/Moscow. **Recommendation: HOLD for the present research candidate/configuration.** Local ONNX execution works, but the Swift test entry point is broken and high-confidence edits can leave or introduce grammatical errors. This is not approval for an app integration, release or merge.

## PASS / FAIL / BLOCKED

| Check | Result | Actual evidence |
| --- | --- | --- |
| Read experiment README / STATUS | PASS | Public source `f2ffe31ee5c99bbb189729412ccebaafb8ec79c4`; private `50e23f859283bf51c0a13576eaeedb242b2a5707` |
| Existing Python tests | PASS | **11/11** passed, 0.248 s test time; synthetic staging/smoke fixtures only |
| Existing AssessmentKit Swift tests | FAIL before execution | `swift test` exited 1: tools-version 5.9 manifest uses `.iOS(.v18)`, introduced in PackageDescription 6.0; **0 Swift tests executed** |
| Complete four-file candidate | PASS | Four files, **264,324,420 bytes**, one pinned revision; existing staging and verifier scripts succeeded |
| SHA-256 / remote provenance | PASS, 4/4 | Independent measured SHA matches candidate inventory; model also matches remote LFS SHA; other three match pinned Git blob OIDs |
| Real offline inference | PASS, 20/20 | CPU ONNX session, real label_probs/error_probs, one pass per original case; network blocked during inference |
| Valid-English preservation | PASS on this fixture | **8/8** unchanged; zero valid-case changes in this small set |
| British spelling / names / Unicode | PASS on this fixture | UK-KEEP and NAME-KEEP byte-for-byte preserved |
| Input/draft preservation | PASS for smoke source; production behavior BLOCKED | Original 20 strings and source JSONL unchanged; previews written separately. No actual personal drafts accessed. Swift guard tests did not execute |
| Error correction quality | FAIL for unconditional use | 5 clean corrections, 5 unchanged fixture errors, 1 partial correction, 1 harmful correction by qualitative review |
| Latency / RAM | PASS measured | See per-case timings; peak process RSS **953.844 MiB** |
| Licensing / distribution approval | BLOCKED | Declared Apache-2.0, provenance/notice and training-data claims not independently cleared |

Only this experiment ran. No Qwen, application build/install, Xcode project changes, native adapter, iPhone work, full regression suite, retraining or model publication. Source/test scripts and the immutable model inventory were left unchanged; only reports and textual execution evidence are committed.

## Model, dependencies and exact file verification

Model: `deepquillapp/gector-grammar`, revision **`2232e0ef109dd12e11e2c74b565b7318e36379e4`**. [Pinned model card](https://huggingface.co/deepquillapp/gector-grammar/blob/2232e0ef109dd12e11e2c74b565b7318e36379e4/README.md) declares Apache-2.0. All four required assets were downloaded at this exact revision using the existing `build_gec_candidate.py`, then checked with `verify_gec_candidate.py` and an independent remote-provenance comparison.

| File | Actual bytes | Measured SHA-256 |
| --- | ---: | --- |
| model.onnx | 256279090 | `c8ce4fcc952f33d399cd668e200527f28b94136b61bec24d7852504d5c7c53e9` |
| tokenizer.json | 3558978 | `c9cbd55a5b79c5b8d99108dcd4978c16610a5f9cb5f7b27502efc2f893b5e720` |
| labels.json | 96276 | `753bb8bd179ba56c169d950bce77ad40893490bce47be9f74281263582d3ec43` |
| verb-form-vocab.txt | 4390076 | `5906804ec8a1acd8cbfc2918522bf429ce5edded8bbc46ffc2be861d280d3abf` |

For `model.onnx`, measured SHA-256 equals the HF LFS digest. The three ordinary Git assets have no LFS SHA: their measured SHA-256 is recorded and their bytes additionally reproduce the Git blob OID exposed at the pinned revision. This distinction is retained in [model-provenance.json](qa_writing/model-provenance.json); no upstream SHA was invented. The complete ONNX session loaded without another weight shard or network download.

Local-only candidate:

`~/.cache/lexilang/writing-gec-qa/candidate-2232e0ef109dd12e11e2c74b565b7318e36379e4/`

The isolated Writing virtualenv uses Python 3.14.7, NumPy 2.5.5, ONNX Runtime 1.32.0, tokenizers 0.23.3 and huggingface_hub 2.4.0. No global Python environment or pronunciation virtualenv was modified. The installed packages are dependencies, not a second model. Network was used only before inference for branch/source inspection, Python wheels and the four DeepQuill files. The staging command took **139.15 s** including download/verification; runtime inference was offline.

## Existing unit tests and scope of the Swift failure

Python: `python3 -m unittest discover -s experiments/writing_en -p 'test_*.py' -v`; [full test log](qa_writing/python-tests.txt). All 8 candidate tests and 3 evaluator tests passed. They do not execute the trained model.

Swift command:

```bash
swift test --package-path AssessmentKit \
  --scratch-path "$QA_ROOT/swift-build"
```

The actual first diagnostic is `Package.swift:6:23: error: 'v18' is unavailable`, with the compiler note that it was introduced in PackageDescription 6.0. The manifest declares Swift tools 5.9. This is a manifest/API-version mismatch, not a failing GEC assertion or proof that the guard works. The command took 1.07 s and never compiled/executed the tests. Full private compiler log is kept with the private report. The manifest and Swift sources were not patched because this task authorizes evidence-only commits; alignment of the declared tools/API versions is a future source fix, not performed here.

The repository's isolated QA deploy guardrails were read. This task did not run that app-deployment workflow or its broad preflight: the user authorized only the standalone package tests and isolated model QA, and prohibited full app QA.

## Actual inference protocol

CPUExecutionProvider, 4 intra-op threads / 1 inter-op thread, memory pattern disabled. Inputs: int64 `input_ids` and `attention_mask`; outputs: float `label_probs` `[1,80,5000]` and `error_probs` `[1,80]`. The tag head is labels.json minus trailing `<PAD>`, with `$KEEP` intact. All outputs were finite, probability bounds and softmax row sums were checked.

The pinned tokenizer.json supplies byte-level BPE, prefix-space processing and BOS/EOS. Original non-whitespace spans become `['$START', *words]`; first-subtoken word IDs select the tags. For these fixtures this matches the whitespace-word approach in the [training implementation's pinned decoder](https://github.com/gotutiyan/gector/blob/a4a342ed7c4733a34263443b605b7edffbef7099/src/gector/predict.py). Padding is 80, the model metadata maximum; no input was silently truncated. The maximum non-pad length observed was 20 tokens.

As documented by the DeepQuill card, a sentence is eligible when a word/anchor error probability reaches 0.6, and a proposed edit also needs label probability ≥0.6. Case transforms are disabled. Verb forms come from the downloaded vocabulary, and unsupported tags/forms are rejected and logged. **One pass per case**, no iterative improvement, threshold sweep or tuning on these examples. Exact parity with a separately runnable DeepQuill application implementation was not established; this is execution of the documented model interface with the inspected GECToR tag semantics.

Edits retain original code-point and UTF-16 ranges; preview application checks their source slices and rejects overlap. Unedited text and whitespace are retained. The runner does not call Swift, touch saved app answers or replace the source draft. The executed local harness is retained as a reviewable **text evidence snapshot**, [runner-source.txt](qa_writing/runner-source.txt), rather than adding/changing repository implementation code.

For each case, [inference-1](qa_writing/inference-1) contains its actual original/preview, first-subtoken mapping, top-five tags/probabilities, accepted/rejected proposals, UTF-16 offsets and raw tensor hashes. Full raw tensors were not committed; these are actual observations from `session.run`, not invented predictions.

## Actual corrections, missed errors and false positives

The existing evaluator reports **7 changed error inputs / 12**, **8 preserved valid inputs / 8**, and 5 unchanged errors. It checks change/preservation only: it cannot establish that a changed sentence is grammatical or independently attest to model execution. See [smoke-evaluation.json](qa_writing/smoke-evaluation.json). The separate traces establish execution, and the following review examines correctness.

Qualitative assessment below is by the assistant against the fixture hints and ordinary standard-English grammar, **not independent expert annotation or a CEFR benchmark**. [manual-review.json](qa_writing/manual-review.json) keeps review judgements separate from [actual predictions](qa_writing/inference-1/predictions.jsonl).

| Error case | Actual model change / preservation | Review |
| --- | --- | --- |
| A1-001 | She go to school every day. → She goes to school every day. | corrected cleanly |
| A1-002 | Unchanged: I has two books. | missed fixture error |
| A1-003 | He is a honest man. → He is an honest man. | corrected cleanly |
| A2-001 | Unchanged: There is many reasons to disagree. | missed fixture error |
| A2-002 | I have went to the library yesterday. → I have gone to the library yesterday. | partial error remaining |
| B1-001 | I look forward to meet you. → I look forward to meeting you. | corrected cleanly |
| B1-002 | Despite of the rain, we continued. → Despite the rain, we continued. | corrected cleanly |
| B2-001 | Unchanged: The results was inconclusive. | missed fixture error |
| B2-002 | Unchanged: If I would have known, I would have acted differently. | missed fixture error |
| C1-001 | The policy was implemented last year, despite it had faced considerable opposition. → The policy was implemented last year, despite it had facing considerable opposition. | harmful wrong correction |
| C1-002 | The evidence suggest that the intervention had a limited impact. → The evidence suggests that the intervention had a limited impact. | corrected cleanly |
| C2-001 | Unchanged: Neither the methodology nor the findings warrants such a sweeping conclusion. | missed fixture error |

Five cases have clean local corrections: A1-001, A1-003, B1-001, B1-002 and C1-002. Five error fixtures remain unchanged: A1-002, A2-001, B2-001, B2-002 and C2-001. These are misses under the supplied fixture expectations, not a universal claim about every dialect or agreement policy.

Two changed cases must **not** be counted as successful full corrections:

- **A2-002:** `went` → `gone`, tag `$TRANSFORM_VERB_VBD_VBN`, label probability **0.652242**. `I have gone ... yesterday` still has the fixture's tense/time conflict. A proposed `have` deletion scored **0.521966** and was rejected. This is partial repair, not a correct final sentence.
- **C1-001:** `faced` → `facing`, tag `$TRANSFORM_VERB_VBN_VBG`, label probability **0.889572**. The preview contains **`despite it had facing`**, which worsens syntax and leaves the targeted despite/clause problem unresolved. A separate `had` deletion scored **0.597895**, just below threshold, and was rejected. High individual tag confidence is not sentence-level grammatical validity; independently thresholded edits can form a bad combination. No threshold was lowered to make this example look better.

There were **0 changed valid inputs among the 8 keep fixtures**, but the harmful C1 edit is a spurious correction within an already erroneous sentence. The valid-input count must not be advertised as a general zero-false-positive guarantee. The two failures above are additional quality failures beyond the evaluator's five unchanged cases.

## Preservation checks

All eight keep cases remained byte-for-byte identical: A1-KEEP, B2-KEEP, C1-KEEP, C2-KEEP, UK-KEEP, NAME-KEEP, STYLE-KEEP and FRAGMENT-KEEP. This includes valid inversion, idiom, conversational fragment and formal prose; no style rewrite was applied.

- **UK-KEEP:** `organisation`, `analyse`, `colour` preserved exactly; no US spelling substitution.
- **NAME-KEEP:** `O’Connor` and `John’s` retained their Unicode curly apostrophes and original punctuation.
- **Source text:** original strings are separately recorded for all 20 cases; the runner checked their UTF-8 hashes and checked that the entire source JSONL was unchanged. Before/after source SHA: `0f6067d416eb74f67cc3e6d115fe99e04eeae21860fc1ac3e04d29d78be2396d`.
- **Draft safety limit:** these checks concern fixture strings and preview offsets. No actual personal drafts, SQLite library or app preferences were accessed. Production saved-draft behavior was not exercised, and the Swift guard's emoji/stale-offset/overlap tests remain unexecuted because of the manifest failure. Do not infer native/app integration safety from the Python preview checks.

## Measured performance and peak RAM

Same local Mac: Apple M4 Pro, 24 GiB RAM, macOS 26.5.2 arm64. All cases are short single-sentence examples, padded to 80 tokens. Timing uses `perf_counter`; peak RSS uses macOS `getrusage(RUSAGE_SELF).ru_maxrss` in bytes, including native ORT allocations.

| Measurement | Observed |
| --- | ---: |
| Tokenizer + verb-table load | 0.126369 s |
| ONNX session load/optimization | 0.305491 s |
| First model forward pass | 12.925 ms |
| First end-to-end preview call | 17.835 ms |
| Remaining 19 model calls | 12.043–40.038 ms |
| Remaining 19 preview calls | 14.266–43.208 ms |
| Instrumented runtime span | 5.610943 s |
| Peak process RSS | **1,000,177,664 bytes / 953.84375 MiB** |

The runtime span starts before NumPy/ORT/tokenizer imports and includes initialization, all 20 calls and trace writes, after candidate/input preflight checks. Preview-call timings exclude shared session loading. RSS is a high-water mark, not live memory. No p95 claim, battery test, long essay, concurrency or Apple-device budget assessment was made.

| Case | Model ms | Preview wall ms | Accepted edits |
| --- | ---: | ---: | ---: |
| A1-001 | 12.925 | 17.835 | 1 |
| A1-002 | 12.043 | 14.266 | 0 |
| A1-003 | 12.323 | 14.740 | 1 |
| A2-001 | 12.665 | 15.211 | 0 |
| A2-002 | 13.571 | 16.328 | 1 |
| B1-001 | 13.434 | 15.986 | 1 |
| B1-002 | 13.424 | 15.953 | 1 |
| B2-001 | 17.619 | 20.078 | 0 |
| B2-002 | 17.857 | 22.663 | 0 |
| C1-001 | 16.682 | 21.230 | 1 |
| C1-002 | 16.553 | 20.367 | 1 |
| C2-001 | 14.099 | 18.070 | 0 |
| A1-KEEP | 17.608 | 20.415 | 0 |
| B2-KEEP | 15.099 | 19.723 | 0 |
| C1-KEEP | 15.537 | 20.010 | 0 |
| C2-KEEP | 14.189 | 19.486 | 0 |
| UK-KEEP | 14.919 | 17.944 | 0 |
| NAME-KEEP | 14.128 | 17.379 | 0 |
| STYLE-KEEP | 13.988 | 18.168 | 0 |
| FRAGMENT-KEEP | 40.038 | 43.208 | 0 |

Full metrics: [run.json](qa_writing/inference-1/run.json), [performance-summary.json](qa_writing/performance-summary.json). Stored fp16 model-file size is not the process RAM footprint.

## Remaining gates and recommendation

**HOLD.** The successful download and real inference are useful research evidence, but this configuration is unsuitable for unconditional correction. Before considering another local quality experiment, the existing Swift manifest needs a separate authorized source fix, and the partial/harmful edits require review of tag interactions and acceptance policy. Do not tune thresholds against these same 20 examples and claim a validated improvement. An independent expert-labelled learner set and dialect-sensitive evaluation are still needed; no essay grade or numeric CEFR score was produced.

The model card declares Apache-2.0 and lists RoBERTa MIT, verb vocabulary Apache-2.0, C4/C4_200M attribution obligations and Gutenberg source provenance. These are upstream declarations, not independent clearance of training, territorial rights or commercial redistribution. No additional checkpoint or training corpus was downloaded. The immutable inventory deliberately retains false release gates; STATUS.json still records the pre-QA state and was not rewritten under this evidence-only task. This dated report describes actual execution.

No changes to main, app architecture, SwiftUI, ReaderKit, Audio, Kokoro, curriculum, model registry, saved drafts or existing source/tests. No new remote branches, merge, Releases, uploaded weights, Qwen, full Lexi regression or iPhone port. Isolated local worktrees check out only the two existing `experiment/offline-writing-gec` branches. Reports/evidence only are committed. Work stops after report publication.

## Evidence and reproduction

- [EVIDENCE_SHA256.tsv](qa_writing/EVIDENCE_SHA256.tsv): size and SHA inventory of text evidence; no model assets included.
- [model-staging.txt](qa_writing/model-staging.txt), [model-verification.txt](qa_writing/model-verification.txt), [model-provenance.json](qa_writing/model-provenance.json).
- [python-tests.txt](qa_writing/python-tests.txt), [runtime-versions.json](qa_writing/runtime-versions.json), [inference stdout](qa_writing/inference-1.txt), [manual-review.json](qa_writing/manual-review.json).

The executed runner snapshot takes `--candidate`, `--cases` and a fresh `--out`, rejects overwritten outputs, verifies the pinned candidate and disables inference-time networking. It was run with the existing `writing_smoke_cases.jsonl` and the local candidate above. The evaluator was then invoked exactly once with the produced predictions JSONL. There was one successful 20-case inference run, no model/threshold iterations and no script-fix reruns. The preserved snapshot is evidence, not new application code.
