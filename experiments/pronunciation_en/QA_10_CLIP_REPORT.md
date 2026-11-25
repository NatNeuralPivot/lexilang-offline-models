# Pronunciada — QA 10 Clip Report

25 ноября 2026, Europe/Moscow. **HOLD для следующего расширения локального исследования без предварительного разбора обнаруженных ошибок.** Это решение только о дальнейшем local research, не о release, merge или app integration.

**Новые 7/7 записей успешно оценены акустически.** Предыдущие 3 результата повторно не вычислялись; вместе имеются результаты для **n=10 различных записей**. Технический запуск прошёл, но сравнение с реальными экспертами выявило пропуски и потенциальные ложные предупреждения, включая ударение. Настройки/калибровки под эти test samples не подбирались.

## Объём и PASS / FAIL / BLOCKED

| Этап | Статус | Проверенное |
| --- | --- | --- |
| Прочитать задание и сохранить существующие ветки | PASS | [QA_NEXT_7_CLIPS_TASK.md](QA_NEXT_7_CLIPS_TASK.md); public обновлён fast-forward только до task commit `317bd27`, private остаётся на существующей experimental branch |
| Точные human labels до inference | PASS, 7/7 | Pinned official test/text, utt2spk, wav.scp, spk2age и resource/scores*.json; Git blob OID проверены |
| Выбор sample/split/speaker | PASS, 7/7 | Ровно заданные ID, test, 7 разных взрослых Mandarin-L1 speakers, исходная выборка не менялась |
| Скачать и заморозить WAV | PASS, 7/7 | HTTP 200, 969 908 байт суммарно, WAV PCM_16 mono 16 kHz, конечные samples, file/PCM SHA-256 уникальны |
| Использовать существующую ZIPA | PASS | Исходный INT8 SHA проверен, 2 прежних ONNX-файла в кэше неизменны; веса/граф не скачивались и не создавались заново |
| Offline acoustic inference | PASS, 7/7 | Каждый WAV один scoring вызов; сеть запрещена; положительный model timing для каждого |
| Числа / timings / audio gates | PASS, 7/7 | Non-finite=[], flags=[], warnings=[], issues=[], нет identical numeric signatures |
| Word alignment human ↔ model | PASS | 51/51 слов: порядок и токены casefold совпадают |
| Phone comparison | PASS 163 слота; BLOCKED 8 слотов | Только точное соответствие нормализованного ARPA и target/явно допустимой альтернативы; восемь variant mismatches не оценивались как совпадение/ошибка |
| Stress comparison | PASS на уровне слова | 51 human word-stress records, 11 non-null model word-stress outputs; human syllable error location отсутствует и не выдумывалась |
| Качество pedagogical flags | HOLD | Ниже конкретные missed-error / false-warning case notes; успешный inference не доказывает качество |

Новых runtime/script failures нет; исправлений после запуска **0 из максимально 2**. Старый `run_acoustic_smoke.py` не менялся. Bootstrap, старые 14 тестов, старые 3 inference, lesson audit и полный QA приложения не повторялись.

## Источники, ревизии и заморозка

