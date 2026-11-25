#!/usr/bin/env python3
"""Score exactly the seven approved frozen WAVs once; no network or downloads."""
import argparse
from dataclasses import asdict
import importlib.metadata
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

from run_acoustic_smoke import digest, UPSTREAM_REV, MODEL_REV, MODEL_SHA, TOKEN_SHA

IDS = ['001200015', '001570024', '003060002', '004570010', '004610037', '005630017', '005670043']
DATA_REV = '613968e3b0b789fc33936fb5eba1973176ba7d11'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream', type=Path, required=True)
    ap.add_argument('--model-cache', type=Path, required=True)
    ap.add_argument('--clips-manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    up, cache, manifest_path, out = [p.resolve() for p in [a.upstream, a.model_cache, a.clips_manifest, a.out]]
    if out.exists():
        ap.error('refusing to overwrite output')
    assert subprocess.check_output(['git', '-C', str(up), 'rev-parse', 'HEAD'], text=True).strip() == UPSTREAM_REV
    manifest = json.loads(manifest_path.read_text())
    assert manifest['revision'] == DATA_REV and manifest['labels_verified_before_inference'] is True
    assert [c['id'] for c in manifest['clips']] == IDS
    assert len({c['speaker'] for c in manifest['clips']}) == 7
    assert len({c['sha256'] for c in manifest['clips']}) == 7
    assert digest(cache/'model.int8.onnx') == MODEL_SHA and digest(cache/'tokens.txt') == TOKEN_SHA
    token_copy = cache/'runtime/models/zipa-small-crctc-500k/tokens.txt'
    assert digest(token_copy) == TOKEN_SHA
    before = {p.name:digest(p) for p in cache.glob('*.onnx')}
    assert len(before) == 2, 'reuse original and already prepared extra-output graph'
    paths = []
    for c in manifest['clips']:
        path = (manifest_path.parent/c['file']).resolve()
        assert path.is_relative_to(manifest_path.parent) and c['split'] == 'test' and c['source_revision'] == DATA_REV
        assert path.stat().st_size == c['bytes'] and digest(path) == c['sha256']
        assert c['transcript'] == c['human_aggregate']['text'] == c['human_five_raters']['text']
        paths.append(path)
    for k in list(os.environ):
        if k.startswith('PRONUNCIADA_'):
            del os.environ[k]
    os.environ.update(PRONUNCIADA_CACHE=str(cache/'runtime'), PRONUNCIADA_BACKBONE=str(cache/'model.int8.onnx'), OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1')
    out.mkdir(parents=True)

    def offline(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'urllib.Request'}:
            raise RuntimeError('network disabled during expansion inference')
    sys.addaudithook(offline)
    started = time.perf_counter()
    sys.path.insert(0, str(up))
    from pronunciada import Scorer
    import numpy as np
    import soundfile as sf
    report = {'status':'running', 'upstream_revision':UPSTREAM_REV, 'model_revision':MODEL_REV,
              'model_sha256':MODEL_SHA, 'input_manifest_sha256':digest(manifest_path),
              'network_disabled':True, 'precision':'int8', 'threads':4, 'strictness':0.5, 'cache_size':1,
              'versions':{p:importlib.metadata.version(p) for p in ['numpy','onnxruntime','kaldi-native-fbank','soundfile']},
              'clips':[], 'flags':[], 'nonfinite_fields':[]}

    def clean(value, path=''):
        if isinstance(value, dict): return {str(k):clean(v,path+'/'+str(k)) for k,v in value.items()}
        if isinstance(value, (list,tuple)): return [clean(v,path+'/'+str(i)) for i,v in enumerate(value)]
        if isinstance(value, np.ndarray): return clean(value.tolist(),path)
        if isinstance(value, np.generic): return clean(value.item(),path)
        if isinstance(value, float) and not math.isfinite(value):
            report['nonfinite_fields'].append(path)
            return None
        return value

    def write(name, value):
        (out/name).write_text(json.dumps(clean(value,name),indent=2,ensure_ascii=False,allow_nan=False)+'\n')

    signatures = set()
    pcm_signatures = set()
    try:
        t = time.perf_counter()
        scorer = Scorer('en', precision='int8', threads=4, strictness=0.5, cache_size=1)
        report['load_seconds'] = time.perf_counter()-t
        report['peak_rss_after_load_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['providers'] = scorer.am.session.get_providers()
        assert report['providers'] == ['CPUExecutionProvider']
        assert scorer.am.embeddings and scorer.prosody is not None and scorer.prosody_error is None
        for c, path in zip(manifest['clips'], paths):
            import hashlib
            wav, sr = sf.read(path, dtype='float32', always_2d=True)
            pcm = hashlib.sha256(wav.tobytes()).hexdigest()
            assert pcm == c['decoded']['float32_samples_sha256'] and pcm not in pcm_signatures
            pcm_signatures.add(pcm)
            assert np.isfinite(wav).all() and sr == c['decoded']['sample_rate']
            t = time.perf_counter()
            result = scorer.score(path, c['transcript'])
            score_s = time.perf_counter()-t
            t = time.perf_counter()
            coaching = result.coaching(sensitivity='balanced')
            coach_s = time.perf_counter()-t
            raw = result.to_dict()
            sig_data = {'sentence':raw['prob'], 'scores':raw['scores'], 'words':[[w['prob'],[p['prob'] for p in w['phones']]] for w in raw['words']]}
            signature = hashlib.sha256(json.dumps(sig_data,sort_keys=True).encode()).hexdigest()
            flags = []
            if signature in signatures: flags.append('identical_numeric_result')
            signatures.add(signature)
            required = {'g2p','load','fbank','model','align','calibrate','prosody','total'}
            if required-set(result.timing_ms) or result.timing_ms.get('model',0)<=0: flags.append('missing_or_cached_model_timing')
            if not result.audio or result.audio.get('issues') or result.audio.get('retry_recommended'): flags.append('audio_quality_gate')
            if result.warnings: flags.append('scorer_warnings')
            for w in result.words:
                assert math.isfinite(w.prob) and 0<=w.prob<=1
                for p in w.phones:
                    assert math.isfinite(p.prob) and 0<=p.prob<=1 and 0<=p.start<=p.end
            metadata = {'id':c['id'],'audio_sha256':c['sha256'],'input_manifest_sha256':report['input_manifest_sha256']}
            write(c['id']+'-result.json', {'input':metadata,'result':raw})
            write(c['id']+'-coaching.json', {'input':metadata,'method':'upstream balanced, unchanged thresholds','items':coaching})
            write(c['id']+'-reference.json', asdict(result._pronunciada['ref']))
            row = {**metadata, 'duration_seconds':len(wav)/sr, 'score_wall_seconds':score_s,
                   'coaching_seconds':coach_s, 'timing_ms':result.timing_ms,
                   'peak_rss_so_far_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   'counts':{'phones':sum(len(w.phones) for w in result.words),'words':len(result.words),
                             'syllables':sum(len(w.syllables) for w in result.words),
                             'word_stress_nonnull':sum(w.stress_prob is not None for w in result.words),
                             'syllable_stress_nonnull':sum(s.stress_prob is not None for w in result.words for s in w.syllables),
                             'sentence_score_fields':len(result.scores),'coaching_items':len(coaching)},
                   'sentence_prob':result.prob,'scores':result.scores,'flags':flags,
                   'warnings':result.warnings,'audio_quality':result.audio,'numeric_signature':signature}
            report['clips'].append(row)
            report['flags'].extend({'id':c['id'],'flag':f} for f in flags)
            print(json.dumps(row),flush=True)
        after = {p.name:digest(p) for p in cache.glob('*.onnx')}
        assert before == after, 'model cache changed'
        report['model_files_unchanged'] = True
        report['status'] = 'PASS' if not report['flags'] and not report['nonfinite_fields'] else 'REVIEW_REQUIRED'
    except Exception as e:
        report['status'] = 'FAIL'
        report['error'] = {'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
        raise
    finally:
        report['run_seconds'] = time.perf_counter()-started
        report['max_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        write('run.json',report)


if __name__ == '__main__':
    main()
