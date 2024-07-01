import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
import plotly.express as px
import chardet
from io import StringIO
from Levenshtein import distance  # Import Levenshtein for faster fuzzy matching

st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

def nettoyer_donnees(df):
    """Nettoie et standardise les données du DataFrame."""

    # 1. Normaliser les noms de pays et d'origine
    def normaliser_pays(nom_pays):
        """Normalise le nom d'un pays."""
        pays_standardises = {
            "France": "France",
            "United Kingdom": "Royaume-Uni",
            "Türkiye": "Turquie",
            "Poland": "Pologne",
            "Netherlands": "Pays-Bas",
            "Italy": "Italie",
            "Germany": "Allemagne",
            "Spain": "Espagne",
            "Czech Republic": "République tchèque",
            "Greece": "Grèce",
            "Egypt": "Égypte",
            "United States": "États-Unis",
            # ... ajouter d'autres pays ici
        }
        return pays_standardises.get(nom_pays, nom_pays)

    df["notifying_country"] = df["notifying_country"].apply(normaliser_pays)
    df["origin"] = df["origin"].apply(normaliser_pays)

    # 2. Correction des noms de dangers (fuzzy matching)
    def corriger_dangers(nom_danger):
        """Corrige les erreurs de frappe dans le nom d'un danger."""
        dangers_standardises = [
            "chlorpyrifos",
            "chlorpyrifos-ethyl",
            "Salmonella",
            "Salmonella spp.",
            "Salmonella Enteritidis",
            "Aflatoxin",
            "Aflatoxin B1",
            "aflatoxin total",
            "ochratoxin A",
            "E220- sulfur dioxide", 
            "cadmium",
            "Listeria monocytogenes",
            "norovirus",
            "peanut  undeclared",
            "gluten  too high content",
            # ... ajouter d'autres dangers ici
        ]
        # Using Levenshtein distance for faster fuzzy matching
        best_match = min(dangers_standardises, key=lambda x: distance(x, nom_danger)) 
        if distance(best_match, nom_danger) <= 3: # Adjust threshold as needed
            return best_match
        else:
            return nom_danger

    # Apply fuzzy matching to each row in the "hazards" column
    df["hazards"] = df.apply(lambda row: corriger_dangers(row['hazards']), axis=1)

    # 3. Conversion des types de données ("date" only!)
    try:
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S")
    except ValueError:
        st.warning(f"Impossible de convertir la colonne 'date' en date.")

    # 4. Gestion des valeurs manquantes
    df = df.fillna("")  # Remplace les valeurs manquantes par des chaînes vides

    return df

def page_accueil():
    """Affiche la page d'accueil."""
    st.title("Analyseur de Données RASFF")
    st.markdown("## Bienvenue !")
    st.markdown(
        """
        Cet outil vous permet d'analyser les données du système RASFF (Rapid Alert System for Food and Feed). 
        Il vous offre des fonctionnalités puissantes pour explorer les tendances, identifier les risques et 
        comprendre les problèmes de sécurité alimentaire.
        """
    )

    st.markdown("## Fonctionnalités")
    st.markdown(
        """
        * **Téléchargement de fichier CSV :** Importez un fichier CSV contenant des données RASFF.
        * **Nettoyage des données :** L'outil nettoie et standardise les données pour une analyse plus précise, 
        en gérant les caractères spéciaux de différentes langues européennes.
        * **Statistiques descriptives :** Obtenez des informations clés sur les données, telles que le nombre total de notifications, les pays les plus souvent impliqués et les dangers les plus courants.
        * **Analyse de tendances :** Identifiez les tendances émergentes dans les notifications RASFF, comme les dangers qui augmentent ou diminuent au fil du temps.
        * **Visualisations :** Visualisez les données à l'aide de graphiques et de tableaux interactifs pour une meilleure compréhension.
        * **Filtres et tri :** Filtrez et triez les données en fonction de critères spécifiques pour répondre à vos questions d'analyse.
        * **Analyse de corrélation :**  Étudiez les relations entre les différentes variables des données.
        """
    )

    st.markdown("## Instructions")
    st.markdown(
        """
        1. Téléchargez un fichier CSV contenant des données RASFF à partir de la page "Analyse".
        2. Sélectionnez les options d'analyse et de tri souhaitées.
        3. Visualisez les résultats et exportez les données si nécessaire.
        """
    )

