# Evidence

Store screenshots, real-run traces, token counts, cost calculations, safety test results, and user-test notes here. Do not store credentials or private personal data.

## Tokenomics runs

`tokenomics_runs.json` records two completed real Civic Lens runs (speech-only and topic comparison), with token totals by agent and elapsed time. A preliminary setup request is disclosed in the log but excluded because its usage could not be recovered. Reproduce the measurements from the project folder with:

```sh
PYDANTIC_AI_NO_BANNER=1 .venv/bin/python scripts/measure_tokenomics.py
```

This makes paid model requests. The script records token counts returned by PydanticAI and estimates cost from the official [OpenAI API pricing table](https://developers.openai.com/api/docs/pricing) for `gpt-6-luna`. The estimate is not an Azure or Portkey invoice and excludes any separate gateway charges or tax. Cached input is included in input totals and separately priced. The scale scenario in `slides.html` assumes 10 monthly runs per user, split evenly between the two measured workflows, and scales linearly from one sample of each.

