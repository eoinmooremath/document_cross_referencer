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
- We use recursive RAG calls to generate a table of contents of the text, one layer at a time.  With this rich piece of information, we can, with some effort, extract all the sections we want from the text. To do the recursive RAG calls, for each call we submit the entire document to the LLM.  Newer Gemini and OpenAi models have token windows of 1,000,000+ tokens, or about 2500 pages, so the entire document should fit. Usually there are between 5-7 calls to the LLM in total.  If you have 10 calls of a 200 page document context, that is roughly 2000 pages, or 800,000 tokens processed. gpt-4.1-mini costs $0.40 per million tokens currently.

## Example
- The example file is the text of the EU General Data Protection Regulation — a 200+ page document with complex nested sections.
- It can be found here:
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
