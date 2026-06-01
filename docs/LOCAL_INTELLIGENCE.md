# Local Intelligence Module

`local_intelligence/` is the V2.02 backend enhancement layer.
It does not change the UI. It works behind the scenes before the current
retrieval / AI generation flow.

## What it does

- Intent classification
- Entity extraction
- Reply quality scoring
- Sample expansion
- Dynamic prompt building

## Typical flow

1. Read the user query.
2. Analyze intent and entities.
3. Score and expand the most relevant samples.
4. Build a prompt that matches the query type.
5. Send the enriched context into the existing retrieval / AI pipeline.

## Python usage

```python
from local_intelligence import IntelligenceManager

manager = IntelligenceManager()
analysis = manager.analyze("课程多少钱", [
    "课程费用2980元，包含30课时。",
    "基础班1980元，适合入门。",
])

print(analysis.summary["intent"])
print(analysis.prompt["system_prompt"])
```

## Other helpers

```python
prompt = manager.build_context_enriched_prompt("课程多少钱", ["上一轮对话"])
best_sample, score, intent = manager.get_best_sample("课程多少钱", [
    "课程费用2980元，包含30课时。",
    "基础班1980元，适合入门。",
])
expanded = manager.expand_samples_for_intent("price", ["课程费用2980元，包含30课时。"])
```

## Integration note

The current app uses the intelligence layer through the preview adapter and
unified inference engine. If the module is unavailable, the app falls back to
the previous behavior automatically.
