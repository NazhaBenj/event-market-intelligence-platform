"""
Scraper - Portail Marocain des Marchés Publics
https://www.marchespublics.gov.ma

Filtres appliqués automatiquement :
  - Mode de passation : Appel d'offres ouvert  (value="1")
  - Catégorie         : Services               (value="3")
  - Mots-clés         : restauration, traiteur, réception,
                        hébergement, séminaire, événement, animation
  (une recherche par mot-clé, résultats fusionnés et dédupliqués)

Installation :
    pip install selenium webdriver-manager pandas openpyxl

Lancement :
    python "scraper_marchespublics (4).py"
"""

import time
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManager

# ===========================================================================
# CONFIG
# ===========================================================================

URL      = "https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
BASE_URL = "https://www.marchespublics.gov.ma/"

MAX_PAGES = None   # None = tout scraper, ex: 5 pour limiter
PAGE_SIZE = "500"  # "10","20","50","100","500"
PAUSE     = 3
TIMEOUT   = 30

# IDs exacts du formulaire (extraits du HTML source)
ID_MODE_PASSATION = "ctl0_CONTENU_PAGE_AdvancedSearch_procedureType"
ID_CATEGORIE      = "ctl0_CONTENU_PAGE_AdvancedSearch_categorie"
ID_KEYWORD        = "ctl0_CONTENU_PAGE_AdvancedSearch_keywordSearch"
ID_BOUTON         = "ctl0_CONTENU_PAGE_AdvancedSearch_lancerRecherche"

# Valeurs des options (issues du HTML)
VAL_MODE_PASSATION = "1"   # Appel d'offres ouvert
VAL_CATEGORIE      = "3"   # Services

# Tous les mots-clés saisis en une seule recherche
KEYWORDS = [
    "restauration",
    "traiteur",
    "reception",
    "hebergement",
    "seminaire",
    "evenement",
    "animation",
]
# Chaîne unique envoyée dans le champ mot-clé
KEYWORD_QUERY = " ".join(KEYWORDS)

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
# TAILLE DE PAGE
# ===========================================================================

def regler_taille_page(driver):
    """Sélectionne 100 résultats par page via l'ID exact du select."""
    try:
        el = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.ID, "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop")
            )
        )
        Select(el).select_by_value(PAGE_SIZE)
        print(f"  OK Taille de page : {PAGE_SIZE}")
        time.sleep(PAUSE)
    except Exception as e:
        print(f"  [WARN] Selecteur taille de page introuvable : {e}")


# ===========================================================================
# APPLICATION DES FILTRES + LANCER RECHERCHE
# ===========================================================================

def appliquer_filtres_et_rechercher(driver, keyword):
    """
    Charge la page, sélectionne les filtres exacts et lance la recherche.
    """
    driver.get(URL)
    wait = WebDriverWait(driver, TIMEOUT)

    # 1. Attendre que le formulaire soit chargé
    wait.until(EC.presence_of_element_located((By.ID, ID_MODE_PASSATION)))
    time.sleep(1)

    # 2. Mode de passation → Appel d'offres ouvert (value="1")
    try:
        sel = Select(driver.find_element(By.ID, ID_MODE_PASSATION))
        sel.select_by_value(VAL_MODE_PASSATION)
        print(f"  OK Mode de passation : Appel d'offres ouvert")
    except Exception as e:
        print(f"  [WARN] Mode de passation : {e}")

    # 3. Catégorie → Services (value="3")
    try:
        sel = Select(driver.find_element(By.ID, ID_CATEGORIE))
        sel.select_by_value(VAL_CATEGORIE)
        print(f"  OK Categorie : Services")
    except Exception as e:
        print(f"  [WARN] Categorie : {e}")

    # 4. Mot-clé
    try:
        inp = driver.find_element(By.ID, ID_KEYWORD)
        inp.clear()
        inp.send_keys(keyword)
        print(f"  OK Mot-cle : {keyword}")
    except Exception as e:
        print(f"  [WARN] Mot-cle : {e}")

    # 5. Lancer la recherche
    try:
        driver.find_element(By.ID, ID_BOUTON).click()
        print(f"  OK Lancer la recherche clique")
    except Exception as e:
        print(f"  [WARN] Bouton recherche : {e}")

    time.sleep(PAUSE)

    # 6. Régler la taille de page à 100
    regler_taille_page(driver)


# ===========================================================================
# SCRAPING D'UNE PAGE
# ===========================================================================

