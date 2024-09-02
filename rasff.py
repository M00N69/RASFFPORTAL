import streamlit as st
import pandas as pd
import plotly.express as px
import chardet
import requests
from io import BytesIO
import openpyxl
from Levenshtein import distance
import datetime

st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

def nettoyer_donnees(df):
    """Nettoie et standardise les données du DataFrame."""
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

    def corriger_dangers(nom_danger):
        """Corrige les erreurs de frappe dans le nom d'un danger."""
        nom_danger = str(nom_danger)
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
        best_match = min(dangers_standardises, key=lambda x: distance(x, nom_danger))
        if distance(best_match, nom_danger) <= 3:
            return best_match
        else:
            return nom_danger

    if "hazards" in df.columns:
        df["hazards"] = df.apply(lambda row: corriger_dangers(row['hazards']), axis=1)

    try:
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S")
    except ValueError:
        st.warning(f"Impossible de convertir la colonne 'date' en date.")
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
        * **Téléchargement et analyse de données :** L'outil peut télécharger automatiquement les fichiers RASFF classés par semaine.
        * **Nettoyage automatique des données :** Les données sont nettoyées et standardisées pour assurer une analyse cohérente.
        * **Statistiques descriptives et visualisations :** Obtenez des informations clés et visualisez les données via des graphiques interactifs.
        * **Analyse de tendances :** Découvrez les tendances émergentes dans les notifications RASFF.
        """
    )
    st.markdown("## Instructions")
    st.markdown(
        """
        1. Sélectionnez l'année et les semaines que vous souhaitez analyser.
        2. Les données seront automatiquement téléchargées et analysées.
        3. Visualisez les résultats et explorez les statistiques descriptives et les corrélations.
        """
    )

def telecharger_et_nettoyer_donnees(annee, semaines):
    """Télécharge et combine les données de plusieurs semaines."""
    dfs = []
    url_template = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    
    for semaine in semaines:
        url = url_template.format(str(annee)[2:], annee, str(semaine).zfill(2))
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_excel(BytesIO(response.content))
            dfs.append(df)
        else:
            st.error(f"Échec du téléchargement des données pour la semaine {semaine}.")
    
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df = nettoyer_donnees(df)
        return df
    else:
        return pd.DataFrame()  # Retourne un DataFrame vide si aucun fichier n'a pu être téléchargé

def page_analyse():
    """Affiche la page d'analyse."""
    st.title("Analyse des Données RASFF")

    # Formulaire pour saisir l'année et les semaines
    annee = st.number_input("Entrez l'année", min_value=2000, max_value=datetime.datetime.now().year, value=datetime.datetime.now().year)
    semaines = st.multiselect("Sélectionnez les semaines", list(range(1, min(36, datetime.datetime.now().isocalendar()[1] + 1))), default=[35])

    if semaines:
        df = telecharger_et_nettoyer_donnees(annee, semaines)
        if not df.empty:
            # Sélection automatique des colonnes nécessaires
            colonnes_a_afficher = ['notifying_country', 'reference', 'hazards', 'date'] if 'hazards' in df.columns else ['notifying_country', 'reference', 'date']
            df = df[colonnes_a_afficher]

            # Explication des données analysées
            st.markdown("## Données analysées")
            st.dataframe(df)
            st.markdown(
                """
                **Données analysées :**
                - `notifying_country` : Le pays ayant émis la notification.
                - `reference` : Référence unique de chaque notification.
                - `hazards` : (si disponible) Type de danger rapporté dans la notification.
                - `date` : Date de la notification.
                """
            )

            # Statistiques descriptives
            st.markdown("## Statistiques descriptives")
            st.write(df.describe(include='all'))

            # Analyse de tendances
            st.markdown("## Analyse de tendances")

            # Graphique à barres (nombre de notifications par pays)
            st.markdown("### Nombre de notifications par pays")
            fig_pays = px.bar(df, x="notifying_country", y="reference", title="Nombre de notifications par pays", labels={'reference': 'Nombre de notifications'})
            st.plotly_chart(fig_pays, use_container_width=True)

            # Histogramme (distribution des dangers) si applicable
            if "hazards" in df.columns:
                st.markdown("### Distribution des dangers")
                fig_dangers = px.histogram(df, x="hazards", title="Distribution des dangers")
                st.plotly_chart(fig_dangers, use_container_width=True)

            # Analyse de corrélation
            if len(df.select_dtypes(include=["number"]).columns) > 1:
                st.markdown("## Analyse de corrélation")
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
        else:
            st.error("Aucune donnée disponible pour les semaines sélectionnées.")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))

if page == "Accueil":
    page_accueil()
elif page == "Analyse":
    page_analyse()
