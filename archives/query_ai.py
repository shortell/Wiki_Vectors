import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Config ===
INPUT_CSV = "data/sp500_wiki_intros_full.csv"
OUTPUT_CSV = "data/sp500_summaries.csv"
PROMPT_PATH = "prompts/gpt_v1.txt"
MODEL = "gpt-5-mini"

# === Load base rewrite instructions ===
if not os.path.exists(PROMPT_PATH):
    raise FileNotFoundError(f"❌ Prompt file not found: {PROMPT_PATH}")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    base_prompt = f.read().strip()

# === Load data ===
df = pd.read_csv(INPUT_CSV)
df["Model_Output"] = ""

# === Main loop ===
for idx, row in df.iterrows():
    symbol = row["Symbol"]
    intro = row["Intro"]

    # Pass the rewrite instructions as the system message
    # and only the Wikipedia text as user content
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": base_prompt
                },
                {
                    "role": "user",
                    "content": f"Rewrite the following company introduction for ticker {symbol}:\n\n{intro}"
                },
            ],
        )

        result = response.choices[0].message.content.strip()
        df.at[idx, "Model_Output"] = result
        print(f"✅ Rewritten {symbol}")

    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        df.at[idx, "Model_Output"] = f"Error: {e}"

# === Save ===
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Done. Output saved to {OUTPUT_CSV}")
