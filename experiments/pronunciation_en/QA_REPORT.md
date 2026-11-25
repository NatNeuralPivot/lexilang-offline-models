# Lexi Lang — Experimental Pronunciation Engine QA

Дата: 25 ноября 2026, Europe/Moscow. **Рекомендация: HOLD.**

Локальная воспроизводимая подготовка ресурсов прошла. Полный акустический inference не выполнен: ZIPA-backbone отсутствует. Готовность к iPhone, корректность фонемных оценок и калибровка на экспертной разметке не доказаны.

## Окружение и исходные ревизии

- Mac16,8, Apple M4 Pro, arm64, 24 GiB RAM; macOS 26.5.2 (25F84).
- Homebrew Python 3.14.7; также доступен Python 3.11.18, но runtime на нём не проверялся.
- Apple Swift 6.3.3, Xcode выбран через `/Applications/Xcode.app/Contents/Developer`; Git 2.43.2. Сборка приложения не запускалась.
- Private `NatNeuralPivot/lexipilot`: `e83dfb65bf7eb0f2e50c6460af8e188a8d562fd7`.
- Public `NatNeuralPivot/lexilang-offline-models`: `5ed887dd596b5640fca37321243d2b90157d72b6`.
- Оба checkout находятся на существующей `experiment/pronunciation-en-lexicon-calibration`. Новых веток нет.
- Pronunciada 1.1.0: закреплённый upstream `4619a298e5e2de927120122585683d18eda1f7c4`; upstream checkout чистый. SHA-256 ниже измерены локально; это не проверка подписи автора или независимого опубликованного checksum-манифеста.

## PASS / FAIL / BLOCKED

| Проверка | Итог | Фактический результат |
| --- | --- | --- |
| Mac / Python / Swift / доступ к обеим веткам | PASS | Две отдельные локальные копии, исходные SHA зафиксированы |
| `test_en_experiment.py` | PASS | 14/14; повторно 14/14 внутри bootstrap и при измерении |
| `bootstrap_local.sh` | PASS | Exit 0, скачан закреплённый исходный код, подготовлено 24 ресурса |
| Все 24 SHA-256 и размеры | PASS | Штатный verifier и отдельное сравнение source ↔ candidate ↔ inventory |
| Воспроизводимость | PASS | Новая сборка в другом каталоге: все 24 файла и inventory побайтово идентичны |
| Полное чтение gzip / NPZ | PASS | Оба gzip прочитаны до EOF; все массивы 12 NPZ загружены с `allow_pickle=False` |
| Словарь EN | PASS | 126 052 ключа, 134 497 вариантов, 8 445 сверх основного; дубликатов нет |
| Доступность runtime-зависимостей на этом Mac | PASS | Бинарные arm64 wheels разрешены и установлены в отдельный QA virtualenv |
| Загрузка двух малых ONNX-графов | PASS | `seqhead_en.onnx` и `stress_v3.onnx`, CPUExecutionProvider; без вызова graph inference |
| Английский аудиовход / fbank | PASS | 3 лицензированных MP3 декодированы в float32 mono 16 kHz, рассчитаны конечные признаки [T,80] |
| Полный акустический inference ZIPA | BLOCKED | Нет fp32/int8 backbone в штатном кэше или заданного override; веса не загружались |
| Smoke test на 5–10 EN-записях | BLOCKED | Есть только 3 EN-примера upstream и нет backbone; 0 записей оценено акустически |
| Full ↔ trimmed scoring parity | BLOCKED | Нужны backbone и записи; не запускалась |
| Человеческая валидация / перекалибровка | BLOCKED | Не предоставлены экспертные акустические метки, отдельные speakers/train/test и B2–C2 adult holdout |
| Лицензии и разрешение на распространение | BLOCKED | Нерешённые stress_v3 share-alike вопросы и полный комплект notices |
| iPhone / Core ML / ONNX parity | BLOCKED | Нет native scorer-порта, конвертации или замеров на физическом устройстве |

