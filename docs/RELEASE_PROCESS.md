# Publishing a verified Lexi offline model pack

This is a **manual, opt-in workflow**. Never publish unreviewed weights and never merge a model update automatically.

## 1. Build an approved device-ready model pack

Use one logical pack for all language resources supported by the release, even if it has multiple model shards; the learner installs the complete pack in one action. Keep each GitHub Release asset below 2 GB.

Produce actual optimized artifacts and benchmark them on target Apple hardware. Store model binaries in a local directory **outside** the Git checkout. Neither the original private app nor this public repository's Git history should contain those binaries. Do not add model ZIPs or ONNX weights directly to Git.

Prepare a **local** specification file, such as \`/tmp/lexi-pack-spec.json\`, after the asset-by-asset legal review. The fields are:

\`\`\`json
{
  "id": "APPROVED_PACK_ID",
  "version": "VERSION",
  "releaseTag": "IMMUTABLE_RELEASE_TAG",
  "license": "Full license summary / see LICENSES.txt",
  "notice": "Actual authors, versions and major attribution obligations",
  "assets": [
    {
      "name": "ACTUAL_FILENAME.onnx",
      "sourceURL": "https://PUBLIC_ORIGINAL_UPSTREAM_SOURCE",
      "license": "ACTUAL_UPSTREAM_LICENSE_ID",
      "redistributionApproved": true,
      "reviewed": true,
      "reviewedBy": "REVIEWER",
      "reviewEvidence": "https://PUBLIC_LICENSE_OR_APPROVAL_EVIDENCE"
    },
    {
      "name": "LICENSES.txt",
      "sourceURL": "https://PUBLIC_ORIGINAL_UPSTREAM_SOURCE",
      "license": "License and attribution notices",
      "redistributionApproved": true,
      "reviewed": true,
      "reviewedBy": "REVIEWER",
      "reviewEvidence": "https://PUBLIC_LICENSE_OR_APPROVAL_EVIDENCE"
    }
  ]
}
\`\`\`

These are **field placeholders only**, not real asset references, files, review evidence or approval. Never set \`redistributionApproved\` or \`reviewed\` to true until the review actually happened. Every file must exist with the **same basename** in the assets directory and be nonempty, including \`LICENSES.txt\`. Review and include all tokenizers, dictionaries and calibration files.

## 2. Stage and verify locally

\`\`\`bash
python3 tools/test_pack_tools.py
python3 tools/prepare_pack.py \
  --spec /tmp/lexi-pack-spec.json \
  --assets-dir /path/to/reviewed/model-files \
  --output-root ./dist
python3 tools/verify_pack.py \
  --manifest dist/APPROVED_PACK_ID/VERSION/pack.json \
  --assets-dir dist/APPROVED_PACK_ID/VERSION
\`\`\`

The staging tool creates \`pack.json\`, \`SHA256SUMS\`, \`NOTICE.txt\`, \`PROVENANCE.json\` and copies *real* reviewed assets. It does **not** publish. Rebuilding a published version is forbidden; bump the version and release tag. If the staging folder already exists, the script refuses to overwrite it.

## 3. Native Apple QA

Before the public release, exercise the actual inference adapter on macOS, iPhone and iPad:

- Model loads and completes inference with airplane mode enabled; model size, download behavior and memory use are acceptable.
- Pronunciation feedback reports phoneme errors and uncertainty only from genuine acoustic inference; with no model installed, show unassessed rather than an invented percent.
- Writing feedback uses source-accurate ranges and distinguishes recommendations from guaranteed grammar correctness; never falsely grade open C1/C2 writing.
- Background/offline installation, interrupted transfer, insufficient disk space, retry and cancellation work. Existing downloaded version stays available until the new pack is completely verified.
- Apple's and Kokoro's existing TTS paths, Audio Recorder and EN/RU/ES language settings remain unchanged.

## 4. Create and inspect a GitHub Release draft

Run from a workstation with an authenticated GitHub CLI, after reviewing all bytes and notices. **This is a command for a future reviewed pack; do not execute with placeholders.**

\`\`\`bash
gh auth login
gh release create IMMUTABLE_RELEASE_TAG \
  dist/APPROVED_PACK_ID/VERSION/* \
  --repo NatNeuralPivot/lexilang-offline-models \
  --title "Lexi Lang offline models VERSION" \
  --notes "Reviewed offline model assets. See LICENSES.txt and PROVENANCE.json." \
  --draft \
  --latest=false
\`\`\`

Verify every uploaded asset's name and size and independently re-download/check SHA-256. Publish the draft only after QA approval. No private GitHub tokens or signed expiring URLs may be embedded into the iPhone app.

## 5. Promote the registry, only after the release is PUBLIC

Edit the public \`packs.json\` from \`"status": "unpublished", "packs": []\` to \`"status": "published"\` and add the **exact** approved \`pack.json\` object to \`packs\`. Confirm every \`downloadURL\` now succeeds anonymously. The client consumes this registry and presents a single “Download offline assessment pack” action; it must not attempt installation when the list is empty.

Current native contract: [private branch](https://github.com/NatNeuralPivot/lexipilot/tree/feature/offline-assessment-engine/AssessmentKit). The macOS/iOS app integration and runtime models are separate milestones.

## 6. Rollback

Never mutate existing GitHub Release assets or silently repoint SHA-256. For a broken release, remove its entry from the public registry, retain any previously verified installed pack, and publish a corrected **new tag/version** after QA.

**Repository baseline:** no downloadable weights, releases or approved packs have been published yet.