def scraper_page(driver):
    """Extrait toutes les offres de la page courante."""
    resultats = []
    time.sleep(PAUSE)

    rows = driver.find_elements(By.CSS_SELECTOR, "table.table-results tbody tr")
    print(f"  -> {len(rows)} lignes trouvees")

    for tr in rows:
        try:
            if not tr.text.strip():
                continue

            # Objet
            objet = ""
            try:
                objet = tr.find_element(
                    By.XPATH, ".//div[contains(@id,'infosBullesObjet')]/div"
                ).text.strip()
            except Exception:
                pass
            if not objet:
                try:
                    raw   = tr.find_element(
                        By.XPATH, ".//div[contains(@id,'panelBlocObjet')]"
                    ).text.strip()
                    objet = raw.replace("Objet :", "").strip()
                except Exception:
                    pass

            # Acheteur
            acheteur = ""
            try:
                raw      = tr.find_element(
                    By.XPATH, ".//div[contains(@id,'panelBlocDenomination')]"
                ).text.strip()
                acheteur = raw.replace("Acheteur public :", "").strip()
            except Exception:
                pass

            # Categorie
            categorie = ""
            try:
                categorie = tr.find_element(
                    By.XPATH, ".//div[contains(@id,'panelBlocCategorie')]"
                ).text.strip()
            except Exception:
                pass

            # Date publication
            date_pub = ""
            try:
                date_pub = tr.find_element(
                    By.XPATH,
                    ".//div[contains(@id,'panelBlocCategorie')]/following-sibling::div[1]"
                ).text.strip()
            except Exception:
                pass

            # Reference
            reference = ""
            try:
                reference = tr.find_element(
                    By.XPATH, ".//span[contains(@id,'reference')]"
                ).text.strip()
            except Exception:
                pass

            # Lieu d'execution
            lieu = ""
            try:
                lieu = tr.find_element(
                    By.XPATH, ".//div[contains(@id,'infosLieuExecution')]/div"
                ).text.strip()
            except Exception:
                pass
            if not lieu:
                try:
                    lieu = tr.find_element(
                        By.XPATH, ".//div[contains(@id,'panelBlocLieuxExec')]"
                    ).text.strip()
                except Exception:
                    pass

            # Date limite
            date_limite = ""
            try:
                raw         = tr.find_element(By.CSS_SELECTOR, "div.cloture-line").text.strip()
                date_limite = " ".join(raw.split())
            except Exception:
                pass

            # URL detail
            url_detail = ""
            try:
                href = tr.find_element(
                    By.XPATH,
                    ".//a[contains(@href,'EntrepriseDetailConsultation')]"
                ).get_attribute("href")
                if href:
                    if href.startswith("?"):
                        url_detail = "https://www.marchespublics.gov.ma/index.php" + href
                    elif href.startswith("index.php"):
                        url_detail = "https://www.marchespublics.gov.ma/" + href
                    else:
                        url_detail = href
            except Exception:
                pass

            if not objet and not acheteur:
                continue

            resultats.append({
                "date_scraping":    date_scraping,
                "url_source":       url_detail,
                "Reference":        reference,
                "Objet":            objet,
                "Acheteur":         acheteur,
                "Categorie":        categorie,
                "Date_publication": date_pub,
                "Lieu_execution":   lieu,
                "Date_limite":      date_limite,
            })

        except Exception as e:
            print(f"    [WARN] Ligne ignoree : {e}")
            continue

    return resultats


# ===========================================================================
# PAGINATION
# ===========================================================================

def aller_page_suivante(driver):
    """Clique sur 'Suivant'. Retourne False si derniere page."""
    try:
        suivant = driver.find_element(
            By.XPATH,
            "//a[contains(@class,'next') or contains(text(),'Suivant') or contains(text(),'>')]"
        )
        if "disabled" in (suivant.get_attribute("class") or ""):
            return False
        suivant.click()
        return True
    except NoSuchElementException:
        return False


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    driver   = creer_driver()
    all_data = []

    try:
        print(f"\n{'='*60}")
        print(f"  Recherche unique : [{KEYWORD_QUERY}]")
        print(f"{'='*60}")

        # Une seule recherche avec tous les mots-clés
        appliquer_filtres_et_rechercher(driver, KEYWORD_QUERY)

        page = 1
        while True:
            print(f"\n  Page {page}")
            resultats = scraper_page(driver)
            all_data.extend(resultats)
            print(f"  -> {len(resultats)} offres  |  total : {len(all_data)}")

            if MAX_PAGES and page >= MAX_PAGES:
                print("  Limite MAX_PAGES atteinte.")
                break

            if not aller_page_suivante(driver):
                print("  Derniere page atteinte.")
                break

            page += 1

    except Exception as e:
        print(f"\n[ERREUR] {e}")

    finally:
        driver.quit()

    # Colonnes finales
    ordre_colonnes = [
        "date_scraping",
        "url_source",
        "Reference",
        "Objet",
        "Acheteur",
        "Categorie",
        "Date_publication",
        "Lieu_execution",
        "Date_limite",
    ]

    if all_data:
        df = pd.DataFrame(all_data)[ordre_colonnes]
        df = df.drop_duplicates(subset=["Reference"], keep="first")
    else:
        print("\n[WARN] Aucune donnee recuperee.")
        df = pd.DataFrame(columns=ordre_colonnes)

    nom_fichier = f"marches_publics_filtres_{date_scraping}.xlsx"
    df.to_excel(nom_fichier, index=False)
    print(f"\nFichier exporte : {nom_fichier}")
    print(f"Total final     : {len(df)} offres\n")
    print(df.head(10).to_string())

    return df


if __name__ == "__main__":
    df = main()
