import os
import re
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# CONFIGURATION
# ============================================================
FICHIER_DATA_CLEAN = "Prestataires_Filtres_Categorises_finale.xlsx"
FICHIER_BD_FINAL   = "DataMart_Final_Global.xlsx"

VILLES_MAROC_MAPPING = {
    "Casablanca": "Casablanca", "Casa": "Casablanca", "Rabat": "Rabat",
    "Marrakech": "Marrakech", "Marrakesh": "Marrakech", "Fès": "Fès", "Fes": "Fès",
    "Tanger": "Tanger", "Tangier": "Tanger", "Agadir": "Agadir",
    "Meknès": "Meknès", "Meknes": "Meknès", "Oujda": "Oujda",
    "Kénitra": "Kénitra", "Kenitra": "Kénitra", "Tétouan": "Tétouan", "Tetouan": "Tétouan",
    "Salé": "Salé", "Sale": "Salé", "El Jadida": "El Jadida",
    "Béni Mellal": "Béni Mellal", "Beni Mellal": "Béni Mellal",
    "Nador": "Nador", "Khouribga": "Khouribga", "Settat": "Settat",
    "Larache": "Larache", "Mohammedia": "Mohammedia", "Safi": "Safi",
    "Taza": "Taza", "Essaouira": "Essaouira", "Ifrane": "Ifrane",
    "Ouarzazate": "Ouarzazate", "Errachidia": "Errachidia",
    "Al Hoceïma": "Al Hoceïma", "Al Hoceima": "Al Hoceïma",
    "Guelmim": "Guelmim", "Berkane": "Berkane", "Taourirt": "Taourirt",
    "Sidi Kacem": "Sidi Kacem", "Sidi Slimane": "Sidi Slimane",
    "Chefchaouen": "Chefchaouen", "Dakhla": "Dakhla", "Laâyoune": "Laâyoune", "Laayoune": "Laâyoune"
}

# ============================================================
# DICTIONNAIRE UNIQUE ET STRICT
# ============================================================
dictionnaire_plateforme = {
    "Studio photo et vidéo": "Photographe & Vidéaste",
    "Photographe / Vidéaste": "Photographe & Vidéaste",
    "Photographes professionnels": "Photographe & Vidéaste",
    "Photographe": "Photographe & Vidéaste",
    "Vidéaste": "Photographe & Vidéaste",
    "Laboratoires photographiques": "Photographe & Vidéaste",
    "DJ": "DJ & Animation Musicale",
    "Chanteur/Chanteuse / DJ": "DJ & Animation Musicale",
    "Animateur enfant / DJ": "DJ & Animation Musicale",
    "Orchestre": "Orchestre & Musiciens",
    "Violoniste": "Orchestre & Musiciens",
    "Orchestre / Violoniste": "Orchestre & Musiciens",
    "Chanteur/Chanteuse": "Chanteur / Chanteuse",
    "Dekka Marrakchia Issawa": "Dekka Marrakchia & Issawa",
    "Traiteurs": "Traiteur",
    "Traiteur": "Traiteur",
    "Pâtissier / Cake designer / Traiteur": "Traiteur",  
    "Service de bar / mixologue": "Service de bar & Mixologie",
    "Pâtissier / Cake designer": "Pâtisserie & Cake Design",
    "Evénementiel": "Agence Événementielle & Planner",
    "Event planner": "Agence Événementielle & Planner",
    "Structures événementielles": "Agence Événementielle & Planner",  
    "Structures événementielles / Traiteur": "Agence Événementielle & Planner",  
    "Structures événementielles / Wedding planner": "Agence Événementielle & Planner",
    "Structures événementielles / Structures gonflables / Wedding planner": "Agence Événementielle & Planner",
    "Décorateur / Event planner": "Agence Événementielle & Planner",
    "Créateur d’ambiance lumineuse / Décorateur / Event planner": "Agence Événementielle & Planner",
    "Créateur d’ambiance lumineuse / Décorateur / Event planner / Fleuriste événementiel": "Agence Événementielle & Planner",
    "Décorateur / Event planner / Fleuriste événementiel": "Agence Événementielle & Planner",
    "Traiteur / Wedding planner": "Agence Événementielle & Planner",
    "Structures événementielles / Traiteur / Wedding planner": "Agence Événementielle & Planner",
    "Pâtissier / Cake designer / Traiteur / Wedding planner": "Agence Événementielle & Planner",
    "Pâtissier / Cake designer / Structures événementielles / Traiteur / Wedding planner": "Agence Événementielle & Planner",
    "Event planner / Lieu de réception": "Agence Événementielle & Planner",
    "Wedding planner": "Wedding planner",  
    "Décoration d'intérieur": "Décoration & Scénographie",
    "Décorateur": "Décoration & Scénographie",
    "Créateur d’ambiance lumineuse / Décorateur": "Décoration & Scénographie",
    "Créateur d’ambiance lumineuse / Décorateur / Fleuriste événementiel": "Décoration & Scénographie",
    "Décorateur / Fleuriste événementiel": "Décoration & Scénographie",
    "Fleuristes": "Fleuriste",
    "Fleuriste événementiel": "Fleuriste",
    "Fleuriste événementiel / Lieu de réception": "Fleuriste",
    "Lieu de réception": "Lieu de Réception",
    "Décorateur / Lieu de réception": "Lieu de Réception",
    "Location de voitures": "Location de Voitures",
    "Location de voiture de mariage": "Location de Voitures",
    "Makeup Artist": "Maquillage & Coiffure (MUA)",
    "Hairstylist": "Maquillage & Coiffure (MUA)",
    "Hairstylist / Makeup Artist": "Maquillage & Coiffure (MUA)",
    "Neggafa": "Neggafa",
    "Robes de mariés": "Robes de Mariée",
    "Spa / soins esthétiques": "Bien-être & Esthétique",
    "Animateur enfant / Jeux animations enfants": "Animation Enfants",
    "Structures gonflables": "Animation Enfants",
    "Magicien": "Magie & Spectacles",
    "Location de matériels pour réception": "Location de Matériel & Tentes",
    "Sécurité événementielle": "Sécurité & Logistique",
    "Sécurité événementielle / VTC / Transport invités": "Sécurité & Logistique",
    "Créateur de cadeaux invités": "Cadeaux Invités",
    "Florist": "Fleuriste", "Dresses": "Robes de Mariée", "Venues": "Lieu de Réception",
    "Beauty": "Maquillage & Coiffure (MUA)", "Photo-film": "Photographe & Vidéaste",
    "Caterer": "Traiteur", "Catering": "Traiteur", "Decor": "Décoration & Scénographie",
    "Negafa": "Neggafa", "Artist": "DJ & Animation Musicale",
    "Event-planner": "Agence Événementielle & Planner", "Cakes": "Pâtisserie & Cake Design"
}