def page_analyse():
    """Affiche la page d'analyse."""
    st.title("Analyse des Données RASFF")

    # Téléchargement du fichier CSV
    uploaded_file = st.file_uploader("Téléchargez un fichier CSV RASFF", type=["csv"])

    if uploaded_file is not None:
        try: 
            # Détecter l'encodage du fichier CSV
            file_content = uploaded_file.read()
            encodage = chardet.detect(file_content)['encoding']
            # Rewind the file pointer
            uploaded_file.seek(0)  

            # Lire le fichier CSV avec le bon encodage 
            df = pd.read_csv(uploaded_file, encoding=encodage, quotechar='"')

            # Convert "reference" to string (ensure it's text)
            df['reference'] = df['reference'].astype(str) 

            # Appliquer la fonction de nettoyage
            df = nettoyer_donnees(df)

            # Options d'analyse et de tri
            st.markdown("## Options d'analyse et de tri")

            # Sélection de colonnes
            colonnes_a_afficher = st.multiselect("Sélectionnez les colonnes à afficher", df.columns)
            df = df[colonnes_a_afficher]

            # Filtres
            filtres = {}
            for colonne in df.columns:
                if df[colonne].dtype == "object":
                    options = df[colonne].unique()
                    filtre_colonne = st.multiselect(f"Filtrez {colonne}", options)
                    if filtre_colonne:
                        filtres[colonne] = filtre_colonne

            # Tri
            colonne_tri = st.selectbox("Trier par", df.columns)
            ordre_tri = st.radio("Ordre de tri", ("Croissant", "Décroissant"))

            if ordre_tri == "Croissant":
                ordre_tri = True
            else:
                ordre_tri = False

            # Application des filtres et du tri
            for colonne, valeurs in filtres.items():
                df = df[df[colonne].isin(valeurs)]

            if colonne_tri:
                df = df.sort_values(by=colonne_tri, ascending=ordre_tri)

            # Affichage des données
            st.markdown("## Données analysées")
            st.dataframe(df)

            # Statistiques descriptives
            st.markdown("## Statistiques descriptives")
            st.write(df.describe())

            # Analyse de tendances
            st.markdown("## Analyse de tendances")

            # Graphique à barres (nombre de notifications par pays)
            st.markdown("### Nombre de notifications par pays")
            fig_pays = px.bar(df, x="notifying_country", y="reference", title="Nombre de notifications par pays")
            st.plotly_chart(fig_pays, use_container_width=True)

            # Histogramme (distribution des dangers)
            st.markdown("### Distribution des dangers")
            fig_dangers = px.histogram(df, x="hazards", title="Distribution des dangers")
            st.plotly_chart(fig_dangers, use_container_width=True)

            # Analyse de corrélation
            st.markdown("## Analyse de corrélation")

            # Matrice de corrélation
            st.markdown("### Matrice de corrélation")
            correlation_matrix = df.corr()
            fig_correlation = px.imshow(correlation_matrix, color_continuous_scale='RdBu_r', title="Matrice de corrélation")
            st.plotly_chart(fig_correlation, use_container_width=True)

            # Graphique à barres (corrélation entre deux variables)
            st.markdown("### Corrélation entre deux variables")
            colonne_x = st.selectbox("Sélectionnez la première variable", df.columns)
            colonne_y = st.selectbox("Sélectionnez la deuxième variable", df.columns)
            fig_correlation_variables = px.bar(df, x=colonne_x, y=colonne_y, title=f"Corrélation entre {colonne_x} et {colonne_y}")
            st.plotly_chart(fig_correlation_variables, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))

if page == "Accueil":
    page_accueil()
elif page == "Analyse":
    page_analyse()
