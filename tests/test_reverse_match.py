"""Verify: do the reply contents actually belong to the displayed parent question?"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.getcwd())

from preview_mode import PreviewModeManager

pm = PreviewModeManager("data/local_data.json")

# Load raw data to check actual parent-reply relationships
with open("data/local_data.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# Build a map: reply_content -> parent_message
reply_to_parent = {}
for sample in raw_data["samples"]:
    parent = sample["parent_message"]
    for reply in sample["replies"]:
        reply_to_parent[reply[:60]] = parent

# Now test: when user searches, what do the sources say vs actual parent?
queries = ["价格太贵了", "好贵啊", "太贵了", "价格问题"]
for q in queries:
    result = pm.match(q, top_k=5)
    candidates = result.get("candidates", [])
    print(f"\n=== Query: '{q}' ===")
    for i, c in enumerate(candidates):
        content = c.get("content", "")
        source = c.get("source", "")
        # Extract parent from source
        actual_parent = reply_to_parent.get(content[:60], "???")
        print(f"  [{i+1}] source shows: {source[:60]}")
        print(f"       actual parent: {actual_parent}")
        print(f"       MATCH: {'YES' if actual_parent in source else 'NO - MISMATCH!'}")
