# BITS Guide — Document-Grounded AI Agent

A practical RAG-style assistant for answering BITS admissions, international 2+2, fees/financing, placements and related academic questions from the supplied document set.

## Architecture

`documents → local extraction/OCR → SQLite FTS retrieval → Gemini → answer + evidence`

The app does not require a vector database. Retrieval is local, deterministic and easy to inspect. Gemini is used for reasoning and answer generation, not as the source of facts.

## Run locally

1. Install Python 3.11+.
2. Install Tesseract OCR and ensure `tesseract` is on PATH.
3. Create a virtual environment.
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and put your Gemini API key in it.
6. Run `python ingest.py`.
7. Run `streamlit run app.py`.

The supplied source files are already in `data/sources/`. To add more documents later, drop them there and run `python ingest.py` again.

## Supported inputs

PDF, PNG, JPG/JPEG, WEBP and TXT. PDF pages are text-extracted with PyMuPDF; weak-text pages and images are OCR'd with Tesseract.

## Important behavior

- Answers are grounded in retrieved document chunks.
- The interface exposes the evidence used for each answer.
- Missing evidence is reported instead of being invented.
- Dates, marks, CGPA thresholds, fees and placement figures are treated as source data, not guarantees.
- For changing admission information, the official BITS admissions website should be checked as the current authority: https://admissions.bits-pilani.ac.in/

## Deployment

This Streamlit app can be deployed on Streamlit Community Cloud, Render, Railway, or a VM. Set `GEMINI_API_KEY` as a secret/environment variable; do not commit `.env`.
