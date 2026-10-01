import random
import time
import re
import os
import json
from datetime import datetime
import pandas as pd
import networkx as nx
from pyvis.network import Network
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 1. CONFIGURATION
# ============================================================
FICHIER_INPUT    = "Nouveaux_Prestataires_Bios.xlsx"
FICHIER_DATA_CLEAN = "Prestataires_Filtres_Categorises_finale.xlsx"
FICHIER_SEGMENTS   = "Analyse_Segments_Collaborations_finale.xlsx"
FICHIER_GRAPHE     = "Graphe_Reseau_Prestataires.html"
FICHIER_BASE_GLOBALE = "Nouveaux_Prestataires_Base_Globale_finale.xlsx"
LIMITE_TEST        = None  # mettre un nombre (ex: 20) pour tester sur un echantillon

COLONNES_BASE_GLOBALE = [
    "ID_Prestataire", "Date_Scraping", "Source", "Nom", "Categorie_Propre", "Ville",
    "Telephone_1", "Telephone_2", "URL_Facebook", "URL_Instagram", "URL_YouTube",
    "Description", "Instagram_Followers", "Facebook_Followers", "note_maps", "nombre_review",
]

SOURCE_LABEL = "Decouvert_Tag"

VILLES_MAROC = [
    "Casablanca", "Rabat", "Marrakech", "Marrakesh", "Fes", "Fès", "Tanger", "Tangier",
    "Agadir", "Meknes", "Meknès", "Oujda", "Kenitra", "Kénitra", "Tetouan", "Tétouan",
    "Sale", "Salé", "El Jadida", "Beni Mellal", "Béni Mellal", "Nador", "Khouribga",
    "Settat", "Larache", "Mohammedia", "Safi", "Taza", "Essaouira", "Ifrane",
    "Ouarzazate", "Errachidia", "Al Hoceima", "Al Hoceïma", "Guelmim", "Berkane",
    "Taourirt", "Sidi Kacem", "Sidi Slimane", "Chefchaouen", "Dakhla", "Laayoune", "Laâyoune",
]

REGEX_TELEPHONE = re.compile(
    r"(?:(?:\+212|00212|212)?[\s\-.]?(?:0)?[5-7][\s\-.]?\d{2}[\s\-.]?\d{2}[\s\-.]?\d{2}[\s\-.]?\d{2})"
)

