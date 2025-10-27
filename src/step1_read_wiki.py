"""

1. Crawl all 500 companies wiki articles

2. For each company get the relevant information

3. Output a csv file with the following columns id, symbol, security,
text (investigate wiki for other relevant columns in the future)

4. csv file should be located in data/companies/sp500_wiki.csv

"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import csv
from typing import List, Tuple
import os

# Configuration: Number of companies to process from the S&P 500 list
# Set to 500 for full processing, or lower number for testing/limited runs
N_COMPANIES_TO_PROCESS = 10

OUTPUT_CSV = "data/companies/wiki_intros.csv"


def fetch_sp500_table(
    url: str, headers: dict, timeout: int = 20
) -> Tuple[BeautifulSoup, pd.DataFrame]:
    """
    Fetch S&P 500 companies table from Wikipedia.

    Args:
        url: Wikipedia URL for S&P 500 list
        headers: HTTP headers for the request
        timeout: Request timeout in seconds

    Returns:
        Tuple of (BeautifulSoup object, DataFrame with company data)
    """
    print("🟢 [Step 1] Starting: Fetching S&P 500 companies table from Wikipedia...")
    start_time = time.time()

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        print("✅ Wikipedia page fetched successfully.")
    except Exception as e:
        print(f"❌ Error fetching page: {e}")
        raise

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "wikitable"})
    df = pd.read_html(str(table))[0]

    elapsed = time.time() - start_time
    print(
        f"✅ [Step 1 Complete] Retrieved S&P 500 table with {len(df)} entries in {elapsed:.2f}s.\n"
    )

    return soup, df


def extract_wikipedia_urls(
    table: BeautifulSoup,
    df: pd.DataFrame,
    n: int,
    base_url: str = "https://en.wikipedia.org",
) -> pd.DataFrame:
    """
    Extract Wikipedia URLs from the S&P 500 table.

    Args:
        table: BeautifulSoup table object
        df: DataFrame with company data
        n: Number of companies to process
        base_url: Base Wikipedia URL

    Returns:
        DataFrame with Wikipedia URLs added
    """
    print("🟢 [Step 2] Starting: Extracting company Wikipedia URLs...")
    step2_start = time.time()

    links = [
        base_url + a["href"] for a in table.select("tbody tr td:nth-of-type(2) a[href]")
    ]
    links = links[:n]
    df = df.iloc[:n].copy()
    df["Wikipedia_URL"] = links

    elapsed = time.time() - step2_start
    print(
        f"✅ [Step 2 Complete] Collected {len(links)} Wikipedia URLs in {elapsed:.2f}s.\n"
    )

    return df


def get_intro(url: str, headers: dict, timeout: int = 15) -> str:
    """
    Fetch the intro paragraphs from a Wikipedia article.

    Args:
        url: Wikipedia article URL
        headers: HTTP headers for the request
        timeout: Request timeout in seconds

    Returns:
        String containing intro paragraphs
    """
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find the main content area
        content_div = soup.find("div", {"class": "mw-parser-output"})
        if not content_div:
            print(f"⚠️  No mw-parser-output div found for {url}")
            return ""

        # Method 1: Try to find proper paragraphs
        paragraphs = []
        found_h2 = False
        
        for el in content_div.find_all(["p", "h2", "div"]):
            if el.name == "h2":
                found_h2 = True
                break
            
            if el.name == "p":
                if el.get("style") and "display:none" in el.get("style"):
                    continue
                
                text = el.get_text(" ", strip=True)
                if text and len(text) > 20:
                    paragraphs.append(text)
        
        # Method 2: If no paragraphs found, try regex-based extraction
        if not paragraphs:
            print(f"⚠️  No paragraphs found for {url}, trying regex approach")
            import re
            
            # Look for text that starts with the company name or similar patterns
            html_text = content_div.get_text(" ", strip=True)
            
            # Try to find the first substantial sentence
            sentences = re.split(r'[.!?]+', html_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 50 and not any(skip in sentence.lower() for skip in 
                    ["jump to", "navigation", "menu", "coordinates", "edit", "view", "talk"]):
                    paragraphs.append(sentence)
                    break
        
        # Method 3: If still no paragraphs, try raw HTML parsing
        if not paragraphs:
            print(f"⚠️  Regex approach failed for {url}, trying raw HTML parsing")
            html = r.text
            
            # Look for the pattern: <p><b>Company Name</b> is...
            import re
            pattern = r'<p><b>([^<]+)</b>\s+is\s+([^<]+(?:<[^>]+>[^<]*</[^>]+>[^<]*)*)'
            matches = re.findall(pattern, html, re.IGNORECASE)
            
            for match in matches:
                company_name = match[0]
                intro_text = match[1]
                # Clean up HTML tags
                intro_text = re.sub(r'<[^>]+>', '', intro_text)
                intro_text = f"{company_name} is {intro_text}".strip()
                
                if len(intro_text) > 20:
                    paragraphs.append(intro_text)
                    break

        intro_text = " ".join(paragraphs)
        result = intro_text.strip()
        
        if not result:
            print(f"❌ No intro text extracted for {url}")
        else:
            print(f"✅ Extracted {len(result)} characters for {url}")
            
        return result

    except Exception as e:
        print(f"❌ Error fetching intro for {url}: {e}")
        return ""


def fetch_all_intros(
    df: pd.DataFrame, headers: dict, delay: float = 0.3
) -> pd.DataFrame:
    """
    Fetch intro paragraphs for all companies in the DataFrame.

    Args:
        df: DataFrame with Wikipedia URLs
        headers: HTTP headers for requests
        delay: Delay between requests in seconds

    Returns:
        DataFrame with Intro column added
    """
    print("🟢 [Step 4] Starting: Fetching intros for all companies...")
    step4_start = time.time()

    intros = []
    successful_fetches = 0
    failed_fetches = 0
    
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        company_name = row["Security"]
        link = row["Wikipedia_URL"]
        
        print(f"🔍 Processing {company_name} ({idx}/{len(df)})...")
        intro_text = get_intro(link, headers)
        
        if intro_text:
            successful_fetches += 1
        else:
            failed_fetches += 1
            print(f"⚠️  Failed to fetch intro for {company_name}")
        
        intros.append(intro_text)
        time.sleep(delay)

        if idx % 5 == 0 or idx == len(df):
            print(f"   📊 Progress: {idx}/{len(df)} companies processed ({successful_fetches} successful, {failed_fetches} failed)")

    df["Intro"] = intros

    elapsed = time.time() - step4_start
    print(f"✅ [Step 4 Complete] All intros fetched in {elapsed:.2f}s.")
    print(f"   📊 Results: {successful_fetches} successful, {failed_fetches} failed\n")

    return df


def clean_and_deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and deduplicate the company data.

    Args:
        df: DataFrame to clean

    Returns:
        Cleaned DataFrame
    """
    print("🟢 [Step 5] Starting: Cleaning and deduplicating data...")
    step5_start = time.time()

    df = df[["Symbol", "Security", "Wikipedia_URL", "Intro"]].copy()
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    df["Security"] = df["Security"].astype(str).str.strip()
    df = df[df["Symbol"] != ""]
    df = df.dropna(subset=["Symbol"])

    before = len(df)
    df = df.drop_duplicates(subset=["Symbol"], keep="first").reset_index(drop=True)
    after = len(df)

    elapsed = time.time() - step5_start
    print(
        f"✅ [Step 5 Complete] Cleaned and deduplicated data in {elapsed:.2f}s. Rows before: {before}, after: {after} (unique symbols)\n"
    )

    return df


