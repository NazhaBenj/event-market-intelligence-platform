import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ============================================================
# CONFIGURATION
# ============================================================
FICHIER_SOURCE = r"C:\Users\Admin\Desktop\stage D&A\DataMart_Identifications_Insta.xlsx"
FICHIER_RESULT = r"C:\Users\Admin\Desktop\stage D&A\DataMart_Comptes_Identifies_Followers.xlsx"
CHROMEDRIVER   = r"C:\Users\Admin\.wdm\drivers\chromedriver\win64\149.0.7827.55\chromedriver-win32\chromedriver.exe"
SAVE_EVERY     = 10

# ============================================================
# CHARGEMENT ET EXTRACTION DES COMPTES IDENTIFIES
# ============================================================
df_source = pd.read_excel(FICHIER_SOURCE, dtype=str)
df_source.fillna("", inplace=True)

# Extraire tous les @usernames uniques depuis la colonne Comptes_identifies
tous_comptes = {}  # username -> {prestataire, source, categorie, ville}

for _, row in df_source.iterrows():
    comptes_str = str(row.get("Comptes_identifies", "")).strip()
    if not comptes_str or comptes_str in ("Aucun", "Prive", "Erreur", "Aucun post"):
        continue

    prestataire = str(row.get("Nom", ""))
    source      = str(row.get("Source", ""))
    categorie   = str(row.get("Categorie_Propre", ""))
    ville       = str(row.get("Ville", ""))
    url_presta  = str(row.get("URL_Instagram", ""))

    # Parser les @usernames
    mentions = re.findall(r"@([\w\.]+)", comptes_str)
    for username in mentions:
        username = username.strip(".")
        if username and len(username) > 2 and "." not in username.split(".")[-1][:3]:
            if username not in tous_comptes:
                tous_comptes[username] = {
                    "Username"          : username,
                    "URL_Instagram"     : f"https://www.instagram.com/{username}/",
                    "Prestataire_source": prestataire,
                    "Source"            : source,
                    "Categorie_Propre"  : categorie,
                    "Ville"             : ville,
                    "URL_Prestataire"   : url_presta,
                    "Instagram_Followers": "",
                }

# Charger checkpoint si existant
try:
    df_done = pd.read_excel(FICHIER_RESULT, dtype=str)
    df_done.fillna("", inplace=True)
    # Mettre a jour avec les donnees deja scrappees
    for _, r in df_done.iterrows():
        u = str(r.get("Username", "")).strip()
        if u in tous_comptes and str(r.get("Instagram_Followers", "")).strip():
            tous_comptes[u]["Instagram_Followers"] = str(r["Instagram_Followers"])
    print(f"Checkpoint charge : {len(df_done)} entrees")
except Exception:
    pass

df_comptes = pd.DataFrame(list(tous_comptes.values()))
total = len(df_comptes)
deja  = df_comptes["Instagram_Followers"].apply(lambda v: bool(re.match(r"^\d", str(v).strip()))).sum()

print(f"Comptes identifies uniques : {total}")
print(f"Deja scrapes               : {deja}")
print(f"A traiter                  : {total - deja}\n")
print("Exemples :")
for u in list(tous_comptes.keys())[:5]:
    print(f"  {tous_comptes[u]['URL_Instagram']}")
print()

# ============================================================
# EXTRAIRE FOLLOWERS
# ============================================================
def get_followers(driver):
    try:
        meta = driver.find_element(
            By.XPATH, "//meta[@name='description']"
        ).get_attribute("content") or ""
        m = re.search(r"(\d[\d\s\.,]*[KkMm]?)\s*(Followers|abonnes?)", meta, re.IGNORECASE)
        if m:
            return m.group(1).strip().replace(" ", "")
    except Exception:
        pass
    try:
        titre = driver.title or ""
        m = re.search(r"(\d[\d\,\.]*[KkMm]?)\s*(Followers|abonnes?)", titre, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        m = re.search(r"(\d[\d\s\,\.]*[KkMm]?)\s*(abonnes?|followers?)", body, re.IGNORECASE)
        if m:
            return m.group(1).strip().replace(" ", "")
    except Exception:
        pass
    return None

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
# SCRAPING
# ============================================================
for i, (username, data) in enumerate(tous_comptes.items()):

    # Sauter si deja scrappe
    if re.match(r"^\d", str(data["Instagram_Followers"]).strip()):
        continue

    url = data["URL_Instagram"]
    print(f"[{i+1}/{total}] {url}")

    try:
        driver.get(url)
        time.sleep(5)

        if "login" in driver.current_url or "accounts" in driver.current_url:
            print("   => Session expiree — reconnecte-toi (60s)")
            tous_comptes[username]["Instagram_Followers"] = "Session expiree"
            time.sleep(60)
            continue

        titre = driver.title.lower()
        if "page not found" in titre or titre == "instagram":
            print("   => Compte inexistant")
            tous_comptes[username]["Instagram_Followers"] = "Inexistant"
            continue

        followers = get_followers(driver)
        if followers:
            print(f"   => {followers} followers")
            tous_comptes[username]["Instagram_Followers"] = followers
        else:
            print("   => Prive ou non trouve")
            tous_comptes[username]["Instagram_Followers"] = "Prive"

    except Exception as e:
        err = str(e)
        if "invalid session id" in err or "no such window" in err:
            print("\n=> Chrome ferme ! Sauvegarde et relancement...")
            pd.DataFrame(list(tous_comptes.values())).to_excel(FICHIER_RESULT, index=False)
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
            print(f"   => Erreur : {err[:60]}")
            tous_comptes[username]["Instagram_Followers"] = "Erreur"

    if (i + 1) % SAVE_EVERY == 0:
        try:
            pd.DataFrame(list(tous_comptes.values())).to_excel(FICHIER_RESULT, index=False)
            print(f"   [Sauvegarde {i+1}/{total}]")
        except PermissionError:
            print("   [Ferme le fichier Excel !]")

    time.sleep(2)

# ============================================================
# SAUVEGARDE FINALE
# ============================================================
try:
    df_final = pd.DataFrame(list(tous_comptes.values()))
    df_final.to_excel(FICHIER_RESULT, index=False)
    nb = df_final["Instagram_Followers"].apply(lambda v: bool(re.match(r"^\d", str(v).strip()))).sum()
    print(f"\nTermine ! {nb}/{total} followers trouves.")
    print(f"Fichier : {FICHIER_RESULT}")
except PermissionError:
    print("\nERREUR : Ferme le fichier Excel !")

try:
    driver.quit()
except Exception:
    pass