# --- DÉBUT DES NOUVEAUX BOUCLIERS STRICTS (AJOUT) ---
REGEX_TEL_ETRANGER = re.compile(r"\+\s*(?!212)\d{1,3}[\s.\-]?\d{4,}")
REGEX_ALPHABET_ASIATIQUE = re.compile(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")

BLACKLIST_INFLUENCEURS = [
    "blog", "blogger", "blogueuse", "blogueur", "lifestyle", 
    "influencer", "influenceur", "influenceuse", "content creator", 
    "créateur de contenu", "public figure", "figure publique", 
    "just for fun", "personal account", "compte personnel", 
    "student", "étudiant", "étudiante", "dm for collab", "ambassador","please","single","health","Travel",
    "Dentiste"

]

BLACKLIST_ECOMMERCE = [
    "prêt-à-porter", "pret a porter", "chaussures", "shoes", 
    "boutique en ligne", "online store", "online shop", "vetements", 
    "vêtements", "worldwide shipping", "livraison internationale", 
    "soldes", "dropshipping", "cosmetics", "produits cosmétiques",
    "parapharmacie", "importation","Shipping","Clothing"
]

BLACKLIST_ESPAGNOL = [
    "boda", "bodas", "novia", "novias", "maquillaje", "peluquería", 
    "peluqueria", "fotógrafo", "fotografo", "vestido de novia", 
    "quinceañera", "madrina", "invitada", "cumpleaños", "citas","compra","norges","fica","Maior","Fala",
    "Ayudamos","#youth_unemployment","Визы в 45 стран мира","mom","Mom"

]
BLACKLIST_PAYS_MONDE = [
    "afghanistan", "albania", "albanie", "algeria", "algerie", "algérie", "andorra", "andorre", 
    "angola", "argentina", "argentine", "armenia", "armenie", "australia", "australie", "austria", 
    "autriche", "azerbaijan", "bahamas", "bahrain", "bahreïn", "bangladesh", "barbados", "belarus", 
    "biélorussie", "belgium", "belgique", "belize", "benin", "bénin", "bolivia", "bolivie", "bosnia", 
    "bosnie", "botswana", "brazil", "bresil", "brésil", "bulgaria", "bulgarie", "burkina faso", 
    "burundi", "cabo verde", "cap vert", "cambodia", "cambodge", "cameroon", "cameroun", "canada", 
    "centrafrique", "chad", "tchad", "chile", "chili", "china", "chine", "colombia", "colombie", 
    "comoros", "comores", "congo", "costa rica", "croatia", "croatie", "cuba", "cyprus", "chypre", 
    "czech", "tchèque", "denmark", "danemark", "djibouti", "dominican", "dominicaine", "ecuador", 
    "équateur", "egypt", "egypte", "égypte", "el salvador", "guinée", "eritrea", "erythrée", "estonia", 
    "estonie", "ethiopia", "ethiopie", "finland", "finlande", "france", "gabon", "gambia", "gambie", 
    "georgia", "géorgie", "germany", "allemagne", "ghana", "greece", "grèce", "guatemala", "haiti", 
    "haïti", "honduras", "hungary", "hongrie", "iceland", "islande", "india", "inde", "indonesia", 
    "indonésie", "iran", "iraq", "irak", "ireland", "irlande", "israel", "israël", "italy", "italie", 
    "côte d'ivoire", "jamaica", "jamaïque", "japan", "japon", "jordan", "jordanie", "kazakhstan", 
    "kenya", "corée", "kosovo", "kuwait", "koweït", "kyrgyzstan", "lebanon", "liban", "liberia", 
    "libya", "libye", "lithuania", "lituanie", "luxembourg", "madagascar", "malaysia", "malaisie", 
    "maldives", "mali", "malta", "malte", "mauritania", "mauritanie", "mauritius", "maurice", "mexico", 
    "mexique", "moldova", "moldavie", "monaco", "mongolia", "mongolie", "montenegro", "monténégro", 
    "myanmar", "birmanie", "namibia", "namibie", "nepal", "népal", "netherlands", "pays-bas", 
    "new zealand", "nouvelle-zélande", "nicaragua", "niger", "nigeria", "nigéria", "macedonia", 
    "macédoine", "norway", "norvège", "oman", "pakistan", "palestine", "panama", "paraguay", "peru", 
    "pérou", "philippines", "poland", "pologne", "portugal", "qatar", "romania", "roumanie", "russia", 
    "russie", "rwanda", "senegal", "sénégal", "serbia", "serbie", "seychelles", "singapore", 
    "singapour", "slovakia", "slovaquie", "slovenia", "slovénie", "somalia", "somalie", "south africa", 
    "afrique du sud", "spain", "espagne", "españa", "sri lanka", "sudan", "soudan", "sweden", "suède", 
    "switzerland", "suisse", "syria", "syrie", "taiwan", "taïwan", "tanzania", "tanzanie", "thailand", 
    "thaïlande", "togo", "tunisia", "tunisie", "turkey", "turquie", "uganda", "ouganda", "ukraine", 
    "uae", "emirates", "émirats", "uk", "royaume-uni", "england", "angleterre", "usa", "america", 
    "états-unis", "uruguay", "venezuela", "vietnam", "yemen", "yémen", "zambia", "zambie", "zimbabwe", 
    "deutschland", "italia", "nederland","normands","+86"
]

BLACKLIST_VILLES_ETRANGERES = [
    "paris", "marseille", "lyon", "toulouse", "nice", "nantes", "montpellier", "strasbourg", 
    "bordeaux", "lille", "rennes", "reims", "toulon", "dijon", "grenoble", "angers", "nîmes", 
    "villeurbanne", "clermont-ferrand", "le mans", "aix-en-provence", "brest", "tours", "amiens", 
    "limoges", "annecy", "boulogne-billancourt", "perpignan", "metz", "besançon", "orléans", 
    "saint-denis", "argenteuil", "rouen", "montreuil", "mulhouse", "corsica", "corse",
    "madrid", "barcelona", "barcelone", "valencia", "valence", "sevilla", "séville", "zaragoza", 
    "saragosse", "malaga", "málaga", "murcia", "murcie", "palma", "bilbao", "alicante", "cordoba", 
    "cordoue", "valladolid", "vigo", "gijon", "gijón", "granada", "grenade",
    "bruxelles", "brussels", "antwerp", "anvers", "ghent", "gand", "charleroi", "liege", "liège",
    "geneva", "genève", "zurich", "zürich", "basel", "bâle", "lausanne", "bern", "berne",
    "london", "londres", "birmingham", "manchester", "glasgow", "liverpool", "edinburgh", "édimbourg",
    "montreal", "montréal", "quebec", "québec", "toronto", "vancouver", 
    "dubai", "dubaï", "abu dhabi", "abou dhabi", "doha", "riyadh", "riyad", "jeddah", "djeddah", 
    "kuwait city", "manama", "muscat", "mascate", 
    "cairo", "caire", "alexandria", "alexandrie", "algiers", "alger", "oran", "tunis", "sfax", 
    "sousse", "dakar", "abidjan","Occitanie","Moscow","Warsaw", "Lisbon","Lisbonne","Athens","Athènes","Budapest",
    "Prague","Prague","Bratislava","Bratislava","Marinilla","Antioquía","Col🇨🇴"
]


MOTS_PARDON = ["formé à", "formée à", "diplômé", "diplômée"]
# --- FIN DES NOUVEAUX BOUCLIERS ---

CATEGORIES_INSTA_BUSINESS = {
    "local business", "product/service", "shopping & retail", "photographer",
    "event planning", "event planning service", "wedding planning service",
    "caterer", "florist", "beauty, cosmetic & personal care", "restaurant",
    "interior design studio", "advertising/marketing agency", "consulting agency",
    "party & event planning", "business service", "boutique",
}

MOTS_CLES_BUSINESS = [
    # Vocabulaire generique deja present
    "devis", "réservation", "reservation", "sur commande", "livraison",
    "sarl", "professionnel", "whatsapp", "commande", "boutique",
    "prestataire", "contactez", "contact:", "n'hésitez pas à nous",
    # Reservation
    "réservations", "réservez", "réserver", "résa", "booking", "book now",
    "book your", "rdv", "rendez-vous", "sur rendez-vous", "sur rdv",
    "prise de rdv", "uniquement sur rdv", "visite sur rendez-vous",
    "حجز", "للحجز", "الحجز", "احجز",
    # Devis / Prix / Tarif
    "devis gratuit", "prix", "tarif", "tarifs", "prix fixe", "sur demande",
    "prix sur demande", "forfait", "pack",
    # Contact / Demande
    "contactez-nous", "contactez nous", "contactez moi", "pour commander",
    "pour info", "info & résa", "infos/réservation", "dm pour", "dm for",
    "message privé", "mp", "envoyez-nous", "pour toute demande",
    "للاستفسار", "للطلب", "للتواصل", "تواصل معنا",
    # Deplacement / Zone de couverture
    "déplacement", "se déplace", "déplacement à domicile",
    "disponible partout", "partout au maroc", "partout dans le royaume",
    "worldwide", "available worldwide", "available all over morocco",
    "toutes les villes", "à domicile", "je me déplace", "working all over",
    "نتنقل", "في جميع المدن", "بجميع المدن",
    # Disponibilite / horaires
    "ouvert", "horaires", "disponible", "7/7", "du lundi au samedi",
    "uniquement sur whatsapp", "joignable uniquement", "joignable",
    # Livraison
    "livraison gratuite", "livraison partout", "shipping", "delivery",
    "worldwide shipping",
    # Telephone / contact
    "tel", "tél", "téléphone", "telephone", "gsm", "wtsp", "watsap",
    "watssap", "wtsapp", "appel", "appeler", "☎️", "📞", "📱", "📲", "✆",
]

PAYS_ETRANGERS = {
    "Paris": "France", "France": "France",
    "Dubai": "Émirats Arabes Unis", "Dubaï": "Émirats Arabes Unis",
    "London": "Royaume-Uni", "Londres": "Royaume-Uni", "United Kingdom": "Royaume-Uni",
    "Espagne": "Espagne", "Spain": "Espagne", "España": "Espagne",
    "Tunisie": "Tunisie", "Tunisia": "Tunisie",
    "Algerie": "Algérie", "Algérie": "Algérie", "Algeria": "Algérie",
    "Italie": "Italie", "Italy": "Italie",
    "USA": "États-Unis", "United States": "États-Unis", "Etats-Unis": "États-Unis", "États-Unis": "États-Unis",
    "Belgique": "Belgique", "Belgium": "Belgique",
    "Germany": "Allemagne", "Allemagne": "Allemagne",
    "Portugal": "Portugal",
    "Egypt": "Égypte", "Egypte": "Égypte", "Égypte": "Égypte",
}

# 🔑 Cle OpenAI pour l'IA de secours (Optionnel), chargee depuis .env
load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client_openai = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ============================================================
# 2. LE DICTIONNAIRE FLEXIBLE CORRIGÉ (Chaînes de caractères "r" de type Raw)
# ============================================================
dictionnaire_racines = {
    "Photographe & Vidéaste": [
        r"photo", r"vid[eé]a", r"film", r"shoot", r"lens", r"cam[eé]r",
        r"vid[eé]ographe", r"videographer", r"videography", r"filmmaker",
        r"cin[eé]aste", r"cinematic", r"drone", r"best[\s-]?of", r"reportage",
        r"r[eé]gie", r"montage vid[eé]o", r"iphonography",
        r"مصور", r"تصوير", r"فوتوغرافي",
    ],
    "DJ & Animation Musicale": [
        r"dj\b", r"disc jockey", r"platine", r"animat\w* music", r"animateur", r"animatrice",
        r"booking", r"management artistique",
        r"دي جي",
    ],
    "Orchestre & Musiciens": [
        r"orchest", r"musicien", r"violon", r"pian", r"saxo", r"groupe\w* music",
        r"chaabi", r"percussionniste", r"ambiance musicale",
        r"أوركسترا", r"فنان",
    ],
    "Chanteur / Chanteuse": [r"chant", r"vocal", r"singer"],
    "Dekka Marrakchia & Issawa": [
        r"dekka", r"dak", r"issaw", r"aissaou", r"marrakchi", r"gnaoua",
        r"bola\s?bola", r"groupe folklorique",
        r"عيساوة", r"بولا بولا", r"الدقة المراكشية",
    ],
    "Traiteur": [
        r"trait", r"cater", r"gastro", r"buffet", r"repas",
        r"tyafer", r"tyaffer", r"tanguif buffet", r"plateaux repas",
        r"ma[iî]tre traiteur", r"chef traiteur",
        r"طرايتور", r"طريطور", r"ممون الحفلات", r"ممون",
    ],
    "Service de bar & Mixologie": [r"bar\b", r"mixolog", r"cocktail", r"boisson"],
    "Pâtisserie & Cake Design": [
        r"p[aâ]tiss", r"cake", r"boulang", r"sucr", r"dessert", r"g[aâ]teau",
        r"cake design", r"wedding cake", r"chocolatier", r"drag[eé]e", r"confiserie",
    ],
    "Agence Événementielle & Planner": [
        r"event", r"organisat", r"agence\b", r"structur",
        r"event manager", r"event design", r"planificateur", r"coordinateur",
        r"event designer",
        r"منظم أعراس", r"تنظيم المناسبات",
    ],
    "Wedding planner": [r"wedding planner", r"event planner", r"organisateur d'[eé]v[eé]nements"],
    "Décoration & Scénographie": [
        r"d[eé]co\w*", r"sc[eé]no", r"design", r"ambianc",
        r"d[eé]coration mariage", r"d[eé]coration [eé]v[eé]nementielle",
    ],
    "Fleuriste": [r"fleur", r"flor", r"bouquet", r"d[eé]coration florale"],
    "Lieu de Réception": [
        r"salle", r"lieu", r"domain", r"reception", r"villa", r"palais", r"hotel", r"venue",
        r"salle des f[eê]tes", r"salle de r[eé]ception", r"event venue", r"riad [eé]v[eé]nementiel",
    ],
    "Location de Voitures": [r"voit", r"auto", r"car ", r"limousin"],
    "Maquillage & Coiffure (MUA)": [
        r"maquil", r"makeup", r"mua", r"coiff", r"hair", r"beaut",
        r"make-?up artist", r"hair ?stylist", r"hairdresser", r"visagiste",
        r"esth[eé]ticienne", r"microblading", r"bridal makeup", r"soft glam",
        r"formatrice makeup",
        r"مكياج", r"ميكب", r"تجميل", r"حلاقة", r"مصففة شعر",
    ],
    "Neggafa": [
        r"Retire", r"negaf", r"neggaf", r"ziyan", r"zian", r"majoud",
        r"tanguif", r"tenguif", r"tanggaft", r"tangaf", r"tangif",
        r"dfou[ae]?3", r"habillage mari[eé]e", r"amaria",
        r"نكافة", r"تنكاف", r"تنكافت", r"دفوع", r"عمارية",
    ],
    "Robes de Mariée": [
        r"robe", r"dress", r"caftan", r"coutur",
        r"wedding dress", r"bridal", r"takchita",
        r"قفطان", r"تكشيطة",
    ],
    "Bien-être & Esthétique": [r"spa ", r"esth[eé]tiq", r"soin", r"massage", r"ongl"],
    "Animation Enfants": [r"enfant", r"gonflab", r"kids", r"clown"],
    "Magie & Spectacles": [r"magi", r"spectac", r"illusion"],
    "Location de Matériel & Tentes": [
        r"tente", r"mat[eé]riel", r"chais", r"table", r"location",
        r"location tenues", r"location robes", r"[eé]cran g[eé]ant",
        r"sonorisation", r"[eé]clairage", r"structure", r"chapiteau",
        r"kraa", r"كراء",
    ],
    "Sécurité & Logistique": [r"s[eé]curit", r"logistiq", r"gard", r"vigil", r"vtc", r"transport"],
    "Cadeaux Invités": [r"cadeau", r"invit", r"souvenir"],
}

# Termes generiques mariage/evenement (tous secteurs) : ne definissent pas une
# categorie a eux seuls, mais servent de signal "vrai prestataire" (voir plus bas).
MOTS_CLES_EVENEMENT_GENERIQUE = [
    r"mariage", r"wedding", r"fian[cç]aille", r"engagement",
    r"[eé]v[eé]nement", r"[eé]v[eé]nementiel", r"c[eé]r[eé]monie",
    r"anniversaire", r"bapt[eê]me", r"naissance", r"henn[eé]", r"henna",
    r"aq[iï]qa", r"akika", r"aqeqa", r"soutenance", r"baby shower", r"gender reveal",
    r"عرس", r"أعراس", r"أفراح", r"خطوبة", r"حفلة", r"مناسبة", r"مناسبات", r"حنة", r"عقيقة",
]

# ============================================================
# 3. FONCTIONS Outils
# ============================================================

# --- FONCTION NOYAU POUR LES NOUVEAUX FILTRES STRICTS ---
def passe_filtre_strict(row):
    bio = str(row.get("Bio", "")).lower()
    adresse = str(row.get("Adresse", "")).lower()
    pseudo = str(row.get("Pseudo", "")).lower()
    username = str(row.get("Username", "")).lower()
    
    texte_complet = f"{bio} {adresse} {pseudo} {username}"
    
    # 1. Limite Abonnés
    followers_raw = str(row.get("Followers_Propre", "0")).replace(" ", "").replace(",", ".")
    try:
        followers = int(float(followers_raw))
    except ValueError:
        followers = 0
    if followers >= 1000000:
        return False, "non_prestataire" # Célébrités rejetées
        
    # 2. Numéro Étranger
    if REGEX_TEL_ETRANGER.search(texte_complet):
        return False, "pays"

    # 3. Alphabet Asiatique
    if REGEX_ALPHABET_ASIATIQUE.search(texte_complet):
        return False, "pays"

    # 4. Influenceurs
    for mot in BLACKLIST_INFLUENCEURS:
        if re.search(r"\b" + re.escape(mot) + r"\b", texte_complet):
            return False, "non_prestataire"
            
    # 5. E-commerce
    for mot in BLACKLIST_ECOMMERCE:
        if re.search(r"\b" + re.escape(mot) + r"\b", texte_complet):
            return False, "non_prestataire"
            
    # 6. Espagnol
    for mot in BLACKLIST_ESPAGNOL:
        if re.search(r"\b" + re.escape(mot) + r"\b", texte_complet):
            return False, "pays"

    # 7. Pays Monde
    for pays in BLACKLIST_PAYS_MONDE:
        if re.search(r"\b" + re.escape(pays) + r"\b", texte_complet):
            return False, "pays"

    # 8. Villes Etrangères
    for ville_ext in BLACKLIST_VILLES_ETRANGERES:
        if re.search(r"\b" + re.escape(ville_ext) + r"\b", texte_complet):
            pardonne = any(pardon in texte_complet for pardon in MOTS_PARDON)
            if not pardonne:
                return False, "pays"

    return True, "ok"
# --- FIN DE LA FONCTION NOYAU ---

def nettoyer_followers(texte):
    if not texte or texte == "" or "(non trouve)" in str(texte):
        return 0
    txt = str(texte).lower().replace(" ", "").replace(",", ".")
    m = re.search(r'([0-9.]+)([km]?)', txt)
    if not m:
        return 0
    valeur = float(m.group(1))
    mult = m.group(2)
    return int(valeur * 1000) if mult == 'k' else (int(valeur * 1000000) if mult == 'm' else int(valeur))

def fallback_api_ia(bio):
    """Retourne (categorie_ou_None, statut) ou statut explique ce qui s'est passe."""
    if not client_openai:
        return None, "IA non disponible (pas de cle OPENAI_API_KEY)"
    categories_possibles = list(dictionnaire_racines.keys())
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            timeout=20,
            messages=[
                {"role": "system", "content": (
                    "Tu classes la bio Instagram d'un prestataire evenementiel (mariage, fetes) "
                    "dans la categorie la plus proche parmi celles fournies, meme si le rapport "
                    "est indirect ou imparfait. Il n'y a pas d'option 'aucune' : tu dois "
                    "obligatoirement choisir une categorie via l'outil fourni."
                )},
                {"role": "user", "content": f"Bio a classer :\n{bio}"},
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "classifier_prestataire",
                    "description": "Choisit la categorie la plus proche pour ce prestataire.",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "categorie": {
                                "type": "string",
                                "enum": categories_possibles,
                            }
                        },
                        "required": ["categorie"],
                        "additionalProperties": False,
                    },
                },
            }],
            tool_choice={"type": "function", "function": {"name": "classifier_prestataire"}},
        )
        args = response.choices[0].message.tool_calls[0].function.arguments
        prediction = json.loads(args).get("categorie", "").strip()
        if prediction in categories_possibles:
            return prediction, "IA OpenAI"
        return None, f"IA OpenAI a repondu une valeur inattendue : '{prediction}'"
    except Exception as e:
        return None, f"Erreur appel API OpenAI : {str(e)[:120]}"

