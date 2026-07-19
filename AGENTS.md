# Project Instructions

## Mission

This repository researches how game primitives, grammar, mechanics, gameplay patterns, and concrete games relate, with the long-term goal of producing the Chinese-language book *游戏原语 (Game Primitives)*.

Use this working model unless a document explicitly argues for a revision:

```text
Primitive --grammar--> Mechanic --orchestration--> Gameplay Pattern --instantiation--> Game
```

Treat the model as a research hypothesis, not a settled fact.

## Language And Style

- Write reader-facing material primarily in Simplified Chinese.
- Give the English term on first use when it improves precision or discoverability.
- Prefer plain explanations and concrete game examples before formal notation.
- Aim for an accessible book without sacrificing definitions, evidence, counterexamples, or uncertainty.
- Do not inflate a list of related words into a taxonomy. Explain types, roles, preconditions, effects, timing, information, and composition.

## Research Discipline

- Label project definitions, literature-derived claims, working hypotheses, and open questions distinctly.
- Preserve source metadata and page or section locators whenever available.
- Test abstractions against examples from different eras, platforms, cultures, player counts, and game families.
- Record counterexamples and ambiguous cases; do not force every game into the current model.
- Avoid claims such as “all,” “minimal,” or “complete” unless the scope and argument are explicit.
- Keep primitive, mechanic, gameplay pattern, genre label, and complete game conceptually separate.

## Repository Layout

- `book/`: outline and manuscript chapters.
- `theory/`: definitions, ontology, grammar, notation, and formal models.
- `catalog/`: structured primitive, mechanic, gameplay-pattern, and game analyses.
- `research/`: sources, literature notes, evidence, and unresolved questions.
- `.codex/`: repository-specific Codex workflow configuration.

When scope or structure changes, update `README.md` or the relevant book/research document in the same change.