Начальный вызов `Scorer("en")` системным Python закончился `ModuleNotFoundError: onnxruntime`. После изолированной установки зависимости импортируются и два малых графа загружаются. Это устраняет проблему окружения, но отсутствие backbone остаётся. Ошибок экспериментальных скриптов на выполненных проверках не выявлено; итераций исправления кода **0 из 2**. Это не исчерпывающий аудит всех возможных входов.

## Сколько файлов действительно собрано

**24 исходных ресурса, 5 619 307 байт**: 22 scoring-ресурса upstream и 2 EN lexicon/LTS. Дополнительно создан `candidate_inventory.json`: 25 файлов внутри одного candidate-каталога, из них 24 assets. Повторная проверочная копия содержит те же 24 ресурса и не считается ещё 24 уникальными файлами. Новые словари или калибровочные коэффициенты не обучались: скопированы upstream-ресурсы.

- EN gzip: 126 053 строки, включая строку метаданных; 134 413 вариантов имеют маркер ударения.
- LTS gzip: 26 260 строк контекстных правил; это не 26 260 слов словаря.
- Состав: 12 NPZ, 7 JSON, 2 ONNX, 2 gzip и 1 token list.
- Все пути, размеры, SHA-256 и заявленные лицензии: [RESOURCE_SHA256.tsv](qa/RESOURCE_SHA256.tsv), [candidate_inventory.json](qa/candidate_inventory.json).
- В `phone_dist.npz/dist` есть 5 906 NaN: upstream определяет их для неразбираемых модификаторных токенов (`features.py:token_distance`). В threshold-массивах `sound_E` и `sound_U` суммарно 7 Inf — допустимые пороги деревьев/листьев, согласованные с `calibrate.py`. Они не заменялись нулями и не объявлялись повреждением. Сам факт чтения массивов не доказывает корректности акустического scoring.

## Зависимости и лицензии

Для builder/verifier/audit достаточно стандартной библиотеки Python; глобальный NumPy 2.5.3 использован для отдельной проверки NPZ. Runtime проверен в `runtime-venv`, системные пакеты не менялись:

| Компонент | Проверенная версия | Заявленная лицензия / ограничение |
| --- | --- | --- |
| NumPy | 2.5.5 | BSD-3-Clause; учитывать также bundled native libraries |
| ONNX Runtime | 1.32.0 | MIT; CPU реально загрузил оба малых графа |
| kaldi-native-fbank | 1.23.3 | Apache-2.0 по upstream licensing audit |
| SoundFile | 0.14.0 | BSD-3-Clause; связанный libsndfile 1.2.2 — LGPL-2.1 по upstream audit |
| Pronunciada code | pinned 1.1.0 | Apache-2.0; bundled data имеет отдельные лицензии |
| EN lexicon / LTS | pinned assets | CMUdict-derived, BSD-2-Clause-style, notices/атрибуция |
| ZIPA token list / отсутствующий backbone | pinned tokens | CC BY 4.0 по upstream; `-ns-` варианты не использовались |

Полный замороженный список десяти установленных пакетов: [runtime-requirements.txt](qa/runtime-requirements.txt). Проверка совместимости wheels и загрузки не заменяет аудит лицензий всех транзитивных бинарных компонентов.

Два явно помеченных upstream hold: `prosody/stress_v3.json`, `prosody/stress_v3.onnx`. Модели обучены в том числе на целях из IT/PT/RU CC BY-SA lexicons; upstream оставляет классификацию производных работ открытой. У `stress_v3.zemb.npz` описано то же происхождение, хотя его флаг `share_alike_question=false`: его тоже следует включить в юридическое рассмотрение, а не считать автоматически разрешённым.

