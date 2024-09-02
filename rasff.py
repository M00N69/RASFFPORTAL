import streamlit as st
import pandas as pd
import plotly.express as px
import chardet
import requests
from io import BytesIO
import openpyxl
from Levenshtein import distance
import datetime

# Importer les listes depuis les fichiers séparés
from product_categories import product_categories
from hazards import hazards
from hazard_categories import hazard_categories
from notifying_countries import notifying_countries
from origin_countries import origin_countries

st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

def corriger_dangers(nom_danger):
    """Corrige les erreurs de frappe dans le nom d'un danger."""
    nom_danger = str(nom_danger)
    best_match = min(hazards, key=lambda x: distance(x, nom_danger))
    if distance(best_match, nom_danger) <= 3:
        return best_match
    else:
        return nom_danger

def mapper_danger_a_categorie(danger):
    """Mappe un danger à sa catégorie de danger correspondante."""
    for categorie, description in hazard_categories.items():
        if description.lower() in danger.lower():
            return categorie
    return "Autre"  # Si aucun match n'est trouvé

def nettoyer_donnees(df):
    """Nettoie et standardise les données du DataFrame."""
    
    # Normaliser les noms de pays et d'origine
    df["notifying_country"] = df["notifying_country"].apply(lambda x: x if x in notifying_countries else x)
    df["origin"] = df["origin"].apply(lambda x: x if x in origin_countries else x)

    # Normaliser les catégories de produits
    df["category"] = df["category"].apply(lambda x: product_categories.get(x, x))

    # Corriger et mapper les dangers à leurs catégories
    if "hazards" in df.columns:
        df["hazards"] = df["hazards"].apply(corriger_dangers)
        df["hazard_category"] = df["hazards"].apply(mapper_danger_a_categorie)

    # Conversion des dates
    try:
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S")
    except ValueError:
        st.warning(f"Impossible de convertir la colonne 'date' en date.")
    df = df.fillna("")
    return df

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

def calculer_statistiques_descriptives(df):
    """Calcule les statistiques descriptives pour le nombre de notifications par pays et par type de danger."""
    # Groupement par pays et par danger
    grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='Nombre de notifications')
    
    # Calcul des statistiques descriptives
    stats = grouped['Nombre de notifications'].describe()
    return stats, grouped

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
            colonnes_a_afficher = ['notifying_country', 'category', 'hazard_category', 'date'] if 'hazard_category' in df.columns else ['notifying_country', 'category', 'date']
            df = df[colonnes_a_afficher]

            # **Nouveau** : Filtrer par catégorie de dangers
            categories_dangers_selectionnees = st.multiselect("Filtrez par catégories de dangers", df['hazard_category'].unique())
            if categories_dangers_selectionnees:
                df = df[df['hazard_category'].isin(categories_dangers_selectionnees)]

            # Calculer les statistiques descriptives sur le nombre de notifications par pays et type de danger
            stats, grouped = calculer_statistiques_descriptives(df)

            # Explication des données analysées
            st.markdown("## Données analysées")
            st.dataframe(df)
            st.markdown(
                """
                **Données analysées :**
                - `notifying_country` : Le pays ayant émis la notification.
                - `category` : Catégorie du produit ou matériel concerné par la notification.
                - `hazard_category` : Catégorie de danger associée au danger rapporté.
                - `date` : Date de la notification.
                """
            )

            # Statistiques descriptives
            st.markdown("## Statistiques descriptives sur les notifications")
            st.write(stats)

            # Afficher le nombre de notifications par pays et type de danger
            st.markdown("### Nombre de notifications par pays et type de danger")
            st.dataframe(grouped)

            # Analyse de tendances
            st.markdown("## Analyse de tendances")

            # Graphique à barres (nombre de notifications par pays)
            st.markdown("### Nombre de notifications par pays")
            fig_pays = px.bar(grouped, x="notifying_country", y="Nombre de notifications", title="Nombre de notifications par pays")
            st.plotly_chart(fig_pays, use_container_width=True)

            # Histogramme (distribution des dangers) si applicable
            if "hazard_category" in df.columns:
                st.markdown("### Distribution des catégories de dangers")
                fig_dangers = px.histogram(grouped, x="hazard_category", y="Nombre de notifications", title="Distribution des catégories de dangers")
                st.plotly_chart(fig_dangers, use_container_width=True)

            # **Nouveau** : Diagramme camembert sur les catégories de produits
            st.markdown("### Répartition des notifications par catégories de produits")
            fig_pie = px.pie(df, names='category', title="Répartition des notifications par catégories de produits")
            st.plotly_chart(fig_pie, use_container_width=True)

        else:
            st.error("Aucune donnée disponible pour les semaines sélectionnées.")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))

if page == "Accueil":
    page_accueil()
elif page == "Analyse":
    page_analyse()
