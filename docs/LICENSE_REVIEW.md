# Licenses and model provenance — release gate

**Do not mirror weights from any model hub without checking redistribution rights.** A public GitHub repository is not a substitute for an upstream license. Our commercial/offline Lexi Lang app must be able to distribute each artifact lawfully.

Every pack must have an explicit asset inventory. For **each** weight shard, tokenizer, phoneme dictionary, alignment resource, pronunciation lexicon, calibration table and other dependency, record:

- Original author, source URL, exact upstream commit/revision and SHA-256.
- Its own governing license(s), complete license text and notices. Different parts of one model often have different rights.
- Whether commercial redistribution, modification, conversion to ONNX/Core ML, and offline delivery inside a paid application are permitted.
- If attribution, share-alike, source disclosure, patent notices, or model-card conditions apply, document and fulfill them.
- Reviewer, review date and a direct public URL to evidence; no inferred or undocumented approvals.
- Size, model architecture/input/output contract and hardware/runtime compatibility for macOS and iOS.

Before preparing a release, create a plain-text `LICENSES.txt` containing **the exact notices/full license texts** required for all components. Place it alongside the approved model assets, and include it as a reviewed asset in the specification. The preparation tool also creates `NOTICE.txt` and `PROVENANCE.json` and includes them in the downloadable pack.

## Current license decisions

| Candidate | Gate | Why |
| --- | --- | --- |
| Pronunciada / ZIPA | **Hold** | Confirm code, all weight/lexicon licenses and Apple ONNX/Core ML runtime support; no verified iOS release is available in this repository |
| OpenPronounce | **Do not redistribute yet** | AGPL and/or commercial-licensing obligations need explicit legal review before closed-source integration |
| Wav2Vec2 + GOP | **Hold** | Each model, tokenizer, dictionary and dataset needs separate license and benchmark review |
| Microsoft Azure / Speechace | **Not offline pack candidates** | Cloud APIs, not redistributable device weights |
| Writing / grammar correction model | **Hold** | No reviewed weights, memory profile, quantization or C1/C2 accuracy benchmark selected yet |

No model weights are committed in `main`; do not create placeholder binary assets or fictional SHA-256 hashes. Sample tests use synthetic bytes only and are explicitly **not** releases.

## Approval checklist

- [ ] Every single artifact has legal redistribution approval, recorded evidence and full attribution
- [ ] All model variants and dependency files needed for **one complete offline install** are included
- [ ] Model compatibility verified on a physical iPhone and macOS device (load, inference, memory, size)
- [ ] Spoken accuracy evaluated using genuinely labeled examples, not ASR confidence
- [ ] Writing feedback benchmarked for precision, false positive rate and CEFR B2–C2
- [ ] Apple device tests confirm no recording or draft is sent to a server
- [ ] GitHub Release assets published and verified; only then registry switched from unpublished

## Pronunciada first-pass source audit (25 November 2026)

Checked directly against [Pronunciada README](https://github.com/moglearn/pronunciada),
[its licensing audit](https://github.com/moglearn/pronunciada/blob/main/docs/LICENSING.md)
and [NOTICE](https://github.com/moglearn/pronunciada/blob/main/NOTICE).

- The upstream code is Apache-2.0. Its runtime acoustic ZIPA model `anyspeech/zipa-small-crctc-500k` is separately licensed **CC BY 4.0** and is downloaded from its original host on first use. The upstream author reports `model.int8.onnx` at roughly **67 MB** and `model.onnx` at roughly **248 MB**, *before* our pack overhead or iOS conversion.
- The upstream README explicitly says **no iOS, Android or WebAssembly builds**. An existing ONNX file does not by itself prove the full Python-based scoring, lexicon, alignment and calibration pipeline can run on an iPhone.
- Lexicons have different rights: EN CMUdict (BSD-2-Clause-style); DE/FR and ES (MIT/derived rules); IT/PT/RU sources and some output adapters (CC BY-SA). A package containing **all** upstream language support requires extra individual licensing and compatibility checks.
- The upstream license audit says that L2-ARCTIC/other non-commercial training dependencies were removed from the shipped word model on 17 November 2026; this is an **upstream claim**, not yet independently reproduced for Lexi. It also lists open attribution/share-alike questions for some downstream trained models.
- The upstream releases currently do **not** contain downloadable binary assets. We are **not** copying its source checkout and pretending it is a device-ready model package.

**Decision:** hold actual binary redistribution while verifying exact upstream artifact revisions/licenses, the Apple runtime implementation and independent pronunciation assessment. For Lexi's immediate English learning needs, ship EN acoustic resources only after proof of compatibility; if a later multi-language pack is approved, install its full language set as one versioned logical pack and hide UI languages not supported by Lexi.

This first-pass technical check does not constitute legal approval for any artifact.
