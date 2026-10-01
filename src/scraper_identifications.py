import time
import re
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ============================================================
# CONFIGURATION
# ============================================================
FICHIER_SOURCE     = "DataMart_Final_Global.xlsx"
FICHIER_RESULT     = "Datamart_Identifications_Complet.xlsx"
FICHIER_CHECKPOINT = "checkpoint_identifications_complet.txt"
CHROMEDRIVER       = r"C:\Users\Admin\.wdm\drivers\chromedriver\win64\149.0.7827.55\chromedriver-win32\chromedriver.exe"

NB_POSTS       = 8   # nombre de posts a analyser dans l'onglet Identifications
SAVE_EVERY     = 1
LIGNE_DEPART   = 995   # reprendre a partir du 186e prestataire de la base source (1-indexe, hors entete)

EXCLUS = {
    "p", "reel", "reels", "explore", "accounts", "stories",
    "tv", "tagged", "about", "directory", "legal", "help",
    "privacy", "terms", "press", "api", "blog", "jobs"
}

# ============================================================
# CHARGEMENT
# ============================================================
print(f"📂 Chargement de la base '{FICHIER_SOURCE}'...")
try:
    df_source = pd.read_excel(FICHIER_SOURCE, dtype=str)
    df_source.fillna("", inplace=True)
except FileNotFoundError:
    print(f"❌ Erreur : Le fichier '{FICHIER_SOURCE}' est introuvable.")
    exit()

df_source = df_source.iloc[LIGNE_DEPART - 1:].reset_index(drop=True)

df = df_source[df_source["URL_Instagram"].str.contains("instagram.com", na=False)].copy()
df = df.reset_index(drop=True)
total = len(df)
print(f"Depart force a la ligne {LIGNE_DEPART} de la base source.")
print(f"Prestataires avec Instagram a partir de cette ligne : {total}\n")

# Depart force : on conserve les resultats deja sauvegardes mais on ne saute aucune URL
deja_faits = set()
try:
    if os.path.exists(FICHIER_RESULT):
        df_done = pd.read_excel(FICHIER_RESULT, dtype=str)
        resultats = df_done.to_dict("records")
    else:
        resultats = []
except Exception:
    resultats = []

print("Aucune verification de checkpoint : toutes les lignes a partir de "
      f"{LIGNE_DEPART} seront traitees.\n")

# ============================================================
# UTILITAIRES (MÉTHODES DE TON BINÔME)
# ============================================================
def url_propre(url):
    m = re.search(r"instagram\.com/([^/?#\s]+)", url)
    if m:
        username = m.group(1).strip("/")
        return f"https://www.instagram.com/{username}/"
    return None

def url_tagged(url):
    m = re.search(r"instagram\.com/([^/?#\s]+)", url)
    if m:
        username = m.group(1).strip("/")
        return f"https://www.instagram.com/{username}/tagged/"
    return None

def extraire_auteur(driver):
    """Recupere le username de l'auteur du post (qui a tagué le prestataire)."""
    m = re.search(r"instagram\.com/([^/]+)/(?:p|reel)/", driver.current_url)
    if m:
        u = m.group(1).strip("/").lower()
        if u and u not in EXCLUS:
            return u
    for a in driver.find_elements(By.TAG_NAME, "a"):
        href = a.get_attribute("href") or ""
        text = (a.text or "").strip()
        if not text or not href:
            continue
        m2 = re.search(r"instagram\.com/([^/?#\s]+)/?$", href)
        if not m2:
            continue
        u = m2.group(1).strip("/").lower()
        if u and u not in EXCLUS and re.match(r"^[\w.]+$", u) and text.lower() == u:
            return u
    return None

def tags_aa1y(driver):
    """TYPE 1 : tags depuis les <div class='_aa1y'><a href='/username/'> (sans clic)."""
    tags = []
    try:
        for a in driver.find_elements(By.XPATH, "//div[contains(@class,'_aa1y')]//a[@href]"):
            href = a.get_attribute("href") or ""
            m = re.search(r"instagram\.com/([^/?#\s]+)", href)
            if m:
                u = m.group(1).strip("/").lower()
                if u and u not in EXCLUS and u not in tags:
                    tags.append(u)
    except Exception:
        pass
    return tags

