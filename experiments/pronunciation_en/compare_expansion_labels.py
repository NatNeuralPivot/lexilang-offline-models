"""Compare frozen human units to saved outputs only; never performs inference."""
from pathlib import Path
from collections import Counter
import argparse
import json
import re
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--upstream',type=Path,required=True)
parser.add_argument('--evidence',type=Path,required=True,help='directory containing input-manifest.json and run-1/')
args = parser.parse_args()
E = args.evidence.resolve()
UP = args.upstream.resolve()
sys.path.insert(0, str(UP))
from pronunciada.text._eu_build import arpa_to_ipa
from pronunciada.text.en import English
from pronunciada.text._eu_common import parse_phone

manifest = json.loads((E/'input-manifest.json').read_text())
rows, phone_rows, events, extras = [], [], [], []
for c in manifest['clips']:
    uid = c['id']
    model = json.loads((E/'run-1'/(uid+'-result.json')).read_text())['result']
    ref = json.loads((E/'run-1'/(uid+'-reference.json')).read_text())
    coaching = json.loads((E/'run-1'/(uid+'-coaching.json')).read_text())['items']
    assert len(model['words']) == len(c['human_aggregate']['words']) == len(c['human_five_raters']['words'])
    phone_events = {}
    stress_events = {}
    for item in coaching:
        if item.get('phone_index') is not None:
            phone_events.setdefault((item['word_index'],item['phone_index']),[]).append(item['kind'])
        elif item['kind'] == 'stress':
            stress_events.setdefault(item['word_index'],[]).append(item['kind'])
    for (wi,pi), kinds in sorted(phone_events.items()):
        events.append({'clip':uid,'unit':'phone','word_index':wi,'phone_index':pi,'kinds':sorted(set(kinds))})
    for wi,kinds in sorted(stress_events.items()):
        events.append({'clip':uid,'unit':'word_stress','word_index':wi,'kinds':sorted(set(kinds))})
    other = set()
    suppressed = 0
    for item in coaching:
        if item.get('phone_index') is not None or item['kind']=='stress': continue
        wi = item.get('word_index')
        if item['kind'] == 'mispronounced_word' and (wi in stress_events or any(k[0]==wi for k in phone_events)):
            suppressed += 1
            continue
        key = (item['kind'],wi,item.get('start'),item.get('end'))
        if key not in other:
            other.add(key)
            events.append({'clip':uid,'unit':item['kind'],'word_index':wi,'start':item.get('start'),'end':item.get('end')})
    for wi, (human, votes, mw) in enumerate(zip(c['human_aggregate']['words'], c['human_five_raters']['words'], model['words'])):
        assert human['text'].casefold() == votes['text'].casefold() == mw['text'].casefold()
        canonical = votes['ref-phones'].split()
        assert canonical == human['phones']
        score_lists = []
        for rater, annotation in enumerate(votes['phones']):
            parsed, scores = [], []
            for token in re.findall(r'\[[^\]]+\]|\([^)]*\)|\{[^}]*\}|\S+', annotation):
                if token.startswith('['):
                    extras.append({'clip':uid,'word_index':wi,'rater':rater,'inserted':token[1:-1]})
                    continue
                score = 0 if token.startswith('(') else 1 if token.startswith('{') else 2
                parsed.append(token.strip('(){}'))
                scores.append(score)
            assert parsed == canonical, (uid,wi,rater,parsed,canonical)
            score_lists.append(scores)
        assert len(score_lists)==5
        normalized = [parse_phone(x)[0] for x in English.rewrite(None,arpa_to_ipa(canonical),human['text'])]
        p0,p1 = ref['words'][wi]['phones']
        model_ref = ref['phones'][p0:p1]
        assert len(normalized)==len(model_ref)==len(mw['phones'])
        word_coach = [x for x in coaching if x.get('word_index')==wi]
        word_row = {'clip':uid,'word_index':wi,'word':human['text'],
                    'human_accuracy_aggregate':human['accuracy'],'human_accuracy_votes':votes['accuracy'],
                    'human_stress_aggregate':human['stress'],'human_stress_votes':votes['stress'],
                    'human_mispronunciations':human.get('mispronunciations',[]),
                    'model_word_prob':mw['prob'],'model_word_stress_prob':mw['stress_prob'],
                    'model_primary_stress':[{'syllable_index':si,'expected':sy['stress_expected'],'prob':sy['stress_prob']} for si,sy in enumerate(mw['syllables']) if sy['stress_expected']==1],
                    'model_coaching_kinds':sorted(set(x['kind'] for x in word_coach)),
                    'human_unanimous_word_accuracy_10':all(v==10 for v in votes['accuracy']),
                    'human_unanimous_stress_10':all(v==10 for v in votes['stress']),
                    'human_majority_wrong_stress':sum(v==5 for v in votes['stress'])>=3,
                    'model_stress_flag':wi in stress_events}
        rows.append(word_row)
        for pi,(arpa,ipa,mph,rph) in enumerate(zip(canonical,normalized,mw['phones'],model_ref)):
            votes_phone = [s[pi] for s in score_lists]
            assert abs(sum(votes_phone)/5-human['phones-accuracy'][pi])<1e-8
            alternatives = [x[0] for x in rph['alts']]
            mapped = ipa == mph['ipa'] or ipa in alternatives
            zero_votes = votes_phone.count(0)
            if not mapped: case='BLOCKED_reference_variant'
            elif zero_votes>=3: case='human_majority_incorrect_flagged' if (wi,pi) in phone_events else 'potential_missed_majority_incorrect'
            elif all(x==2 for x in votes_phone): case='potential_false_warning_unanimous_accepted' if (wi,pi) in phone_events else 'unanimous_accepted_unflagged'
            else: case='disputed_or_accent_flagged' if (wi,pi) in phone_events else 'disputed_or_accent_unflagged'
            phone_rows.append({'clip':uid,'word_index':wi,'word':human['text'],'phone_index':pi,'human_arpa':arpa,
                               'human_normalized_ipa':ipa,'model_target_ipa':mph['ipa'],'model_accepted_alternatives':alternatives,
                               'mapping':'one_to_one_exact_or_declared_alt' if mapped else 'BLOCKED_reference_variant',
                               'human_scores_5':votes_phone,'human_mean_0_2':human['phones-accuracy'][pi],
                               'model_phone_prob':mph['prob'],'model_coaching_flag':(wi,pi) in phone_events,
                               'model_coaching_kinds':phone_events.get((wi,pi),[]),'case':case})

