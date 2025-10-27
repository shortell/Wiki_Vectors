"""
1. read the original company text from data/companies/sp500_wiki.csv

2. read the prompt from data/prompts/main_prompt.txt

3. For each company send its wiki text and the prompt to an LLM to sanitize
it and enrich it for a vector embedding

4. Once all companies are sanitized write the data to 
data/companies/sanitized.csv with columns id, symbol, sanitized_text

"""

import re


def local_sanitize_paragraphs(text: str) -> str:
    """
    - Removes bracketed references like [1], [ 10 ], [update], [a], etc.
    - Removes stray spaces before punctuation.
    - Collapses multiple spaces.
    - Preserves dollar amounts (e.g., $35.4 billion).
    """
    if not text:
        return ""

    # remove any bracketed expression [ ... ]
    text = re.sub(r'\[\s*[^\]]*?\]', '', text)

    # remove stray spaces before punctuation
    text = re.sub(r'\s+([,\.])', r'\1', text)

    # collapse multiple spaces/newlines to single space
    text = re.sub(r'\s+', ' ', text).strip()

    return text
