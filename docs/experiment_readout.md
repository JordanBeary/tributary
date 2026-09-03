# Experiment read-out: the nurture holdout

Status: v1.0, 2026-09-01 · Numbers from `models/out/experiment_power.json` (script `models/experiment_power.py`), which recomputes them from `analysis/dashboards/data/06_uplift.json`, `simulation/params/uplift_params.json`, `analysis/dashboards/data/derived_figures.json`, and the `fct_marketing_contacts` mart
Provenance: A

## The question

Does pre-submission nurture messaging cause more people to apply, and if so, whom should the program message? The marketing silo can only see click lift; the application and revenue outcomes live in the CRM and the auction lake and reach the experiment only through resolved identity.

## The design

Intention-to-treat. Contacts were randomized at acquisition within engagement segment, 85% treated and 15% holdout; holdout contacts received no messages. Treated 729,856, holdout 128,797. The outcome is whether the contact became an applicant within the year; revenue per contact is the secondary outcome. Assignment is balanced across acquisition channels (dashboard 06, balance panel).

## The read

- Application-rate lift: **+0.109pp** (treated 84.57%, holdout 84.46%), standard error 0.109pp, 95% CI **-0.105pp to +0.324pp**. The simulator injected +0.115pp. The point estimate lands on the injected effect; the interval spans zero.
- Revenue lift per contact: **-$0.99**, 95% CI -$3.64 to +$1.66. Revenue per contact is dominated by who the contact is, not by whether they were messaged.
- The effect is concentrated by construction in engagement segment 5 (injected +0.521pp; the other four segments are below +0.02pp). Segment 5's empirical lift is **+0.367pp**, 95% CI -0.094pp to +0.828pp, on 166,248 contacts.

The honest summary: consistent with the injected effect, not proven by this sample.

## Why it is underpowered, in numbers

Two-proportion z-test, two-sided alpha 0.05, 80% power, control application rate 84.46%:

| To detect | Allocation | Contacts needed | Have |
| --- | --- | --- | --- |
| Pooled +0.115pp | 85/15 (as run) | **6,083,863** (7.1x the sample) | 858,653 |
| Pooled +0.115pp | 50/50 | 3,096,165 | 858,653 |
| Pooled +0.115pp | 85/15, 90% power | 8,144,567 | 858,653 |
| Segment 5 +0.521pp | 85/15 | 266,126 | 166,248 |
| Segment 5 +0.521pp | 50/50 | 134,179 | 166,248 (but already assigned) |

Minimum detectable pooled effect at the sample in hand: **0.307pp**, nearly three times the injected effect. The experiment was never going to establish the level; it can establish the ranking.

## Decision rule

1. Do not claim a pooled application or revenue lift for the nurture program. Any level statement waits for a sample the size above.
2. Act on the ranking, which two independent reads agree on: the naive per-segment arm difference and the cross-fitted T-learner (`models/cards/model_4_uplift.md`) both put segment 5 first, and response-model targeting scores below random. The send policy is **message segment 5; stop messaging segments 1-4**.
3. Value of the policy at the injected effect: about **866 incremental applicants a year** from segment 5, worth about **$249,519** of auction revenue (3.3 applications per applicant x $87.18 per application). Messaging segments 1-4 is worth about $27,375 a year at their injected uplift. The material gain is cost avoidance: **1,766,645 messages** to 588,545 contacts a year whose uplift is indistinguishable from zero. The per-message send cost is not in any silo; marketing supplies it and the avoided cost prices itself.

## The follow-up test

A test sized for the segment-5 effect rather than the pooled one. Segment 5 accrues about 13,854 new contacts a month.

- At the current 85/15 split: 266,126 contacts, about **19 months** of segment-5 acquisition.
- At 50/50: 134,179 contacts, about **10 months**. Recommended: the holdout costs nothing in this program (holdout contacts receive no messages and apply at the same rate), so a larger control arm is nearly free.
- Guardrail: monitor segments 1-4 unmessaged for a quarter; if their application rate falls by more than the MDE of that sample, resume and re-test.
- If the marketplace can only run one experiment this quarter, run the floor test (strategy memo) first: its expected value is two orders of magnitude larger.

## What transfers

The power arithmetic and the decision rule transfer to any real program. The specific effect sizes do not: they were injected from Criteo-scale uplift (calibration spec Section 3), which is realistic in being small, not in being this marketplace's.
