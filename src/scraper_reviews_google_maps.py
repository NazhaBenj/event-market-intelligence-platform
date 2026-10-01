"""
Scraper Google Maps pour DataMart Prestataires GoAfrica
Extrait pour chaque prestataire :
  - note_maps       : note/rating  (ex: 4.2)
  - nombre_review   : nb d'avis    (ex: 12)
  - description_maps: catégorie    (ex: "Traiteur")
Checkpoint automatique — reprise possible si interruption.
"""

import pandas as pd
import time
import json
import os
import re
import sys
import io
import random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ─── Configuration ────────────────────────────────────────────────────────────
WORKING_DIR     = r"C:\Users\Admin\Desktop\stage D&A"
INPUT_FILE      = "DataMart_Prestataires_GoAfrica_Instagram_Final.xlsx"
OUTPUT_FILE     = "DataMart_Prestataires_GoAfrica_Instagram_Final_avec_reviews.xlsx"
CHECKPOINT_FILE = "checkpoint_reviews.json"
DELAY_MIN       = 2.5
DELAY_MAX       = 4.0
SAVE_EVERY      = 25
# ──────────────────────────────────────────────────────────────────────────────

os.chdir(WORKING_DIR)


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--lang=fr-MA,fr")
    options.add_argument("--window-size=1366,768")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def extraire_infos_page(driver):
    """
    Depuis une page de fiche lieu Google Maps, extrait :
      - note       : float  (ex: 4.2)
      - nb_reviews : int    (ex: 12)
      - description: str    (ex: "Traiteur")
    Retourne un dict avec les 3 clés (valeur None si non trouvée).
    """
    note = None
    nb_reviews = None
    description = None

    # ── NOTE + NB REVIEWS via aria-label ──────────────────────────────────────
    # Google Maps met souvent "4,2 étoiles 12 avis" dans un aria-label
    for selector in [
        'span[aria-label*="étoile"]',
        'span[aria-label*="star"]',
        'button[aria-label*="étoile"]',
        'button[aria-label*="star"]',
    ]:
        for el in driver.find_elements(By.CSS_SELECTOR, selector):
            label = el.get_attribute("aria-label") or ""
            # note
            m_note = re.search(r"([\d][,\.]\d)", label)
            if m_note and note is None:
                note = float(m_note.group(1).replace(",", "."))
            # nb avis
            m_avis = re.search(r"([\d][\d\s]*)\s*avis", label, re.IGNORECASE)
            if m_avis and nb_reviews is None:
                nb = re.sub(r"\s", "", m_avis.group(1))
                if nb.isdigit():
                    nb_reviews = int(nb)

    # ── NB REVIEWS via aria-label "avis" seul ─────────────────────────────────
    if nb_reviews is None:
        for selector in ['span[aria-label*="avis"]', 'button[aria-label*="avis"]',
                         'span[aria-label*="reviews"]', 'button[aria-label*="reviews"]']:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                label = el.get_attribute("aria-label") or ""
                m = re.search(r"([\d][\d\s,\.]*)\s*(?:avis|reviews?)", label, re.IGNORECASE)
                if m:
                    nb = re.sub(r"[\s,\.]", "", m.group(1))
                    if nb.isdigit():
                        nb_reviews = int(nb)
                        break
            if nb_reviews is not None:
                break

    # ── NOTE + NB REVIEWS via texte de page : "4,2\n(12)" ────────────────────
    if note is None or nb_reviews is None:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            # Pattern : "4,2\n(12)" ou "4,2 (12)"
            m = re.search(r"(\d[,\.]\d)\s*[\n\r ]*\((\d[\d\s]*)\)", body_text)
            if m:
                if note is None:
                    note = float(m.group(1).replace(",", "."))
                if nb_reviews is None:
                    nb = re.sub(r"\s", "", m.group(2))
                    if nb.isdigit():
                        nb_reviews = int(nb)
        except Exception:
            pass

    # ── NB REVIEWS via span "(12)" ────────────────────────────────────────────
    if nb_reviews is None:
        for sp in driver.find_elements(By.CSS_SELECTOR, "span.fontBodyMedium, span.UY7F9"):
            txt = sp.text.strip()
            m = re.fullmatch(r"\((\d[\d\s\xa0\.]*)\)", txt)
            if m:
                nb = re.sub(r"[\s\xa0\.]", "", m.group(1))
                if nb.isdigit():
                    nb_reviews = int(nb)
                    break

    # ── DESCRIPTION/CATÉGORIE ─────────────────────────────────────────────────
    # Sur Google Maps la catégorie est un bouton cliquable juste sous le nom
    cat_selectors = [
        "button.DkEaL",
        "span.YhemCb",
        "div.LBgpqf button",
        "button[jsaction*='category']",
        "span.mgr77e",
    ]
    for sel in cat_selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            txt = el.text.strip()
            if txt and len(txt) > 2 and not re.match(r"^[\d\(\)]+$", txt):
                description = txt
                break
        if description:
            break

    # Fallback catégorie : bouton role=button sans chiffres, sans "avis"/"étoile"
    if description is None:
        for el in driver.find_elements(By.CSS_SELECTOR, '[role="button"]'):
            txt = el.text.strip()
            if (txt and 3 < len(txt) < 60
                    and not re.search(r"\d", txt)
                    and "avis" not in txt.lower()
                    and "étoile" not in txt.lower()
                    and "fermer" not in txt.lower()
                    and "partager" not in txt.lower()
                    and "enregistrer" not in txt.lower()
                    and "itinéraire" not in txt.lower()):
                description = txt
                break

    return {"note": note, "reviews": nb_reviews, "description": description}


