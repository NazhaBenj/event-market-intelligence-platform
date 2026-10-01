import random
import time
import re
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ============================================================
# CONFIGURATION DES FICHIERS
# ============================================================
FICHIER_DATAMART = "Datamart_Identifications_Complet.xlsx" 
FICHIER_BD_FINAL = "DataMart_Final_Global.xlsx" 
FICHIER_OUTPUT   = "Nouveaux_Prestataires_Bios.xlsx" 
FICHIER_CHECKPOINT = "checkpoint_bios.txt" 

SAVE_EVERY = 5

# ============================================================
# 1. PRÉPARATION DES DONNÉES (RÉCONCILIATION & TRAÇABILITÉ)
# ============================================================
print("📂 Chargement des fichiers Excel...")

try:
    df_datamart = pd.read_excel(FICHIER_DATAMART, dtype=str).fillna("")
    df_bd = pd.read_excel(FICHIER_BD_FINAL, dtype=str).fillna("")
except FileNotFoundError as e:
    print(f"❌ Erreur de fichier : {e}")
    exit()

def extraire_username_pur(texte):
    """Extrait un nom d'utilisateur pur depuis une URL ou un Tag"""
    texte = str(texte).strip().lower()
    if not texte: return None
    if "instagram.com" in texte:
        m = re.search(r"instagram\.com/([^/?#\s]+)", texte)
        return m.group(1).strip("/") if m else None
    if texte.startswith("@"):
        return texte.replace("@", "").strip()
    return texte

# A. Récupérer tous les usernames existants
print("🔍 Analyse de la base existante...")
usernames_existants = set()
for url in df_bd["URL_Instagram"]:
    user = extraire_username_pur(url)
    if user:
        usernames_existants.add(user)

# B. Extraire les tags uniques ET LEUR COMPTE D'ORIGINE
print("🧹 Extraction des tags et de leurs prestataires d'origine...")
dictionnaire_tags_sources = {}

for idx, row in df_datamart.iterrows():
    nom_source = str(row.get("Nom", "")).strip()
    if not nom_source:
        continue

    for col in ["Auteurs_posts", "Comptes_identifies"]:
        if col in df_datamart.columns:
            cellule = row[col]
            if pd.notna(cellule) and cellule not in ["Aucun", "Erreur", "Prive", ""]:
                tags = [t.strip() for t in str(cellule).split(",")]
                for tag in tags:
                    user = extraire_username_pur(tag)
                    if user:
                        if user not in dictionnaire_tags_sources:
                            dictionnaire_tags_sources[user] = set()
                        # On ajoute le nom du prestataire qui l'a tagué
                        dictionnaire_tags_sources[user].add(nom_source)

tags_uniques = set(dictionnaire_tags_sources.keys())

print(f"✅ Bilan : {len(tags_uniques)} comptes uniques identifiés dans le réseau.")
print(f"✅ Bilan : {len(usernames_existants)} comptes déjà connus dans bd_final.xlsx.\n")

# C. Gestion du Checkpoint
deja_faits = set()
resultats = []
if os.path.exists(FICHIER_OUTPUT):
    try:
        df_out = pd.read_excel(FICHIER_OUTPUT, dtype=str).fillna("")
        deja_faits.update(df_out["Username"].dropna().tolist())
        resultats = df_out.to_dict("records")
    except Exception: pass

if os.path.exists(FICHIER_CHECKPOINT):
    try:
        with open(FICHIER_CHECKPOINT, "r", encoding="utf-8") as f:
            deja_faits.update(f.read().splitlines())
    except Exception: pass

tags_a_traiter = [user for user in dictionnaire_tags_sources.keys() if user not in deja_faits]
print(f"🚀 Il reste {len(tags_a_traiter)} comptes à traiter (nouveaux + anciens non vérifiés).")

# ============================================================
# 2. FONCTIONS DE SCRAPING
# ============================================================
def texte(parent, xpath):
    try:
        return parent.find_element(By.XPATH, xpath).text.strip()
    except Exception:
        return ""

def decoder_lien(href):
    try:
        qs = parse_qs(urlparse(href).query)
        if "u" in qs:
            return unquote(qs["u"][0]).split("?")[0]
    except Exception:
        pass
    return href

# ============================================================
# 3. LANCEMENT DE CHROME
# ============================================================
if not tags_a_traiter:
    print("🎉 Tous les comptes ont déjà été traités ! Fin du script.")
    exit()

options = webdriver.ChromeOptions()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