def determiner_categorie(bio, pseudo, instagram_cat):
    # Regroupement textuel global en minuscules
    texte_total = f"{str(bio)} {str(pseudo)} {str(instagram_cat)}".lower()

    # Étape A : Recherche directe et flexible via les expressions régulières
    for cat_finale, racines in dictionnaire_racines.items():
        for racine in racines:
            if re.search(racine, texte_total):
                return cat_finale, "Dictionnaire Flexible"

    # Étape B : Recours à l'IA Zero-Shot
    if str(bio).strip() and bio != "(non trouve)" and "INTROUVABLE" not in str(bio):
        prediction_ia, statut_ia = fallback_api_ia(str(bio))
        print(f"      [IA] {statut_ia}")
        if prediction_ia:
            return prediction_ia, "IA OpenAI"
        return "À vérifier manuellement", statut_ia

    return "À vérifier manuellement", "Bio vide/non exploitable (IA non appelee)"

def extraire_ville(adresse, bio):
    for texte in (adresse, bio):
        texte = str(texte)
        for ville in VILLES_MAROC:
            if re.search(re.escape(ville), texte, re.IGNORECASE):
                return ville
    return "Non trouvé"

def extraire_telephones(adresse, bio):
    texte_total = f"{adresse} {bio}"
    trouves = REGEX_TELEPHONE.findall(texte_total)
    vus = []
    for t in trouves:
        t_propre = re.sub(r"[\s.\-]", "", t)
        if t_propre not in vus:
            vus.append(t_propre)
    tel1 = vus[0] if len(vus) > 0 else "Non trouvé"
    tel2 = vus[1] if len(vus) > 1 else ""
    return tel1, tel2

