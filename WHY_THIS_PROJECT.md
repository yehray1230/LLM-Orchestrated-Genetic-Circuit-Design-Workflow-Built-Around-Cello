# Why This Project Exists

This project began in early 2026, when I became interested in a specific idea
behind OpenClaw-style agentic systems: an AI system does not have to work only
from user instructions. It can also continue from environmental feedback: tool
outputs, failed checks, intermediate artifacts, state changes, and scoring
signals.

That idea felt especially relevant to biological design. Many general-purpose
agent workflows struggle with long-context drift and hallucination. But some
early-stage regulatory-logic design tasks have a different shape: the context
can be relatively compact, while the logical density is high. Truth tables,
Boolean gates, Verilog, Cello compatibility, simulation outputs, sequence
checks, and benchmark scores can all become structured feedback for an
iterative workflow.

I wanted to explore whether that structure could make AI-assisted genetic
circuit design more auditable.

## Motivation

AI has obvious potential in biological design, but biological fluency can be
misleading. A model can produce confident language about promoters, logic
gates, expression, or plasmids even when the underlying evidence is incomplete.
For synthetic biology, that gap matters. A design is not useful simply because
it sounds plausible; it needs assumptions, constraints, failure modes, and
validation boundaries that a human researcher can inspect.

This project is my attempt to build around that concern. It does not treat an
LLM answer as the final design. Instead, it treats each candidate as something
to be translated, checked, simulated, scored, criticized, and revised.

## What I Chose To Build

The current prototype is an LLM-orchestrated computational workflow built
around Cello and related evaluation tools. It translates natural-language
regulatory logic intent into candidate circuit representations, then evaluates
those candidates with deterministic checks, simplified simulation, heuristic
scoring, and explicit claim boundaries.

The workflow is intentionally layered:

- natural-language intent is converted into structured assumptions;
- candidate logic is represented as truth-table expectations and
  Cello-compatible Verilog;
- Cello output is separated into mock workflow evidence versus externally
  mapped evidence;
- ODE simulation is treated as simplified screening, not calibrated in vivo
  prediction;
- benchmark scores are used as transparent heuristics, not biological proof;
- missing evidence and readiness blockers are surfaced instead of hidden.

Cello provides an important static logic-design reference point, but biological
design does not stop at static logic. Temporal behavior, burden, robustness,
part evidence, sequence constraints, and model assumptions all affect whether a
candidate deserves further attention. This project treats static logic as one
layer of evidence, not the whole design problem.

## The Hardest Part

The hardest part has been evaluation.

In a physical experiment, a design can eventually be judged by measurement. In
a computational prototype, deciding whether a candidate is "good" is much less
straightforward. Logic consistency, simulated dynamics, burden, robustness,
Cello compatibility, sequence evidence, and readiness all point at different
aspects of quality.

That is why I have spent significant effort on the scoring and readiness
layers. I do not want a single impressive-looking output to be mistaken for a
validated biological result. I want the system to show why a candidate looks
promising, where the evidence is weak, and what would need to be checked next.

## What I Am Not Claiming

This is not a one-shot genetic-circuit designer.

It does not claim to produce experimentally validated genetic logic gates. It
does not guarantee biological buildability. It does not replace expert review,
host-specific calibration, wet-lab construction, or measurement.

The current project is best understood as computational design assistance: a
way to make candidate generation, intermediate reasoning, scoring assumptions,
and biological uncertainty more visible.

## What I Hope This Becomes

My goal is for this project to become more than a toy demo. I hope it can grow
into a research-grade tool, or at least a useful prototype for discussing how
AI-assisted synthetic-biology workflows should be evaluated.

The next evaluation direction is to compare how different frontier models
perform on the same fixed design tasks, using the project's scoring and
readiness framework rather than relying on anecdotal single-run outputs. Those
results should be added only after the tasks, model settings, and evaluation
criteria are clear enough to be reported responsibly.

Longer term, I am interested in workflows where AI systems do not merely
generate biological designs, but help make the assumptions behind those designs
easier to inspect.

## Personal Note

I am an undergraduate life-science student building this as an independent
research prototype. I do not present it as a finished academic tool. I built it
as a serious way to learn through implementation, to practice making biological
claims carefully, and to seek feedback from researchers working closer to the
frontier.

What I hope this repository communicates is not that I already have all the
answers. It is that I am trying to approach the problem with seriousness,
technical effort, and respect for the gap between computational possibility and
biological evidence.
