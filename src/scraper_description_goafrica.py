"""
Scraper description GoAfrica
- Lit DataMart_Prestataires_GoAfrica_Instagram_Final_avec_reviews.xlsx
- Pour chaque URL_Source, scrape <div id="short-description">
- Remplit la colonne Description
- TEST_ONLY = True  → affiche uniquement les 10 premiers (sans sauvegarder)
- TEST_ONLY = False → traite tout et sauvegarde le fichier
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import json
import os
import sys
import io
import random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Configuration ────────────────────────────────────────────────────────────
WORKING_DIR     = r"C:\Users\Admin\Desktop\stage D&A"
INPUT_FILE      = "DataMart_Prestataires_GoAfrica_Instagram_Final_avec_reviews.xlsx"
OUTPUT_FILE     = "DataMart_Prestataires_GoAfrica_Instagram_Final_avec_reviews.xlsx"  # même fichier
CHECKPOINT_FILE = "checkpoint_description.json"
TEST_ONLY       = False  # ← changer en False pour traiter toutes les lignes
TEST_ROWS       = 20
DELAY_MIN       = 0.4
DELAY_MAX       = 0.9
SAVE_EVERY      = 50
# ─────────────────────────────────────────────────────────────────────────────

os.chdir(WORKING_DIR)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-MA,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def scraper_description(url):
    """Retourne le texte de <div id='short-description'> ou None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        div  = soup.find("div", id="short-description")
        if div:
            return div.get_text(strip=True)
        return None
    except Exception as e:
        print(f"    [Erreur] {url[:60]} → {type(e).__name__}: {str(e)[:60]}", flush=True)
        return None


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(data):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    df    = pd.read_excel(INPUT_FILE)
    total = len(df)

    # ── MODE TEST ─────────────────────────────────────────────────────────────
    if TEST_ONLY:
        print("=" * 60, flush=True)
        print(f"MODE TEST — {TEST_ROWS} premiers prestataires", flush=True)
        print("=" * 60, flush=True)
        descriptions = []
        for i in range(min(TEST_ROWS, total)):
            row = df.iloc[i]
            url = str(row.get("URL_Source", "")).strip()
            nom = str(row.get("Nom", ""))[:50]
            print(f"\n[{i+1}] {nom}", flush=True)
            print(f"     URL : {url}", flush=True)
            desc = scraper_description(url)
            descriptions.append(desc)
            print(f"     Description : {str(desc)[:120] if desc else 'Non trouvee'}", flush=True)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        # Sauvegarder les 20 premières lignes avec la colonne Description
        df_test = df.iloc[:TEST_ROWS].copy()
        df_test["Description"] = descriptions
        df_test.to_excel("test_20_lignes.xlsx", index=False)
        print(f"\nFichier test sauvegarde : test_20_lignes.xlsx", flush=True)
        print("Si OK, mettre TEST_ONLY = False et relancer.", flush=True)
        return

    # ── MODE COMPLET ──────────────────────────────────────────────────────────
    print("=" * 60, flush=True)
    print(f"MODE COMPLET — {total} prestataires", flush=True)
    print("=" * 60, flush=True)

    checkpoint = load_checkpoint()
    print(f"Checkpoint : {len(checkpoint)}/{total} deja traites", flush=True)

    try:
        for idx, row in df.iterrows():
            key = str(idx)
            if key in checkpoint:
                continue

            url = str(row.get("URL_Source", "")).strip()
            nom = str(row.get("Nom", ""))[:50]
            pct = (idx + 1) / total * 100

            print(f"[{idx+1}/{total}] ({pct:.1f}%) {nom}", flush=True)

            desc = scraper_description(url)
            checkpoint[key] = desc
            print(f"    → {str(desc)[:100] if desc else 'None'}", flush=True)

            if (idx + 1) % SAVE_EVERY == 0:
                save_checkpoint(checkpoint)
                print(f"    [Checkpoint sauvegarde — {len(checkpoint)}/{total}]", flush=True)

            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    except KeyboardInterrupt:
        print("\nInterruption — sauvegarde checkpoint...", flush=True)
    finally:
        save_checkpoint(checkpoint)

    # Remplir la colonne Description
    df["Description"] = df.index.map(lambda i: checkpoint.get(str(i)))

    df.to_excel(OUTPUT_FILE, index=False)
    nb_ok = sum(1 for v in checkpoint.values() if v is not None)
    print(f"\nFichier sauvegarde : {OUTPUT_FILE}", flush=True)
    print(f"Descriptions trouvees : {nb_ok}/{total}", flush=True)
    print("Termine.", flush=True)


if __name__ == "__main__":
    main()
