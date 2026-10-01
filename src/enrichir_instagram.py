import time
import random
import os
import urllib.parse
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 0. FONCTION ANTI-CAPTCHA & AUTO-COOKIES
# ==========================================
def attendre_resolution_captcha(driver):
    while "sorry" in driver.current_url.lower() or "google.com/recaptcha" in driver.current_url.lower():
        print("   🚨 CAPTCHA DÉTECTÉ ! Résous-le manuellement dans la fenêtre Chrome...")
        time.sleep(5)
        
    try:
        boutons = driver.find_elements(By.XPATH, "//button | //div[@role='button']")
        for btn in boutons:
            texte = btn.text.lower()
            if "tout accepter" in texte or "accept all" in texte or "j'accepte" in texte:
                btn.click()
                time.sleep(2)
                break
    except Exception:
        pass

# ==========================================
# 1. FONCTION DE VALIDATION DES LIENS
# ==========================================
def extraire_meilleur_lien(driver, reseau, nom_recherche):
    if reseau == "instagram":
        mots_interdits = ['/p/', '/reel/', '/reels/', '/stories/', '/explore/', '/tags/', '/tv/', '/channel/', 'help.', 'about.']
        domaine = "instagram.com"
    else:
        mots_interdits = ['/watch/', '/videos/', '/video/', '/photos/', '/posts/', '/groups/', '/events/', '/story.php', '/reel/', '/reels/', 'permalink.php', 'help.', 'about.', '/public/', '/category/']
        domaine = "facebook.com"

    mot_cle_principal = nom_recherche.lower().split()[0] if nom_recherche.lower().split() else ""
    tous_les_liens = driver.find_elements(By.XPATH, "//a[@href]")
    
    if not tous_les_liens:
        return "Non trouvé"

    for element in tous_les_liens:
        try:
            href = element.get_attribute("href")
            if not href or domaine not in href: continue
            if any(interdit in href for interdit in mots_interdits): continue
            
            href_lower = href.lower()
            texte_lien = element.text.lower()
            
            if (mot_cle_principal != "") and (mot_cle_principal in href_lower or mot_cle_principal in texte_lien):
                return href
        except Exception: continue
    return "Non trouvé"

# ==========================================
# 2. CONFIGURATION ET CHARGEMENT DU FICHIER
# ==========================================
file_input = "DataMart_Prestataires_GoAfrica_Instagram_Final_avec_reviews.xlsx"
file_output = "DataMart_Prestataires_GoAfrica_Enrichi_RS.xlsx"

print(f"📂 Chargement de {file_input}...")
if os.path.exists(file_output):
    df = pd.read_excel(file_output, dtype=str)
    df.fillna("", inplace=True)
else:
    try:
        df = pd.read_excel(file_input, dtype=str) 
        df.fillna("", inplace=True)
        if "URL_Instagram" not in df.columns: df["URL_Instagram"] = ""
        if "URL_Facebook" not in df.columns:  df["URL_Facebook"] = ""
    except FileNotFoundError:
        print(f"❌ Erreur : Le fichier '{file_input}' est introuvable.")
        exit()

# =====================================================================
# 3. EXTRACTION INTELLIGENTE ET UNIFIÉE DES ADRESSES
# =====================================================================
print("🗺️ DÉMARRAGE : Vérification de la colonne Ville...")

if 'Lieu' in df.columns:
    df["Lieu"] = df["Lieu"].fillna("").astype(str)

    def extraire_lieu_definitif(texte):
        adresse, region, ville, pays = "", "", "", "Maroc"
        if not texte.strip(): return pd.Series(["", "", "", ""])
        lignes = [ligne.strip() for ligne in texte.split('\n') if ligne.strip()]
        if not lignes: return pd.Series(["", "", "", ""])

        cp_match = re.search(r'\b(\d{5})\b', " ".join(lignes))
        cp = cp_match.group(1) if cp_match else None

        idx_ville = -1
        for i in reversed(range(len(lignes))):
            ligne_LC = lignes[i].lower()
            if (cp and cp in lignes[i]) or ("-" in lignes[i]) or (any(v in ligne_LC for v in ["casablanca", "marrakesh", "rabat", "tanger", "agadir", "fes"])):
                if ligne_LC not in ["maroc", "morocco", "ma"]:
                    idx_ville = i
                    break
        if idx_ville == -1: idx_ville = len(lignes) - 1

        ligne_ville = lignes[idx_ville]
        if cp: ligne_ville = ligne_ville.replace(cp, "")
        ligne_ville = re.sub(r'(?i)\b(maroc|morocco)\b', '', ligne_ville)
        ligne_ville = re.sub(r'[-\,]', ' ', ligne_ville)
        ville = re.sub(r'\s+', ' ', ligne_ville).strip()

        lignes_avant = lignes[:idx_ville]
        if len(lignes_avant) == 1: adresse = lignes_avant[0]
        elif len(lignes_avant) >= 2:
            region = lignes_avant[-1]
            adresse = " - ".join(lignes_avant[:-1])

        if not region or region.strip() == "": region = ville
        return pd.Series([adresse, region, ville, pays])

    df[["Adresse", "Region", "Ville", "Pays"]] = df["Lieu"].apply(extraire_lieu_definitif)
    df = df.drop(columns=["Lieu"])
    if 'Code_Postal' in df.columns: df = df.drop(columns=["Code_Postal"])

