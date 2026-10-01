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
FICHIER_SOURCE     = r"C:\Users\Admin\Desktop\stage D&A\DataMart_Final_Global.xlsx"
FICHIER_RESULT     = r"C:\Users\Admin\Desktop\stage D&A\DataMart_Tags_Instagram.xlsx"
FICHIER_CHECKPOINT = r"C:\Users\Admin\Desktop\stage D&A\checkpoint_tags.txt"
CHROMEDRIVER       = r"C:\Users\Admin\.wdm\drivers\chromedriver\win64\149.0.7827.55\chromedriver-win32\chromedriver.exe"
NB_POSTS           = 9    # posts analyses par profil
TEST_LIMIT         = 5    # mettre 99999 pour tout traiter

EXCLUS = {
    "p", "reel", "reels", "explore", "accounts", "stories",
    "tv", "tagged", "about", "directory", "legal", "help",
    "privacy", "terms", "press", "api", "blog", "jobs"
}

# ============================================================
# CHARGEMENT
# ============================================================
print(f"Chargement {FICHIER_SOURCE}...")
df_source = pd.read_excel(FICHIER_SOURCE, dtype=str)
df_source.fillna("", inplace=True)

df = df_source[df_source["URL_Instagram"].str.contains("instagram.com", na=False)].copy()
df = df.reset_index(drop=True)
df = df.head(TEST_LIMIT)
total = len(df)
print(f"Prestataires avec Instagram : {total}")

# Checkpoint
deja_faits = set()
if os.path.exists(FICHIER_CHECKPOINT):
    with open(FICHIER_CHECKPOINT, "r", encoding="utf-8") as f:
        deja_faits = set(f.read().splitlines())
print(f"Deja traites : {len(deja_faits)}\n")

# Charger resultats existants
resultats = []
if os.path.exists(FICHIER_RESULT):
    try:
        df_old = pd.read_excel(FICHIER_RESULT, dtype=str)
        resultats = df_old.to_dict("records")
    except Exception:
        pass

# ============================================================
# UTILITAIRES
# ============================================================
def extraire_username(href):
    if not href:
        return None
    # Lien absolu : https://www.instagram.com/username/
    m = re.search(r"instagram\.com/([^/?#\s]+)", href)
    if m:
        u = m.group(1).strip("/").lower()
        return u if u not in EXCLUS else None
    # Lien relatif : /username/ ou /username
    m2 = re.match(r"^/([a-zA-Z0-9_\.]+)/?$", href)
    if m2:
        u = m2.group(1).strip("/").lower()
        return u if u not in EXCLUS else None
    return None

def username_vers_url(username):
    return f"https://www.instagram.com/{username}/"

# ============================================================
# LANCEMENT CHROME
# ============================================================
options = webdriver.ChromeOptions()
options.add_argument("--disable-notifications")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# ============================================================
# CONNEXION INSTAGRAM
# ============================================================
driver.get("https://www.instagram.com/accounts/login/")
print("=" * 55)
print("  CONNECTE-TOI A INSTAGRAM DANS LA FENETRE CHROME")
print("  Le script demarre automatiquement apres connexion")
print("=" * 55 + "\n")

def connecte(d):
    u = d.current_url
    return (
        "instagram.com" in u
        and "accounts/login" not in u
        and "auth_platform"  not in u
        and "challenge"      not in u
    )

WebDriverWait(driver, 600).until(connecte)
print("Connecte ! Debut dans 5 secondes...\n")
time.sleep(5)

# ============================================================
# FONCTION : extraire tags d'un post (gere les 2 types)
# ============================================================
def extraire_tags_post(url_post):
    """
    TYPE 1 - Bulles image : les tags sont dans des <div class="_aa1y"><a href="/user/">
              Ils sont DEJA dans le DOM sans clic (href recuperable directement).
    TYPE 2 - Popup dialog : cliquer le <button class="_aswp"> puis lire le dialog.
    """
    driver.get(url_post)
    time.sleep(5)

    usernames_trouves = []

    # ── TYPE 1 : chercher les <div class="_aa1y"> directement ─────────
    # Ces divs contiennent les <a href="/username/"> des comptes tagués.
    # Ils sont dans le DOM meme avant le clic (scale=0 -> pas de texte visible
    # mais le href est accessible).
    try:
        aa1y = driver.find_elements(By.XPATH, "//div[contains(@class,'_aa1y')]//a[@href]")
        for a in aa1y:
            href = a.get_attribute("href") or ""
            u = extraire_username(href)
            if u and u not in usernames_trouves:
                usernames_trouves.append(u)
                print(f"      [_aa1y] @{u}")
    except Exception:
        pass

    if usernames_trouves:
        return usernames_trouves

    # ── TYPE 2 : cliquer le bouton Identifications -> popup dialog ─────
    clique = False

    # M1 : bouton contenant <title>Identifications</title>
    try:
        btn = driver.find_element(
            By.XPATH, "//button[.//title[text()='Identifications']]"
        )
        driver.execute_script("arguments[0].click()", btn)
        time.sleep(3)
        clique = True
    except Exception:
        pass

    # M2 : bouton par classe legacy _aswp
    if not clique:
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(@class,'_aswp')]")
            driver.execute_script("arguments[0].click()", btn)
            time.sleep(3)
            clique = True
        except Exception:
            pass

    # M3 : aria-label sur SVG ou ancetre
    if not clique:
        try:
            for sel in [
                "//button[@aria-label]",
                "//div[@role='button'][@aria-label]",
            ]:
                for el in driver.find_elements(By.XPATH, sel):
                    aria = (el.get_attribute("aria-label") or "").lower()
                    if "identif" in aria or "tag" in aria:
                        driver.execute_script("arguments[0].click()", el)
                        time.sleep(3)
                        clique = True
                        break
                if clique:
                    break
        except Exception:
            pass

    if clique:
        try:
            popup = driver.find_element(By.XPATH, "//div[@role='dialog']")
            for a in popup.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href") or ""
                u = extraire_username(href)
                if u and u not in usernames_trouves:
                    usernames_trouves.append(u)
                    print(f"      [Dialog] @{u}")
        except Exception:
            pass

    return usernames_trouves