def slugifier(texte):
    texte = str(texte).strip().lower()
    texte = re.sub(r"[^a-z0-9]+", "_", texte)
    return texte.strip("_")

def extraire_pays(adresse, bio, ville_maroc, tel1):
    texte_total = f"{adresse} {bio}"
    if ville_maroc != "Non trouvé":
        return "Maroc"
    if tel1 != "Non trouvé":
        return "Maroc"
    if re.search(r"\bmaroc\b|\bmorocco\b", texte_total, re.IGNORECASE):
        return "Maroc"
    for mot, pays in PAYS_ETRANGERS.items():
        if re.search(re.escape(mot), texte_total, re.IGNORECASE):
            return pays
    return "Maroc"  # aucun signal : on suppose Maroc par defaut

def est_categorie_business(categorie_insta):
    return str(categorie_insta).strip().lower() in CATEGORIES_INSTA_BUSINESS

def a_mots_cles_business(bio):
    bio_lower = str(bio).lower()
    return any(mot in bio_lower for mot in MOTS_CLES_BUSINESS)

def a_mots_cles_evenement(bio):
    bio_lower = str(bio).lower()
    return any(re.search(racine, bio_lower) for racine in MOTS_CLES_EVENEMENT_GENERIQUE)

def a_mots_cles_metier(bio):
    bio_lower = str(bio).lower()
    for racines in dictionnaire_racines.values():
        for racine in racines:
            if re.search(racine, bio_lower):
                return True
    return False

