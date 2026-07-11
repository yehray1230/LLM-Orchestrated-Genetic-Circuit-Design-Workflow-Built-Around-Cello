# Cold Outreach Packet

Purpose: prepare a small first-wave outreach package for presenting the current
project as a `0.x research preview`, not as a finished synthetic-biology CAD
tool.

Use this packet before sending cold emails to synthetic-biology,
computational-biology, Cello, genetic-circuit-design, or AI-assisted scientific
design contacts.

## One-Sentence Framing

This is an LLM-orchestrated computational design-assistance workflow built
around Cello that translates natural-language regulatory-logic intent into
candidate genetic-circuit representations, then ranks and critiques those
candidates using simplified simulation and heuristic evaluation.

## What To Ask For

Use one request per email:

```text
Would this computational design-assistance framing be useful or misleading for
early genetic-circuit design discussions, and what evidence would you expect to
see before taking the workflow seriously?
```

Avoid asking for collaboration, endorsement, funding, and detailed technical
review in the same first message.

## First-Wave Audience

Start with 3-5 recipients in one audience type so the feedback is comparable.

Good first-wave targets:

- researchers or students familiar with genetic circuit design;
- computational biology researchers interested in AI-assisted workflows;
- synthetic biology CAD or Cello-adjacent users;
- advisors, lab alumni, or near-network contacts who can give blunt feedback.

Defer broad outreach until after the first replies identify whether the framing
is clear.

## Flagship Demo

Use one stable flagship case:

```text
Activate GFP only when input A is present and input B is absent.
```

Short logic:

```text
A AND NOT B -> GFP
```

The demo packet should show:

- natural-language intent;
- structured design specification;
- truth table or logic matrix;
- Cello-compatible Verilog;
- `cello_mode`, `cello_claim_level`, `cello_warning`, and `mapping_status`;
- ODE or simulation summary, if available;
- benchmark or readiness summary;
- export artifacts or explicit export blockers;
- limitations and next checks.

## Do Not Claim

Do not claim that the project:

- designs complete plasmids end to end;
- guarantees biological buildability;
- validates genetic logic gates experimentally;
- predicts in vivo expression quantitatively;
- makes mock Cello output equivalent to external Cello mapping;
- replaces expert synthetic-biology review;
- provides wet-lab-ready protocols, primers, or ordering instructions.

## Pre-Send Gate

Send the first wave only when all required items are true:

- [ ] `README.md` gives the correct `0.x research preview` framing.
- [ ] `QUICKSTART.md` can get a new reader to the primary local interface.
- [ ] `docs/limitations.md` clearly states safe claims and claims to avoid.
- [ ] Case 01 has at least one current run summary or an explicit "pending"
      status that is not overstated.
- [ ] The email links to a repo, demo artifact, screenshot, or short summary
      that can stand alone.
- [ ] Mock Cello and external Cello are visibly separated.
- [ ] Test or demo evidence has been generated recently, or the email says the
      demo is a preview and asks for framing feedback rather than evaluation of
      validated results.
- [ ] The first email has one clear call to action.

## Evidence Commands

Run these before claiming the current checkout is locally verified:

```powershell
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe -m src.scripts.generate_demo_baseline --timeout-seconds 60
```

If a full run is too slow for the first preparation pass, run a narrower smoke
check and record that limitation:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_demo_baseline_freeze.py tests\test_readiness_evaluator.py -q
.\venv\Scripts\python.exe -m src.scripts.generate_demo_baseline --timeout-seconds 60
```

Recommended evidence folder:

```text
outputs/mvp_validation/<YYYY-MM-DD>_<commit>/
```

Keep generated evidence local unless a specific artifact is intentionally
prepared for sharing.

## Email Draft

Subject options:

```text
Feedback request: LLM-assisted genetic-circuit design research preview
Question on computational genetic-circuit design workflow
```

Draft:

```text
Hi <Name>,

I am working on a 0.x research preview of an LLM-orchestrated computational
design-assistance workflow for genetic regulatory circuits. The current
prototype translates natural-language regulatory-logic intent into structured
design candidates, Cello-compatible Verilog, simplified simulation/readiness
evidence, and explicit limitation reports.

The safest summary is: it is a computational screening and workflow prototype,
not a complete plasmid-design platform and not wet-lab validation.

One flagship example is:

  Activate GFP only when input A is present and input B is absent.
  A AND NOT B -> GFP

I would be grateful for a quick framing check: does this kind of tool look
useful for early genetic-circuit design discussion, or does the current framing
risk overstating what the evidence can support?

Project: <repo or summary link>

Thank you,
<Your name>
```

## Follow-Up Tracker

Use this table for the first wave.

| Contact | Audience type | Sent date | Ask | Reply | Follow-up |
| --- | --- | --- | --- | --- | --- |
|  |  |  | Framing check |  |  |

## After Five Emails

Pause after 3-5 first-wave emails and sort feedback into:

- unclear framing;
- missing evidence;
- overclaim risk;
- demo usability issue;
- genuinely interesting next opportunity.

Do not expand the audience until the first-wave feedback has been folded into
the README, demo summary, or email wording.
