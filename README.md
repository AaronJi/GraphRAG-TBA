# GraphRAG-TBA: Code, Derived Data, and Experimental Outputs

This repository provides a quick way to reproduce the TBA pipeline. The paper
uses **Llama-3.3-70B-Instruct** for indexing and querying, and **GPT-4o** for
association, behavior, and response scoring. The live index and query scripts
use **GPT-5.6 Luna** through the OpenAI API.

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
same 100 cases without API calls. In a previous reproduction run, TBA's
expected-behavior rate exceeded that of the Direct baseline by
**9 percentage points**.

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

Set `OPENAI_API_KEY` in your environment or in a `.env` file at the repository
root. Replace the placeholder with a key from a project that can use
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

Both scripts read the endpoint and model from the `llm` section in
`settings.yaml`. They call OpenAI Chat Completions with `reasoning_effort=none`.

## Index

```sh
python index.py
```

The script expands each action into its annotated values and uses the saved
association scores to retain principles at $\tau=70$. It assembles 4,326
documents in memory and passes them to GraphRAG 0.5.0. The pipeline uses GPT
for entity and relationship extraction, description summarization, and
community reports, then writes the new index to `output/YYYYMMDD-HHMMSS/`.
Use `python index.py --dry-run` to validate the input and configuration
without model calls.

## Online query

```sh
python query.py
python query.py --index-dir output/YYYYMMDD-HHMMSS
```

The first command uses GPT with the historical index in `output/`. The second
uses GPT with the newly built index. Both run Direct and TBA on the bundled test
subset. The TBA query generates and scores one skill per level-0 community
report, then uses up to three eligible skills for its final choice. New skills,
predictions, and rates are saved in `output/query/`.