def get_existing_symbols(output_path: str) -> set:
    """
    Get symbols that already exist in the output CSV file AND have valid Intro content.
    
    Args:
        output_path: Path to the output CSV file
        
    Returns:
        Set of existing symbols with valid Intro content
    """
    if not os.path.exists(output_path):
        print(f"📄 Output file {output_path} doesn't exist yet - no symbols to skip")
        return set()
    
    try:
        existing_df = pd.read_csv(output_path)
        
        # Filter for symbols that have non-empty Intro content
        valid_intros = existing_df[
            existing_df['Intro'].notna() & 
            (existing_df['Intro'].astype(str).str.strip() != '')
        ]
        
        existing_symbols = set(valid_intros['Symbol'].astype(str).str.strip())
        empty_intros = len(existing_df) - len(valid_intros)
        
        print(f"📄 Found {len(existing_symbols)} symbols with valid Intro content in {output_path}")
        if empty_intros > 0:
            print(f"⚠️  Found {empty_intros} symbols with empty/missing Intro content - these will be reprocessed")
        
        return existing_symbols
    except Exception as e:
        print(f"⚠️  Error reading existing file {output_path}: {e}")
        return set()


def filter_new_symbols(df: pd.DataFrame, existing_symbols: set) -> pd.DataFrame:
    """
    Filter out rows with symbols that already exist.
    
    Args:
        df: DataFrame with company data
        existing_symbols: Set of symbols that already exist
        
    Returns:
        Filtered DataFrame with only new symbols
    """
    if not existing_symbols:
        print("✅ No existing symbols to filter - processing all companies")
        return df
    
    # Clean symbols for comparison
    df['Symbol_clean'] = df['Symbol'].astype(str).str.strip()
    
    # Filter out existing symbols
    before_count = len(df)
    df_new = df[~df['Symbol_clean'].isin(existing_symbols)].copy()
    after_count = len(df_new)
    
    skipped_count = before_count - after_count
    print(f"🔄 Filtered companies: {before_count} total, {skipped_count} skipped (existing), {after_count} new")
    
    # Remove the temporary column
    df_new = df_new.drop('Symbol_clean', axis=1)
    
    return df_new


