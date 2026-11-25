# Lexi Lang — Offline Model Distribution

> **Distribution repository — not an installable model release yet.**
> The registry currently contains zero approved model packs. No model weights or phone-ready inference engines have been published.

This **public** repository is the download source for optional offline assessment model packs used by Lexi Lang on macOS, iPhone and iPad. The application's source code and learner data remain in the separate **private** repository [NatNeuralPivot/lexipilot](https://github.com/NatNeuralPivot/lexipilot).

## What will be distributed

- **Writing assessment** — a context-aware English grammar, spelling and style model; not the existing deterministic fallback.
- **Pronunciation assessment** — a real acoustic phoneme/prosody scorer for recorded speech. Transcript matching and Apple Speech confidence must never be represented as acoustic accuracy.
- **Pack resources** — dictionaries, tokenizer, calibration data and appropriate third-party notices required by either model.

A single user-initiated installation installs a complete **versioned pack** with every required component; large packs may contain multiple GitHub Release assets. The app must verify every asset's byte size and SHA-256 before activating it. Once installed, the pack is reused offline and is not tied to the user's selected explanation language (EN/RU/ES).

## Repository layout

| Path | Purpose |
| --- | --- |
| [packs.json](packs.json) | Public registry of *actually published* packs (initially empty) |
| [schemas/pack-manifest.schema.json](schemas/pack-manifest.schema.json) | Validated manifest schema matching the native app |
| [tools/prepare_pack.py](tools/prepare_pack.py) | Local, standard-library-only release preparation, licensing gates and SHA-256 calculation |
| [tools/verify_pack.py](tools/verify_pack.py) | Independent local verification against a staged manifest |
| [tools/test_pack_tools.py](tools/test_pack_tools.py) | Unit tests; run locally, no heavy CI |
| [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md) | Exact publishing and rollback protocol |
| [docs/LICENSE_REVIEW.md](docs/LICENSE_REVIEW.md) | Per-component license and provenance checklist |

## Distribution contract

1. Only link to **public GitHub Releases assets**: `https://github.com/NatNeuralPivot/lexilang-offline-models/releases/download/<tag>/<filename>`.
2. A pack contains `id`, `version`, `license`, `notice`, and a nonempty `assets` list. Each asset contains `name`, `downloadURL`, `bytes`, `sha256`.
3. Each asset must be an immutable GitHub Release file (no raw GitHub LFS pointers, Hugging Face URLs, private-release links, or files within the application bundle).
4. Publish licenses, notices and original source provenance with the assets. A repository being public does **not** grant redistribution rights over third-party weights.
5. Do not mark a pack ready until model loading and measured on-device accuracy have been QA-tested on target Apple devices. GitHub upload alone does not complete that work.

### Current status

| Component | Status |
| --- | --- |
| Public GitHub repository | Created |
| Release manifest schema, tools | In development |
| Approved/repackaged writing model | **Not available** |
| Approved/repackaged acoustic model | **Not available** |
| iOS / macOS benchmarking | **Not completed** |
| Downloadable model release | **Not published** |

Do not treat an empty registry as a broken download: the app should show **“Offline assessment pack coming soon”** rather than invent a download URL or score.

See [release process](docs/RELEASE_PROCESS.md) before making the first release.