До распространения нужны согласованные лицензии каждого artifact, полные LICENSE/NOTICE и атрибуции ZIPA, CMUdict, FLEURS, speechocean762; отдельно уточнить расхождение обозначений лицензии speechocean762 у OpenSLR и HF, отмеченное upstream. Здесь приведены декларации закреплённого upstream, а не юридическое одобрение. Новые сборы данных или обучение не выполнялись.

## Реальная возможность запуска на Mac

Этот Mac может загрузить runtime и малые ONNX-головы, декодировать MP3 и выполнить fbank. Изолированная установка не включала backbone и не запускала авто-download из `Scorer`. В исходном окружении `onnxruntime`, `kaldi-native-fbank`, `soundfile` отсутствовали.

`~/.cache/pronunciada` отсутствует; `model_cached(int8/fp32)` возвращает false; `PRONUNCIADA_CACHE` и `PRONUNCIADA_BACKBONE` не заданы. В HF-кэше есть Kokoro, но нет ZIPA — другая модель не является заменой. В upstream девять MP3, из них английских только три:

| Запись | Длительность | Fbank | Decode + resample + fbank |
| --- | ---: | --- | ---: |
| en-clean.mp3 | 2.211 s | [221,80] | 0.0029 s |
| en-learner-1.mp3 | 3.070 s | [307,80] | 0.0033 s |
| en-learner-2.mp3 | 3.999 s | [400,80] | 0.0047 s |

Это held-out test-split speechocean762 clips, CC BY 4.0 по `site/samples/ATTRIBUTION.md`; только локальная обработка. Остальные шесть имеют другие языки и не подменяют EN smoke sample. Личные записи пользователя не использовались; Kokoro TTS не выдавался за речь учащихся. Upstream JSON с готовыми score не использовались как наши результаты. **Реальных фонемных оценок получено 0.**

ORT сообщает доступность CoreMLExecutionProvider, но он не использовался; это не доказательство работы Core ML или iPhone.

## Измеренное время и память

| Проверка | Wall time | Peak RSS |
| --- | ---: | ---: |
| Bootstrap с загрузкой upstream | 31.11 s | 87.15 MiB |
| public-tests-measured | 0.1636 s | 33.00 MiB |
| verify-measured | 0.0536 s | 26.92 MiB |
| rebuild-measured | 0.2759 s | 40.61 MiB |
| lesson-audit-native | 0.1591 s | 53.94 MiB |
| lesson-audit-all-json | 0.1754 s | 53.61 MiB |
| lesson-audit-advanced | 0.0825 s | 35.05 MiB |
| Runtime probe: imports + 2 ONNX load + 3 audio/fbank + OOV targets | 4.2273 s | 84.34 MiB |

Bootstrap измерен `/usr/bin/time -l` вне sandbox; прочие CLI — `perf_counter` + `os.wait4` per child, runtime probe — `getrusage(RUSAGE_SELF)`. На macOS `ru_maxrss` указан в байтах; таблица пересчитана в MiB. Это единичные замеры, без статистического latency benchmark. Первые sandbox-вызовы `time -l` не смогли прочитать `kern.clockrate` и вернули instrumentation error после успешных скриптов; для итоговой таблицы использованы отдельные успешные измерения. RSS runtime probe **не** является потреблением памяти полного acoustic engine. End-to-end latency, батарея и iPhone RAM не измерены.

## Что нужно для iPhone / Core ML / ONNX

Это список будущих условий, **не разрешение на их выполнение в этом QA**:

