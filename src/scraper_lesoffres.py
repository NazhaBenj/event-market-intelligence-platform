"""
Scraper - lesoffres.ma
https://lesoffres.ma/offres.php

Filtres appliques :
  - Domaine d'activite : Services
  - Categorie          : Services
  - Procedure          : Appel d'offres ouvert
  - Mots-cles          : restauration, traiteur, reception,
                         hebergement, seminaire, evenement, animation

Installation :
    pip install selenium webdriver-manager pandas openpyxl

Lancement :
    python scraper_lesoffres.py
"""

import time
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from webdriver_manager.chrome import ChromeDriverManager

# ===========================================================================
# CONFIG
# ===========================================================================

URL_HOME   = "https://lesoffres.ma"
URL_OFFRES = "https://lesoffres.ma/offres.php"

EMAIL    = "nazha.benjarnij@usmba.ac.ma"
PASSWORD = "Nazha@123"

PAUSE   = 3
TIMEOUT = 30

# Mots-cles (chacun entre separement avec Entree)
KEYWORDS = [
    "restauration",
    "traiteur",
    "reception",
    "hebergement",
    "seminaire",
    "evenement",
    "animation",
]

date_scraping = datetime.now().strftime("%Y-%m-%d")


# ===========================================================================
# DRIVER
# ===========================================================================

def creer_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.maximize_window()
    return driver


# ===========================================================================
# CONNEXION
# ===========================================================================

def se_connecter(driver):
    wait = WebDriverWait(driver, TIMEOUT)

    print("Ouverture de lesoffres.ma...")
    driver.get(URL_HOME)
    time.sleep(PAUSE)

    # Clic sur le bouton de connexion
    try:
        login_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//i[contains(@class,'fa-sign-in-alt')]/ancestor::a")
        ))
        login_btn.click()
        print("OK Bouton connexion clique")
        time.sleep(2)
    except Exception as e:
        print(f"[WARN] Bouton connexion : {e}")

    # Email
    try:
        email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
        email_input.clear()
        email_input.send_keys(EMAIL)
        print("OK Email saisi")
    except Exception as e:
        print(f"[WARN] Email : {e}")

    # Mot de passe
    try:
        pwd_input = wait.until(EC.presence_of_element_located((By.ID, "password")))
        pwd_input.clear()
        pwd_input.send_keys(PASSWORD)
        print("OK Mot de passe saisi")
    except Exception as e:
        print(f"[WARN] Mot de passe : {e}")

    # Submit
    try:
        submit = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[type='submit']")
        ))
        submit.click()
        print("OK Connexion soumise")
        time.sleep(PAUSE)
    except Exception as e:
        print(f"[WARN] Submit : {e}")

    print(f"URL apres connexion : {driver.current_url}")
    print(f"Titre page          : {driver.title}")


# ===========================================================================
# HELPERS FILTRES (autocomplete + select)
# ===========================================================================

def _autocomplete_select(driver, input_id, dropdown_id, valeur):
    """
    Tape 'valeur' dans un input autocomplete et clique sur la
    premiere option correspondante dans le dropdown.
    """
    wait = WebDriverWait(driver, TIMEOUT)
    try:
        inp = wait.until(EC.element_to_be_clickable((By.ID, input_id)))
        inp.click()
        inp.clear()
        inp.send_keys(valeur)
        time.sleep(1.5)

        # Attendre que le dropdown soit visible
        dropdown = wait.until(EC.visibility_of_element_located((By.ID, dropdown_id)))
        options  = dropdown.find_elements(By.TAG_NAME, "div")

        for opt in options:
            if valeur.lower() in opt.text.lower():
                driver.execute_script("arguments[0].click();", opt)
                print(f"  OK Autocomplete '{input_id}' -> '{opt.text.strip()}'")
                time.sleep(0.8)
                return True

        # Si aucune option exacte, cliquer la premiere
        if options:
            driver.execute_script("arguments[0].click();", options[0])
            print(f"  OK Autocomplete '{input_id}' -> '{options[0].text.strip()}' (premier)")
            time.sleep(0.8)
            return True

    except Exception as e:
        print(f"  [WARN] Autocomplete '{input_id}' : {e}")
    return False


def _saisir_mots_cles(driver, keywords):
    """
    Pour chaque mot-cle :
      1. Clique sur le champ
      2. Tape le mot
      3. Appuie sur Entree  → le tag est ajoute dans selectedKeywordsContainer
    Repete pour chaque mot, puis retourne (le clic sur Chercher est fait apres).
    """
    wait = WebDriverWait(driver, TIMEOUT)
    for kw in keywords:
        try:
            # Retrouver l'input a chaque iteration (le DOM peut se rafraichir)
            inp = wait.until(EC.element_to_be_clickable((By.ID, "keywordsFilter")))
            inp.click()
            time.sleep(0.3)
            inp.clear()
            inp.send_keys(kw)
            time.sleep(0.3)
            inp.send_keys(Keys.RETURN)   # valide et ajoute le tag
            time.sleep(0.8)              # attendre que le tag apparaisse
            print(f"  OK Mot-cle '{kw}' ajoute (Entree)")
        except Exception as e:
            print(f"  [WARN] Mot-cle '{kw}' : {e}")


# ===========================================================================
# APPLICATION DES FILTRES
# ===========================================================================