# ============================================================
# SCRAPING PRINCIPAL
# ============================================================
try:
    for idx, row in df.iterrows():
        url_raw      = str(row.get("URL_Instagram", "")).strip()
        nom          = str(row.get("Nom", "")).strip()
        source       = str(row.get("Source", "")).strip()
        categorie    = str(row.get("Categorie_Propre", "")).strip()
        ville        = str(row.get("Ville", "")).strip()

        # Extraire username du prestataire
        m = re.search(r"instagram\.com/([^/?#\s]+)", url_raw)
        if not m:
            continue
        username_presta = m.group(1).strip("/").lower()

        if username_presta in deja_faits:
            continue

        url_tagged = f"https://www.instagram.com/{username_presta}/tagged/"
        print(f"\n[{idx+1}/{total}] {nom} (@{username_presta})")

        try:
            driver.get(url_tagged)
            time.sleep(5)

            if "login" in driver.current_url or "accounts" in driver.current_url:
                print("   => Session expiree — reconnecte-toi")
                time.sleep(60)
                continue

            if "tagged" not in driver.current_url:
                print("   => Onglet Identifications inaccessible (prive)")
                resultats.append({
                    "Nom": nom, "Source": source,
                    "Categorie_Propre": categorie, "Ville": ville,
                    "URL_Instagram": url_raw,
                    "Tags_usernames": "Prive",
                    "Tags_liens": "Prive",
                    "Nombre_tags": 0,
                    "Posts_analyses": 0
                })
                deja_faits.add(username_presta)
                continue

            # Collecter URLs des posts
            posts = driver.find_elements(
                By.XPATH, "//a[contains(@href,'/p/') or contains(@href,'/reel/')]"
            )
            urls_posts = []
            for p in posts[:NB_POSTS]:
                href = p.get_attribute("href")
                if href and href not in urls_posts:
                    urls_posts.append(href)

            print(f"   => {len(urls_posts)} posts dans l'onglet Identifications")

            if not urls_posts:
                resultats.append({
                    "Nom": nom, "Source": source,
                    "Categorie_Propre": categorie, "Ville": ville,
                    "URL_Instagram": url_raw,
                    "Tags_usernames": "Aucun post",
                    "Tags_liens": "Aucun post",
                    "Nombre_tags": 0,
                    "Posts_analyses": 0
                })
                deja_faits.add(username_presta)
                continue

            # Analyser chaque post
            tous_tags = []
            for url_post in urls_posts:
                try:
                    tags = extraire_tags_post(url_post)
                    for t in tags:
                        if t != username_presta and t not in tous_tags:
                            tous_tags.append(t)
                except Exception as e:
                    if "invalid session id" in str(e) or "no such window" in str(e):
                        raise e
                    continue

            tags_str   = ", ".join(f"@{t}" for t in tous_tags)
            liens_str  = ", ".join(username_vers_url(t) for t in tous_tags)
            print(f"   => {len(tous_tags)} tags uniques : {tags_str[:100]}")

            resultats.append({
                "Nom": nom, "Source": source,
                "Categorie_Propre": categorie, "Ville": ville,
                "URL_Instagram": url_raw,
                "Tags_usernames": tags_str   if tous_tags else "Aucun",
                "Tags_liens":     liens_str  if tous_tags else "Aucun",
                "Nombre_tags": len(tous_tags),
                "Posts_analyses": len(urls_posts)
            })

        except Exception as e:
            err = str(e)
            if "invalid session id" in err or "no such window" in err:
                raise e
            print(f"   => Erreur : {err[:80]}")
            resultats.append({
                "Nom": nom, "Source": source,
                "Categorie_Propre": categorie, "Ville": ville,
                "URL_Instagram": url_raw,
                "Tags_usernames": "Erreur", "Tags_liens": "Erreur",
                "Nombre_tags": 0, "Posts_analyses": 0
            })

        # Sauvegarder checkpoint
        deja_faits.add(username_presta)
        with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
            f.write(username_presta + "\n")

        # Sauvegarder resultats
        try:
            pd.DataFrame(resultats).to_excel(FICHIER_RESULT, index=False)
        except PermissionError:
            print("   [Ferme le fichier Excel !]")

        time.sleep(2)

except Exception as e:
    print(f"\nErreur critique : {e}")
    if "invalid session id" in str(e) or "no such window" in str(e):
        print("Chrome a ete ferme. Relance le script pour continuer.")

# ============================================================
# SAUVEGARDE FINALE
# ============================================================
finally:
    try:
        df_final = pd.DataFrame(resultats)
        df_final.to_excel(FICHIER_RESULT, index=False)
        nb = df_final[df_final["Nombre_tags"].astype(str).str.match(r"^\d")]["Nombre_tags"].astype(int).sum()
        print(f"\nTermine ! {len(df_final)} profils traites, {nb} tags collectes.")
        print(f"Fichier : {FICHIER_RESULT}")
    except Exception as ex:
        print(f"Erreur sauvegarde : {ex}")
    try:
        driver.quit()
    except Exception:
        pass
