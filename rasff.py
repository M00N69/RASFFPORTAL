import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import datetime
from Levenshtein import distance
from groq import Groq  # Import the Groq client
from pandasai import PandasAI
from pandasai.llm import GroqLLM

# Import lists from separate files (replace these with actual data or create dummy data if missing)
from product_categories import product_categories
from hazards import hazards
from hazard_categories import hazard_categories
from notifying_countries import notifying_countries
from origin_countries import origin_countries

# Function to configure the Groq client for PandasAI
def get_groq_client():
    """Initialise and return a Groq client using the API key from Streamlit secrets."""
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

# Initialize PandasAI with Groq as the LLM
groq_client = get_groq_client()
groq_llm = GroqLLM(groq_client)  # Use GroqLLM for PandasAI
pandas_ai = PandasAI(llm=groq_llm)

# Streamlit page configuration
st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# Functions for processing data
def corriger_dangers(nom_danger):
    """Corrects typos in the name of a hazard."""
    nom_danger = str(nom_danger)
    best_match = min(hazards, key=lambda x: distance(x, nom_danger))
    if distance(best_match, nom_danger) <= 3:
        return best_match
    else:
        return nom_danger

def mapper_danger_a_categorie(danger):
    """Maps a hazard to its corresponding hazard category."""
    for categorie, description in hazard_categories.items():
        if description.lower() in danger.lower():
            return categorie
    return "Autre"  # If no match is found

def nettoyer_donnees(df):
    """Cleans and standardizes the data."""
    df["notifying_country"] = df["notifying_country"].apply(lambda x: x if x in notifying_countries else x)
    df["origin"] = df["origin"].apply(lambda x: x if x in origin_countries else x)
    df["category"] = df["category"].apply(lambda x: product_categories.get(x, x))

    # Correct and map hazards to their categories
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
    """Downloads and combines data from multiple weeks."""
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
        return pd.DataFrame()  # Return an empty DataFrame if no files could be downloaded

def calculer_statistiques_descriptives(df):
    """Calculates descriptive statistics for the number of notifications per country and type of hazard."""
    grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='Nombre de notifications')
    stats = grouped['Nombre de notifications'].describe()
    return stats, grouped

# Main function for the app
def main():
    st.title("Analyseur de Données RASFF")

    # Form to input year and weeks
    annee = st.number_input("Entrez l'année", min_value=2000, max_value=datetime.datetime.now().year, value=datetime.datetime.now().year)
    semaines = st.multiselect("Sélectionnez les semaines", list(range(1, min(36, datetime.datetime.now().isocalendar()[1] + 1))), default=[35])

    if semaines:
        df = telecharger_et_nettoyer_donnees(annee, semaines)
        if not df.empty:
            st.dataframe(df.head())

            # New feature: Filter by hazard category
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

            # Distribution of hazard categories
            if "hazard_category" in df.columns:
                st.markdown("### Distribution des catégories de dangers")
                fig_dangers = px.histogram(grouped, x="hazard_category", y="Nombre de notifications", title="Distribution des catégories de dangers")
                st.plotly_chart(fig_dangers, use_container_width=True)

            # Integration with Groq LLM via PandasAI for natural language interaction
            st.markdown("## Posez des questions à propos des données")
            question = st.text_input("Posez une question en langage naturel sur les données :")

            if st.button("Analyser"):
                if question.strip():
                    try:
                        # Use PandasAI with Groq LLM to answer user queries about the RASFF data
                        response = pandas_ai.run(df, prompt=question)
                        st.write("Réponse :")
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
    st.title("Bienvenue dans l'Analyseur RASFF")
    st.write("Utilisez cette application pour analyser les données du système RASFF (Rapid Alert System for Food and Feed).")
elif page == "Analyse":
    main()
