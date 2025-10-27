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


def fetch_sp500_table(url: str, headers: dict, timeout: int = 20) -> Tuple[BeautifulSoup, pd.DataFrame]:
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
    print(f"✅ [Step 1 Complete] Retrieved S&P 500 table with {len(df)} entries in {elapsed:.2f}s.\n")
    
    return soup, df


def extract_wikipedia_urls(table: BeautifulSoup, df: pd.DataFrame, n: int, base_url: str = "https://en.wikipedia.org") -> pd.DataFrame:
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
    
    links = [base_url + a["href"] for a in table.select("tbody tr td:nth-of-type(2) a[href]")]
    links = links[:n]
    df = df.iloc[:n].copy()
    df["Wikipedia_URL"] = links
    
    elapsed = time.time() - step2_start
    print(f"✅ [Step 2 Complete] Collected {len(links)} Wikipedia URLs in {elapsed:.2f}s.\n")
    
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
        
        content_div = soup.find("div", {"class": "mw-parser-output"})
        if not content_div:
            return ""
        
        paragraphs = []
        for el in content_div.find_all(["p", "h2"], recursive=False):
            if el.name == "h2":
                break
            if el.name == "p" and el.get_text(strip=True):
                paragraphs.append(el.get_text(" ", strip=True))
        
        intro_text = " ".join(paragraphs)
        return intro_text.strip()
    
    except Exception as e:
        return ""


def fetch_all_intros(df: pd.DataFrame, headers: dict, delay: float = 0.3) -> pd.DataFrame:
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
    for idx, link in enumerate(df["Wikipedia_URL"], 1):
        intros.append(get_intro(link, headers))
        time.sleep(delay)
        
        if idx % 10 == 0 or idx == len(df):
            print(f"   ⏱️  Fetched intros for {idx}/{len(df)} companies...")
    
    df["Intro"] = intros
    
    elapsed = time.time() - step4_start
    print(f"✅ [Step 4 Complete] All intros fetched successfully in {elapsed:.2f}s.\n")
    
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
    print(f"✅ [Step 5 Complete] Cleaned and deduplicated data in {elapsed:.2f}s. Rows before: {before}, after: {after} (unique symbols)\n")
    
    return df


def save_to_csv(df: pd.DataFrame, output_path: str = "sp500_wiki_intros_full.csv") -> None:
    """
    Add ID column and save DataFrame to CSV.
    
    Args:
        df: DataFrame to save
        output_path: Path for output CSV file
    """
    print("🟢 [Step 6] Starting: Adding ID and saving to CSV...")
    step6_start = time.time()
    
    df.insert(0, "ID", range(1, len(df) + 1))
    df.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)
    
    elapsed = time.time() - step6_start
    print(f"✅ [Step 6 Complete] Exported {len(df)} rows to {output_path} in {elapsed:.2f}s.")
    print(f"   🔹 Unique symbols: {df['Symbol'].nunique()}\n")


def main(n: int = 1, output_path: str = "sp500_wiki_intros_full.csv"):
    """
    Main function to orchestrate the entire scraping process.
    
    Args:
        n: Number of companies to process
        output_path: Path for output CSV file
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; sp500-fetcher/2.0; +https://example.com)"}
    
    # Step 1: Fetch table
    soup, df = fetch_sp500_table(url, headers)
    
    # Step 2: Extract URLs
    table = soup.find("table", {"class": "wikitable"})
    df = extract_wikipedia_urls(table, df, n)
    
    # Step 3: Function definition (already done above)
    print("🟢 [Step 3] Starting: Defining function to fetch Wikipedia intro paragraphs...")
    print(f"✅ [Step 3 Complete] Intro extraction function defined successfully.\n")
    
    # Step 4: Fetch intros
    df = fetch_all_intros(df, headers)
    
    # Step 5: Clean data
    df = clean_and_deduplicate(df)
    
    # Step 6: Save to CSV
    save_to_csv(df, output_path)


if __name__ == "__main__":
    N = 500  # How many companies to process; set higher for full run
    main(n=N)