---
name: Add a dataset
about: Propose an attack set, benign source, or indirect/structured set
title: "[dataset] <name>"
labels: dataset
---

**Dataset**
- Name / HuggingFace id:
- Type: [ ] direct attacks  [ ] benign (real traffic)  [ ] indirect / structured
- License:
- Gated? (needs HF access approval):

**Why add it?**
What does it cover that the current sets don't?

**Held-out?**
Confirm it isn't standard training data for the evaluated detectors (or note the caveat).

> Note: we store only scores + labels in results, never prompt text — so committing
> results never redistributes gated data.