def est_vrai_prestataire(categorie_insta, bio, liens_externes):
    """
    'Vrai prestataire' si AU MOINS UN signal est present :
    categorie Instagram business-like, lien externe, mots-cles business,
    mots-cles metier/mariage, ou mots-cles evenement generique dans la bio.
    """
    business_like = est_categorie_business(categorie_insta)
    lien_externe = bool(str(liens_externes).strip())
    mots_cles = a_mots_cles_business(bio)
    mots_metier = a_mots_cles_metier(bio)
    mots_evenement = a_mots_cles_evenement(bio)

    return business_like or lien_externe or mots_cles or mots_metier or mots_evenement

    return condition1 and condition2

@st.cache_data(show_spinner="Construction de la base globale a partir des nouveaux comptes...")
def construire_base_globale(df_clean):
    df_nouveaux = df_clean[df_clean["Existe_Dans_BD_Final"].str.strip() == "Non"].copy()

    date_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lignes = []
    nb_exclus_pays = 0
    nb_exclus_non_prestataire = 0

    for idx, row in df_nouveaux.iterrows():
        username = str(row.get("Username", "")).strip()
        pseudo = str(row.get("Pseudo", "")).strip()
        adresse = str(row.get("Adresse", "")).strip()
        bio = str(row.get("Bio", "")).strip()

        nom = pseudo if pseudo else username
        ville = extraire_ville(adresse, bio)
        tel1, tel2 = extraire_telephones(adresse, bio)
        pays = extraire_pays(adresse, bio, ville, tel1)

        if pays != "Maroc":
            nb_exclus_pays += 1
            continue
            
        # --- INTÉGRATION DU FILTRAGE ULTRA-STRICT ---
        # Le filtrage strict est inséré ici. Les rejets augmentent les compteurs natifs 
        # pour que l'interface Streamlit continue de fonctionner exactement comme avant.
        est_valide_strict, type_rejet = passe_filtre_strict(row)
        if not est_valide_strict:
            if type_rejet == "pays":
                nb_exclus_pays += 1
            else:
                nb_exclus_non_prestataire += 1
            continue
        # ---------------------------------------------

        categorie_insta = str(row.get("Categorie", "")).strip()
        liens_externes = str(row.get("Liens_externes", "")).strip()
        if not est_vrai_prestataire(categorie_insta, bio, liens_externes):
            nb_exclus_non_prestataire += 1
            continue

        slug_nom = slugifier(nom) or slugifier(username)
        id_prestataire = f"pr_{slug_nom}_{idx + 1}"

        lignes.append({
            "ID_Prestataire": id_prestataire,
            "Date_Scraping": date_scraping,
            "Source": SOURCE_LABEL,
            "Nom": nom,
            "Categorie_Propre": row.get("Categorie_Finale", "") or "Non trouvé",
            "Ville": ville,
            "Telephone_1": tel1,
            "Telephone_2": tel2,
            "URL_Facebook": "Non trouvé",
            "URL_Instagram": row.get("URL_Instagram", "") or f"https://www.instagram.com/{username}/",
            "URL_YouTube": "Non trouvé",
            "Description": bio if bio else "Non trouvé",
            "Instagram_Followers": row.get("Followers_Propre", ""),
            "Facebook_Followers": "",
            "note_maps": "",
            "nombre_review": "",
        })

    df_final = pd.DataFrame(lignes, columns=COLONNES_BASE_GLOBALE)
    df_final.to_excel(FICHIER_BASE_GLOBALE, index=False)
    return df_final, nb_exclus_pays, nb_exclus_non_prestataire

