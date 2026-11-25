# Lexi Lang — Pronunciada Acoustic QA

25 ноября 2026, Europe/Moscow. **Результат: GO — для расширения локального исследовательского smoke test до 5–10 лицензированных EN-записей.** Это не GO для интеграции или распространения: соответствующие gates остаются HOLD. Дополнительные записи в этой задаче не скачивались и не оценивались. После сохранения отчёта работа остановлена.

## PASS / FAIL / BLOCKED

| Проверка | Итог | Результат |
| --- | --- | --- |
| Официальный ZIPA-small INT8, лицензия и revision | PASS | Ссылка из ZIPA authors repo на AnySpeech; pinned HF commit, CC BY 4.0 |
| Локальная загрузка / SHA-256 | PASS | 70 677 672 байта, SHA совпал с LFS metadata той же ревизии |
| Token vocabulary | PASS | SHA-256 и Git blob OID проверены; файл побайтово совпадает с pinned Pronunciada |
| Первая попытка с `cache_size=0` | FAIL | Upstream `KeyError` после удаления возвращаемого posterior cache entry |
| Повтор с поддерживаемым `cache_size=1` | PASS | 3/3 distinct recordings, для каждого `timing_ms.model > 0` |
| Фонемы / слова / ударение | PASS | Сохранены 60 phone records, 19 word records, все syllable records; 4 слова имеют non-null stress probability |
| Реальные акустические ошибки/подсказки | PASS исполнения | 0 / 8 / 3 upstream balanced coaching items; предсказания, не подтверждённые экспертом ошибки |
| Offline scoring | PASS | После скачивания network audit hook запрещал connect/DNS/urllib; CPUExecutionProvider |
| Официальный граф ↔ extra-output граф | PASS | На en-clean backbone log_probs и lengths bit-identical; max delta 0 |
| Замеры времени и памяти | PASS | Перечислены ниже, реальные измерения одного успешного процесса |
| Возможность 5–10 EN recordings | PASS оценки доступности | 7 дополнительных adult test WAV, 7 отдельных speakers, HTTP HEAD 200; inference не запускался |
| Независимая оценка качества / C1–C2 | BLOCKED | Три ранее отобранных demo-примера не образуют новый независимый benchmark |
| Разрешение на распространение полного scorer | BLOCKED | Stress / coaching share-alike вопросы и полный комплект notices остаются открытыми |

Предыдущие 14/14 unit tests, 24 ресурса и lesson audit приняты как пройденные; **bootstrap, lesson audit и полный regression suite не повторялись**. В исходном upstream и приложении код не менялся. Одна корректировка конфигурации QA runner, без изменения модели или алгоритмов.

## Модель, лицензия и точная ревизия

Проверено на Mac16,8 / Apple M4 Pro / 24 GiB, macOS 26.5.2 arm64, Python 3.14.7. Использован существующий изолированный QA virtualenv: NumPy 2.5.5, ONNX Runtime 1.32.0, kaldi-native-fbank 1.23.3, SoundFile 0.14.0.

