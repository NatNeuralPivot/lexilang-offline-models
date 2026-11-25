#!/usr/bin/env python3
"""Offline three-clip Pronunciada smoke run. No download, training, or app writes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import traceback

UPSTREAM_REV = '4619a298e5e2de927120122585683d18eda1f7c4'
MODEL_REV = 'dfe87c97662606fa6db90ad06f627d4363314744'
MODEL_SHA = 'd0e28b68164e8b1fbd6105100c01798828aa0855000ce9bbbd1a2cec233adf13'
TOKEN_SHA = 'f8e042a0c9130532b22d03ec7cae2f75a23fbec70c450c31a8efb51787b2b8fe'
CLIPS = [
    ('en-clean', 'It was good for me', '000240010', 'cc84cf34130ac5cdd0c5000fbfa7b3c5ef037029b27fe4fd145a632154b24384'),
    ('en-learner-1', 'It was a beautiful day for a float', '014200206', '48d9c362250c3d19971286a101af582e04d5fae4dcafa7d912396852247be4b4'),
    ('en-learner-2', 'Follow the link below to register', '021160249', 'cab7ece1ad082eb4539e3a7b63d3daa04bcc9f07a1dfbaf8149fe9674717d822'),
]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream', type=Path, required=True)
    ap.add_argument('--model-cache', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    up, cache, out = a.upstream.resolve(), a.model_cache.resolve(), a.out.resolve()
    if a.threads < 1 or a.threads > 8:
        ap.error('threads must be 1..8')
    if out.exists():
        ap.error('output must not already exist')
    revision = subprocess.check_output(['git', '-C', str(up), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != UPSTREAM_REV:
        ap.error('unexpected upstream commit')
    model, tokens = cache/'model.int8.onnx', cache/'tokens.txt'
    if digest(model) != MODEL_SHA or digest(tokens) != TOKEN_SHA:
        ap.error('model/token SHA mismatch')
    if tokens.read_bytes() != (up/'pronunciada/data/zipa_tokens.txt').read_bytes():
        ap.error('model/package tokens differ')
    for name, _, _, sha in CLIPS:
        if digest(up/f'site/samples/{name}.mp3') != sha:
            ap.error('audio SHA mismatch: '+name)
    # Exact downloaded graph is retained. Upstream creates its extra-output variant
    # next to this override; all mutable runtime artifacts stay in the isolated cache.
    for key in list(os.environ):
        if key.startswith('PRONUNCIADA_'):
            del os.environ[key]
    token_dir = cache/'runtime/models/zipa-small-crctc-500k'
    token_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tokens, token_dir/'tokens.txt')
    os.environ['PRONUNCIADA_CACHE'] = str(cache/'runtime')
    os.environ['PRONUNCIADA_BACKBONE'] = str(model)
    os.environ['OMP_NUM_THREADS'] = str(a.threads)
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    out.mkdir(parents=True)
    opened = set()

    def audit(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'urllib.Request'}:
            raise RuntimeError('network disabled for acoustic smoke run')
        if event == 'open' and isinstance(args[0], (str, bytes)):
            p = Path(os.fsdecode(args[0])).resolve()
            if p.is_relative_to(up/'pronunciada/data'):
                opened.add(p)

    sys.addaudithook(audit)
    started = time.perf_counter()
    sys.path.insert(0, str(up))
    from pronunciada import Scorer
    import numpy as np
    import onnxruntime as ort
    imports_s = time.perf_counter()-started
    report = {'status':'running', 'upstream_revision':revision,
              'model_revision':MODEL_REV, 'model_sha256':MODEL_SHA,
              'tokens_sha256':TOKEN_SHA, 'network_disabled':True,
              'threads':a.threads, 'precision':'int8', 'strictness':0.5,
              'posterior_cache_size':1, 'imports_seconds':imports_s,
              'versions':{p:importlib.metadata.version(p) for p in ['numpy','onnxruntime','kaldi-native-fbank','soundfile']},
              'clips':[], 'nonfinite_fields_serialized_as_null':[]}

    def clean(value, path=''):
        if isinstance(value, dict):
            return {str(k):clean(v,path+'/'+str(k)) for k,v in value.items()}
        if isinstance(value, (list,tuple)):
            return [clean(v,path+'/'+str(k)) for k,v in enumerate(value)]
        if isinstance(value, np.generic):
            return clean(value.item(),path)
        if isinstance(value, np.ndarray):
            return clean(value.tolist(),path)
        if isinstance(value, float) and not math.isfinite(value):
            report['nonfinite_fields_serialized_as_null'].append(path)
            return None
        return value

    def write(name, data):
        (out/name).write_text(json.dumps(clean(data,name),indent=2,ensure_ascii=False,allow_nan=False)+'\n')

    try:
        t = time.perf_counter()
        scorer = Scorer('en', precision='int8', threads=a.threads, strictness=0.5, cache_size=1)
        report['scorer_load_seconds'] = time.perf_counter()-t
        report['rss_after_load_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['providers'] = scorer.am.session.get_providers()
        report['encoder_outputs'] = list(scorer.am.embed_outputs)
        report['prosody_initialization_error'] = scorer.prosody_error
        assert scorer.am.embeddings and scorer.prosody is not None and scorer.prosody_error is None
        assert report['providers'] == ['CPUExecutionProvider']
        for name, text, corpus_id, sha in CLIPS:
            t = time.perf_counter()
            result = scorer.score(up/f'site/samples/{name}.mp3', text)
            elapsed = time.perf_counter()-t
            raw = result.to_dict()
            assert result.timing_ms['model'] > 0 and result.words
            for word in result.words:
                assert math.isfinite(word.prob) and 0 <= word.prob <= 1
                for phone in word.phones:
                    assert math.isfinite(phone.prob) and 0 <= phone.prob <= 1
                    assert phone.end >= phone.start >= 0
            write(name+'.json', raw)
            t = time.perf_counter()
            coaching = result.coaching(sensitivity='balanced')
            coaching_s = time.perf_counter()-t
            # coaching can enrich phone.heard; capture the final public fields too.
            write(name+'.json', result.to_dict())
            write(name+'-coaching.json', {'method':'upstream balanced coaching; predicted review flags, not verified errors','items':coaching})
            low_phones = [{'word':w.text,'ipa':p.ipa,'prob':p.prob,'heard':p.heard,'start':p.start,'end':p.end} for w in result.words for p in w.phones if p.prob < 0.5]
            low_words = [{'word':w.text,'prob':w.prob,'omitted':w.omitted,'present_prob':w.present_prob} for w in result.words if w.prob < 0.5 or w.omitted]
            stress = [{'word':w.text,'word_stress_prob':w.stress_prob,'syllables':[{'expected':s.stress_expected,'prob':s.stress_prob} for s in w.syllables]} for w in result.words if w.stress_prob is not None]
            row = {'id':name,'corpus_id':corpus_id,'audio_sha256':sha,'text':text,
                   'duration_seconds':result._pronunciada['dur'],
                   'score_wall_seconds':elapsed, 'timing_ms':result.timing_ms,
                   'coaching_seconds':coaching_s,
                   'rss_peak_so_far_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   'sentence_prob':result.prob,'scores':result.scores,
                   'words':len(result.words),'phones':sum(len(w.phones) for w in result.words),
                   'stress':stress,'phones_below_0_5':low_phones,'words_below_0_5_or_omitted':low_words,
                   'warnings':result.warnings,'audio_quality':result.audio,
                   'coaching_items':len(coaching)}
            report['clips'].append(row)
            print(json.dumps(clean(row)),flush=True)
        report['status'] = 'PASS_ACOUSTIC_EXECUTION_NOT_ACCURACY_VALIDATION'
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error'] = {'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        raise
    finally:
        report['run_seconds'] = time.perf_counter()-started
        report['max_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Hash only actually-opened runtime resources; no bootstrap or lesson audit.
        report['opened_runtime_resources'] = [{'path':str(p.relative_to(up)),'sha256':digest(p)} for p in sorted(opened) if p.is_file()]
        report['local_model_files'] = [{'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(cache.glob('*.onnx'))]
        write('run.json', report)


if __name__ == '__main__':
    main()