- Pronunciada: `4619a298e5e2de927120122585683d18eda1f7c4`, неизменённый full Python runtime.
- ZIPA `anyspeech/zipa-small-crctc-500k`, HF revision `dfe87c97662606fa6db90ad06f627d4363314744`; `model.int8.onnx`, 70 677 672 байта, SHA-256 `d0e28b68164e8b1fbd6105100c01798828aa0855000ce9bbbd1a2cec233adf13`.
- Модель осталась в существующем `~/.cache/lexilang/en-pronunciation-acoustic-qa/zipa-small-int8-dfe87c97662606fa6db90ad06f627d4363314744/`; runtime использовал прежний extra-output graph.
- Корпус: [jimbozhang/speechocean762](https://github.com/jimbozhang/speechocean762/tree/613968e3b0b789fc33936fb5eba1973176ba7d11), revision `613968e3b0b789fc33936fb5eba1973176ba7d11`.
- Aggregate scores: [resource/scores.json](https://github.com/jimbozhang/speechocean762/blob/613968e3b0b789fc33936fb5eba1973176ba7d11/resource/scores.json); five-rater annotations: [resource/scores-detail.json](https://github.com/jimbozhang/speechocean762/blob/613968e3b0b789fc33936fb5eba1973176ba7d11/resource/scores-detail.json).
- Input manifest SHA-256 до inference: `41d0596090363e28b0f857323b7e1e79bd9048ee5c750d1ee2cac6f27b1266f7`. [input-manifest.json](qa_10_clips/input-manifest.json) сохранён побайтово с транскриптами, label fragments, URL, размерами, hashes и decoder metadata; human fields отделены от model outputs.

Сетевые операции выполнялись **до** inference: fetch двух experiment refs, Git tree metadata, шесть текстовых annotation/test files (29 688 644 байта) и ровно семь WAV (969 908 байт). Полный корпус не скачивался. WAV и полные source JSON остаются вне Git:

`~/.cache/lexilang/pronunciada-next7-qa-613968e3b0b789fc33936fb5eba1973176ba7d11/`

При inference Python audit hook запрещал DNS/connect/urllib; CPUExecutionProvider. `Scorer("en", precision="int8", threads=4, strictness=0.5, cache_size=1)`, без изменения нормализации, balanced coaching или calibrations. Full pipeline: WAV → 16 kHz mono → fbank → ZIPA → alignment → calibrated phone/word/sentence/stress. Модельные posteriors не заменялись транскрипцией.

## Новые WAV: URL / SHA-256 / размер

Все URL закреплены на ревизии корпуса, SHA измерены по реально скачанным байтам. Samples проверены декодированием, не только HEAD.

| ID (pinned WAV) | Speaker | Байт | Длительность | SHA-256 |
| --- | --- | ---: | ---: | --- |
| [001200015](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0120/001200015.WAV) | 0120 | 144428 | 4.512 s | `a5a580e119a75a9fca04f9c6c52d301bc904e313581a60d5e94588bbfb38ddda` |
| [001570024](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0157/001570024.WAV) | 0157 | 122284 | 3.820 s | `0253783338ba943f3998ac13e0a036d0cbe9424b09b388d45cd5d45377563936` |
| [003060002](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0306/003060002.WAV) | 0306 | 127404 | 3.980 s | `d862b9084cdf6b171589a310efc74808f7d42a8d1e8329c4ac2e4c48c47352a3` |
| [004570010](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0457/004570010.WAV) | 0457 | 180652 | 5.644 s | `ac8ed9577744e63842631b913e5516d449c93418273c64f3b2dc0ed943fe5c4d` |
| [004610037](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0461/004610037.WAV) | 0461 | 168652 | 5.269 s | `8d3c5ce6c72ae9b524dbc41ea12e278b91d2287c1d912f7f129e2e08acab0c40` |
| [005630017](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0563/005630017.WAV) | 0563 | 120524 | 3.765 s | `c70dd71e1bc20414ac69ebf734e016e0500023b358c3f427b49f04ef9e5231a5` |
| [005670043](https://raw.githubusercontent.com/jimbozhang/speechocean762/613968e3b0b789fc33936fb5eba1973176ba7d11/WAVE/SPEAKER0567/005670043.WAV) | 0567 | 105964 | 3.310 s | `79bdb7bbb7eda0425e05643e911f719b7c7a68537226f81e416ff63c308ec23c` |

Все семь — PCM_16, 16 000 Hz, 1 channel. Human transcript взят точно из test/text и проверен против обоих scores-файлов; необычная фраза `HAVE THEY OWN` в официальном reference не «исправлялась» на другой текст. Отдельные file SHA и decoded float32 PCM SHA позволяют выявить повтор аудио при другой упаковке; повторов нет.

## Предыдущие 3 и новые 7 — отдельно

Baseline — неизменённые [QA_ACOUSTIC_REPORT.md](QA_ACOUSTIC_REPORT.md) / [qa_acoustic/run.json](qa_acoustic/run.json), public baseline commit `d10cf22`. Human comparison ниже выполнен **только для новых семи**; предыдущие excerpts не выдаются за новый аудит тех трёх.

| Набор | Distinct recordings | Phones | Words | Syllables | Word stress non-null | Syllable stress non-null | Sentence score fields | Raw coaching items |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Предыдущие, reused evidence | 3 | 60 | 19 | 25 | 4 | 4 | 12 | 11 |
| Новые, этот запуск | 7 | 171 | 51 | 69 | 11 | 11 | 28 | 28 |
| Имеющиеся результаты всего | 10 | 231 | 70 | 94 | 15 | 15 | 40 | 39 |

Дополнительно: sentence `prob` — 7 новых / 10 всего; каждый score map содержит accuracy/fluency/prosodic/total. Это названия выходов regression head, не рассчитанная accuracy исследования. Per-phone feature dictionaries сохранены вместе с raw probabilities; null stress на односложных словах не превращался в 0 или 1.

## Сопоставление с экспертами: метод и case notes

Слово сопоставляется по порядку и точному casefold-токену, без ASR. Для каждого human phone прочитаны все пять исходных аннотаций: bare=2 (correct), `{phone}`=1 (accent), `(phone)`=0 (incorrect/missing); `[phone]` — вставка. Среднее пяти оценок проверено против официального aggregate phones-accuracy. Наличие accent=1 не объявляется ошибкой автоматически.

Для прозрачных case notes: majority incorrect означает ≥3 из 5 оценок 0; unanimously accepted — все пять оценок 2. Остальные disagreement/акценты остаются отдельной категорией. Это правила описания случаев, не новый calibration threshold. Model flag берётся из неизменённого balanced coaching; он **не** равен `phone.prob < 0.5`.

ARPA переводится штатным `arpa_to_ipa` и EN rewrite pinned upstream, без обучения или вызова builder. При одинаковом количестве фонем используется тот же ordered index только если IPA совпадает с target или явно допустимой alternate. **163/171 слотов сопоставимы, 8 BLOCKED**: RESEARCHERS (2), AFTER (2), PROPERTY (2), ANOTHER (1), ALTOGETHER (1). Эти восемь не использованы в утверждениях о sound hits/misses/false warnings. Три single-rater insertion annotations сохранены, но не проецировались на nonexistent canonical slots.

### Восемь сопоставимых majority-incorrect phone cases

Ниже события, а не confusion matrix и не recall. Фонемные probabilities и coaching flags — отдельные калибраторы.

| ID / слово / ARPA | Ратеров с 0 из 5 | Phone probability | Balanced sound flag | Case note |
| --- | ---: | ---: | --- | --- |
| 003060002 / SET / EH0 | 4 | 0.442480 | да | совпадает локализация проблемы |
| 003060002 / HOOK / UH0 | 4 | 0.843878 | да | совпадает локализация проблемы |
| 003060002 / THE / AH0 | 5 | 0.722996 | нет | потенциальный пропуск |
| 003060002 / PRESSURE / EH1 | 5 | 0.605359 | да | совпадает локализация проблемы |
| 004570010 / ONLY / L | 3 | 0.941284 | нет | потенциальный пропуск |
| 004610037 / THAT'S / DH | 3 | 0.660085 | да | совпадает локализация проблемы |
| 005670043 / EXPECT / P | 3 | 0.977693 | нет | потенциальный пропуск |
| 005670043 / EXPECT / EH1 | 4 | 0.976878 | нет | потенциальный пропуск |

SET, HOOK, PRESSURE и THAT'S /DH/ получили sound flags на экспертно отмеченных slots. У HOOK probability при этом 0.843878: порог 0.5 пропустил бы coaching event. Для THE /AH0/, ONLY /L/ и двух EXPECT slots нет соответствующего balanced sound flag; EXPECT не получил и word mispronunciation flag. Высокие sentence probabilities не должны скрывать эти локальные пропуски. Некоторые phoneme `heard`/replacement поля остаются null из-за confidence gate; локализация предупреждения не означает уверенно установленную замену звука.

### Три потенциальных false-warning sound cases

Все пять экспертов поставили соответствующему phone 2; в каждом случае IPA mapping разрешён.

| ID / слово / phone | Model phone probability | Model warning |
| --- | ---: | --- |
| 003060002 / JUST / T | 0.543126 | substitution |
| 004570010 / AT / AE0 | 0.859470 | substitution |
| 004610037 / THAT'S / AE0 | 0.208565 | substitution |

Это потенциальные ложные **phone** warnings для ручного прослушивания. Например, THAT'S содержит реальную экспертную проблему /DH/, но это не подтверждает warning на отдельно принятом /AE0/. В JUST другие звуки оценены неодинаково; отсутствие проблемы /T/ не означает, что всё слово единогласно принято. У AT все пять word-accuracy ratings также равны 10, но balanced coaching выдал substitution и word wrapper.

### Stress / word / delivery

- **PROPERTY, 004570010:** human word-stress `[5,5,5,5,5]`, aggregate=5 (wrong). Model word-stress probability **0.908405**, primary-syllable probability **0.240370**, stress coaching отсутствует. Это сильный missed-stress case на уровне слова. Отдельный sound warning PROPERTY относится к reference-variant slot и не засчитывался как совпадение по ударению.
- **RESEARCHERS, 001570024:** human stress `[10,10,5,10,5]` (majority accepted, есть несогласие), model word-stress probability **0.359070**, primary-syllable **0.012910**, balanced stress flag. Это disputed case, а не доказанный unanimous false positive. Human word-accuracy aggregate=10, model word probability **0.350874**; степени/шкалы напрямую не вычитаются.
- **FOUND, 001570024:** human /AW0/ ratings `[2,1,0,2,0]`, aggregate=1.0; sound flag отсутствует. Есть человеческое расхождение и акцент — этот пример не превращался в majority-incorrect miss.
- **STORY, 004610037:** delivery warning `pause_mid_phrase`. Общая sentence fluency label не имеет timestamp этой паузы, поэтому истинность этого отдельного delivery event **BLOCKED** без прослушивания/разметки пауз.

Human stress доступен на уровне слова, не как место ошибки в слоге; таких syllable labels не реконструировали. Для 11 non-null word stress выходов сравнение возможно; 40 остальных слов имеют null model stress и не считаются ни подтверждёнными, ни пропущенными stress errors.

Полное сопоставление 51 word и 171 phone, все пять human ratings, mapping status, source mispronunciations и model fields: [expert-comparison.json](qa_10_clips/expert-comparison.json).

### Дедупликация предупреждений

Новые 28 raw coaching items содержат **14 phone-slot events, 1 word-stress event и 1 delivery event = 16 distinct model events**. 12 `mispronounced_word` wrappers подавлены при наличии sound/stress event того же слова. Это число разных warning units, не число доказанных ошибок и не статистическая precision. Minority/disputed cases не объявлены истинными или ложными автоматически.

## Время, память и контроль качества

Измерено на том же Mac (Apple M4 Pro, 24 GiB, macOS arm64), существующим Python 3.14.7 QA virtualenv: NumPy 2.5.5, ONNX Runtime 1.32.0, kaldi-native-fbank 1.23.3, SoundFile 0.14.0.

Scorer load — **0.573858 s**, с существующим локальным extra-output graph. First scoring call — **96.488 ms**; следующие шесть разных аудио дали **37.234–85.585 ms**. Это process-warm observations, не latency percentiles и не повторные cached scoring calls.

| ID | Audio s | Full scoring ms | ZIPA-only ms | Coaching ms | Peak RSS so far MiB | Phones / words / syllables | Raw coaching |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 001200015 | 4.512 | 96.488 | 37.190 | 2.016 | 297.453 | 32 / 10 / 13 | 0 |
| 001570024 | 3.820 | 43.851 | 23.063 | 6.147 | 310.391 | 25 / 8 / 10 | 3 |
| 003060002 | 3.980 | 49.103 | 23.987 | 3.902 | 313.359 | 23 / 7 / 8 | 8 |
| 004570010 | 5.644 | 85.585 | 51.115 | 1.155 | 329.984 | 32 / 10 / 14 | 6 |
| 004610037 | 5.269 | 53.252 | 28.912 | 0.924 | 330.656 | 25 / 5 / 11 | 7 |
| 005630017 | 3.765 | 39.766 | 22.118 | 0.589 | 330.797 | 17 / 6 / 7 | 2 |
| 005670043 | 3.310 | 37.234 | 20.248 | 0.540 | 330.812 | 17 / 5 / 6 | 2 |

Peak process RSS: **346 882 048 байт = 330.8125 MiB**, включая native ORT и Python allocations. Полный runtime span (imports/init + 7 scoring/coaching + output writes/guards) — **1.139006 s**; это не сумма только inference times и не включает предварительное скачивание annotations/WAV. Методы: `perf_counter`, upstream `timing_ms`, macOS `getrusage(RUSAGE_SELF).ru_maxrss` в байтах. Значения per-clip RSS — high-water so far, не live RAM; battery/virtual memory не измерялись.

Все семь имеют model timing >0; posterior cache=1 не дал hit на разных waveform. Все audio gates: issues=[], retry=false; warnings=[], nonfinite=[], разные numeric signatures. Ни один score не достраивался из текста. Нулевых/выдуманных полей для успешности не добавлено.

Детали: [run.json](qa_10_clips/run-1/run.json), [run stdout](qa_10_clips/run-1.txt); индивидуальные `ID-result.json`, `ID-coaching.json`, `ID-reference.json` в [run-1](qa_10_clips/run-1). Raw outputs привязаны к исходному audio SHA и frozen input-manifest SHA. Failure logs отсутствуют, так как исключений при запуске не было; stdout сохранён полностью.

## Лицензии и решение только о local research

Записи и human annotations: speechocean762, Junbo Zhang et al., Interspeech 2021. [Первичный OpenSLR SLR101](https://www.openslr.org/101/) указывает CC BY 4.0; pinned official repo — источник выбранных WAV и scores. Ранее отмеченное расхождение с Apache-2.0 меткой HF dataset card не закрыто этим QA. Аудио не публикуется. ZIPA weights — CC BY 4.0 по закреплённой model card; Pronunciada code — Apache-2.0, data имеют отдельные права.

Остаются прежние stress_v3 и coaching attr_heads share-alike вопросы. Текущий запуск не является новой юридической проверкой или разрешением на redistribution. Нет новых model artifacts, Releases или обучения.

**HOLD для следующего локального batch без ручного разбора** THE, EXPECT, ONLY, PROPERTY stress и трёх potential false warnings. Нужны прослушивание с экспертом, проверка допустимых EN variants и объяснение различий phone probability/coaching/stress aggregation. Результаты обосновывают адресное исследование этих случаев, но не увеличение объёма без гипотезы и не подстройку thresholds на этих test примерах. Это не REJECT всей модели: acoustic pipeline работает; не GO без оговорок: конкретные misses/false-warning cases существенны.

10 коротких записей от Mandarin-L1 speakers не являются статистически подтверждённой accuracy, precision, recall, F1, ECE/Brier или CEFR-валидацией. Взрослый возраст не означает C1/C2. Ни межакцентная применимость, ни качество advanced curriculum этим набором не установлены.

## Evidence, воспроизведение и остановка

- Новый [run_expansion_smoke.py](run_expansion_smoke.py) переиспользует hash/revision guards старого runner и выполняет только manifest seven. Предыдущий runner неизменён.
- Новый [compare_expansion_labels.py](compare_expansion_labels.py) читает **только сохранённые результаты**, без inference; standalone версия воспроизвела побайтово тот же expert-comparison.json.
- [EVIDENCE_SHA256.tsv](qa_10_clips/EVIDENCE_SHA256.tsv) содержит размеры и SHA-256 всех текстовых evidence. Полные source scores остаются в локальном кэше; Git содержит только нужные excerpts внутри manifest.

Вызов выполненного scoring (OUT — новый каталог, чтобы не перезаписывать результаты):

```bash
"$QA_ROOT/runtime-venv/bin/python" \
  "$QA_ROOT/public/experiments/pronunciation_en/run_expansion_smoke.py" \
  --upstream "$HOME/.cache/lexilang/en-pronunciation-experiment/pronunciada-4619a298e5e2de927120122585683d18eda1f7c4" \
  --model-cache "$HOME/.cache/lexilang/en-pronunciation-acoustic-qa/zipa-small-int8-dfe87c97662606fa6db90ad06f627d4363314744" \
  --clips-manifest "$HOME/.cache/lexilang/pronunciada-next7-qa-613968e3b0b789fc33936fb5eba1973176ba7d11/input-manifest.json" \
  --out "$OUT"
```

QA_ROOT — `~/Lexi-Pronunciation-QA`. Эта команда документирует воспроизводимость; автоматически следующий запуск не назначался. Только existing `experiment/pronunciation-en-lexicon-calibration` ветки; `main`, app architecture, SwiftUI, ReaderKit, Audio, Kokoro, Curriculum и личные данные не менялись. Нет новых branches, merges в main, Releases, iPhone work, полного regression или обучения. После сохранения отчётов работа остановлена.
