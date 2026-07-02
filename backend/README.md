# Lumen backend

FastAPI service for Lumen. See the [project README](../README.md) for the full picture.

```bash
python -m venv .venv && source .venv/Scripts/activate  # Windows Git Bash
pip install -e ".[dev]"
cp .env.example .env   # add your Anthropic key
uvicorn app.main:app --reload
pytest
```
