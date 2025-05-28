"""
examples/run_analysis.py
------------------------
Minimal driver script for the Document Cross-Reference pipeline.

Usage (from project root):

    # Option A: pass the key on the CLI
    python examples/run_analysis.py \
        --document examples/Euro_doc.txt \
        --output   out \
        --max-passes 2 \
        --api-key  sk-...

    # Option B: export the key once, then omit --api-key
    set OPENAI_API_KEY=sk-...
    python examples/run_analysis.py
"""

import argparse
import json
import os
import sys
from pathlib import Path

# --- Make sure the `src/` package is importable ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # one level up from /examples
sys.path.insert(0, str(PROJECT_ROOT))

from src.main import analyze_document


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run cross-reference analysis on a single document."
    )
    parser.add_argument(
        "--document", "-d",
        default="examples/Euro_doc.txt",
        help="Path to the input plain-text file (default: examples/Euro_doc.txt)"
    )
    parser.add_argument(
        "--output", "-o",
        default="out",
        help="Directory where intermediate / final files will be written"
    )
    parser.add_argument(
        "--max-passes", "-n",
        type=int,
        default=2,
        help="Maximum LLM passes when generating the TOC"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key (or set OPENAI_API_KEY env variable)"
    )
    args = parser.parse_args()

    if not args.api_key:
        parser.error("No API key supplied.  Pass --api-key or set OPENAI_API_KEY.")

    result = analyze_document(
        document_path=args.document,
        api_key=args.api_key,
        output_dir=args.output,
        max_passes=args.max_passes
    )

    print(json.dumps(result["all_refs"], indent=2))


if __name__ == "__main__":
    main()