def tags_dialog(driver):
    """TYPE 2 : tags depuis le popup dialog apres clic sur bouton."""
    tags = []
    try:
        popup = driver.find_element(By.XPATH, "//div[@role='dialog']")
        for a in popup.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            m = re.search(r"instagram\.com/([^/?#\s]+)", href)
            if m:
                u = m.group(1).strip("/").lower()
                if u and u not in EXCLUS and u not in tags:
                    tags.append(u)
    except Exception:
        pass
    return tags

def cliquer_identifications(driver):
    """Cliquer le bouton Identifications (TYPE 2 - popup dialog)."""
    for xpath in [
        "//button[.//title[text()='Identifications']]",
        "//button[contains(@class,'_aswp')]",
    ]:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            driver.execute_script("arguments[0].click()", btn)
            time.sleep(3)
            return True
        except Exception:
            pass
    return False

def avancer_carousel(driver):
    """Cliquer la fleche Suivant du carousel. Retourne True si navigation reussie."""
    for aria in ["Suivant", "Next", "suivant", "next"]:
        try:
            btn = driver.find_element(By.XPATH, f"//button[@aria-label='{aria}']")
            driver.execute_script("arguments[0].click()", btn)
            time.sleep(2)
            return True
        except Exception:
            pass
    return False

# ============================================================
# LANCEMENT CHROME (TA MÉTHODE)
# ============================================================
options = webdriver.ChromeOptions()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

driver.get("https://www.instagram.com/accounts/login/")
print("=" * 55)
print("➡️ CONNECTE-TOI A INSTAGRAM DANS LA FENETRE CHROME")
print("=" * 55 + "\n")

def connecte(d):
    u = d.current_url
    return ("instagram.com" in u and "accounts/login" not in u and "auth_platform" not in u)

WebDriverWait(driver, 600).until(connecte)
print("✅ Connexion réussie ! Début du traitement dans 5 secondes...\n")
time.sleep(5)

