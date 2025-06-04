# Document Cross-Referencer

A Python package for:

1. Generating a hierarchical Table of Contents from large plain-text documents.
2. Analyzing and extracting cross‑references between sections.
3. Separating document into chunks based on sections.
4. **Extracting the smallest/deepest chunks** - automatically identifies and extracts the text of the most granular sections for focused analysis.

## Features

- **Iterative TOC Extraction**: Multi-pass, consistency‑driven heading extraction using RAG.
- **Section Tagging**: Embed markers into raw text for downstream processing using regex.
- **Reference Analysis**: Identify and organize all in‑text references by section using RAG.
- **Smallest Chunks Extraction**: Automatically identifies the deepest sections in the document hierarchy (leaf nodes) and extracts their complete text content into a structured JSON format.

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

## Concept
- We use recursive RAG calls to generate a table of contents of the text, one layer at a time.  With this rich piece of information, we can, with some effort, extract all the sections we want from the text. To do the recursive RAG calls, for each call we submit the entire document to the LLM.  Newer Gemini and OpenAi models have token windows of 1,000,000+ tokens, or about 2500 pages, so the entire document should fit. Usually there are between 5-7 calls to the LLM in total.  If you have 10 calls of a 200 page document context, that is roughly 2000 pages, or 800,000 tokens processed. gpt-4.1-mini costs $0.40 per million tokens currently.

## Example Results

The example file is the text of the EU General Data Protection Regulation — a 200+ page document with complex nested sections.

**Source**: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679

**Generated Outputs**:
- **`examples/EU_document_toc.md`**: Visual table of contents showing the hierarchical structure the program automatically generated
- **`out/EU_document_tagged.txt`**: Original document with section boundary markers showing where the program identified each section
- **`out/EU_document_all_refs.json`**: Complete cross-reference analysis - shows which articles reference which other articles, creating a network map of document relationships
- **`out/EU_document_smallest_chunks.json`**:  **100 individual sections** extracted as the smallest meaningful units - from short definitions (200 chars) to detailed articles (5000+ chars), ready for analysis

**Real Impact**: Instead of manually parsing a 200-page regulation, you get pre-extracted, focused sections that you can immediately search, analyze, or process with other tools.

## Example
- The example file is the text of the EU General Data Protection Regulation — a 200+ page document with complex nested sections.
- It can be found here:
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
- Check out ``EU_document_toc.md`` in the examples folder for a visual look at the table of contents the program automatically generated.
- Check out ``EU_document_tagged.txt`` in the out folder to see in where in the text the program decided the sections exist.  
 