# ============================================================
# 4. EXÉCUTION DU PIPELINE (ÉTAPES 1 & 2, MISES EN CACHE)
# ============================================================
@st.cache_data(show_spinner="Filtration, catégorisation et calcul des liaisons...")
def executer_etapes_1_2(fichier_input):
    df_brut = pd.read_excel(fichier_input, dtype=str).fillna("")
    if LIMITE_TEST:
        df_brut = df_brut.head(LIMITE_TEST)

    comptes_gardes = []
    for idx, row in df_brut.iterrows():
        existe = str(row.get("Existe_Dans_BD_Final", "")).strip()
        followers_clean = nettoyer_followers(row.get("Followers", ""))

        if followers_clean < 500 and existe == "Non":
            continue

        row_dict = row.to_dict()
        row_dict["Followers_Propre"] = int(followers_clean)

        # Si pas de bio, on ne classe pas du tout : categorie laissee vide
        bio_brute = str(row.get("Bio", "")).strip()
        if not bio_brute or bio_brute == "(non trouve)" or "INTROUVABLE" in bio_brute:
            cat, methode = "", "Bio non disponible"
        else:
            cat, methode = determiner_categorie(row.get("Bio", ""), row.get("Pseudo", ""), row.get("Categorie", ""))

        row_dict["Categorie_Finale"] = cat
        row_dict["Methode_Classification"] = methode

        comptes_gardes.append(row_dict)

    df_clean = pd.DataFrame(comptes_gardes)
    df_clean.to_excel(FICHIER_DATA_CLEAN, index=False)

    # ---- ÉTAPE 2 : RELATIONS & FRÉQUENCES ----
    relations = []
    categories_nodes = {}

    for idx, row in df_clean.iterrows():
        cible = str(row.get("Username", "")).strip()
        cat_cible = str(row.get("Categorie_Finale", ""))
        sources_brutes = str(row.get("Compte_Origine", ""))

        if not cible or not sources_brutes:
            continue

        categories_nodes[cible] = cat_cible
        prestataires_sources = [s.strip() for s in sources_brutes.split("|") if s.strip()]

        for source in prestataires_sources:
            if source not in categories_nodes:
                categories_nodes[source] = "Prestataire Réseau"

            relations.append({
                "Source": source,
                "Cible": cible,
                "Categorie_Cible": cat_cible
            })

    df_edges = pd.DataFrame(relations)
    df_stats = df_edges.groupby(['Source', 'Categorie_Cible']).size().reset_index(name='Nombre_Collaborations')
    df_stats = df_stats.sort_values(by=['Source', 'Nombre_Collaborations'], ascending=[True, False])
    df_stats.to_excel(FICHIER_SEGMENTS, index=False)

    return df_clean, df_edges, categories_nodes, df_stats


