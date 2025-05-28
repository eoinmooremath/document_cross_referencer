# Document Cross-Referencer

A Python package for:

1. Generating a hierarchical Table of Contents from large plain-text documents.
2. Analyzing and extracting cross‑references between sections.
3. Separating document into chunks based on sections.

## Features

- **Iterative TOC Extraction**: Multi-pass, consistency‑driven heading extraction using RAG.
- **Section Tagging**: Embed markers into raw text for downstream processing using regex.
- **Reference Analysis**: Identify and organize all in‑text references by section using RAG.

## Concept
- We use recursive RAG calls to generate a table of contents of the text, one layer at a time.  With this rich piece of information, we can, with some effort, extract all the sections we want from the text.

```bash
pip install -r requirements.txt
```

## Quick Start
