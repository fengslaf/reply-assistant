# Version History

## V0.2.04
- Added V2.04 intelligent generation modules and a toggle to enable them in settings.
- Added a product home page with two peer modules: reply assistant and customer data system.
- Kept the public edition focused on local free usage.
- Added `personal_data.py` and isolated storage under `data/personal_data/`.
- Added dynamic grade progression with `初三 -> 高一` and `高三 -> 高三+N`.

## V0.2.03
- Added `local_search/embedding_service.py` and `local_search/chroma_repo.py`.
- Enabled intent-first filtering before retrieval.
- Enabled semantic vector retrieval backed by Chroma.
- Auto-syncs `local_data.json` into the vector index when available.

## V0.2.02
- Added `local_intelligence/` as a backend enhancement layer.
- Kept the UI unchanged.
- Intelligent enhancement now runs before the existing retrieval / AI flow.

## V0.2.01
- Added `local_context/` and `local_cluster/`.
- Kept the UI unchanged.

## V0.2.0
- Added `local_search/`, `remote_ai/`, and `preview_adapter.py`.
- Introduced the first V2 retrieval bridge.