st.set_page_config(page_title="Réseau des Prestataires", layout="wide")
st.title("🕸️ Réseau des collaborations entre prestataires")

if not os.path.exists(FICHIER_INPUT):
    st.error(f"Le fichier {FICHIER_INPUT} est introuvable.")
    st.stop()

df_clean, df_edges, categories_nodes, df_stats = executer_etapes_1_2(FICHIER_INPUT)
st.success(f"Étapes 1 & 2 réussies : '{FICHIER_DATA_CLEAN}' et '{FICHIER_SEGMENTS}' exportés.")

# ---- ÉTAPE 3 : CARTOGRAPHIE DU RÉSEAU (AFFICHÉE DANS STREAMLIT) ----
df_graph_edges = df_edges.groupby(['Source', 'Cible']).size().reset_index(name='Poids')

G = nx.Graph()
for idx, row in df_graph_edges.iterrows():
    G.add_edge(row['Source'], row['Cible'], value=int(row['Poids']), title=f"Interactions : {row['Poids']}")

for node in G.nodes():
    groupe_cat = categories_nodes.get(node, "Inconnue")
    G.nodes[node]['group'] = groupe_cat
    G.nodes[node]['title'] = f"Compte : @{node}\nSegment : {groupe_cat}"

net = Network(height="850px", width="100%", bgcolor="#ffffff", font_color="black", directed=False)
net.barnes_hut(gravity=-10000, central_gravity=0.3, spring_length=150)
net.from_nx(G)

