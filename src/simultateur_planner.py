import os
import re
import pandas as pd
import random
import streamlit as st

# ============================================================
# 1. RÈGLES MÉTIER ET MULTIPLICATEURS (BUDGET)
# ============================================================
REGLES_TARIFICATION = {
    "Traiteur": {"prix_base": 3500, "unite": "par table (10p)", "calcul_quantite": lambda inv: inv / 10},
    "Lieu de Réception": {"prix_base": 15000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Photographe & Vidéaste": {"prix_base": 5000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Neggafa": {"prix_base": 8000, "unite": "pack complet", "calcul_quantite": lambda inv: 1},
    "DJ & Animation Musicale": {"prix_base": 4000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Pâtisserie & Cake Design": {"prix_base": 800, "unite": "par gâteau", "calcul_quantite": lambda inv: (inv / 50)},
    "Animation Enfants": {"prix_base": 1500, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Décoration & Scénographie": {"prix_base": 5000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Maquillage & Coiffure (MUA)": {"prix_base": 2500, "unite": "par prestation", "calcul_quantite": lambda inv: 1},
    "Robes de Mariée": {"prix_base": 4000, "unite": "par robe", "calcul_quantite": lambda inv: 1},
    "Wedding planner": {"prix_base": 6000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Location de Voitures": {"prix_base": 2000, "unite": "par véhicule", "calcul_quantite": lambda inv: 1},
    "Fleuriste": {"prix_base": 3000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Orchestre & Musiciens": {"prix_base": 6000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Dekka Marrakchia & Issawa": {"prix_base": 4500, "unite": "pack complet", "calcul_quantite": lambda inv: 1},
    "Service de bar & Mixologie": {"prix_base": 3500, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Magie & Spectacles": {"prix_base": 2000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Cadeaux Invités": {"prix_base": 500, "unite": "par table (10p)", "calcul_quantite": lambda inv: inv / 10},
    "Chanteur / Chanteuse": {"prix_base": 5000, "unite": "par événement", "calcul_quantite": lambda inv: 1},
    "Sécurité & Logistique": {"prix_base": 3000, "unite": "par événement", "calcul_quantite": lambda inv: 1}
}

COEF_VILLES = {
    "Casablanca": 1.4, "Rabat": 1.4, "Marrakech": 1.6,
    "Tanger": 1.2, "Agadir": 1.2, "Fès": 1.0, "Meknès": 1.0, "Oujda": 0.9
}

CONFIG_EVENEMENTS = {
    "Mariage": {
        "coef_prix": 1.0,
        "categories_requises": ["Traiteur", "Lieu de Réception", "Photographe & Vidéaste", "Neggafa", "DJ & Animation Musicale", "Maquillage & Coiffure (MUA)", "Décoration & Scénographie", "Robes de Mariée", "Wedding planner", "Location de Voitures", "Fleuriste", "Orchestre & Musiciens", "Dekka Marrakchia & Issawa"]
    },
    "Fiançailles / Khatba": {
        "coef_prix": 0.7,
        "categories_requises": ["Traiteur", "Photographe & Vidéaste", "Neggafa", "Maquillage & Coiffure (MUA)", "Décoration & Scénographie", "Fleuriste"]
    },
    "Soirée Henné": {
        "coef_prix": 0.6,
        "categories_requises": ["Neggafa", "Photographe & Vidéaste", "DJ & Animation Musicale", "Décoration & Scénographie", "Traiteur"]
    },
    "Fête de Naissance (Hqiqa / Baptême)": {
        "coef_prix": 0.6,
        "categories_requises": ["Traiteur", "Photographe & Vidéaste", "DJ & Animation Musicale", "Décoration & Scénographie", "Pâtisserie & Cake Design"]
    },
    "Baby Shower": {
        "coef_prix": 0.35,
        "categories_requises": ["Décoration & Scénographie", "Pâtisserie & Cake Design", "Photographe & Vidéaste", "Traiteur"]
    },
    "Anniversaire": {
        "coef_prix": 0.4,
        "categories_requises": ["Pâtisserie & Cake Design", "DJ & Animation Musicale", "Photographe & Vidéaste", "Décoration & Scénographie", "Service de bar & Mixologie"]
    },
    "Anniversaire Enfant": {
        "coef_prix": 0.3,
        "categories_requises": ["Pâtisserie & Cake Design", "Animation Enfants", "Magie & Spectacles", "Photographe & Vidéaste", "Cadeaux Invités"]
    },
    "Soirée Privée / VIP": {
        "coef_prix": 0.9,
        "categories_requises": ["Traiteur", "Lieu de Réception", "Service de bar & Mixologie", "DJ & Animation Musicale", "Orchestre & Musiciens", "Chanteur / Chanteuse", "Décoration & Scénographie", "Sécurité & Logistique"]
    }
}

GAMMES_FOLLOWERS = {
    "Économique / Débutant": (0, 5000),
    "Standard / Confirmé": (5000, 30000),
    "Premium / Influenceur": (30000, 150000),
    "Luxe / VIP": (150000, 5000000)
}

def calculer_coef_followers(followers):
    if followers < 5000: return 1.0
    elif followers < 30000: return 1.3
    elif followers < 150000: return 1.6
    else: return 2.0

def estimer_prix(categorie, ville, followers, nb_invites, type_event):
    if categorie not in REGLES_TARIFICATION: return 0
    prix_base = REGLES_TARIFICATION[categorie]["prix_base"]
    quantite = REGLES_TARIFICATION[categorie]["calcul_quantite"](nb_invites)
    coef_v = COEF_VILLES.get(ville, 1.0)
    coef_f = calculer_coef_followers(followers)
    coef_evt = CONFIG_EVENEMENTS[type_event]["coef_prix"]
    return int((prix_base * coef_v * coef_f * coef_evt) * quantite)

# ============================================================
# 2. DICTIONNAIRES ET OUTILS DE NETTOYAGE STRICT
# ============================================================
FICHIER_DATA_CLEAN = "Prestataires_Filtres_Categorises_finale.xlsx"
FICHIER_BD_FINAL   = "DataMart_Final_Global.xlsx"

dictionnaire_plateforme = {
    "Studio photo et vidéo": "Photographe & Vidéaste", "Photographe / Vidéaste": "Photographe & Vidéaste", "Photographes professionnels": "Photographe & Vidéaste", "Photographe": "Photographe & Vidéaste", "Vidéaste": "Photographe & Vidéaste", "Laboratoires photographiques": "Photographe & Vidéaste",
    "DJ": "DJ & Animation Musicale", "Chanteur/Chanteuse / DJ": "DJ & Animation Musicale", "Animateur enfant / DJ": "DJ & Animation Musicale",
    "Orchestre": "Orchestre & Musiciens", "Violoniste": "Orchestre & Musiciens", "Orchestre / Violoniste": "Orchestre & Musiciens", "Chanteur/Chanteuse": "Chanteur / Chanteuse",
    "Dekka Marrakchia Issawa": "Dekka Marrakchia & Issawa",
    "Traiteurs": "Traiteur", "Traiteur": "Traiteur", "Pâtissier / Cake designer / Traiteur": "Traiteur",
    "Service de bar / mixologue": "Service de bar & Mixologie", "Pâtissier / Cake designer": "Pâtisserie & Cake Design",
    "Evénementiel": "Agence Événementielle & Planner", "Event planner": "Agence Événementielle & Planner", "Structures événementielles": "Agence Événementielle & Planner", "Wedding planner": "Wedding planner",
    "Décoration d'intérieur": "Décoration & Scénographie", "Décorateur": "Décoration & Scénographie",
    "Fleuristes": "Fleuriste", "Fleuriste événementiel": "Fleuriste",
    "Lieu de réception": "Lieu de Réception", "Location de voitures": "Location de Voitures", "Location de voiture de mariage": "Location de Voitures",
    "Makeup Artist": "Maquillage & Coiffure (MUA)", "Hairstylist": "Maquillage & Coiffure (MUA)", "Hairstylist / Makeup Artist": "Maquillage & Coiffure (MUA)",
    "Neggafa": "Neggafa", "Robes de mariés": "Robes de Mariée", "Spa / soins esthétiques": "Bien-être & Esthétique",
    "Animateur enfant / Jeux animations enfants": "Animation Enfants", "Structures gonflables": "Animation Enfants", "Magicien": "Magie & Spectacles",
    "Location de matériels pour réception": "Location de Matériel & Tentes", "Sécurité événementielle": "Sécurité & Logistique", "Sécurité événementielle / VTC / Transport invités": "Sécurité & Logistique", "Créateur de cadeaux invités": "Cadeaux Invités",
    "Florist": "Fleuriste", "Dresses": "Robes de Mariée", "Venues": "Lieu de Réception",
    "Beauty": "Maquillage & Coiffure (MUA)", "Photo-film": "Photographe & Vidéaste",
    "Caterer": "Traiteur", "Catering": "Traiteur", "Decor": "Décoration & Scénographie",
    "Negafa": "Neggafa", "Artist": "DJ & Animation Musicale",
    "Event-planner": "Agence Événementielle & Planner", "Cakes": "Pâtisserie & Cake Design"
}

VILLES_MAROC_MAPPING = {
    "Casablanca": "Casablanca", "Rabat": "Rabat", "Marrakech": "Marrakech", "Marrakesh": "Marrakech", "Fès": "Fès", "Fes": "Fès",
    "Tanger": "Tanger", "Agadir": "Agadir", "Meknès": "Meknès", "Meknes": "Meknès", "Oujda": "Oujda", "Kénitra": "Kénitra", "Kenitra": "Kénitra",
    "Tétouan": "Tétouan", "Salé": "Salé", "Sale": "Salé", "El Jadida": "El Jadida", "Béni Mellal": "Béni Mellal"
}

REGEX_TEL_ETRANGER = re.compile(r"\+\s*(?!212)\d{1,3}[\s.\-]?\d{4,}")
REGEX_ALPHABET_ASIATIQUE = re.compile(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")
BLACKLIST = ["blog", "blogger", "lifestyle", "influencer", "influenceur", "student", "prêt-à-porter", "shoes", "boutique en ligne", "dropshipping", "cosmetics", "boda", "bodas", "novia", "madrid", "paris", "london", "dubai"]

def normaliser_categorie(cat_brute):
    cat_clean = str(cat_brute).strip()
    for anc, off in dictionnaire_plateforme.items():
        if cat_clean.lower() == anc.lower(): return off
    for off in set(dictionnaire_plateforme.values()):
        if cat_clean.lower() == off.lower(): return off
    return "Sans catégorie"

def extraire_ville_normalisee(adresse, bio):
    texte = str(adresse) + " " + str(bio)
    for var, off in VILLES_MAROC_MAPPING.items():
        if re.search(r"\b" + re.escape(var) + r"\b", texte, re.IGNORECASE): return off
    return "Inconnue"

def nettoyer_followers(texte):
    txt = str(texte).lower().replace(" ", "").replace(",", ".")
    m = re.search(r'([0-9.]+)([km]?)', txt)
    if not m: return 0
    val, mult = float(m.group(1)), m.group(2)
    return int(val * 1000) if mult == 'k' else (int(val * 1000000) if mult == 'm' else int(val))

def passe_filtre_strict(row):
    texte = f"{row.get('Bio','')} {row.get('Adresse','')} {row.get('Pseudo','')} {row.get('Username','')}".lower()
    foll = nettoyer_followers(row.get("Followers_Propre", "0"))
    if foll >= 1000000 or REGEX_TEL_ETRANGER.search(texte) or REGEX_ALPHABET_ASIATIQUE.search(texte): return False
    for mot in BLACKLIST:
        if re.search(r"\b" + re.escape(mot) + r"\b", texte): return False
    return True

# ============================================================
# 3. FUSION DES DONNÉES ET CALCUL DE LA POPULARITÉ
# ============================================================
@st.cache_data
def charger_et_unifier_donnees():
    prestataires_dict = {}
    
    # --- ETAPE A : Calculer la popularité (Nombre de Tags) ---
    df_scraped = pd.DataFrame()
    tag_counts = {}
    if os.path.exists(FICHIER_DATA_CLEAN):
        df_scraped = pd.read_excel(FICHIER_DATA_CLEAN, dtype=str).fillna("")
        for idx, row in df_scraped.iterrows():
            cible = str(row.get("Username", "")).strip().lower()
            cible = re.sub(r'^@', '', cible)
            sources = [s for s in str(row.get("Compte_Origine", "")).split("|") if s.strip()]
            if cible:
                tag_counts[cible] = tag_counts.get(cible, 0) + len(sources)

    # --- ETAPE B : Intégrer les anciens de bd_final ---
    if os.path.exists(FICHIER_BD_FINAL):
        df_bd = pd.read_excel(FICHIER_BD_FINAL, dtype=str).fillna("")
        for idx, row in df_bd.iterrows():
            cat = normaliser_categorie(row.get("Categorie_Propre", ""))
            ville = extraire_ville_normalisee(row.get("Ville", ""), "")
            url = str(row.get("URL_Instagram", "")).strip()
            nom = str(row.get("Nom", "")).strip()

            username = ""
            if url:
                match = re.search(r'instagram\.com/([^/?]+)', url)
                if match: username = match.group(1).lower().strip()
            if not username: username = nom.lower().replace(" ", "_")

            foll = nettoyer_followers(row.get("Instagram_Followers", "0"))

            if cat != "Sans catégorie":
                prestataires_dict[username] = {
                    "Username": username, "Nom": nom or username, "Categorie_Finale": cat,
                    "Ville": ville, "Followers_Propre": foll, "URL_Instagram": url,
                    "Nombre_Tags": tag_counts.get(username, 0) # On injecte la popularité calculée
                }

    # --- ETAPE C : Intégrer les nouveaux scrappés (Filtre Strict) ---
    if not df_scraped.empty:
        for idx, row in df_scraped.iterrows():
            if not passe_filtre_strict(row): continue
            
            # S'il est déjà dans bd_final, on ignore car on l'a déjà traité à l'Étape B
            if str(row.get("Existe_Dans_BD_Final", "")).strip().lower() == "oui": continue 

            cible = str(row.get("Username", "")).strip().lower()
            cible = re.sub(r'^@', '', cible)
            cat = normaliser_categorie(row.get("Categorie_Finale", ""))
            ville = extraire_ville_normalisee(row.get("Adresse", ""), row.get("Bio", ""))
            foll = nettoyer_followers(row.get("Followers_Propre", "0"))
            
            if cible and cat != "Sans catégorie" and cible not in prestataires_dict:
                prestataires_dict[cible] = {
                    "Username": cible, "Nom": str(row.get("Pseudo", "")) or cible, "Categorie_Finale": cat,
                    "Ville": ville, "Followers_Propre": foll, "URL_Instagram": str(row.get("URL_Instagram", "")),
                    "Nombre_Tags": tag_counts.get(cible, 0)
                }

    df_unified = pd.DataFrame(list(prestataires_dict.values()))
    return df_unified

# ============================================================
# 4. INTERFACE UTILISATEUR : LE SIMULATEUR COMPLET
# ============================================================
st.set_page_config(page_title="Eventia Budget Planner", layout="wide")
st.title("🎉 Planificateur Événementiel Intelligent")

st.markdown("""
<style>
[data-baseweb="tag"] {
    background-color: #7C3AED !important;
    border-radius: 8px !important;
}
[data-baseweb="tag"] span {
    color: white !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

ICONES_CATEGORIES = {
    "Traiteur": "🍽️", "Lieu de Réception": "🏛️", "Photographe & Vidéaste": "📸",
    "Neggafa": "👑", "DJ & Animation Musicale": "🎧", "Maquillage & Coiffure (MUA)": "💄",
    "Décoration & Scénographie": "🎈", "Robes de Mariée": "👗", "Wedding planner": "📋",
    "Location de Voitures": "🚗", "Fleuriste": "💐", "Orchestre & Musiciens": "🎻",
    "Dekka Marrakchia & Issawa": "🥁", "Service de bar & Mixologie": "🍹",
    "Pâtisserie & Cake Design": "🎂", "Animation Enfants": "🎪", "Magie & Spectacles": "🎩",
    "Cadeaux Invités": "🎁", "Chanteur / Chanteuse": "🎤", "Sécurité & Logistique": "🛡️"
}

if not os.path.exists(FICHIER_BD_FINAL) and not os.path.exists(FICHIER_DATA_CLEAN):
    st.error("Aucun fichier de données trouvé. Veuillez placer bd_final.xlsx et Prestataires_Filtres_Categorises_finale.xlsx dans le dossier.")
    st.stop()

df_prestataires = charger_et_unifier_donnees()

# ---- BARRE LATÉRALE ----
st.sidebar.header("📋 Configuration de l'événement")
type_evenement = st.sidebar.selectbox("Type d'événement", list(CONFIG_EVENEMENTS.keys()))
villes_dispo = sorted([v for v in df_prestataires["Ville"].unique() if v != "Inconnue"])
ville_choisie = st.sidebar.selectbox("Ville de l'événement", villes_dispo)
nb_invites = st.sidebar.slider("Nombre d'invités", min_value=10, max_value=800, value=150, step=10)

categories_liees = CONFIG_EVENEMENTS[type_evenement]["categories_requises"]

st.sidebar.markdown("---")
st.sidebar.subheader("🗂️ Catégories à inclure")
st.sidebar.caption(f"Pré-sélectionnées pour « {type_evenement} ». Retirez ce que vous ne voulez pas.")

categories_necessaires = st.sidebar.multiselect(
    "Catégories",
    options=categories_liees,
    default=[],
    key=f"cats_v2_{type_evenement}",
    format_func=lambda c: f"{ICONES_CATEGORIES.get(c, '🔹')} {c}",
    label_visibility="collapsed"
)

nb_total = len(categories_liees)
nb_choisi = len(categories_necessaires)
couleur_badge = "#16A34A" if nb_choisi == nb_total else ("#D97706" if nb_choisi > 0 else "#DC2626")
st.sidebar.markdown(
    f"<span style='background-color:{couleur_badge}; color:white; padding:2px 10px; "
    f"border-radius:12px; font-size:0.8rem; font-weight:600;'>✓ {nb_choisi} / {nb_total} sélectionnée(s)</span>",
    unsafe_allow_html=True
)
if not categories_necessaires:
    st.sidebar.warning("⚠️ Sélectionnez au moins une catégorie.")

tab1, tab2 = st.tabs(["📊 Estimer selon le prestige (Gamme)", "🎯 J'ai un budget fixe (Meilleur choix)"])

# ---------------------------------------------------------
# ONGLET 1 : ESTIMATION PAR GAMME
# ---------------------------------------------------------
with tab1:
    st.header(f"Estimer le coût d'un(e) {type_evenement}")
    gamme_choisie = st.select_slider("Quel niveau de prestige recherchez-vous ?", options=list(GAMMES_FOLLOWERS.keys()))

    if st.button("Calculer l'estimation 🧮", key="btn_bottomup", disabled=not categories_necessaires):
        min_foll, max_foll = GAMMES_FOLLOWERS[gamme_choisie]
        df_ville_t1 = df_prestataires[df_prestataires["Ville"] == ville_choisie]
        df_filtre = df_ville_t1[
            (df_ville_t1["Followers_Propre"] >= min_foll) &
            (df_ville_t1["Followers_Propre"] <= max_foll)
        ]

        cout_total_estime = 0
        equipe = []

        for categorie in categories_necessaires:
            df_cat = df_filtre[df_filtre["Categorie_Finale"] == categorie]
            hors_gamme = False

            if df_cat.empty:
                # Personne dans la gamme demandée pour cette catégorie -> on retombe sur toute la ville
                df_cat = df_ville_t1[df_ville_t1["Categorie_Finale"] == categorie]
                hors_gamme = True

            if not df_cat.empty:
                # On priorise le prestataire qui a de bonnes recommandations
                prestataire = df_cat.sort_values(by="Nombre_Tags", ascending=False).iloc[0]
                # En repli hors gamme, on tarife quand même au niveau de la gamme DEMANDÉE
                # (pas au niveau réel du profil de repli, sinon "VIP" pourrait coûter moins cher qu'attendu)
                followers_tarification = min_foll if hors_gamme else prestataire["Followers_Propre"]
                prix = estimer_prix(categorie, ville_choisie, followers_tarification, nb_invites, type_evenement)
                cout_total_estime += prix
                equipe.append((categorie, prestataire, prix))

        col_g, col_d = st.columns([2, 1])
        with col_g:
            for cat, p, prix in equipe:
                with st.expander(f"✅ {cat} : {p['Nom']} (@{p['Username']})"):
                    st.write(f"**Tarif évalué :** {prix:,} MAD")
                    st.write(f"**Abonnés :** {p['Followers_Propre']:,}")
                    st.write(f"**Popularité :** Recommandé {p['Nombre_Tags']} fois par des pros.")
        with col_d:
            st.metric(label="Budget Total Estimé", value=f"{cout_total_estime:,} MAD")

# ---------------------------------------------------------
# ONGLET 2 : OPTIMISATION BUDGET FIXE (RAPPORT QUALITÉ/PRIX)
# ---------------------------------------------------------
with tab2:
    st.header("Optimisation du Budget Fixe")
    budget_max = st.number_input("Budget total maximum (MAD)", min_value=5000, max_value=1000000, value=50000, step=5000)

    mode_gamme = st.radio(
        "Comment appliquer la gamme de prestige ?",
        options=["Sans préférence de gamme", "Gamme stricte (filtre)", "Gamme préférée (souple)"],
        horizontal=True,
        key="mode_gamme_tab2"
    )

    gamme_cible_tab2 = None
    if mode_gamme != "Sans préférence de gamme":
        gamme_cible_tab2 = st.select_slider(
            "Quelle gamme viser ?", options=list(GAMMES_FOLLOWERS.keys()), key="gamme_tab2"
        )

    if st.button("Trouver les meilleurs prestataires 🚀", key="btn_target", disabled=not categories_necessaires):
        df_ville = df_prestataires[df_prestataires["Ville"] == ville_choisie].copy()
        df_ville["Prix_Estime"] = df_ville.apply(lambda r: estimer_prix(r["Categorie_Finale"], ville_choisie, r["Followers_Propre"], nb_invites, type_evenement), axis=1)
        df_ville = df_ville[df_ville["Prix_Estime"] > 0]

        min_foll_t2, max_foll_t2 = GAMMES_FOLLOWERS[gamme_cible_tab2] if gamme_cible_tab2 else (None, None)

        budget_par_categorie = budget_max / len(categories_necessaires)
        cout_final = 0
        equipe_optimisee = []
        avertissements = []

        for categorie in categories_necessaires:
            df_cat = df_ville[df_ville["Categorie_Finale"] == categorie].copy()
            if df_cat.empty:
                continue

            # --- Sous-ensemble limité à la gamme visée, si applicable ---
            df_cat_gamme = df_cat
            if gamme_cible_tab2:
                df_cat_gamme = df_cat[
                    (df_cat["Followers_Propre"] >= min_foll_t2) & (df_cat["Followers_Propre"] <= max_foll_t2)
                ]

            if mode_gamme == "Gamme stricte (filtre)":
                # On ne regarde QUE la gamme demandée
                if df_cat_gamme.empty:
                    avertissements.append(f"Aucun prestataire « {categorie} » trouvé dans la gamme « {gamme_cible_tab2} » pour cette ville.")
                    continue
                df_abordable = df_cat_gamme[df_cat_gamme["Prix_Estime"] <= budget_par_categorie * 1.1]
                if not df_abordable.empty:
                    meilleur_choix = df_abordable.sort_values(by=["Nombre_Tags", "Followers_Propre"], ascending=[False, False]).iloc[0]
                else:
                    meilleur_choix = df_cat_gamme.sort_values(by="Prix_Estime").iloc[0]

            elif mode_gamme == "Gamme préférée (souple)":
                # On essaie d'abord dans la gamme, sinon on retombe sur toute la ville
                df_abordable_gamme = df_cat_gamme[df_cat_gamme["Prix_Estime"] <= budget_par_categorie * 1.1] if not df_cat_gamme.empty else df_cat_gamme
                if not df_abordable_gamme.empty:
                    meilleur_choix = df_abordable_gamme.sort_values(by=["Nombre_Tags", "Followers_Propre"], ascending=[False, False]).iloc[0]
                else:
                    df_abordable = df_cat[df_cat["Prix_Estime"] <= budget_par_categorie * 1.1]
                    if not df_abordable.empty:
                        meilleur_choix = df_abordable.sort_values(by=["Nombre_Tags", "Followers_Propre"], ascending=[False, False]).iloc[0]
                        if df_cat_gamme.empty or meilleur_choix["Username"] not in df_cat_gamme["Username"].values:
                            avertissements.append(f"« {categorie} » : aucun prestataire de la gamme « {gamme_cible_tab2} » dans le budget, choix hors gamme retenu.")
                    else:
                        meilleur_choix = df_cat.sort_values(by="Prix_Estime").iloc[0]
                        avertissements.append(f"« {categorie} » : aucun prestataire dans le budget, le moins cher de la ville a été retenu.")

            else:
                # Sans préférence de gamme : comportement d'origine
                df_abordable = df_cat[df_cat["Prix_Estime"] <= budget_par_categorie * 1.1]
                if not df_abordable.empty:
                    meilleur_choix = df_abordable.sort_values(by=["Nombre_Tags", "Followers_Propre"], ascending=[False, False]).iloc[0]
                else:
                    meilleur_choix = df_cat.sort_values(by="Prix_Estime").iloc[0]

            cout_final += meilleur_choix["Prix_Estime"]
            equipe_optimisee.append(meilleur_choix)

        for msg in avertissements:
            st.warning(f"⚠️ {msg}")

        col_g2, col_d2 = st.columns([2, 1])
        with col_g2:
            for p in equipe_optimisee:
                with st.expander(f"✅ {p['Categorie_Finale']} : {p['Nom']} (@{p['Username']})"):
                    st.write(f"**Prix Estimé :** {p['Prix_Estime']:,} MAD")
                    st.write(f"**Popularité :** Tagué {p['Nombre_Tags']} fois par d'autres pros du mariage.")
                    if p['URL_Instagram']:
                        st.markdown(f"[Voir le profil Instagram]({p['URL_Instagram']})")
        with col_d2:
            st.metric("Budget Initial", f"{budget_max:,} MAD")
            st.metric("Coût Total de l'équipe", f"{cout_final:,} MAD", delta=int(budget_max - cout_final))