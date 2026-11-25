#!/usr/bin/env bash
# One-shot local experiment: NO GH release, merge, Xcode edits or model weights.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
rev="4619a298e5e2de927120122585683d18eda1f7c4"
root="$HOME/.cache/lexilang/en-pronunciation-experiment"
upstream="$root/pronunciada-$rev"
candidate="$root/candidate-$rev"
mkdir -p "$root"
command -v python3 >/dev/null || { echo "Python 3 required" >&2; exit 2; }
command -v git >/dev/null || { echo "Git required" >&2; exit 2; }
if [[ ! -d "$upstream/.git" ]]; then
  echo "Fetching audited Pronunciada source revision (not ZIPA model weights)"
  git clone --filter=blob:none --no-checkout "https://github.com/moglearn/pronunciada.git" "$upstream"
  git -C "$upstream" checkout --detach "$rev"
else
  actual="$(git -C "$upstream" rev-parse HEAD)"
  [[ "$actual" == "$rev" ]] || { echo "Unexpected source revision: $actual" >&2; exit 2; }
fi
echo "Running synthetic local unit tests"
python3 -m unittest discover -s "$here" -p "test_*.py" -v
echo "Preparing immutable dictionary + calibration candidate"
if [[ -e "$candidate" ]]; then
  echo "Reusing existing immutable candidate (integrity will be verified)"
else
  python3 "$here/build_en_candidate.py" --pronunciada "$upstream" --out "$candidate"
fi
python3 "$here/verify_en_candidate.py" --candidate "$candidate"
echo
echo "Candidate at: $candidate"
echo "Missing: ZIPA weights, Apple runtime parity and human-score QA."
echo "DO NOT publish the candidate or switch packs.json to published."
