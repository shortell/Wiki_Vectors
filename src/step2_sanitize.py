"""
1. read the original company text from data/companies/sp500_wiki.csv

2. read the prompt from data/prompts/main_prompt.txt

3. For each company send its wiki text and the prompt to an LLM to sanitize
it and enrich it for a vector embedding

4. Once all companies are sanitized write the data to 
data/companies/sanitized.csv with columns id, symbol, sanitized_text

"""