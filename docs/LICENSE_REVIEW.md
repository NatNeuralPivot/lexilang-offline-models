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
