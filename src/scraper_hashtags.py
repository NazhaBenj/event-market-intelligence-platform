import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================
# CONFIGURATION
# ============================================================
FICHIER_SOURCE  = r"C:\Users\Admin\Desktop\stage D&A\DataMart_Final_Global.xlsx"
FICHIER_RESULT  = r"C:\Users\Admin\Desktop\stage D&A\DataMart_Hashtags_Insta.xlsx"
CHROMEDRIVER    = r"C:\Users\Admin\.wdm\drivers\chromedriver\win64\149.0.7827.55\chromedriver-win32\chromedriver.exe"
NB_POSTS        = 9   # nombre de posts a analyser par profil
SAVE_EVERY      = 5

# ============================================================
# CHARGEMENT
# ============================================================
df_source = pd.read_excel(FICHIER_SOURCE, dtype=str)
df_source.fillna("", inplace=True)

# Garder seulement les lignes avec une URL Instagram valide
df = df_source[df_source["URL_Instagram"].str.contains("instagram.com", na=False)].copy()
df = df.reset_index(drop=True)
total = len(df)

print(f"Prestataires avec Instagram : {total}")

# Charger checkpoint si existant
try:
    df_done = pd.read_excel(FICHIER_RESULT, dtype=str)
    deja_faits = set(df_done["URL_Instagram"].dropna().tolist())
    print(f"Checkpoint : {len(deja_faits)} deja traites")
except Exception:
    df_done = pd.DataFrame()
    deja_faits = set()

resultats = df_done.to_dict("records") if not df_done.empty else []

# ============================================================
# NORMALISER URL
# ============================================================
def url_propre(url):
    m = re.search(r"instagram\.com/([^/?#\s]+)", url)
    if m:
        username = m.group(1).strip("/")
        return f"https://www.instagram.com/{username}/"
    return None

# ============================================================
# EXTRAIRE HASHTAGS D'UN TEXTE
# ============================================================
def extraire_hashtags(texte):
    tags = re.findall(r"#[\wÀ-ɏ؀-ۿ]+", texte)
    return [t.lower() for t in tags]

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
print("\n" + "=" * 55)
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
# SCRAPING DES HASHTAGS
# ============================================================
for idx, row in df.iterrows():
    url_raw = str(row.get("URL_Instagram", "")).strip()

    # Sauter si deja traite
    if url_raw in deja_faits:
        continue

    url = url_propre(url_raw)
    if not url:
        continue

    nom        = str(row.get("Nom", "")).strip()
    source     = str(row.get("Source", "")).strip()
    categorie  = str(row.get("Categorie_Propre", "")).strip()
    ville      = str(row.get("Ville", "")).strip()

    print(f"[{idx+1}/{total}] {nom} — {url}")

    try:
        # Aller sur le profil
        driver.get(url)
        time.sleep(5)

        if "login" in driver.current_url or "accounts" in driver.current_url:
            print("   => Session expiree — reconnecte-toi (60s)")
            time.sleep(60)
            continue

        # Trouver les vignettes des posts sur la page profil
        posts = driver.find_elements(By.XPATH, "//article//a[contains(@href,'/p/')]")
        if not posts:
            posts = driver.find_elements(By.XPATH, "//a[contains(@href,'/p/')]")

        posts = posts[:NB_POSTS]
        print(f"   => {len(posts)} posts trouves")

        if not posts:
            resultats.append({
                "Nom": nom, "Source": source,
                "Categorie_Propre": categorie, "Ville": ville,
                "URL_Instagram": url_raw,
                "Hashtags": "Aucun post",
                "Nombre_hashtags": 0
            })
            deja_faits.add(url_raw)
            continue

        # Collecter les URLs des posts
        urls_posts = []
        for post in posts:
            href = post.get_attribute("href")
            if href and "/p/" in href and href not in urls_posts:
                urls_posts.append(href)

        # Ouvrir chaque post et extraire les hashtags
        tous_hashtags = []

        for url_post in urls_posts:
            try:
                driver.get(url_post)
                time.sleep(4)

                # Chercher la description du post (contient les hashtags)
                texte_post = ""

                # Methode 1 : balise meta description
                try:
                    meta = driver.find_element(
                        By.XPATH, "//meta[@name='description']"
                    ).get_attribute("content") or ""
                    texte_post += " " + meta
                except Exception:
                    pass

                # Methode 2 : texte visible de la page
                try:
                    body = driver.find_element(By.TAG_NAME, "body").text
                    texte_post += " " + body
                except Exception:
                    pass

                tags = extraire_hashtags(texte_post)
                tous_hashtags.extend(tags)

            except Exception as e:
                if "invalid session id" in str(e):
                    raise e
                continue

        # Dedupliquer les hashtags
        hashtags_uniques = list(dict.fromkeys(tous_hashtags))
        hashtags_str = ", ".join(hashtags_uniques)

        print(f"   => {len(hashtags_uniques)} hashtags : {hashtags_str[:80]}...")

        resultats.append({
            "Nom": nom,
            "Source": source,
            "Categorie_Propre": categorie,
            "Ville": ville,
            "URL_Instagram": url_raw,
            "Hashtags": hashtags_str,
            "Nombre_hashtags": len(hashtags_uniques)
        })
        deja_faits.add(url_raw)

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
                "Hashtags": "Erreur",
                "Nombre_hashtags": 0
            })
            deja_faits.add(url_raw)

    # Sauvegarde periodique
    if (idx + 1) % SAVE_EVERY == 0:
        try:
            pd.DataFrame(resultats).to_excel(FICHIER_RESULT, index=False)
            print(f"   [Sauvegarde {idx+1}/{total}]")
        except PermissionError:
            print("   [Ferme le fichier Excel !]")

    time.sleep(2)

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
