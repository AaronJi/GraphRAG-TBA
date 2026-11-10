# GraphRAG-TBA: Code, Derived Data, and Experimental Outputs

This repository provides a quick way to reproduce the TBA pipeline. The paper
uses **Llama-3.3-70B-Instruct** for indexing and querying, and **GPT-4o** for
association, behavior, and response scoring. This reproduction uses
**MiniMax-Text-01** for association scoring, indexing, and querying. Offline
replay computes the expected-behavior rate from saved choices and dataset labels.

This release covers **Maslow**. The bundled **100 cases** form a subset of the
Maslow test set for quick replay from saved intermediate files. The cases also
appear in the historical indexing corpus. Other experimental settings are
pending.

## Quick start

Use Python 3.11 and run these commands from the repository root.

```sh
python -m pip install -r requirement.txt
python replay.py
```

Replay reads the saved level-0 community reports, skills, and A/B predictions
from `output/`. It verifies the association threshold $\tau=70$, reapplies
the skill threshold $\epsilon=70$ and $K=3$, and compares Direct and TBA on the
same 100 cases without API calls. The saved run yields **58/100 for Direct** and
**67/100 for TBA**, a difference of 9 percentage points.

## Project layout

- `input/dilemma_actions.jsonl` holds 2,720 action records from 1,360 historical
  DailyDilemmas cases, with ordered value names and their aligned Maslow labels.
- `input/seed_principles.json` contains the 10 Maslow principles, and
  `input/evaluation_cases.jsonl` contains the 100 evaluation cases.
- `prompts/` holds the association, indexing, and two-stage query prompts.
- `settings.yaml` is the native GraphRAG 0.5.0 configuration.
- `output/` holds the historical association scores, index tables, skills,
  predictions, and rates.

## Live setup

Indexing and online querying require an OpenAI-compatible endpoint serving
`MiniMax-Text-01`. Set `GRAPHRAG_API_KEY` in the environment or in `.env`.
The bundled `.env` contains a placeholder. Both scripts use the `llm` section
in `settings.yaml` for the endpoint and model.

## Index

```sh
python index.py
```

The script expands each action into its annotated values and uses the saved
association scores to retain principles at $\tau=70$. It assembles the 4,326
historical index documents in memory, passes them to the native GraphRAG 0.5.0
pipeline, and writes the new index to `output/YYYYMMDD-HHMMSS/`.
Use `python index.py --dry-run` to validate the input and configuration
without model calls.

## Online query

```sh
python query.py
python query.py --index-dir output/YYYYMMDD-HHMMSS
```

The first command uses the historical index in `output/`. The second selects
a new index. Both run Direct and TBA on the bundled test subset. The TBA query
generates and scores one skill per level-0 community report, then uses up to
three eligible skills for its final choice. New skills, predictions, and rates
are saved in `output/query/`.