1. Закрепить ревизию, SHA-256, лицензию и notices полного ZIPA-backbone; проверить загрузку и 5–10 отдельных лицензированных EN recordings с реальными target transcripts. По upstream `docs/LICENSING.md`, веса примерно 67 MB int8 / 248 MB fp32; локально они отсутствуют, размеры не измерялись.
2. Портировать или связать совместимый ONNX runtime, 16 kHz mono audio, Kaldi-compatible 80-bin fbank и нужные промежуточные encoder outputs. Одного CTC transcript недостаточно: seqhead требует enc0–enc5/final и дополнительные признаки.
3. Сохранить нормализацию чисел, сокращений, апострофов, варианты EN, LTS, ударение, CTC alignment, adapter, sound/word/sentence/prosody calibration. Восстановить ожидаемые runtime paths из flat assets. Эти 24 файла не являются самостоятельным готовым движком.
4. Для Core ML отдельно подтвердить конвертацию операторов/форм/precision и численную эквивалентность. Наличие CoreML provider на Mac не заменяет эту проверку.
5. Сравнить full Python ↔ trimmed EN ↔ native outputs и ошибки на тех же записях, затем проверить физический iPhone: cold/warm latency, peak RAM, длительные записи, offline и батарея. Проверить false positives и экспертно размеченные B2–C2 samples. Не подменять это ASR confidence или совпадением транскрипции.
6. Только после отдельного разрешения рассматривать адаптер к существующему `LexiAcousticScorer`; текущую архитектуру/SwiftUI/Audio/Kokoro/ReaderKit и уроки не менять. В закреплённом README upstream нет iOS build.

## Решение и пределы QA

**HOLD**: сборщик ресурсов годится для дальнейшего контролируемого исследования, но оснований для готового pronunciation scorer, интеграции или распространения пока нет. Не REJECT: детерминированная сборка, словарь и runtime prerequisites прошли. Не GO: backbone, EN acoustic smoke, лицензии, native parity и экспертная оценка заблокированы.

Коммитятся только отчёты и текстовые QA evidence. `main` не изменялся и не мёржился; дополнительных веток, весов, GitHub Releases, app builds, полного regression suite и обучения не было. Основной checkout с незакоммиченным `Native/LexiPilotApp.swift` не редактировался. После сохранения отчёта работа остановлена.

## Источники и воспроизведение

Исходники/лицензии относятся только к pinned commit:

- [Pronunciada source](https://github.com/moglearn/pronunciada/tree/4619a298e5e2de927120122585683d18eda1f7c4).
- [LICENSING.md](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/docs/LICENSING.md), [runtime inventory](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/pronunciada/data/LICENSES_SHIPPED.json), [sample attribution](https://github.com/moglearn/pronunciada/blob/4619a298e5e2de927120122585683d18eda1f7c4/site/samples/ATTRIBUTION.md).
- [Unit-test log](qa/public-tests-measured.log), [bootstrap log](qa/bootstrap-initial.log), [runtime probe](qa/runtime-probe.json).

В public checkout выполнены `python3 experiments/pronunciation_en/test_en_experiment.py`, `bash experiments/pronunciation_en/bootstrap_local.sh`, `verify_en_candidate.py --candidate ...`; отдельная сборка `build_en_candidate.py --pronunciada ... --out ...` сравнена побайтово. `lesson_lexicon_audit.py --candidate ... --lessons-json ... --out ...` запускался отдельно на Native JSON, на всех найденных prompt-bearing JSON и на двух advanced packs. Повторные проверки касались только этого эксперимента.

## Аудит уроков и отсутствующие слова

PASS выполнения `lesson_lexicon_audit.py` на локальных JSON private-репозитория; обнаружены OOV, включая B2–C2. Проверены Native resources, дополнительные docs packs и два advanced packs. Частоты повторяющихся prompts отдельно отмечены в полном отчёте. LTS/normalization front-end формирует непустые target phones для всех обнаруженных OOV; фонетическая правильность этих целей не подтверждена.

Списки слов, пути lesson JSON, hashes, точные per-level counts и scope limitations сохранены только в [полном private QA_REPORT.md](https://github.com/NatNeuralPivot/lexipilot/blob/experiment/pronunciation-en-lexicon-calibration/AssessmentKit/Experiments/PronunciationEN/QA_REPORT.md) и его приложениях. Они не переносятся из private в public repository. Coverage — только exact dictionary lookup по prompt fields, не pronunciation accuracy и не аудит всех полей урока.