summary={'unit':'case counts only; no accuracy/precision/recall/F1 claim',
         'human_word_records':len(rows),'human_phone_records':len(phone_rows),
         'phone_case_counts':dict(Counter(x['case'] for x in phone_rows)),
         'deduplicated_model_events':len(events),'model_event_units':dict(Counter(x['unit'] for x in events)),
         'human_inserted_phone_annotations_not_projected_to_target_slots':extras,
         'word_stress_nonnull':sum(x['model_word_stress_prob'] is not None for x in rows),
         'human_majority_wrong_stress_cases':[x for x in rows if x['human_majority_wrong_stress']],
         'model_stress_flag_cases':[x for x in rows if x['model_stress_flag']]}
output={'method':{'word_matching':'ordered exact casefold tokens; no ASR transcript matching',
                  'phone_mapping':'same ordered index only when counts match and normalized ARPA matches target or an explicitly allowed alternate; other individual slots BLOCKED',
                  'human_phone_scores':'bare=2, curly=1 (accent), parenthesis=0 (incorrect/missing), bracket=insertion; five raters preserved; mean verified against official aggregate',
                  'case_policy':'majority >=3 raters score 0; unanimous accepted requires five scores 2; other disagreements retained without forcing binary truth',
                  'model_flags':'unchanged upstream balanced coaching, not a phone.prob <0.5 rule',
                  'stress':'human five word-stress ratings compared to model word-stress flag only; human syllable error location not inferred',
                  'event_dedup':'one per word/phone slot, one stress-pattern event per word, suppress duplicate mispronounced_word item when sound/stress event exists; retain distinct delivery events'},
        'summary':summary,'words':rows,'phones':phone_rows,'model_events':events}
(E/'expert-comparison.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,indent=2,ensure_ascii=False))
for p in phone_rows:
    if p['case'] not in ['unanimous_accepted_unflagged','disputed_or_accent_unflagged','BLOCKED_reference_variant']:
        print(p['clip'],p['word'],p['human_arpa'],p['human_scores_5'],p['case'],p['model_phone_prob'])
