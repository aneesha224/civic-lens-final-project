# Final Project Requirements Checklist

Source: course project requirements page, reviewed October 24, 2026.

## Target

Aim for Tier 2: a working, thoughtful, clearly differentiated app with measured token costs, a real safety defense, and evidence-backed report content. Tier 3 evidence—especially a real user test—is worth pursuing when practical.

## Required submissions

- [ ] GitHub repository link submitted on Canvas. (Push the final commit first.)
- [x] `report.html`, self-contained, approximately 10–15 printed pages. (11 page sections; CSS and app capture are inline.)
- [x] `slides.html`, self-contained, no more than 10 slides, using reveal.js. (Nine slides; Reveal.js 5.1.0 and its CSS are bundled inline.)
- [ ] Optional 2–3 minute demo video as a backup. (Optional; not created.)

## App and repository

- [x] App performs useful real work for a defined person or organization. (Supports students, journalists, and civic researchers tracing public political language.)
- [x] Idea has a meaningful twist beyond overdone project types. (Keeps legislative and non-legislative source collections distinct while linking selected text to earlier citations.)
- [x] App works end to end with real tools, data, and useful outputs. (Two real model-run traces are saved; a local transcript-reader workflow was captured.)
- [x] README explains setup and run steps clearly enough for a fresh clone.
- [x] `.env.example` lists the supported credential keys without real values.
- [x] No real `.env` file, API key, or secret is committed. (The tracked environment file is `.env.example`.)
- [x] App reads `.env` in its own folder first and then searches parent folders. (`load_dotenv()` is called before requests need credentials.)
- [x] Uses `PORTKEY_API_KEY` or `OPENAI_API_KEY` for model credentials.
- [x] Includes a small test dataset under `data/test/`.
- [ ] Fresh-clone dry run succeeds with the `.env` one folder above the repo.
- [ ] Teaching staff can get the app running within 10 minutes.

## Report sections, in order

- [x] Title, author, repository/app links, and one-sentence description.
- [x] Motivation and current cost of the problem. (The report describes workflow burden and explicitly says time savings have not been measured.)
- [x] What is new, including named alternatives and honest comparison.
- [x] Agents: roles, tools, organization diagram, models, rationale, and one real run with screenshots. (Four-step Rubio run with AI briefing screenshots; topic-comparison step not captured.)
- [x] Tokenomics: measured input/cached/output tokens, cost per run/user/month and at 100 and 10,000 users, cost controls, and performance tradeoffs.
- [x] Safety: relevant attack and malfunction risks, overspending controls, and a working defense shown by a credential-free test.
- [x] Impact: sourced corpus and model-run numbers. (No real-user outcome study is claimed.)
- [x] Limits and next steps.
- [x] A genuine app screenshot and inline diagrams are embedded; the slide deck has no external runtime assets.

## Tier 2 evidence targets

- [ ] At least one real user or realistic user workflow tested.
- [x] Real token counts captured from app runs, not estimates alone.
- [x] Cost calculations documented with formulas and source pricing.
- [x] Exact-quotation filtering is demonstrated by the saved credential-free safety test output.
- [x] Screenshots show the app and agent steps; safety defenses shown by two passing tests (quote guard, prompt injection).
- [x] Report and slides are consistent with the app’s source scope and current UI.

## Periodic audit

At each meaningful milestone, check this file, run the available tests, verify the README setup path, inspect the deliverables, and record unresolved risks in the project conversation or evidence folder.

## Remaining gaps (Oct 26)

- No real user test (Impact capped at half credit without it).
- Topic-comparison run not screenshotted; safety-auditor verdict not shown in UI.
- Fresh-clone dry run with `.env` one folder up not performed.
- Token measurements predate the richer briefing and higher limits.

## Important configuration note

The course page says the course key may use `gpt-6-luna` only, while the workspace instructions specify `gpt-5.6-luna` as the general default. For this course project, follow the course’s current model rule when using the course key; if the instructions conflict at implementation time, confirm with the instructor before spending tokens.