- Официальный [ZIPA authors repository](https://github.com/lingjzhu/zipa) содержит ссылку на выбранный 64M Cr-small 500k checkpoint; его MIT code license не подменяет отдельную лицензию весов.
- Модель: `anyspeech/zipa-small-crctc-500k`, файл `model.int8.onnx`; не `-ns-` variant.
- HF revision: `dfe87c97662606fa6db90ad06f627d4363314744`.
- Лицензия в [model card закреплённой ревизии](https://huggingface.co/anyspeech/zipa-small-crctc-500k/blob/dfe87c97662606fa6db90ad06f627d4363314744/README.md): **CC BY 4.0**. Карточка и API metadata проверены до загрузки; сам hash не является юридическим разрешением на распространение всего Pronunciada-пакета.
- Pronunciada code/calibrations: unchanged commit `4619a298e5e2de927120122585683d18eda1f7c4` (1.1.0).
- Исходные экспериментальные HEAD: public `be91b577a461d6e548863d5fa3cce1bd7cd5847c`, private `6893e513145ba0eca34fffa44bf7a84e4aaf4a6b`; remote branch fetch выполнен перед сохранением.

| Локальный файл | Байт | Измеренный SHA-256 |
| --- | ---: | --- |
| model.int8.onnx | 70677672 | `d0e28b68164e8b1fbd6105100c01798828aa0855000ce9bbbd1a2cec233adf13` |
| tokens.txt | 769 | `f8e042a0c9130532b22d03ec7cae2f75a23fbec70c450c31a8efb51787b2b8fe` |
| model.int8.emb-enc0-enc1-enc2-enc3-enc4-enc5-final.onnx | 70678887 | `36a7cdc229e08c57b6c568fc0a4b6dc697c01f435b09183699b9a1f5b19c034c` |

Последний файл — локально созданная upstream-функцией версия для чтения промежуточных encoder activations, без обучения. Исходный скачанный файл сохранён. Для первого реального аудио отдельно сравнены raw outputs исходного и дополненного графа: `[1,107,127]` log_probs и length `[107]` совпадают побитово. Это не full-versus-trimmed scoring parity и не сравнение FP32/INT8.

Веса и производный граф находятся только в:

`~/.cache/lexilang/en-pronunciation-acoustic-qa/zipa-small-int8-dfe87c97662606fa6db90ad06f627d4363314744/`

Оба файла ONNX вместе занимают 141 356 559 байт. В Git сохранены только текстовые метаданные и результаты. Полные URL загрузки, remote LFS SHA, Git blob OID и timings: [model-provenance.json](qa_acoustic/model-provenance.json).

## Что реально выполнялось

Полный pinned Python `Scorer("en", precision="int8", threads=4, strictness=0.5, cache_size=1)`: audio decode → 16 kHz mono → fbank → ZIPA ONNX → EN adapter → CTC alignment → acoustic feature/calibration → sentence/prosody heads. Запрошены enc0–enc5 и final; embeddings и stress scorer успешно загружены. Изменений strictness, дообучения, искусственного сглаживания оценок или замены phoneme scoring на ASR alignment не было.

Три различных waveform обработаны по одному разу в успешном запуске. Posterior cache размером 1 не дал ни одного hit, что дополнительно подтверждено положительным временем model для каждого результата. Готовые upstream `site/samples/*.json/result` не использовались как наши predictions. Из них отдельно сохранены только `meta` с исходными human annotations для контекста, после inference; они не подавались scorer.

Этот запуск использует **полный upstream runtime**, а не только ранее собранный 24-file candidate. Python audit увидел 26 открытых package data files, включая дополнительные `coach/model.json`, `coach/gate.json`, `coach/inventory.json`, `coach/attr_heads.npz`. Два ONNX head-графа открываются нативным ORT и не видны этому Python hook. Список Python-opened paths/hashes приведён в [run.json](qa_acoustic/run.json); он не объявляется исчерпывающим native file-access trace.

## Записи и акустические оценки

Все три записи — лицензированные test-split speechocean762 clips из pinned upstream. Источник и условия: [ATTRIBUTION.md](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/site/samples/ATTRIBUTION.md), [OpenSLR SLR101 — CC BY 4.0](https://www.openslr.org/101/). Атрибуция корпуса: Junbo Zhang et al., speechocean762, Interspeech 2021. Аудио не копировалось в Git и не отправлялось на inference-сервис.

`prob` — выход upstream calibrator на шкале 0–1. Поле `scores.total` — отдельный regression-style output; это не измеренная accuracy на нашем тесте и не «процент правильного произношения».

| Запись / corpus ID | Длительность | Phones / words | Sentence prob | scores.total | Coaching items |
| --- | ---: | --- | ---: | ---: | ---: |
| en-clean / 000240010 | 2.211 s | 13 / 5 | 0.992689 | 0.904008 | 0 |
| en-learner-1 / 014200206 | 3.070 s | 24 / 8 | 0.742899 | 0.716741 | 8 |
| en-learner-2 / 021160249 | 3.999 s | 23 / 6 | 0.982487 | 0.833373 | 3 |

Все phone/word/syllable поля с полным числом знаков, timestamps, raw acoustic features, warnings и audio-quality metrics сохранены отдельно: [en-clean.json](qa_acoustic/en-clean.json), [en-learner-1.json](qa_acoustic/en-learner-1.json), [en-learner-2.json](qa_acoustic/en-learner-2.json). Не-finite полей в public result dict не обнаружено; serializer ничего не заменял на null. Имеющиеся null stress-поля — штатное отсутствие оценки соответствующего канала, а не 0 и не 1. Все три audio-quality gate прошли без issues/retry; warnings пусты.

Все 19 word probabilities:

- **en-clean**: It=0.998146, was=0.974494, good=0.989505, for=0.974598, me=0.998044.
- **en-learner-1**: It=0.871349, was=0.959810, a=0.974644, beautiful=0.639339, day=0.944445, for=0.931165, a=0.778784, float=0.106500.
- **en-learner-2**: Follow=0.988740, the=0.984017, link=0.953440, below=0.939945, to=0.998047, register=0.416361.

## Ударение, ошибки и ограничения интерпретации

| Слово | Word stress probability | Ожидаемый primary syllable | Primary syllable probability |
| --- | ---: | ---: | ---: |
| beautiful | 0.998901 | 1 | 0.979339 |
| Follow | 0.996106 | 1 | 0.920760 |
| below | 0.945689 | 2 | 0.371312 |
| register | 0.464060 | 1 | 0.020754 |

Word stress и syllable stress — разные upstream outputs; они не обязаны совпадать. Для en-clean все слова односложные, поэтому word stress probabilities отсутствуют.

- **en-clean:** balanced coaching не выдал подсказок; нет phone/word probabilities ниже 0.5. Это результат данного примера, не доказательство отсутствия всех возможных ошибок.
- **en-learner-1:** `float` имеет word probability **0.106500**; /l/ — **0.273025**, /oʊ/ — **0.338440**. В acoustic evidence есть низкая поддержка этих звуков. Balanced coaching сохраняет replacement как null, когда его gate не разрешает уверенно назвать услышанный звук. В raw PhoneResult `heard` может содержать диагностическую гипотезу; она не равнозначна уверенному coaching claim.
- **en-learner-2:** `register` имеет word probability **0.416361**, word stress **0.464060**, вероятность правильного primary stress первого слога **0.020754**. Upstream coaching предполагает ударение на втором слоге (JSON индексы expected=0, heard=1). Для /ɛ/ phone acceptability **0.8265**, но отдельный coaching error model даёт error_prob **0.614**; это разные калибраторы, а не правило `error=1-phone.prob`. Поэтому один порог 0.5 по phones не воспроизводит все coaching flags.

Полные 11 items: [en-clean-coaching.json](qa_acoustic/en-clean-coaching.json), [en-learner-1-coaching.json](qa_acoustic/en-learner-1-coaching.json), [en-learner-2-coaching.json](qa_acoustic/en-learner-2-coaching.json). В них есть sound и word flags для одной проблемы: **11 items не означают 11 независимых ошибок**. В runner диагностический список `phones_below_0_5` — только дополнительная выборка, не определение истинной ошибки.

В исходных sample human metadata указаны /L/ deletion в FLOAT и /EH/→/IH/ в REGISTER: [expert-context.json](qa_acoustic/expert-context.json). Это контекст из upstream, а не новая независимая экспертиза. Он поддерживает проверку направлений phone flags; все дополнительные coaching/stress claims ещё требуют прослушивания и adjudication. Три примера уже использовались upstream как иллюстрации, новых confidence intervals, accuracy, ECE/Brier или C1–C2 quality claims здесь нет.

## Измеренные время и RAM

| Этап | Реальное время |
| --- | ---: |
| Загрузка и SHA официального INT8 файла | 34.496 s |
| Загрузка и проверка tokens | 1.377 s |
| Импорты успешного runtime процесса | 0.124 s |
| Первый scorer init, включая создание extra-output файла; затем попытка упала на cache_size=0 | 0.717 s |
| Scorer init успешного процесса, готовый локальный extra-output файл | 0.475 s |
| Успешный run: импорты + init + 3 scoring + coaching, до финального hashing evidence | 1.959 s |

| Запись | score wall | ZIPA model | fbank | delivery/F0 | prosody head | coaching отдельно |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| en-clean | 1234.144 ms | 20.887 ms | 5.892 ms | 1163.737 ms | 1.614 ms | 10.449 ms |
| en-learner-1 | 45.065 ms | 23.218 ms | 3.189 ms | 4.787 ms | 2.003 ms | 6.497 ms |
| en-learner-2 | 45.988 ms | 24.153 ms | 3.124 ms | 5.119 ms | 3.164 ms | 1.158 ms |

Первый полный scoring вызов — **1.234 s**, из него delivery stage занял **1.164 s**. Это измеренный first-call overhead; он не скрыт за 20.9 ms backbone. Последующие два разных аудио заняли **45.065 / 45.988 ms**. Это единичные process-warm наблюдения, не p50/p95 benchmark и не оценка cold start из полностью холодного OS file cache.

Пиковый RSS успешного процесса: **327 401 472 байта = 312.234 MiB**. После scorer init high-water RSS составлял 263 733 248 байт (251.516 MiB), не current/live RSS. Отдельный процесс raw backbone parity достиг 262 307 840 байт (250.156 MiB); к основной цифре он не прибавляется. Метод: `perf_counter`, upstream `timing_ms`, `resource.getrusage(RUSAGE_SELF).ru_maxrss`, macOS units — bytes. Native ORT allocations включены в RSS. Зарезервированная виртуальная память, battery и device-specific пределы не измерялись.

## Обнаруженная ошибка и корректировка

Первая попытка создала и загрузила acoustic graph, выполнила backbone, но не вернула ни одной SentenceResult: `_posteriors` записывает entry, при `_cache_size=0` удаляет его и затем читает `self._lp_cache[key]`, получая KeyError. Это не проблема весов и не «нулевой pronunciation score».

Runner переведён на `cache_size=1`; все три waveform различны, каждый scoring один раз, и все `model` timings положительны. Upstream не патчился. Учёт: **1 корректировка из допускаемых 2**. Сохранены [attempt-1.json](qa_acoustic/attempt-1.json) и [attempt-1.txt](qa_acoustic/attempt-1.txt); неудачный результат не смешивался с успешными scores. Никаких повторов полного bootstrap/regression не было.

## Возможность расширения до 5–10

**Технически и по доступности исходников — да.** Проверены только небольшие test-манифесты официального [speechocean762 repo](https://github.com/jimbozhang/speechocean762/tree/613968e3b0b789fc33936fb5eba1973176ba7d11), revision `613968e3b0b789fc33936fb5eba1973176ba7d11`. Выбраны первые по sorted utterance ID примеры семи разных adults ≥18, без трёх уже использованных speakers и без выбора по model outputs:

| Candidate ID | Speaker | Возраст | HEAD bytes |
| --- | --- | ---: | ---: |
| 001200015 | 0120 | 19 | 144428 |
| 001570024 | 0157 | 21 | 122284 |
| 003060002 | 0306 | 21 | 127404 |
| 004570010 | 0457 | 21 | 180652 |
| 004610037 | 0461 | 23 | 168652 |
| 005630017 | 0563 | 22 | 120524 |
| 005670043 | 0567 | 21 | 105964 |

Все семь URL ответили HTTP 200 / audio/wav на HEAD, суммарно **969,908 байт** по Content-Length. Это позволит добрать 2 записи до 5 или 7 до 10 без скачивания полного корпуса. Список URL и выборка: [expansion-candidates.json](qa_acoustic/expansion-candidates.json). HEAD не проверяет содержимое WAV: до будущего теста нужно скачать выбранные файлы, измерить SHA, сверить transcript, split и human labels, затем использовать те же замороженные настройки. Новые аудиофайлы сейчас не скачаны и не оценены.

OpenSLR указывает CC BY 4.0; HF dataset card показывает другую метку Apache-2.0. Для дальнейшего локального исследования ориентир — первичный корпус и его attribution, для коммерческого распространения metadata discrepancy нужно отдельно закрыть. Эти Mandarin-L1 adult samples не представляют всех учащихся B2–C2.

## Нерешённые gates и остановка

Для локального увеличения smoke sample **GO**: настоящий acoustic pipeline работает и не требует iPhone-порта. Для product quality и распространения остаётся **HOLD**:

- Нет независимой проверки false positives и дополнительных stress claims; слишком мало и заранее отобраны записи.
- Shared `stress_v3.json`/`.onnx` имеют открытые share-alike вопросы; `.zemb.npz` имеет то же происхождение. Реально использованный coaching `attr_heads.npz` также помечен upstream `share_alike_question=true`; это дополнительный gate по сравнению с чистым 24-file scoring candidate. Полные notices и legal classification не завершены.
- Полная достаточность trimmed 24-file pack не проверена; этот запуск использовал full upstream package. Native/iPhone/Core ML выводов из него не следует.

Никаких изменений `main`, SwiftUI, архитектуры, уроков, Audio, ReaderKit или Kokoro. Только существующие `experiment/pronunciation-en-lexicon-calibration` ветки; модель и аудио в Git не публикуются, Releases отсутствуют. Нет полного regression suite, обучения и перехода к iPhone. После отчёта следующие этапы не запускались.

## Воспроизведение и evidence

Runner: [run_acoustic_smoke.py](https://github.com/NatNeuralPivot/lexilang-offline-models/blob/experiment/pronunciation-en-lexicon-calibration/experiments/pronunciation_en/run_acoustic_smoke.py). Он не скачивает веса: требует указанные pinned source/model/token/audio hashes, запрещает сеть в inference, отказывается перезаписывать output directory.

```bash
"$QA_ROOT/runtime-venv/bin/python" \
  "$QA_ROOT/public/experiments/pronunciation_en/run_acoustic_smoke.py" \
  --upstream "$HOME/.cache/lexilang/en-pronunciation-experiment/pronunciada-4619a298e5e2de927120122585683d18eda1f7c4" \
  --model-cache "$HOME/.cache/lexilang/en-pronunciation-acoustic-qa/zipa-small-int8-dfe87c97662606fa6db90ad06f627d4363314744" \
  --out /tmp/lexi-new-acoustic-smoke --threads 4
```

QA_ROOT — локальный каталог `~/Lexi-Pronunciation-QA`. Это запись уже выполненного вызова с новым example output path, а не автоматически запланированный следующий тест. [run.json](qa_acoustic/run.json) содержит полные timings, runtime versions, реально открытые ресурсы и hashes локальных графов; [backbone-output-parity.json](qa_acoustic/backbone-output-parity.json) — отдельную проверку original/extra-output posterior parity. [EVIDENCE_SHA256.tsv](qa_acoustic/EVIDENCE_SHA256.tsv) фиксирует текстовые evidence artifacts.
