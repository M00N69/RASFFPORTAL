import streamlit as st
import pandas as pd
import plotly.express as px
import chardet
from Levenshtein import distance

st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

def nettoyer_donnees(df):
    """Nettoie et standardise les données du DataFrame."""

    # 1. Normaliser les noms de pays et d'origine
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
    df["notifying_country"] = df["notifying_country"].map(lambda x: pays_standardises.get(x, x))
    df["origin"] = df["origin"].map(lambda x: pays_standardises.get(x, x))

    # 2. Correction des noms de dangers (fuzzy matching)
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
        "peanut undeclared",
        "gluten too high content",
        # ... ajouter d'autres dangers ici
    ]

    def corriger_dangers(nom_danger):
        best_match = min(dangers_standardises, key=lambda x: distance(x, nom_danger))
        return best_match if distance(best_match, nom_danger) <= 3 else nom_danger

    df["hazards"] = df["hazards"].apply(corriger_dangers)

    # 3. Conversion des types de données
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S", errors='coerce')

    # 4. Gestion des valeurs manquantes
    df = df.fillna("")

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
        * **Nettoyage des données :** L'outil nettoie et standardise les données pour une analyse plus précise.
        * **Statistiques descriptives :** Obtenez des informations clés sur les données.
        * **Analyse de tendances :** Identifiez les tendances émergentes dans les notifications RASFF.
        * **Visualisations :** Visualisez les données à l'aide de graphiques interactifs.
        * **Filtres et tri :** Filtrez et triez les données en fonction de critères spécifiques.
        * **Analyse de corrélation :** Étudiez les relations entre les différentes variables des données.
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

    uploaded_file = st.file_uploader("Téléchargez un fichier CSV RASFF", type=["csv"])

    if uploaded_file is not None:
        try:
            file_content = uploaded_file.read()
            encodage = chardet.detect(file_content)['encoding']
            uploaded_file.seek(0)

            df = pd.read_csv(uploaded_file, encoding=encodage, quotechar='"')
            df = nettoyer_donnees(df)

            st.markdown("## Options d'analyse et de tri")

            colonnes_a_afficher = st.multiselect("Sélectionnez les colonnes à afficher", df.columns)
            df_display = df[colonnes_a_afficher] if colonnes_a_afficher else df

            filtres = {}
            for colonne in df.columns:
                if df[colonne].dtype == "object":
                    options = df[colonne].unique()
                    filtre_colonne = st.multiselect(f"Filtrez {colonne}", options)
                    if filtre_colonne:
                        filtres[colonne] = filtre_colonne

            colonne_tri = st.selectbox("Trier par", df.columns)
            ordre_tri = st.radio("Ordre de tri", ("Croissant", "Décroissant"))
            
            for colonne, valeurs in filtres.items():
                df_display = df_display[df_display[colonne].isin(valeurs)]

            if colonne_tri:
                df_display = df_display.sort_values(by=colonne_tri, ascending=(ordre_tri == "Croissant"))

            st.markdown("## Données analysées")
            st.dataframe(df_display)

            st.markdown("## Statistiques descriptives")
            st.write(df_display.describe())

            st.markdown("## Analyse de tendances")

            st.markdown("### Nombre de notifications par pays")
            fig_pays = px.bar(df_display, x="notifying_country", y="reference", title="Nombre de notifications par pays")
            st.plotly_chart(fig_pays, use_container_width=True)

            st.markdown("### Distribution des dangers")
            fig_dangers = px.histogram(df_display, x="hazards", title="Distribution des dangers")
            st.plotly_chart(fig_dangers, use_container_width=True)

            st.markdown("## Analyse de corrélation")
            
            colonnes_numeriques = df_display.select_dtypes(include=['float64', 'int64']).columns
            if len(colonnes_numeriques) > 1:
                st.markdown("### Matrice de corrélation")
                correlation_matrix = df_display[colonnes_numeriques].corr()
                fig_correlation = px.imshow(correlation_matrix, color_continuous_scale='RdBu_r', title="Matrice de corrélation")
                st.plotly_chart(fig_correlation, use_container_width=True)

                st.markdown("### Corrélation entre deux variables")
                colonne_x = st.selectbox("Sélectionnez la première variable", colonnes_numeriques)
                colonne_y = st.selectbox("Sélectionnez la deuxième variable", colonnes_numeriques)
                fig_correlation_variables = px.scatter(df_display, x=colonne_x, y=colonne_y, title=f"Corrélation entre {colonne_x} et {colonne_y}")
                st.plotly_chart(fig_correlation_variables, use_container_width=True)
            else:
                st.warning("Pas assez de colonnes numériques pour l'analyse de corrélation.")

        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))

if page == "Accueil":
    page_accueil()
elif page == "Analyse":
    page_analyse()
