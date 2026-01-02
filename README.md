# din12831-heatload

Kleines, community-freundliches Tool zur **raumweisen Heizlastberechnung** (MVP) auf Basis von Python + Streamlit.

> Hinweis: Aktuell ist das ein MVP ohne normgerechte Report-Ausgabe.

## DevContainer (empfohlen)

1. In VS Code: **Reopen in Container**
2. Im Container-Terminal:

```bash
streamlit run app.py
```

Dann öffnet VS Code automatisch den weitergeleiteten Port **8501**.

## Lokal (optional)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
