---
name: Add a detector
about: Propose a prompt-injection detector to add to the leaderboard
title: "[detector] <model name>"
labels: detector
---

**Model**
- Name (for the tables):
- HuggingFace id:
- Params:
- `attack_label` (softmax index for "attack", or a list to sum):
- Gated? (needs HF access approval):

**Checklist**
- [ ] It's a standard `AutoModelForSequenceClassification` (no `trust_remote_code`).
- [ ] Publicly accessible on the HF Hub (gated is OK).
- [ ] I can run the harness and include result rows + scores, or I'm asking a maintainer to.

Anything else (links, paper, notes)?