net.set_options("""
var options = {
  "nodes": { "font": { "size": 14 } },
  "interaction": { "hover": true, "navigationButtons": true, "zoomView": false },
  "physics": { "stabilization": { "iterations": 100 } }
}
""")

onglet_graphe, onglet_stats, onglet_base_globale = st.tabs(
    ["🕸️ Graphe réseau", "📊 Statistiques par segment", "🗂️ Base globale (nouveaux prestataires)"]
)

with onglet_graphe:
    components.html(net.generate_html(), height=870, scrolling=True)

with onglet_stats:
    st.dataframe(df_stats, use_container_width=True)

with onglet_base_globale:
    df_base_globale, nb_exclus_pays, nb_exclus_non_prestataire = construire_base_globale(df_clean)

    nb_non_total = (df_clean["Existe_Dans_BD_Final"].str.strip() == "Non").sum()
    nb_villes_trouvees = (df_base_globale["Ville"] != "Non trouvé").sum()
    nb_tel_trouves = (df_base_globale["Telephone_1"] != "Non trouvé").sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Comptes nouveaux convertis", f"{len(df_base_globale)} / {nb_non_total}")
    col2.metric("Exclus (hors Maroc)", f"{nb_exclus_pays}")
    col3.metric("Exclus (pas vrai prestataire)", f"{nb_exclus_non_prestataire}")
    col4.metric("Villes extraites", f"{nb_villes_trouvees}/{len(df_base_globale)}")
    col5.metric("Téléphones extraits", f"{nb_tel_trouves}/{len(df_base_globale)}")

    st.success(f"Fichier généré : '{FICHIER_BASE_GLOBALE}'")
    st.dataframe(df_base_globale, use_container_width=True)

    with open(FICHIER_BASE_GLOBALE, "rb") as f:
        st.download_button(
            "Télécharger le fichier Excel",
            data=f,
            file_name=FICHIER_BASE_GLOBALE,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )