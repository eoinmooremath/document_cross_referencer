# Document Cross-Referencer

A Python package for:

1. Generating a hierarchical Table of Contents from large plain-text documents.
2. Analyzing and extracting cross‑references between sections.
3. Separating document into chunks based on sections.
4. **🔆 Extracting the smallest/finest/deepest chunks** - automatically identifies and extracts the text of the most granular sections for focused analysis.

## Features

- **Iterative TOC Extraction**: Multi-pass, consistency‑driven heading extraction using RAG.
- **Section Tagging**: Embed markers into raw text for downstream processing using regex.
- **Reference Analysis**: Identify and organize all in‑text references by section using RAG.
- **🔆 Deepest Chunks Extraction**: Automatically identifies the deepest (finest, smallest) sections in the document hierarchy (leaf nodes) and extracts their complete text content into a structured JSON format.
  ```
  📄 Document → 🌳 Hierarchy → 🎯 Leaf Sections → 📦 JSON Chunks
  ```

## Concept
We use recursive RAG calls to generate a table of contents of the text, one layer at a time.  With this rich piece of information, we can, with some regex effort, extract all the sections we want from the text. 

Additionally, to identify cross referenced sections, rather than do that manually, we ask the LLM to it for us, using the updated table of contents. 

When we do the LLM calls, for each call we submit the entire document.  Newer Gemini and OpenAi models have token windows of 1,000,000+ tokens, or about 2500 pages, so the entire document should fit. Usually there are between 5-7 calls to the LLM in total.  If you have 10 calls of a 200 page document context, that is roughly 2000 pages, or 800,000 tokens processed. gpt-4.1-mini costs $0.40 per million tokens currently, so thats $0.32 of input per analysis (output probably not that much, either.)

As far as the time goes, it took me about 2 minutes to generate the table of contents in `examples/EU_document_toc.md`, and another 5-6 minutes to process the cross references, for about 8 minutes total. This was using GPT 4.1. You can definitely cut the cross-referencing if you don't need it, and having more sections to cross reference will obviously take more time. 


## Key Outputs

The system generates several valuable outputs for document analysis:

- **`{document}_toc.md`**: Hierarchical table of contents with section IDs
- **`{document}_tagged.txt`**: Original document with section boundary markers
- **`{document}_all_refs.json`**: Complete cross-reference analysis showing which sections reference which other sections
- **`{document}_smallest_chunks.json`**:  **Most valuable output** - Contains the text of all the smallest/deepest sections, perfect for:
  - Focused content analysis
  - Semantic search over granular sections  
  - Training data for ML models
  - Detailed document understanding

## Smallest Chunks Feature

The **smallest chunks** feature is particularly powerful because it automatically identifies the most granular, actionable pieces of content in your document. Instead of working with entire chapters or large sections, you get the individual articles, subsections, or paragraphs that contain the actual substantive content.

**How it works**: The algorithm traverses the document hierarchy and identifies sections that are at the deepest level before the structure steps back up to a higher level. These represent the "leaf nodes" of your document tree - the most specific, focused content units.

**Example**: In a legal document with structure like:
```
Chapter I → Article 1 → Paragraph (a) ✓ (smallest chunk)
Chapter I → Article 1 → Paragraph (b) ✓ (smallest chunk)  
Chapter I → Article 2 ✓ (smallest chunk - no sub-paragraphs)
Chapter II → Article 3 → Paragraph (a) ✓ (smallest chunk)
```

## Example Results

The example file is the text of the EU General Data Protection Regulation — a 200+ page document with complex nested sections.

**Source**: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679

**Generated Outputs**:
- **`examples/EU_document_toc.md`**: Visual table of contents showing the hierarchical structure the program automatically generated
- **`out/EU_document_tagged.txt`**: Original document with section boundary markers showing where the program identified each section
- **`out/EU_document_all_refs.json`**: Complete cross-reference analysis - shows which articles reference which other articles, creating a network map of document relationships - maps section IDs to the complete text of all sections which reference that section
- **`out/EU_document_smallest_chunks.json`**: A JSON object (dictionary) containing the exact text content from each of the deepest sections - maps section IDs to their complete text

**Real Impact**: Instead of manually parsing a 200-page regulation, you get pre-extracted, focused sections that you can immediately search, analyze, or process with other tools.
