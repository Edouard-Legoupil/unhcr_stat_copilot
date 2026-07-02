uv run python scripts/convert_unhcr_reports_docling.py

uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

uv run python -m py_compile scripts/build_reports_vector_index.py

uv run python scripts/build_reports_vector_index.py build \
  --reset \
  --model BAAI/bge-small-en-v1.5