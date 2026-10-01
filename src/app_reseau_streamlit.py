import os
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# CONFIGURATION
# ============================================================
FICHIER_DATA_CLEAN = "Prestataires_Filtres_Categorises_2.xlsx"
FICHIER_SEGMENTS    = "Analyse_Segments_Collaborations_2.xlsx"

st.set_page_config(page_title="Réseau des Prestataires", layout="wide")
st.title("🕸️ Réseau des collaborations entre prestataires")

# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================
@st.cache_data
def charger_donnees():
    df_clean = pd.read_excel(FICHIER_DATA_CLEAN, dtype=str).fillna("")
    df_segments = pd.read_excel(FICHIER_SEGMENTS, dtype=str).fillna("")
    return df_clean, df_segments

if not os.path.exists(FICHIER_DATA_CLEAN):
    st.error(f"Fichier introuvable : {FICHIER_DATA_CLEAN}")
    st.stop()

df_clean, df_segments = charger_donnees()

# ============================================================
# RECONSTRUCTION DES RELATIONS (memes regles que analyse_reseau_prestataires.py)
# ============================================================
@st.cache_data
def construire_relations(df_clean):
    relations = []
    categories_nodes = {}

    for _, row in df_clean.iterrows():
        cible = str(row.get("Username", "")).strip()
        cat_cible = str(row.get("Categorie_Finale", "")) or "Sans categorie"
        sources_brutes = str(row.get("Compte_Origine", ""))

        if not cible or not sources_brutes:
            continue

        categories_nodes[cible] = cat_cible
        prestataires_sources = [s.strip() for s in sources_brutes.split("|") if s.strip()]

        for source in prestataires_sources:
            if source not in categories_nodes:
                categories_nodes[source] = "Prestataire Réseau"
            relations.append({"Source": source, "Cible": cible, "Categorie_Cible": cat_cible})

    return pd.DataFrame(relations), categories_nodes

df_edges, categories_nodes = construire_relations(df_clean)

# ============================================================
# BARRE LATÉRALE : FILTRES
# ============================================================
st.sidebar.header("Filtres")

toutes_categories = sorted(set(categories_nodes.values()))
categories_choisies = st.sidebar.multiselect(
    "Catégories à afficher", toutes_categories, default=toutes_categories
)

recherche_compte = st.sidebar.text_input("Rechercher un compte (username)")

poids_min = st.sidebar.slider("Nombre minimum de collaborations (épaisseur du lien)", 1, 10, 1)

# ============================================================
# FILTRAGE DU GRAPHE
# ============================================================
comptes_valides = {c for c, cat in categories_nodes.items() if cat in categories_choisies}
df_filtre = df_edges[df_edges["Cible"].isin(comptes_valides) | df_edges["Source"].isin(comptes_valides)]

if recherche_compte:
    comptes_lies = set(df_filtre.loc[
        df_filtre["Source"].str.contains(recherche_compte, case=False, na=False)
        | df_filtre["Cible"].str.contains(recherche_compte, case=False, na=False),
        ["Source", "Cible"]
    ].values.flatten())
    df_filtre = df_filtre[df_filtre["Source"].isin(comptes_lies) | df_filtre["Cible"].isin(comptes_lies)]

df_graph_edges = df_filtre.groupby(["Source", "Cible"]).size().reset_index(name="Poids")
df_graph_edges = df_graph_edges[df_graph_edges["Poids"] >= poids_min]

st.write(f"**{df_graph_edges['Source'].nunique() + df_graph_edges['Cible'].nunique()}** comptes affichés, "
         f"**{len(df_graph_edges)}** liens.")

# ============================================================
# CONSTRUCTION DU GRAPHE PYVIS
# ============================================================
G = nx.Graph()
for _, row in df_graph_edges.iterrows():
    G.add_edge(row["Source"], row["Cible"], value=int(row["Poids"]), title=f"Interactions : {row['Poids']}")

for node in G.nodes():
    groupe_cat = categories_nodes.get(node, "Inconnue")
    G.nodes[node]["group"] = groupe_cat
    G.nodes[node]["title"] = f"Compte : @{node}\nSegment : {groupe_cat}"

net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black", directed=False)
net.barnes_hut(gravity=-10000, central_gravity=0.3, spring_length=150)
net.from_nx(G)
net.set_options("""
var options = {
  "nodes": { "font": { "size": 14 } },
  "interaction": { "hover": true, "navigationButtons": true, "zoomView": false },
  "physics": { "stabilization": { "iterations": 100 } }
}
""")

html_graphe = net.generate_html()

# ============================================================
# AFFICHAGE
# ============================================================
onglet_graphe, onglet_stats = st.tabs(["🕸️ Graphe réseau", "📊 Statistiques par segment"])

with onglet_graphe:
    if len(G.nodes()) == 0:
        st.warning("Aucun compte ne correspond aux filtres choisis.")
    else:
        components.html(html_graphe, height=780, scrolling=True)

with onglet_stats:
    source_choisie = st.selectbox(
        "Filtrer par prestataire source (optionnel)",
        ["(tous)"] + sorted(df_segments["Source"].unique().tolist())
    )
    if source_choisie != "(tous)":
        st.dataframe(df_segments[df_segments["Source"] == source_choisie], use_container_width=True)
    else:
        st.dataframe(df_segments, use_container_width=True)
