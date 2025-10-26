import os
import pandas as pd
from openai import OpenAI

# Initialize OpenAI client (ensure OPENAI_API_KEY is set in your environment)
client = OpenAI()

# === Config ===
INPUT_CSV = "data/sp500_wiki_intros_full.csv"
OUTPUT_CSV = "data/sp500_summaries.csv"
PROMPT = "prompts/gpt_v1.txt"  # folder with text files named like "MMM.txt"

# === Load CSV ===
df = pd.read_csv(INPUT_CSV)

# Add a new column for model output
df["Model_Output"] = ""

# === Process each row ===
for idx, row in df.iterrows():
    symbol = row["Symbol"]
    intro = row["Intro"]
    text_path = os.path.join(PROMPT)

    # Read corresponding text file
    if not os.path.exists(text_path):
        print(f"⚠️ Missing file for {symbol}: {text_path}")
        continue
    with open(text_path, "r", encoding="utf-8") as f:
        base_text = f.read()

    # Combine intro and file text
    combined_text = f"{intro}\n\n{base_text}"

    # === Send to OpenAI ===
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",  # or gpt-4.1, gpt-5, etc.
            input=f"Process the following company info:\n\n{combined_text}",
        )
        result = response.output[0].content[0].text
        df.at[idx, "Model_Output"] = result

    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        df.at[idx, "Model_Output"] = f"Error: {e}"

# === Save new CSV ===
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Done. Output saved to {OUTPUT_CSV}")
