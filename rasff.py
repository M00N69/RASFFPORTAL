import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import datetime
from Levenshtein import distance
from pandasai import PandasAI
from groq import Groq  # Importation du client Groq pour LLM

# Importer les listes depuis les fichiers séparés
from product_categories import product_categories
from hazards import hazards
from hazard_categories import hazard_categories
from notifying_countries import notifying_countries
from origin_countries import origin_countries

# Fonction pour configurer le client Groq
def get_groq_client():
    """Initialise et renvoie un client Groq avec la clé API."""
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

# Initialisation de PandasAI avec Groq comme LLM
groq_client = get_groq_client()
pandas_ai = PandasAI(groq_client)

# Configurer la page Streamlit
st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# Fonctions pour le traitement des données
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
    df["notifying_country"] = df["notifying_country"].apply(lambda x: x if x in notifying_countries else x)
    df["origin"] = df["origin"].apply(lambda x: x if x in origin_countries else x)
    df["category"] = df["category"].apply(lambda x: product_categories.get(x, x))

    # Corriger et mapper les dangers à leurs catégories
    if "hazards" in df.columns:
        df["hazards"] = df["hazards"].apply(corriger_dangers)
        df["hazard_category"] = df["hazards"].apply(mapper_danger_a_categorie)

    try:
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S")
    except ValueError:
        st.warning("Impossible de convertir la colonne 'date' en date.")
    
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
        return pd.DataFrame()

def calculer_statistiques_descriptives(df):
    """Calcule les statistiques descriptives pour le nombre de notifications par pays et par type de danger."""
    grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='Nombre de notifications')
    stats = grouped['Nombre de notifications'].describe()
    return stats, grouped

def page_accueil():
    """Affiche la page d'accueil."""
    st.title("Analyseur de Données RASFF")
    st.markdown("## Bienvenue !")
    st.markdown(
        """
        Cet outil vous permet d'analyser les données du système RASFF (Rapid Alert System for Food and Feed). 
        Explorez les tendances, identifiez les risques et comprenez les problèmes de sécurité alimentaire.
        """
    )
    st.markdown("## Fonctionnalités")
    st.markdown(
        """
        * **Téléchargement et analyse de données**
        * **Nettoyage automatique des données**
        * **Statistiques descriptives et visualisations**
        * **Analyse de tendances**
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
            colonnes_a_afficher = ['notifying_country', 'category', 'hazard_category', 'date'] if 'hazard_category' in df.columns else ['notifying_country', 'category', 'date']
            df = df[colonnes_a_afficher]

            # Nouveau : Filtre par catégorie de danger
            categories_dangers_selectionnees = st.multiselect("Filtrez par catégories de dangers", df['hazard_category'].unique())
            if categories_dangers_selectionnees:
                df = df[df['hazard_category'].isin(categories_dangers_selectionnees)]

            stats, grouped = calculer_statistiques_descriptives(df)

            st.markdown("## Données analysées")
            st.dataframe(df)

            st.markdown("## Statistiques descriptives sur les notifications")
            st.write(stats)

            st.markdown("### Nombre de notifications par pays et type de danger")
            st.dataframe(grouped)

            st.markdown("## Analyse de tendances")
            st.markdown("### Nombre de notifications par pays")
            fig_pays = px.bar(grouped, x="notifying_country", y="Nombre de notifications", title="Nombre de notifications par pays")
            st.plotly_chart(fig_pays, use_container_width=True)

            # Nouveau : Distribution des dangers
            if "hazard_category" in df.columns:
                st.markdown("### Distribution des catégories de dangers")
                fig_dangers = px.histogram(grouped, x="hazard_category", y="Nombre de notifications", title="Distribution des catégories de dangers")
                st.plotly_chart(fig_dangers, use_container_width=True)

            st.markdown("### Répartition des notifications par catégories de produits")
            fig_pie = px.pie(df, names='category', title="Répartition des notifications par catégories de produits")
            st.plotly_chart(fig_pie, use_container_width=True)

            # Intégration du modèle Groq avec PandasAI pour l'interaction utilisateur
            st.markdown("## Posez des questions à propos des données")
            question = st.text_input("Posez une question en langage naturel sur les données :")

            if st.button("Analyser"):
                if question.strip():
                    try:
                        # Utilisation de Groq avec PandasAI
                        response = pandas_ai.run(df, prompt=question)
                        st.write(response)
                    except Exception as e:
                        st.error(f"Erreur lors de l'analyse : {e}")
                else:
                    st.warning("Veuillez poser une question valide.")
        else:
            st.error("Aucune donnée disponible pour les semaines sélectionnées.")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))

if page == "Accueil":
    page_accueil()
elif page == "Analyse":
    page_analyse()