# ============================================================
# SCRAPING (CODE DE TON BINÔME INTACT)
# ============================================================
try:
    for idx, row in df.iterrows():
        url_raw = str(row.get("URL_Instagram", "")).strip()

        if url_raw in deja_faits:
            continue

        url_tag = url_tagged(url_raw)
        if not url_tag:
            continue

        nom       = str(row.get("Nom", "")).strip()
        source    = str(row.get("Source", "")).strip()
        categorie = str(row.get("Categorie_Propre", "")).strip()
        ville     = str(row.get("Ville", "")).strip()

        print(f"[{idx+1}/{total}] {nom}")
        print(f"   => Onglet Identifications : {url_tag}")

        comptes_identifies = []
        auteurs_posts      = []

        try:
            driver.get(url_tag)
            time.sleep(5)

            if "login" in driver.current_url or "accounts" in driver.current_url:
                print("   => Session expiree — reconnecte-toi (60s)")
                time.sleep(60)
                continue

            if "tagged" not in driver.current_url:
                print("   => Onglet Identifications inaccessible (prive)")
                resultats.append({
                    "Nom": nom, "Source": source,
                    "Categorie_Propre": categorie, "Ville": ville,
                    "URL_Instagram": url_raw,
                    "Auteurs_posts": "Prive",
                    "Comptes_identifies": "Prive",
                    "Nombre_identifications": 0,
                })
                deja_faits.add(url_raw)
                with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                    f.write(url_raw + "\n")
                continue

            posts = driver.find_elements(By.XPATH, "//a[contains(@href,'/p/') or contains(@href,'/reel/')]")
            urls_posts = []
            for p in posts[:NB_POSTS]:
                href = p.get_attribute("href")
                if href and href not in urls_posts:
                    urls_posts.append(href)

            print(f"   => {len(urls_posts)} posts trouves dans Identifications")

            if not urls_posts:
                resultats.append({
                    "Nom": nom, "Source": source,
                    "Categorie_Propre": categorie, "Ville": ville,
                    "URL_Instagram": url_raw,
                    "Auteurs_posts": "Aucun post",
                    "Comptes_identifies": "Aucun post",
                    "Nombre_identifications": 0,
                })
                deja_faits.add(url_raw)
                with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                    f.write(url_raw + "\n")
                continue

            for url_post in urls_posts:
                try:
                    driver.get(url_post)
                    time.sleep(5)

                    auteur = extraire_auteur(driver)
                    if auteur:
                        c = f"@{auteur}"
                        if c not in auteurs_posts:
                            auteurs_posts.append(c)
                            print(f"      [Auteur] {c}")

                    tags_image = set()
                    is_reel = "/reel/" in url_post or "/reel/" in driver.current_url

                    if is_reel:
                        if cliquer_identifications(driver):
                            tags_image.update(tags_dialog(driver))
                    else:
                        tags_image = set(tags_aa1y(driver))
                        if not tags_image:
                            if cliquer_identifications(driver):
                                tags_image.update(tags_dialog(driver))
                        is_carousel = bool(driver.find_elements(By.XPATH, "//div[contains(@class,'_9zm2')]"))
                        if is_carousel:
                            for _ in range(19):
                                if not avancer_carousel(driver):
                                    break
                                tags_image.update(tags_aa1y(driver))

                    for t in tags_image:
                        c = f"@{t}"
                        if c not in comptes_identifies:
                            comptes_identifies.append(c)

                except Exception as e:
                    if "invalid session id" in str(e):
                        raise e
                    continue

            auteurs_str  = ", ".join(auteurs_posts)
            comptes_str  = ", ".join(comptes_identifies)
            print(f"   => {len(auteurs_posts)} auteurs  |  {len(comptes_identifies)} co-tags")
            print(f"      Auteurs  : {auteurs_str[:80]}")
            print(f"      Co-tags  : {comptes_str[:80]}")

            resultats.append({
                "Nom": nom, "Source": source,
                "Categorie_Propre": categorie, "Ville": ville,
                "URL_Instagram": url_raw,
                "Auteurs_posts":      auteurs_str  if auteurs_posts      else "Aucun",
                "Comptes_identifies": comptes_str  if comptes_identifies else "Aucun",
                "Nombre_identifications": len(comptes_identifies),
            })
            deja_faits.add(url_raw)
            with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                f.write(url_raw + "\n")

        except Exception as e:
            err = str(e)
            if "invalid session id" in err or "no such window" in err:
                print("\n=> Chrome ferme ! Sauvegarde et relancement...")
                pd.DataFrame(resultats).to_excel(FICHIER_RESULT, index=False)
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.get("https://www.instagram.com/accounts/login/")
                print("=> RECONNECTE-TOI a Instagram...\n")
                WebDriverWait(driver, 600).until(connecte)
                print("Connecte ! Reprise dans 5 secondes...\n")
                time.sleep(5)
                continue
            else:
                print(f"   => Erreur : {err[:80]}")
                resultats.append({
                    "Nom": nom, "Source": source,
                    "Categorie_Propre": categorie, "Ville": ville,
                    "URL_Instagram": url_raw,
                    "Auteurs_posts": "Erreur",
                    "Comptes_identifies": "Erreur",
                    "Nombre_identifications": 0,
                })
                deja_faits.add(url_raw)
                with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                    f.write(url_raw + "\n")

        if (idx + 1) % SAVE_EVERY == 0:
            try:
                pd.DataFrame(resultats).to_excel(FICHIER_RESULT, index=False)
                print(f"   [Sauvegarde {idx+1}/{total}]")
            except PermissionError:
                print("   [Ferme le fichier Excel !]")

        time.sleep(2)

except KeyboardInterrupt:
    print("\n\n=> Arret demande (Ctrl+C) — sauvegarde en cours...")

# ============================================================
# SAUVEGARDE FINALE
# ============================================================
try:
    df_final = pd.DataFrame(resultats)
    df_final.to_excel(FICHIER_RESULT, index=False)
    print(f"\nTermine ! {len(df_final)} prestataires traites.")
    print(f"Fichier : {FICHIER_RESULT}")
except PermissionError:
    print("\nERREUR : Ferme le fichier Excel !")

try:
    driver.quit()
except Exception:
    pass