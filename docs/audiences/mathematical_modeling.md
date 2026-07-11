# Audience Guide: Mathematical and Systems Modeling

## Why this audience may care

The modeling layer is intended as a transparent diagnostic and comparative
lens. It asks whether simplified equations and explicit assumptions can help an
AI-assisted workflow identify likely bottlenecks and missing evidence without
claiming quantitative cellular prediction.

## Questions to examine

- What are the state variables, equations, units, and boundary conditions?
- Which parameters are defaults, literature-derived, UCF-derived, fitted, or
  user supplied?
- Which outputs are identifiable or comparable under the available data?
- Where do deterministic, stochastic, temporal, and perturbation models diverge?
- Which conclusions remain stable under parameter and model uncertainty?

## Relevant implemented paths

- reduced resource-aware ODE screening;
- bounded Gillespie-style stochastic audits with truncation metadata;
- temporal inputs, parameter sweeps, and simplified bifurcation reports;
- Monte Carlo perturbation and versioned scoring configurations;
- explicit null or not-evaluated domains when evidence is unavailable.

## Current modeling boundary

The equations and default parameters are project-specific computational
screening assumptions. They are mostly uncalibrated and are not a complete
chemical reaction network, host-cell model, or predictor of in vivo expression.

## Open research direction

The planned multi-layer resource-accounting model would connect DNA copy-number
and promoter context, RNAP demand, RNA turnover, ribosome demand, protein
maturation/degradation, and growth-dilution feedback. Its intended output is a
diagnostic decomposition of assumptions and bottlenecks—not a virtual cell or
digital twin.

## Open contribution surfaces

- parameter provenance and dimensional consistency review;
- structural and practical identifiability analysis;
- calibrated host-specific parameter sets;
- global sensitivity and uncertainty quantification;
- comparison against measured reference circuits;
- model-selection criteria for deciding when added complexity is justified.

## Start with these files

1. [Model assumptions](../model_assumptions.md)
2. [Evaluation metrics](../evaluation_metrics.md)
3. [Future roadmap](../future_roadmap.md)
4. [ODE implementation](../../src/tools/ode_simulator.py)
5. [Readiness evaluator](../../benchmark_suite/readiness_evaluator.py)

## Claims the assistant must not make

Do not call the current model mechanistically complete, calibrated, predictive,
whole-cell, or a digital twin. Do not interpret heuristic scores as likelihoods
of experimental success.
