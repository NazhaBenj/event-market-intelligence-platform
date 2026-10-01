import pandas as pd
import unicodedata
import re

# ── CHARGEMENT ───────────────────────────────────────────────
fichier_entree = "GoAfrica.xlsx"

print(f"Chargement du fichier {fichier_entree}...")
df = pd.read_excel(fichier_entree)
print(f"Fichier chargé : {df.shape[0]} lignes.")

# ── NETTOYAGE TÉLÉPHONES ─────────────────────────────────────
print("\nNettoyage des téléphones...")

def format_numero_marocain_final(num):
    if pd.isna(num):
        return ""
    num_propre = str(num).replace(" ", "").replace("-", "").replace(".", "").replace("+", "")
    if num_propre.startswith("212"):
        num_propre = num_propre[3:]
    if num_propre.startswith("0"):
        pass
    elif len(num_propre) == 9 and num_propre[0] in ["5", "6", "7"]:
        num_propre = "0" + num_propre
    if len(num_propre) == 10 and num_propre.isdigit():
        return f"{num_propre[0:2]} {num_propre[2:4]} {num_propre[4:6]} {num_propre[6:8]} {num_propre[8:10]}"
    return str(num).strip()

df["Telephone_1"] = df["Telephone_1"].apply(format_numero_marocain_final)
df["Telephone_2"] = df["Telephone_2"].apply(format_numero_marocain_final)

condition_doublon = (df["Telephone_1"] == df["Telephone_2"]) & (df["Telephone_1"] != "")
nb_doublons = condition_doublon.sum()
df.loc[condition_doublon, "Telephone_2"] = ""

print(f"  Numéros formatés.")
print(f"  {nb_doublons} doublons supprimés de Telephone_2.")

filtre_differents = (
    (df["Telephone_1"] != df["Telephone_2"]) &
    (df["Telephone_1"] != "") &
    (df["Telephone_2"] != "")
)
print(f"  {filtre_differents.sum()} profils avec deux numéros distincts.")

# ── ADRESSES ─────────────────────────────────────────────────
print("\nAdresses deja extraites (Adresse, Region, Ville, Pays).")
colonnes_verif = ["Adresse", "Region", "Ville", "Pays"]
for col in colonnes_verif:
    if col not in df.columns:
        df[col] = ""
nb_vides = ((df[colonnes_verif].fillna("") == "").any(axis=1)).sum()
print(f"  Lignes avec cases vides : {nb_vides}")

# ── SUPPRESSION COLONNES ─────────────────────────────────────
print("\nSuppression des colonnes inutiles...")
colonnes_a_supprimer = ["URL_Youtube", "URL_LinkedIn", "Description"]
colonnes_existantes = [col for col in colonnes_a_supprimer if col in df.columns]
if colonnes_existantes:
    df = df.drop(columns=colonnes_existantes)
    print(f"  Supprimées : {colonnes_existantes}")

# ── NETTOYAGE ABONNÉS ────────────────────────────────────────
print("\nNettoyage des abonnés...")
if "Facebook_Followers" in df.columns:
    df["Facebook_Followers"] = pd.to_numeric(
        df["Facebook_Followers"].astype(str).str.replace(r'[^\d]', '', regex=True),
        errors='coerce'
    )
if "Instagram_Followers" in df.columns:
    df["Instagram_Followers"] = pd.to_numeric(
        df["Instagram_Followers"].astype(str).str.replace(r'[^\d]', '', regex=True),
        errors='coerce'
    )
print("  Abonnés convertis en entiers.")

# ── ID_PRESTATAIRE ───────────────────────────────────────────
print("\nGeneration des IDs prestataires...")

def slugify(texte):
    texte = str(texte).strip().lower()
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    texte = re.sub(r"[^a-z0-9]+", "_", texte)
    texte = texte.strip("_")
    return texte

def generer_id(nom, ville, numero):
    nom_slug  = slugify(nom)[:20]
    ville_slug = slugify(ville)[:15] if ville else "maroc"
    return f"pr_{nom_slug}_{ville_slug}_{numero}"

df["ID_Prestataire"] = [
    generer_id(row["Nom"], row.get("Ville", ""), i + 1)
    for i, (_, row) in enumerate(df.iterrows())
]
print(f"  IDs generes. Exemple : {df['ID_Prestataire'].iloc[0]}")

# ── SOURCE ───────────────────────────────────────────────────
print("\nNettoyage colonne Source...")
if "Source" in df.columns:
    df["Source"] = "GoAfrica"
    print("  Source remplacee par 'GoAfrica'.")

# ── EXPORT ───────────────────────────────────────────────────
fichier_export = "GoAfrica_CLEAN.xlsx"
print(f"\nSauvegarde dans {fichier_export}...")
try:
    df.to_excel(fichier_export, index=False)
    print(f"Exportation réussie : {df.shape[0]} lignes, {df.shape[1]} colonnes.")
except PermissionError:
    print(f"Erreur : ferme le fichier '{fichier_export}' dans Excel et relance.")