def appliquer_filtres(driver):
    wait = WebDriverWait(driver, TIMEOUT)

    print("\n--- Application des filtres ---")

    # 1. Domaine d'activite -> Services
    _autocomplete_select(driver, "activityFilter", "activityDropdown", "Services")

    # 2. Categorie -> Services  (simple <select>)
    try:
        sel = Select(driver.find_element(By.ID, "categoryFilter"))
        sel.select_by_value("Services")
        print("  OK Categorie : Services")
    except Exception as e:
        print(f"  [WARN] Categorie : {e}")

    # 3. Procedure -> Appel d'offres ouvert
    _autocomplete_select(driver, "procedureFilter", "procedureDropdown", "Appel d'offres ouvert")

    # 4. Mots-cles
    _saisir_mots_cles(driver, KEYWORDS)

    # 5. Clic sur Chercher
    try:
        btn = wait.until(EC.element_to_be_clickable((By.ID, "searchBtn")))
        btn.click()
        print("  OK Bouton Chercher clique")
        time.sleep(PAUSE)
    except Exception as e:
        print(f"  [WARN] Bouton Chercher : {e}")


# ===========================================================================
# SCROLL INFINI (charger tous les resultats)
# ===========================================================================

def scroll_tout_charger(driver):
    """
    Fait defiler la page jusqu'en bas jusqu'a ce que plus
    aucune nouvelle carte ne soit chargee.
    """
    print("\n--- Chargement de toutes les offres (scroll) ---")
    derniere_hauteur = driver.execute_script("return document.body.scrollHeight")
    nb_cartes_avant  = 0

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.5)

        nouvelle_hauteur = driver.execute_script("return document.body.scrollHeight")
        nb_cartes        = len(driver.find_elements(By.CSS_SELECTOR, "div.tender-card"))

        print(f"  Cartes chargees : {nb_cartes}")

        if nouvelle_hauteur == derniere_hauteur and nb_cartes == nb_cartes_avant:
            print("  Fin du scroll : toutes les offres sont chargees.")
            break

        derniere_hauteur = nouvelle_hauteur
        nb_cartes_avant  = nb_cartes


# ===========================================================================
# SCRAPING DES CARTES
# ===========================================================================

def scraper_cartes(driver):
    """Extrait les infos de chaque tender-card visible sur la page."""
    cartes    = driver.find_elements(By.CSS_SELECTOR, "div.tender-card")
    resultats = []
    print(f"\n--- Scraping de {len(cartes)} cartes ---")

    for card in cartes:
        try:
            # Procedure (tag colore)
            procedure = ""
            try:
                procedure = card.find_element(By.CSS_SELECTOR, ".appel-offre-tag").text.strip()
            except Exception:
                pass

            # Titre + URL detail
            titre     = ""
            url_detail = ""
            try:
                lien      = card.find_element(By.CSS_SELECTOR, "h3 > a")
                titre     = lien.text.strip()
                url_detail = lien.get_attribute("href") or ""
            except Exception:
                pass

            # Infos dans les <p> de .tender-info
            acheteur   = ""
            lieu       = ""
            date_pub   = ""
            date_limite = ""
            categorie  = ""
            estimation = ""
            caution    = ""

            try:
                paras = card.find_elements(By.CSS_SELECTOR, ".tender-info p")
                for p in paras:
                    txt = p.text.strip()
                    # Identifier par l'icone FontAwesome
                    try:
                        icone = p.find_element(By.TAG_NAME, "i").get_attribute("class")
                    except Exception:
                        icone = ""

                    if "fa-building" in icone:
                        acheteur = txt
                    elif "fa-map-marker" in icone:
                        lieu = txt
                    elif "fa-calendar" in icone:
                        date_pub = txt.replace("Pub:", "").strip()
                    elif "fa-clock" in icone:
                        date_limite = txt.replace("Limite:", "").strip()
                    elif "fa-tag" in icone:
                        categorie = txt
                    elif "fa-calculator" in icone:
                        estimation = txt.replace("Estimation:", "").strip()
                    elif "fa-shield" in icone:
                        caution = txt.replace("Caution:", "").strip()
            except Exception:
                pass

            if not titre and not acheteur:
                continue

            resultats.append({
                "date_scraping": date_scraping,
                "url_detail":    url_detail,
                "Titre":         titre,
                "Procedure":     procedure,
                "Acheteur":      acheteur,
                "Categorie":     categorie,
                "Lieu":          lieu,
                "Date_pub":      date_pub,
                "Date_limite":   date_limite,
                "Estimation":    estimation,
                "Caution":       caution,
            })

        except Exception as e:
            print(f"  [WARN] Carte ignoree : {e}")
            continue

    return resultats


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    driver = creer_driver()

    try:
        # 1. Connexion
        se_connecter(driver)

        # 2. Aller sur la page des offres
        driver.get(URL_OFFRES)
        time.sleep(PAUSE)

        # 3. Appliquer les filtres
        appliquer_filtres(driver)

        # 4. Charger tous les resultats via scroll
        scroll_tout_charger(driver)

        # 5. Scraper toutes les cartes
        data = scraper_cartes(driver)

    except Exception as e:
        print(f"\n[ERREUR] {e}")
        data = []

    finally:
        driver.quit()

    # Export Excel
    ordre_colonnes = [
        "date_scraping",
        "url_detail",
        "Titre",
        "Procedure",
        "Acheteur",
        "Categorie",
        "Lieu",
        "Date_pub",
        "Date_limite",
        "Estimation",
        "Caution",
    ]

    if data:
        df = pd.DataFrame(data)[ordre_colonnes]
        df = df.drop_duplicates(subset=["url_detail"], keep="first")
    else:
        print("\n[WARN] Aucune donnee recuperee.")
        df = pd.DataFrame(columns=ordre_colonnes)

    nom_fichier = f"lesoffres_filtres_{date_scraping}.xlsx"
    df.to_excel(nom_fichier, index=False)
    print(f"\nFichier exporte : {nom_fichier}")
    print(f"Total           : {len(df)} offres\n")
    print(df.head(10).to_string())

    return df


if __name__ == "__main__":
    df = main()