# Correction manuelle pour Maev Maroc
nom_prestataire = "Maev Maroc"
if nom_prestataire in df["Nom"].values:
    df.loc[df["Nom"] == nom_prestataire, "Adresse"] = "Etage 5 - Appt 24، Résidence la Perle de Gueliz، Angle rue Mauritanie & Bd Mansour Eddehbi"
    df.loc[df["Nom"] == nom_prestataire, "Region"] = "Marrakesh-Safi"
    df.loc[df["Nom"] == nom_prestataire, "Ville"] = "Marrakesh"
    df.loc[df["Nom"] == nom_prestataire, "Pays"] = "Maroc"
    df.loc[df["Nom"] == nom_prestataire, "URL_Instagram"] = "https://www.instagram.com/maev_weddings"
    df.loc[df["Nom"] == nom_prestataire, "Instagram_Followers"] = "10300"

# ==========================================
# 4. LANCEMENT DU NAVIGATEUR FURTIF
# ==========================================
print("\n🚀 Lancement du navigateur Chrome furtif pour le scraping...")
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--lang=fr-MA,fr")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
driver.maximize_window()
time.sleep(2)

# ==========================================
# 5. MOTEUR DE RECHERCHE (AVEC REPRISE AUTOMATIQUE)
# ==========================================
total_lignes = len(df)
lignes_sautees = 0

try:
    for index, row in df.iterrows():
        url_insta_actuel = str(row.get("URL_Instagram", "")).strip()
        url_fb_actuel = str(row.get("URL_Facebook", "")).strip()

        # NOUVELLE LOGIQUE DE REPRISE : Si la case n'est pas vide, c'est que ça a déjà été traité (même si c'est "Non trouvé")
        insta_est_traite = url_insta_actuel != "" and url_insta_actuel.lower() != "nan"
        fb_est_traite = url_fb_actuel != "" and url_fb_actuel.lower() != "nan"

        if insta_est_traite and fb_est_traite:
            lignes_sautees += 1
            continue # On passe à la ligne suivante en silence

        if lignes_sautees > 0:
            print(f"⏩ {lignes_sautees} prestataires déjà traités ont été sautés. Reprise du scraping...")
            lignes_sautees = 0 # On réinitialise pour ne l'afficher qu'une fois lors de la reprise

        nom = str(row.get("Nom", "")).strip()
        ville = str(row.get("Ville", "")).strip() 
        cat_propre = str(row.get("Categories", "")).split('/')[0].strip()
        
        print(f"\n🔍 [{index+1}/{total_lignes}] Analyse : {nom} ({cat_propre}) à {ville}")
        
        # --- RECHERCHE INSTA ---
        if not insta_est_traite:
            query_insta = f"{nom} {cat_propre} {ville} instagram maroc"
            driver.get(f"https://www.google.com/search?q={urllib.parse.quote(query_insta)}")
            attendre_resolution_captcha(driver)
            time.sleep(random.uniform(2, 4))
            
            lien_insta = extraire_meilleur_lien(driver, "instagram", nom)
            df.at[index, "URL_Instagram"] = lien_insta
            print(f"   -> Insta : {lien_insta}")
        else:
            print(f"   -> Insta : Déjà présent ({url_insta_actuel})")

        # --- RECHERCHE FB ---
        if not fb_est_traite:
            query_fb = f"{nom} {ville} facebook maroc"
            driver.get(f"https://www.google.com/search?q={urllib.parse.quote(query_fb)}")
            attendre_resolution_captcha(driver)
            time.sleep(random.uniform(2, 4))
            
            lien_fb = extraire_meilleur_lien(driver, "facebook", nom)
            df.at[index, "URL_Facebook"] = lien_fb
            print(f"   -> FB    : {lien_fb}")
        else:
            print(f"   -> FB    : Déjà présent ({url_fb_actuel})")

        # Sauvegarde automatique toutes les 5 lignes
        if (index + 1) % 5 == 0:
            try:
                df.to_excel(file_output, index=False)
            except PermissionError:
                pass

except KeyboardInterrupt:
    print("\n\n🛑 INTERRUPT MANUELLE DÉTECTÉE (Ctrl+C appuyé) ! 🛑")
    print("⏳ Ne ferme pas la fenêtre ! Sauvegarde des données extraites en cours...")
    
except Exception as e:
    print(f"\n❌ Une erreur inattendue a stoppé le script : {e}")

finally:
    try:
        df.to_excel(file_output, index=False)
        print(f"✅ Toutes les données scrapées jusqu'ici ont été sauvegardées dans '{file_output}'")
    except PermissionError:
        print(f"❌ Impossible de sauvegarder : le fichier '{file_output}' est ouvert dans Excel ! Ferme-le.")

    try:
        driver.quit()
        print("🛑 Navigateur fermé proprement.")
    except Exception:
        pass