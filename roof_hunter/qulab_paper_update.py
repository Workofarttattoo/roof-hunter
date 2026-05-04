import os
import json
import requests
from datetime import datetime, timedelta

def reconstruct_abstract(inverted_index):
    """Reconstructs the abstract string from OpenAlex's inverted index."""
    if not inverted_index:
        return ""
    # Create an array large enough to hold all words
    max_idx = max([max(positions) for positions in inverted_index.values()])
    words = [""] * (max_idx + 1)
    
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
            
    return " ".join(words)

def fetch_recent_openalex_papers(days_back=3, max_results=50):
    """Fetches recent Chemistry and Materials Science papers from OpenAlex."""
    # C185592680 = Chemistry, C192562407 = Materials Science
    date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = f"https://api.openalex.org/works?filter=concepts.id:C185592680|C192562407,from_publication_date:{date_from}&sort=publication_date:desc&per-page={max_results}"
    
    print(f"Fetching newest science from OpenAlex (since {date_from})...")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching from OpenAlex: {response.status_code}")
        return []
        
    data = response.json()
    papers = []
    for work in data.get("results", []):
        if not work.get("title"):
            continue
            
        paper = {
            "title": work.get("title"),
            "publication_date": work.get("publication_date"),
            "doi": work.get("doi"),
            "is_open_access": work.get("open_access", {}).get("is_oa", False),
            "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
            "authors": [a.get("author", {}).get("display_name") for a in work.get("authorships", [])]
        }
        papers.append(paper)
    return papers

def main():
    papers = fetch_recent_openalex_papers()
    
    # Save the new updates to the clean daily_updates folder
    os.makedirs("daily_updates", exist_ok=True)
    today_str = datetime.now().strftime('%Y%m%d')
    filepath = os.path.join("daily_updates", f"openalex_science_update_{today_str}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "source": "OpenAlex",
            "paper_count": len(papers),
            "papers": papers
        }, f, indent=2)
        
    print(f"Saved {len(papers)} newest papers to {filepath}")

if __name__ == "__main__":
    main()