print("🚀 Lancement du navigateur Chrome...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
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
# 4. BOUCLE D'ANALYSE ET DE SCRAPING
# ============================================================
total_a_faire = len(tags_a_traiter)

try:
    for idx, username in enumerate(tags_a_traiter):
        
        # Récupération des prestataires d'origine (joint avec un | s'il y en a plusieurs)
        sources_origine = " | ".join(sorted(list(dictionnaire_tags_sources.get(username, []))))

        # Structure de base de la ligne Excel avec la nouvelle colonne
        data = {
            "Compte_Origine": sources_origine,
            "Username": username,
            "URL_Instagram": f"https://www.instagram.com/{username}/",
            "Existe_Dans_BD_Final": "Non",
            "Pseudo": "",
            "Publications": "",
            "Followers": "",
            "Following": "",
            "Categorie": "",
            "Bio": "",
            "Adresse": "",
            "Lien_Threads": "",
            "Liens_externes": ""
        }

        print(f"[{idx + 1}/{total_a_faire}] @{username} (Tagué par : {sources_origine[:40]}...)")

        # VÉRIFICATION : Le compte existe-t-il déjà ?
        if username in usernames_existants:
            print("   => 🟢 DÉJÀ DANS LA BASE. Scraping ignoré.")
            data["Existe_Dans_BD_Final"] = "Oui"
            resultats.append(data)
            
            with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                f.write(username + "\n")
            continue

        # SI NOUVEAU COMPTE : Scraping de la Bio
        print("   => 🔵 NOUVEAU COMPTE. Lancement du Scraping de la Bio...")
        try:
            driver.get(data["URL_Instagram"])
            time.sleep(random.uniform(4.0, 7.0))

            if "login" in driver.current_url or "accounts" in driver.current_url:
                print("   ⚠️ Session expirée — reconnecte-toi")
                time.sleep(random.uniform(60.0, 80.0))
                continue

            if "Page introuvable" in driver.title or "Page Not Found" in driver.title:
                print("   ❌ Compte introuvable ou supprimé.")
                data["Bio"] = "COMPTE INTROUVABLE"
                resultats.append(data)
                with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                    f.write(username + "\n")
                continue

            # --- LOGIQUE D'EXTRACTION ---
            section = driver.find_element(By.XPATH, "//section[contains(@class,'x98rzlu')]")
            blocs = section.find_elements(By.XPATH, "./div[contains(@class,'x7a106z')]")
            header_info = blocs[0] if len(blocs) > 0 else section
            bio_info    = blocs[1] if len(blocs) > 1 else section

            data["Pseudo"] = texte(header_info, ".//h2/span") or texte(header_info, ".//div[contains(@class,'x1e56ztr')]")

            try:
                counts_div = header_info.find_element(By.XPATH, ".//div[contains(@class,'x1e56ztr')]/following-sibling::div[1]")
                counts = counts_div.find_elements(By.XPATH, "./div")
                for c in counts:
                    txt = c.text.strip()
                    try:
                        exact = c.find_element(By.XPATH, ".//span[@title]").get_attribute("title")
                        txt = f"{txt} ({exact})"
                    except Exception:
                        pass
                    low = txt.lower()
                    if "publication" in low or "post" in low:
                        data["Publications"] = txt
                    elif "follower" in low or "abonné" in low:
                        data["Followers"] = txt
                    elif "suivi" in low or "following" in low:
                        data["Following"] = txt
            except Exception:
                pass

            try:
                plus_btn = bio_info.find_element(By.XPATH, ".//div[@role='button' and .//span[text()='plus' or text()='more']]")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", plus_btn)
                driver.execute_script("arguments[0].click()", plus_btn)
                time.sleep(1)
            except Exception:
                pass

            data["Categorie"] = texte(bio_info, ".//div[contains(@class,'_ap3a') and contains(@class,'_aacy') and contains(@class,'_aad6')]")
            data["Bio"]       = texte(bio_info, ".//span[contains(@class,'_ap3a') and contains(@class,'_aacx') and contains(@class,'_aad7')]")
            data["Adresse"]   = texte(bio_info, ".//h1[contains(@class,'_ap3a') and contains(@class,'_aacy') and contains(@class,'_aad6')]")

            try:
                data["Lien_Threads"] = bio_info.find_element(By.XPATH, ".//a[contains(@href,'threads.com')]").get_attribute("href")
            except Exception:
                pass

            liens_trouves = []
            try:
                bouton_liens = bio_info.find_element(By.XPATH, ".//button[contains(@class,'_aswp')]")
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", bouton_liens)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click()", bouton_liens)
                time.sleep(1.5)

                dialog = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.XPATH, "//div[@aria-modal='true']"))
                for a in dialog.find_elements(By.TAG_NAME, "a"):
                    href = a.get_attribute("href") or ""
                    texte_affiche = a.text.strip()
                    if href:
                        liens_trouves.append(f"{texte_affiche} : {decoder_lien(href)}")
                try:
                    fermer = dialog.find_element(By.XPATH, ".//div[@aria-label='Fermer' or @aria-label='Close']")
                    driver.execute_script("arguments[0].click()", fermer)
                except Exception: pass
            except Exception:
                pass

            if not liens_trouves:
                try:
                    lien_unique = texte(bio_info, ".//button[contains(@class,'_aswp')]//div[contains(@class,'_aada')]")
                    if lien_unique:
                        liens_trouves.append(lien_unique)
                except Exception:
                    pass

            data["Liens_externes"] = " | ".join(liens_trouves)

            print(f"      [✓] Bio extraite. ({data['Followers']})")
            resultats.append(data)

            with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                f.write(username + "\n")

        except Exception as e:
            if "invalid session id" in str(e):
                raise e
            print("   ❌ Profil privé ou inatteignable.")
            data["Bio"] = "ERREUR OU PRIVE"
            resultats.append(data)
            with open(FICHIER_CHECKPOINT, "a", encoding="utf-8") as f:
                f.write(username + "\n")

        if (idx + 1) % SAVE_EVERY == 0:
            try:
                pd.DataFrame(resultats).to_excel(FICHIER_OUTPUT, index=False)
            except PermissionError:
                print("   [⚠️ FERME LE FICHIER EXCEL DE SORTIE !]")

        time.sleep(random.uniform(2.0, 5.0))

except KeyboardInterrupt:
    print("\n🛑 Interruption manuelle détectée.")

finally:
    try:
        pd.DataFrame(resultats).to_excel(FICHIER_OUTPUT, index=False)
        print(f"\n🎉 Terminé ! Les données sont sauvegardées dans {FICHIER_OUTPUT}")
    except PermissionError:
        print(f"\n❌ ERREUR : Le fichier {FICHIER_OUTPUT} est ouvert. Les données n'ont pas pu être sauvegardées.")
    
    try:
        driver.quit()
    except:
        pass