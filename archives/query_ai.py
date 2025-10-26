from openai import OpenAI
import os
import pandas as pd
from datetime import datetime
import dotenv

dotenv.load_dotenv()

# === Config ===
INPUT_CSV = "archives/sp500_wiki_intros_full.csv"
OUTPUT_CSV = "archives/sp500_summaries.csv"
PROMPT = "prompts/gpt_v1.txt"
MODEL = "gpt-5-mini"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_text(response):
    """Safely extract model-generated text from OpenAI response object."""
    try:
        # iterate through structured objects (new API format)
        for item in getattr(response, "output", []):
            # item might be a typed object, so access attributes directly
            item_type = getattr(item, "type", None)
            content = getattr(item, "content", None)

            if item_type == "message" and content:
                # content is a list of content blocks
                texts = []
                for c in content:
                    if isinstance(c, dict) and "text" in c:
                        texts.append(c["text"])
                    elif hasattr(c, "text"):
                        texts.append(c.text)
                if texts:
                    return "\n".join(texts)

        # fallback for simpler schema
        if hasattr(response, "output_text"):
            return response.output_text

    except Exception as e:
        print(f"[extract_text] Error extracting text: {e}")

    return None


def log(msg):
    print(f"[{datetime.now()}] {msg}")


def main():
    df = pd.read_csv(INPUT_CSV)
    results = []

    log(
        f"📄 Loaded {len(df)} rows from {INPUT_CSV} with columns: {df.columns.tolist()}"
    )

    for i, row in df.iterrows():
        name = row["Security"]
        intro = row["Intro"]
        prompt = (
            "You are a data refinement AI trained for semantic optimization of company profiles "
            "for embedding-based clustering.\n\n"
            "Objective: Rewrite the provided company introduction to focus on its primary industries, "
            "core products, services, and market position.\n\n"
            f"Input:\n{intro}"
        )

        log(f"🚀 Processing {name}...")
        try:
            response = client.responses.create(model=MODEL, input=prompt)
            log(f"📨 Raw response received for {name}")

            text = extract_text(response)
            if not text:
                raise ValueError("No valid text content found in response")

            results.append({"Security": name, "Summary": text})
            log(f"✅ {name} processed successfully")

        except Exception as e:
            log(f"❌ Error processing {name}: {e}")
            results.append({"Security": name, "Summary": f"ERROR: {e}"})

    output_df = pd.DataFrame(results)
    output_df.to_csv(OUTPUT_CSV, index=False)
    log(f"💾 Saved {len(results)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
