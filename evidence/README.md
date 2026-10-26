# Evidence

Store screenshots, real-run traces, token counts, cost calculations, safety test results, and user-test notes here. Do not store credentials or private personal data.

## Local app capture

`civic_lens_public_transcript.png` is a genuine screenshot from the local Civic Lens app, captured October 26, 2026, after selecting Bernie Sanders’s complete 2025 Fighting Oligarchy rally transcript. It shows the source-linked reader and locally generated phrase/topic cues for the August 26, 2025 Chicago rally (<https://www.rev.com/transcripts/bernie-sanders-rally-in-chicago>). The app ran without an AI credential, so no model answer is shown; this is browsing evidence, not an agent-run screenshot or a user study. The same PNG is embedded in `report.html` and `slides.html`.

## Tokenomics runs

`tokenomics_runs.json` records two measurement batches (Oct 25, compact output; Oct 26, current briefing via OpenAI), each with (speech-only and topic comparison), with token totals by agent and elapsed time. A preliminary setup request is disclosed in the log but excluded because its usage could not be recovered. Reproduce the measurements from the project folder with:

```sh
PYDANTIC_AI_NO_BANNER=1 .venv/bin/python scripts/measure_tokenomics.py
```

This makes paid model requests. The script records token counts returned by PydanticAI and estimates cost from the official [OpenAI API pricing table](https://developers.openai.com/api/docs/pricing) for `gpt-6-luna`. The estimate is not an Azure or Portkey invoice and excludes any separate gateway charges or tax. Cached input is included in input totals and separately priced. The scale scenario in `slides.html` assumes 10 monthly runs per user, split evenly between the two measured workflows, and scales linearly from one sample of each.


## Prompt-injection test

`tests/test_prompt_injection.py` simulates a model that obeyed an instruction hidden in a transcript. Run it with `.venv/bin/python -m unittest discover -s tests -p 'test_prompt_injection.py'` and save the output here as `safety_prompt_injection.txt`.