def save_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """
    Add ID column and save DataFrame to CSV, updating existing rows or appending new ones.

    Args:
        df: DataFrame to save
        output_path: Path for output CSV file
    """
    print("🟢 [Step 6] Starting: Adding ID and saving to CSV...")
    step6_start = time.time()

    if os.path.exists(output_path):
        # Read existing data
        existing_df = pd.read_csv(output_path)
        print(f"📄 Found existing file with {len(existing_df)} rows")
        
        # Separate new symbols from existing ones
        existing_symbols = set(existing_df['Symbol'].astype(str).str.strip())
        df_new_symbols = df[~df['Symbol'].astype(str).str.strip().isin(existing_symbols)].copy()
        df_existing_symbols = df[df['Symbol'].astype(str).str.strip().isin(existing_symbols)].copy()
        
        # Handle new symbols - append with new IDs
        if len(df_new_symbols) > 0:
            next_id = existing_df['ID'].max() + 1
            df_new_symbols.insert(0, "ID", range(next_id, next_id + len(df_new_symbols)))
            print(f"📝 Adding {len(df_new_symbols)} new symbols with IDs starting from {next_id}")
        
        # Handle existing symbols - update their Intro content
        updated_count = 0
        if len(df_existing_symbols) > 0:
            print(f"🔄 Updating Intro content for {len(df_existing_symbols)} existing symbols")
            for _, row in df_existing_symbols.iterrows():
                symbol = row['Symbol'].strip()
                mask = existing_df['Symbol'].astype(str).str.strip() == symbol
                if mask.any():
                    existing_df.loc[mask, 'Intro'] = row['Intro']
                    updated_count += 1
        
        # Combine all data
        if len(df_new_symbols) > 0:
            combined_df = pd.concat([existing_df, df_new_symbols], ignore_index=True)
        else:
            combined_df = existing_df
        
        combined_df.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
        
        print(f"✅ [Step 6 Complete] Updated {updated_count} existing rows and added {len(df_new_symbols)} new rows in {time.time() - step6_start:.2f}s.")
        print(f"   🔹 Total rows: {len(combined_df)}, Updated symbols: {updated_count}, New symbols: {len(df_new_symbols)}")
    else:
        # Create new file
        df.insert(0, "ID", range(1, len(df) + 1))
        df.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
        
        print(f"✅ [Step 6 Complete] Created new file with {len(df)} rows in {time.time() - step6_start:.2f}s.")
        print(f"   🔹 Unique symbols: {df['Symbol'].nunique()}")
    
    print()


def main(n: int = 1):
    """
    Main function to orchestrate the entire scraping process.

    Args:
        n: Number of companies to process
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; sp500-fetcher/2.0; +https://example.com)"
    }

    # Step 0: Check for existing symbols to skip
    print("🟢 [Step 0] Starting: Checking for existing symbols to skip...")
    existing_symbols = get_existing_symbols(OUTPUT_CSV)
    print(f"✅ [Step 0 Complete] Found {len(existing_symbols)} existing symbols to skip.\n")

    # Step 1: Fetch table
    soup, df = fetch_sp500_table(url, headers)

    # Step 2: Extract URLs
    table = soup.find("table", {"class": "wikitable"})
    df = extract_wikipedia_urls(table, df, n)

    # Step 2.5: Filter out existing symbols
    print("🟢 [Step 2.5] Starting: Filtering out existing symbols...")
    df = filter_new_symbols(df, existing_symbols)
    print(f"✅ [Step 2.5 Complete] Filtered to {len(df)} new companies to process.\n")

    # If no new companies to process, exit early
    if len(df) == 0:
        print("🎉 No new companies to process - all symbols already exist!")
        return

    # Step 3: Function definition (already done above)
    print(
        "🟢 [Step 3] Starting: Defining function to fetch Wikipedia intro paragraphs..."
    )
    print(f"✅ [Step 3 Complete] Intro extraction function defined successfully.\n")

    # Step 4: Fetch intros
    df = fetch_all_intros(df, headers)

    # Step 5: Clean data
    df = clean_and_deduplicate(df)

    # Step 6: Save to CSV
    save_to_csv(df, OUTPUT_CSV)


if __name__ == "__main__":
    main(n=N_COMPANIES_TO_PROCESS)