def scraper_prestataire(driver, nom, lieu):
    """Recherche le prestataire sur Google Maps et retourne un dict d'infos."""
    try:
        lieu_propre = str(lieu).replace("\n", " ").strip() if pd.notna(lieu) else ""
        nom_propre  = str(nom).strip() if pd.notna(nom) else ""
        query = f"{nom_propre} {lieu_propre}".strip()
        url   = "https://www.google.com/maps/search/" + query.replace(" ", "+")

        driver.get(url)
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        infos = extraire_infos_page(driver)

        # Si rien trouvé → peut-être une liste de résultats → cliquer sur le 1er
        if all(v is None for v in infos.values()):
            results = driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
            if results:
                driver.get(results[0].get_attribute("href"))
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                infos = extraire_infos_page(driver)

        return infos

    except WebDriverException as e:
        print(f"    [WebDriverError] {str(e)[:80]}", flush=True)
        return {"note": None, "reviews": None, "description": None}
    except Exception as e:
        print(f"    [Erreur] {type(e).__name__}: {str(e)[:80]}", flush=True)
        return {"note": None, "reviews": None, "description": None}


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(data: dict):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60, flush=True)
    print("Scraper Google Maps — Note + Reviews + Description", flush=True)
    print("=" * 60, flush=True)

    df    = pd.read_excel(INPUT_FILE)
    total = len(df)
    print(f"Prestataires chargés : {total}", flush=True)

    checkpoint = load_checkpoint()
    print(f"Checkpoint : {len(checkpoint)}/{total} déjà traités", flush=True)

    print("Démarrage Chrome headless...", flush=True)
    driver = get_driver()
    print("Chrome démarré.\n", flush=True)

    try:
        for idx, row in df.iterrows():
            key = str(idx)
            if key in checkpoint:
                continue

            nom  = row.get("Nom", "")
            lieu = row.get("Lieu", "")
            pct  = (idx + 1) / total * 100

            print(f"[{idx+1}/{total}] ({pct:.1f}%) {str(nom)[:55]}", flush=True)

            infos = scraper_prestataire(driver, nom, lieu)
            checkpoint[key] = infos

            print(
                f"    → Note: {infos['note']}  "
                f"Avis: {infos['reviews']}  "
                f"Catégorie: {str(infos['description'])[:50]}",
                flush=True,
            )

            if (idx + 1) % SAVE_EVERY == 0:
                save_checkpoint(checkpoint)
                print(f"    [Checkpoint sauvegardé — {len(checkpoint)}/{total}]", flush=True)

            time.sleep(random.uniform(0.3, 0.8))

    except KeyboardInterrupt:
        print("\nInterruption — sauvegarde checkpoint...", flush=True)
    finally:
        save_checkpoint(checkpoint)
        driver.quit()
        print("Navigateur fermé.", flush=True)

    # ── Construire les 3 colonnes ──────────────────────────────────────────────
    def get_val(idx, key):
        entry = checkpoint.get(str(idx))
        if entry is None:
            return None
        if isinstance(entry, dict):
            return entry.get(key)
        # compatibilité ancien format (juste un int)
        return entry if key == "reviews" else None

    df["note_maps"]       = df.index.map(lambda i: get_val(i, "note"))
    df["nombre_review"]   = df.index.map(lambda i: get_val(i, "reviews"))
    df["description_maps"]= df.index.map(lambda i: get_val(i, "description"))

    df.to_excel(OUTPUT_FILE, index=False)

    nb_notes = sum(1 for v in checkpoint.values() if isinstance(v, dict) and v.get("note") is not None)
    nb_rev   = sum(1 for v in checkpoint.values() if isinstance(v, dict) and v.get("reviews") is not None)
    nb_desc  = sum(1 for v in checkpoint.values() if isinstance(v, dict) and v.get("description") is not None)

    print(f"\nFichier sauvegardé : {OUTPUT_FILE}", flush=True)
    print(f"Notes trouvées       : {nb_notes}/{total}", flush=True)
    print(f"Reviews trouvés      : {nb_rev}/{total}", flush=True)
    print(f"Descriptions trouvées: {nb_desc}/{total}", flush=True)
    print("Terminé.", flush=True)


if __name__ == "__main__":
    main()
