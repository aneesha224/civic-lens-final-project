# Final Project Requirements Checklist

Source: course project requirements page, reviewed October 24, 2026.

## Target

Aim for Tier 2: a working, thoughtful, clearly differentiated app with measured token costs, a real safety defense, and evidence-backed report content. Tier 3 evidence—especially a real user test—is worth pursuing when practical.

## Required submissions

- [ ] GitHub repository link submitted on Canvas.
- [ ] `report.html`, self-contained, approximately 10–15 printed pages.
- [ ] `slides.html`, self-contained, no more than 10 slides, using reveal.js.
- [ ] Optional 2–3 minute demo video as a backup.

## App and repository

- [ ] App performs useful real work for a defined person or organization.
- [ ] Idea has a meaningful twist beyond overdone project types.
- [ ] App works end to end with real tools, data, and useful outputs.
- [ ] README explains setup and run steps clearly enough for a fresh clone.
- [ ] `.env.example` lists every required key without real values.
- [ ] No real `.env` file, API key, or secret is committed.
- [ ] App reads `.env` in its own folder first and the parent folder second.
- [ ] Uses exactly `PORTKEY_API_KEY` or `OPENAI_API_KEY` as applicable.
- [ ] Includes a small test dataset if production data is large.
- [ ] Fresh-clone dry run succeeds with the `.env` one folder above the repo.
- [ ] Teaching staff can get the app running within 10 minutes.

## Report sections, in order

- [ ] Title, author, repository/app links, and one-sentence description.
- [ ] Motivation and current cost of the problem.
- [ ] What is new, including named alternatives and honest comparison.
- [ ] Agents: roles, tools, organization diagram, models, rationale, and one real run with screenshots.
- [ ] Tokenomics: measured input/cached/output tokens, cost per run/user/month and at 100 and 10,000 users, cost controls, and performance tradeoffs.
- [ ] Safety: relevant attack and malfunction risks, overspending controls, and a working defense shown by screenshot or test.
- [ ] Impact: sourced numbers and ideally evidence from a real user.
- [ ] Limits and next steps.
- [ ] Screenshots and diagrams are embedded so the HTML works when double-clicked.

## Tier 2 evidence targets

- [ ] At least one real user or realistic user workflow tested.
- [ ] Real token counts captured from app runs, not estimates alone.
- [ ] Cost calculations documented and reproducible.
- [ ] At least one prompt-injection, malfunction, or cost-safety defense demonstrated.
- [ ] Screenshots show the app, agent steps, and safety defense working.
- [ ] Report and slides are polished, readable, and consistent with the app.

## Periodic audit

At each meaningful milestone, check this file, run the available tests, verify the README setup path, inspect the deliverables, and record unresolved risks in the project conversation or evidence folder.

## Important configuration note

The course page says the course key may use `gpt-6-luna` only, while the workspace instructions specify `gpt-5.6-luna` as the general default. For this course project, follow the course’s current model rule when using the course key; if the instructions conflict at implementation time, confirm with the instructor before spending tokens.

