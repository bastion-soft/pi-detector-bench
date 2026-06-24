<!-- Thanks for contributing! See CONTRIBUTING.md. -->

## What does this PR do?
- [ ] Add a detector
- [ ] Methodology change / fix
- [ ] Add a dataset
- [ ] Docs / other

## Summary
<!-- What changed, and why. If it changes the ranking, call that out explicitly. -->

## Checklist
- [ ] `ruff check .` and `ruff format --check .` pass.
- [ ] If adding a detector: `models.yaml` entry + regenerated `results/*` + score files under `results/scores*/` (scores + labels only, no prompt text).
- [ ] Numbers reproduce from committed scores (`python -m scripts.rebuild_results_from_scores` shows 0 changed for unaffected rows).
- [ ] Interpretation is honest about weak spots (including where it doesn't win).