# ============================================================
# BOUCLIERS ULTRA-STRICTS
# ============================================================
REGEX_TEL_ETRANGER = re.compile(r"\+\s*(?!212)\d{1,3}[\s.\-]?\d{4,}")
REGEX_ALPHABET_ASIATIQUE = re.compile(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")

BLACKLIST_INFLUENCEURS = ["blog", "blogger", "blogueuse", "blogueur", "lifestyle", "influencer", "influenceur", "influenceuse", "content creator", "créateur de contenu", "public figure", "figure publique", "just for fun", "personal account", "compte personnel", "student", "étudiant", "étudiante", "dm for collab", "ambassador","please","single","health","Travel", "Dentiste"]
BLACKLIST_ECOMMERCE = ["prêt-à-porter", "pret a porter", "chaussures", "shoes", "boutique en ligne", "online store", "online shop", "vetements", "vêtements", "worldwide shipping", "livraison internationale", "soldes", "dropshipping", "cosmetics", "produits cosmétiques", "parapharmacie", "importation","Shipping","Clothing"]
BLACKLIST_ESPAGNOL = ["boda", "bodas", "novia", "novias", "maquillaje", "peluquería", "peluqueria", "fotógrafo", "fotografo", "vestido de novia", "quinceañera", "madrina", "invitada", "cumpleaños", "citas","compra","norges","fica","Maior","Fala", "Ayudamos","#youth_unemployment","Визы в 45 стран мира","mom","Mom"]
BLACKLIST_PAYS_MONDE = ["afghanistan", "albania", "albanie", "algeria", "algerie", "algérie", "andorra", "andorre", "angola", "argentina", "argentine", "armenia", "armenie", "australia", "australie", "austria", "autriche", "azerbaijan", "bahamas", "bahrain", "bahreïn", "bangladesh", "barbados", "belarus", "biélorussie", "belgium", "belgique", "belize", "benin", "bénin", "bolivia", "bolivie", "bosnia", "bosnie", "botswana", "brazil", "bresil", "brésil", "bulgaria", "bulgarie", "burkina faso", "burundi", "cabo verde", "cap vert", "cambodia", "cambodge", "cameroon", "cameroun", "canada", "centrafrique", "chad", "tchad", "chile", "chili", "china", "chine", "colombia", "colombie", "comoros", "comores", "congo", "costa rica", "croatia", "croatie", "cuba", "cyprus", "chypre", "czech", "tchèque", "denmark", "danemark", "djibouti", "dominican", "dominicaine", "ecuador", "équateur", "egypt", "egypte", "égypte", "el salvador", "guinée", "eritrea", "erythrée", "estonia", "estonie", "ethiopia", "ethiopie", "finland", "finlande", "france", "gabon", "gambia", "gambie", "georgia", "géorgie", "germany", "allemagne", "ghana", "greece", "grèce", "guatemala", "haiti", "haïti", "honduras", "hungary", "hongrie", "iceland", "islande", "india", "inde", "indonesia", "indonésie", "iran", "iraq", "irak", "ireland", "irlande", "israel", "israël", "italy", "italie", "côte d'ivoire", "jamaica", "jamaïque", "japan", "japon", "jordan", "jordanie", "kazakhstan", "kenya", "corée", "kosovo", "kuwait", "koweït", "kyrgyzstan", "lebanon", "liban", "liberia", "libya", "libye", "lithuania", "lituanie", "luxembourg", "madagascar", "malaysia", "malaisie", "maldives", "mali", "malta", "malte", "mauritania", "mauritanie", "mauritius", "maurice", "mexico", "mexique", "moldova", "moldavie", "monaco", "mongolia", "mongolie", "montenegro", "monténégro", "myanmar", "birmanie", "namibia", "namibie", "nepal", "népal", "netherlands", "pays-bas", "new zealand", "nouvelle-zélande", "nicaragua", "niger", "nigeria", "nigéria", "macedonia", "macédoine", "norway", "norvège", "oman", "pakistan", "palestine", "panama", "paraguay", "peru", "pérou", "philippines", "poland", "pologne", "portugal", "qatar", "romania", "roumanie", "russia", "russie", "rwanda", "senegal", "sénégal", "serbia", "serbie", "seychelles", "singapore", "singapour", "slovakia", "slovaquie", "slovenia", "slovénie", "somalia", "somalie", "south africa", "afrique du sud", "spain", "espagne", "españa", "sri lanka", "sudan", "soudan", "sweden", "suède", "switzerland", "suisse", "syria", "syrie", "taiwan", "taïwan", "tanzania", "tanzanie", "thailand", "thaïlande", "togo", "tunisia", "tunisie", "turkey", "turquie", "uganda", "ouganda", "ukraine", "uae", "emirates", "émirats", "uk", "royaume-uni", "england", "angleterre", "usa", "america", "états-unis", "uruguay", "venezuela", "vietnam", "yemen", "yémen", "zambia", "zambie", "zimbabwe", "deutschland", "italia", "nederland","normands","+86"]
BLACKLIST_VILLES_ETRANGERES = ["paris", "marseille", "lyon", "toulouse", "nice", "nantes", "montpellier", "strasbourg", "bordeaux", "lille", "rennes", "reims", "toulon", "dijon", "grenoble", "angers", "nîmes", "villeurbanne", "clermont-ferrand", "le mans", "aix-en-provence", "brest", "tours", "amiens", "limoges", "annecy", "boulogne-billancourt", "perpignan", "metz", "besançon", "orléans", "saint-denis", "argenteuil", "rouen", "montreuil", "mulhouse", "corsica", "corse", "madrid", "barcelona", "barcelone", "valencia", "valence", "sevilla", "séville", "zaragoza", "saragosse", "malaga", "málaga", "murcia", "murcie", "palma", "bilbao", "alicante", "cordoba", "cordoue", "valladolid", "vigo", "gijon", "gijón", "granada", "grenade", "bruxelles", "brussels", "antwerp", "anvers", "ghent", "gand", "charleroi", "liege", "liège", "geneva", "genève", "zurich", "zürich", "basel", "bâle", "lausanne", "bern", "berne", "london", "londres", "birmingham", "manchester", "glasgow", "liverpool", "edinburgh", "édimbourg", "montreal", "montréal", "quebec", "québec", "toronto", "vancouver", "dubai", "dubaï", "abu dhabi", "abou dhabi", "doha", "riyadh", "riyad", "jeddah", "djeddah", "kuwait city", "manama", "muscat", "mascate", "cairo", "caire", "alexandria", "alexandrie", "algiers", "alger", "oran", "tunis", "sfax", "sousse", "dakar", "abidjan","Occitanie","Moscow","Warsaw", "Lisbon","Lisbonne","Athens","Athènes","Budapest", "Prague","Prague","Bratislava","Bratislava","Marinilla","Antioquía","Col🇨🇴"]
MOTS_PARDON = ["formé à", "formée à", "diplômé", "diplômée"]

# ============================================================
# OUTILS DE NETTOYAGE STRICTS
# ============================================================
def normaliser_categorie(cat_brute):
    cat_clean = str(cat_brute).strip()
    if not cat_clean or cat_clean in ["Non trouvé", "Inconnue", "nan"]:
        return "Sans catégorie"
        
    for ancienne_appellation, nom_officiel in dictionnaire_plateforme.items():
        if cat_clean.lower() == ancienne_appellation.lower():
            return nom_officiel

    valeurs_officielles = set(dictionnaire_plateforme.values())
    for officiel in valeurs_officielles:
        if cat_clean.lower() == officiel.lower():
            return officiel

    return "Sans catégorie"

def extraire_ville_normalisee(adresse, bio):
    for texte in (adresse, bio):
        texte = str(texte)
        for variante, ville_officielle in VILLES_MAROC_MAPPING.items():
            if re.search(r"\b" + re.escape(variante) + r"\b", texte, re.IGNORECASE):
                return ville_officielle
    return "Inconnue"

def passe_filtre_strict(row):
    bio = str(row.get("Bio", "")).lower()
    adresse = str(row.get("Adresse", "")).lower()
    pseudo = str(row.get("Pseudo", "")).lower()
    username = str(row.get("Username", "")).lower()
    texte_complet = f"{bio} {adresse} {pseudo} {username}"
    
    followers_raw = str(row.get("Followers_Propre", "0")).replace(" ", "").replace(",", ".")
    try: followers = int(float(followers_raw))
    except ValueError: followers = 0
    if followers >= 1000000: return False
        
    if REGEX_TEL_ETRANGER.search(texte_complet): return False
    if REGEX_ALPHABET_ASIATIQUE.search(texte_complet): return False

    for mot in BLACKLIST_INFLUENCEURS + BLACKLIST_ECOMMERCE + BLACKLIST_ESPAGNOL + BLACKLIST_PAYS_MONDE:
        if re.search(r"\b" + re.escape(mot) + r"\b", texte_complet): return False

    for ville_ext in BLACKLIST_VILLES_ETRANGERES:
        if re.search(r"\b" + re.escape(ville_ext) + r"\b", texte_complet):
            pardonne = any(pardon in texte_complet for pardon in MOTS_PARDON)
            if not pardonne: return False

    return True

# ============================================================
# INTERFACE STREAMLIT
# ============================================================
st.set_page_config(page_title="Réseau des Prestataires", layout="wide")
st.title("🕸️ Réseau des collaborations entre prestataires")

if not os.path.exists(FICHIER_DATA_CLEAN):
    st.error(f"Le fichier {FICHIER_DATA_CLEAN} est introuvable.")
    st.stop()
if not os.path.exists(FICHIER_BD_FINAL):
    st.warning(f"⚠️ Le fichier {FICHIER_BD_FINAL} est introuvable.")

# ============================================================
# CHARGEMENT + RECONSTRUCTION DES RELATIONS
# ============================================================
@st.cache_data
def charger_et_construire(fichier_data_clean, fichier_bd):
    df_clean = pd.read_excel(fichier_data_clean, dtype=str).fillna("")
    
    memoire_bd_urls = {}  
    memoire_bd_noms = {}  
    
    if os.path.exists(fichier_bd):
        df_bd = pd.read_excel(fichier_bd, dtype=str).fillna("")
        for idx, row in df_bd.iterrows():
            cat_brute = str(row.get("Categorie_Propre", "")).strip()
            ville_bd = str(row.get("Ville", "")).strip()
            
            cat_propre = normaliser_categorie(cat_brute)
            ville_propre = extraire_ville_normalisee(ville_bd, "")

            url = str(row.get("URL_Instagram", "")).strip()
            if url:
                match = re.search(r'instagram\.com/([^/?]+)', url)
                if match:
                    username_extrait = match.group(1).lower().strip()
                    memoire_bd_urls[username_extrait] = {"cat": cat_propre, "ville": ville_propre}

            nom = str(row.get("Nom", "")).strip().lower()
            if nom:
                memoire_bd_noms[nom] = {"cat": cat_propre, "ville": ville_propre}

    relations = []
    categories_nodes = {}
    villes_nodes = {}

    for idx, row in df_clean.iterrows():
        if not passe_filtre_strict(row): continue
        
        cible_original = str(row.get("Username", "")).strip()
        cible_lower = cible_original.lower()
        
        cat_cible = normaliser_categorie(row.get("Categorie_Finale", ""))
        ville_cible = extraire_ville_normalisee(row.get("Adresse", ""), row.get("Bio", ""))
        existe_bd = str(row.get("Existe_Dans_BD_Final", "")).strip().lower()

        if existe_bd == "oui":
            if cible_lower in memoire_bd_urls:
                if cat_cible == "Sans catégorie":
                    cat_cible = memoire_bd_urls[cible_lower]["cat"]
                if ville_cible == "Inconnue":
                    ville_cible = memoire_bd_urls[cible_lower]["ville"]

        categories_nodes[cible_original] = cat_cible
        villes_nodes[cible_original] = ville_cible

        sources_brutes = str(row.get("Compte_Origine", ""))
        if not cible_original or not sources_brutes: continue

        prestataires_sources = [s.strip() for s in sources_brutes.split("|") if s.strip()]

        for source in prestataires_sources:
            source_lower = source.lower()
            
            if source not in categories_nodes:
                if source_lower in memoire_bd_noms:
                    cat_s = memoire_bd_noms[source_lower]["cat"]
                    ville_s = memoire_bd_noms[source_lower]["ville"]
                    categories_nodes[source] = cat_s if cat_s != "Sans catégorie" else "Prescripteur / Non Scrappé"
                    villes_nodes[source] = ville_s
                else:
                    categories_nodes[source] = "Prescripteur / Non Scrappé"
                    villes_nodes[source] = "Inconnue"

            relations.append({
                "Source": source,
                "Cible": cible_original,
                "Categorie_Cible": cat_cible,
                "Ville_Cible": villes_nodes[cible_original],
            })

    df_edges = pd.DataFrame(relations)
    if not df_edges.empty:
        df_stats = df_edges.groupby(['Source', 'Categorie_Cible']).size().reset_index(name='Nombre_Collaborations')
        df_stats = df_stats.sort_values(by=['Source', 'Nombre_Collaborations'], ascending=[True, False])
    else: df_stats = pd.DataFrame()

    return df_edges, categories_nodes, villes_nodes, df_stats

df_edges, categories_nodes, villes_nodes, df_stats = charger_et_construire(FICHIER_DATA_CLEAN, FICHIER_BD_FINAL)

# ============================================================
# BARRE LATÉRALE : FILTRES VILLE / CATÉGORIE
# ============================================================
st.sidebar.header("Filtres (Appliqués sur les Cibles)")

villes_disponibles = sorted([v for v in df_edges["Ville_Cible"].unique() if v != "Inconnue"])
ville_choisie = st.sidebar.selectbox("Ville de la cible", ["Toutes"] + villes_disponibles)

categories_disponibles = sorted([c for c in df_edges["Categorie_Cible"].unique() if c not in ["Sans catégorie", "Prescripteur / Non Scrappé"]])
categorie_choisie = st.sidebar.selectbox("Catégorie de la cible", ["Toutes"] + categories_disponibles)

df_edges_filtre = df_edges
if ville_choisie != "Toutes":
    df_edges_filtre = df_edges_filtre[df_edges_filtre["Ville_Cible"] == ville_choisie]
if categorie_choisie != "Toutes":
    df_edges_filtre = df_edges_filtre[df_edges_filtre["Categorie_Cible"] == categorie_choisie]

st.write(f"**{df_edges_filtre['Cible'].nunique()}** cibles affichées, pour **{len(df_edges_filtre)}** collaborations.")

# ============================================================
# ÉTAPE 3 : CARTOGRAPHIE DU RÉSEAU (GRAPHE ORIENTÉ)
# ============================================================
df_graph_edges = df_edges_filtre.groupby(['Source', 'Cible']).size().reset_index(name='Poids')

@st.cache_data(show_spinner="Construction du graphe interactif...")
def construire_html_graphe(df_graph_edges, categories_nodes, villes_nodes):
    G = nx.DiGraph() 
    
    for idx, row in df_graph_edges.iterrows():
        G.add_edge(row['Source'], row['Cible'], value=int(row['Poids']), title=f"Tagué {row['Poids']} fois")

    in_degrees = dict(G.in_degree())

    for node in G.nodes():
        groupe_cat = categories_nodes.get(node, "Prescripteur / Non Scrappé")
        groupe_ville = villes_nodes.get(node, "Inconnue")
        
        taille = 15 + (in_degrees.get(node, 0) * 3)
        role = "🎯 CIBLE (Tagué)" if in_degrees.get(node, 0) > 0 else "📢 SOURCE (Tagueur)"
        hover_text = f"Nom : {node}\nRôle : {role}\nCatégorie : {groupe_cat}\nVille : {groupe_ville}"

        G.nodes[node]['group'] = groupe_cat
        G.nodes[node]['title'] = hover_text
        G.nodes[node]['size'] = taille

    net = Network(height="850px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    net.barnes_hut(gravity=-10000, central_gravity=0.3, spring_length=150)
    net.from_nx(G)

    net.set_options("""
    var options = {
      "nodes": { 
          "shape": "dot",
          "font": { "size": 14 } 
      },
      "edges": {
          "arrows": {
              "to": { "enabled": true, "scaleFactor": 0.5 }
          },
          "color": { "inherit": "to" }
      },
      "interaction": { "hover": true, "navigationButtons": true, "zoomView": false },
      "physics": { "stabilization": { "iterations": 100 } }
    }
    """)

    return net.generate_html(), len(G.nodes())

st.subheader("🕸️ Graphe interactif (Orienté)")
if df_graph_edges.empty:
    st.warning("Aucun compte ne correspond aux filtres choisis.")
else:
    html_graphe, nb_noeuds = construire_html_graphe(df_graph_edges, categories_nodes, villes_nodes)
    components.html(html_graphe, height=870, scrolling=True)

# ============================================================
# ÉTAPE 4 : ANALYSE DÉTAILLÉE DES PARTENAIRES (NOUVEAU)
# ============================================================
st.subheader("🤝 Analyse détaillée des partenaires")

# On prépare un tableau complet avec les catégories des Sources et des Cibles
df_partenaires = df_graph_edges.copy()
df_partenaires['Catégorie Source'] = df_partenaires['Source'].map(categories_nodes)
df_partenaires['Catégorie Cible'] = df_partenaires['Cible'].map(categories_nodes)

onglet_recherche, onglet_palmares = st.tabs(["🔍 Rechercher un profil précis", "🏆 Palmarès global des collaborations"])

with onglet_recherche:
    tous_comptes = sorted(set(df_partenaires['Source'].unique()) | set(df_partenaires['Cible'].unique()))
    compte_recherche = st.selectbox("Sélectionnez ou tapez le nom d'un prestataire :", [""] + tous_comptes)
    
    if compte_recherche:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Qui {compte_recherche} recommande-t-il ? (Cibles qu'il a tagué)**")
            recommande = df_partenaires[df_partenaires['Source'] == compte_recherche][['Cible', 'Catégorie Cible', 'Poids']]
            recommande = recommande.sort_values(by='Poids', ascending=False)
            recommande.columns = ['Partenaire (Cible)', 'Métier', 'Nombre de tags']
            if not recommande.empty:
                st.dataframe(recommande, use_container_width=True)
            else:
                st.info("Aucune recommandation faite par ce profil.")
            
        with col2:
            st.markdown(f"**Qui recommande {compte_recherche} ? (Sources qui l'ont tagué)**")
            est_recommande = df_partenaires[df_partenaires['Cible'] == compte_recherche][['Source', 'Catégorie Source', 'Poids']]
            est_recommande = est_recommande.sort_values(by='Poids', ascending=False)
            est_recommande.columns = ['Prescripteur (Source)', 'Métier', 'Nombre de tags reçus']
            if not est_recommande.empty:
                st.dataframe(est_recommande, use_container_width=True)
            else:
                st.info("Ce profil n'a pas été tagué.")

with onglet_palmares:
    st.markdown("**Tous les partenariats triés par la force du lien (nombre de tags)**")
    df_global_view = df_partenaires.sort_values(by='Poids', ascending=False)
    df_global_view = df_global_view[['Source', 'Catégorie Source', 'Cible', 'Catégorie Cible', 'Poids']]
    df_global_view.columns = ['Tagueur (Source)', 'Métier du Tagueur', 'Tagué (Cible)', 'Métier du Tagué', 'Force (Tags)']
    st.dataframe(df_global_view, use_container_width=True)

st.subheader("📊 Statistiques globales de recommandations par segment")
st.dataframe(df_stats, use_container_width=True)