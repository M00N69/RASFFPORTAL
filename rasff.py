import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import datetime
from Levenshtein import distance
from pandasai import PandasAI
from groq import Groq  # Importing Groq client for LLM

# Importing lists from external files
from product_categories import product_categories
from hazards import hazards
from hazard_categories import hazard_categories
from notifying_countries import notifying_countries
from origin_countries import origin_countries

# Function to configure the Groq client
def get_groq_client():
    """Initialize and return a Groq client with the API key."""
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

# Initialize PandasAI with Groq as LLM
groq_client = get_groq_client()
pandas_ai = PandasAI(groq_client)

# Configure Streamlit page
st.set_page_config(
    page_title="RASFF Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# Data cleaning functions
def corriger_dangers(nom_danger):
    """Corrects typos in a hazard name."""
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
    return "Other"  # If no match is found

def nettoyer_donnees(df):
    """Clean and standardize the DataFrame."""
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
        st.warning("Unable to convert the 'date' column to a date.")
    
    df = df.fillna("")
    return df

def telecharger_et_nettoyer_donnees(annee, semaines):
    """Download and combine data for multiple weeks."""
    dfs = []
    url_template = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    
    for semaine in semaines:
        url = url_template.format(str(annee)[2:], annee, str(semaine).zfill(2))
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_excel(BytesIO(response.content))
            dfs.append(df)
        else:
            st.error(f"Failed to download data for week {semaine}.")
    
    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df = nettoyer_donnees(df)
        return df
    else:
        return pd.DataFrame()

def calculer_statistiques_descriptives(df):
    """Calculate descriptive statistics for the number of notifications by country and hazard type."""
    grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='Number of Notifications')
    stats = grouped['Number of Notifications'].describe()
    return stats, grouped

def page_accueil():
    """Display the homepage."""
    st.title("RASFF Data Analyzer")
    st.markdown("## Welcome!")
    st.markdown(
        """
        This tool allows you to analyze data from the Rapid Alert System for Food and Feed (RASFF). 
        Explore trends, identify risks, and understand food safety issues.
        """
    )
    st.markdown("## Features")
    st.markdown(
        """
        * **Download and analyze data**
        * **Automatic data cleaning**
        * **Descriptive statistics and visualizations**
        * **Trend analysis**
        """
    )

def page_analyse():
    """Display the analysis page."""
    st.title("RASFF Data Analysis")

    # Form to input year and weeks
    annee = st.number_input("Enter the year", min_value=2000, max_value=datetime.datetime.now().year, value=datetime.datetime.now().year)
    semaines = st.multiselect("Select the weeks", list(range(1, min(36, datetime.datetime.now().isocalendar()[1] + 1))), default=[35])

    if semaines:
        df = telecharger_et_nettoyer_donnees(annee, semaines)
        if not df.empty:
            colonnes_a_afficher = ['notifying_country', 'category', 'hazard_category', 'date'] if 'hazard_category' in df.columns else ['notifying_country', 'category', 'date']
            df = df[colonnes_a_afficher]

            # New: Filter by hazard category
            categories_dangers_selectionnees = st.multiselect("Filter by hazard categories", df['hazard_category'].unique())
            if categories_dangers_selectionnees:
                df = df[df['hazard_category'].isin(categories_dangers_selectionnees)]

            stats, grouped = calculer_statistiques_descriptives(df)

            st.markdown("## Analyzed Data")
            st.dataframe(df)

            st.markdown("## Descriptive Statistics on Notifications")
            st.write(stats)

            st.markdown("### Number of Notifications by Country and Hazard Type")
            st.dataframe(grouped)

            st.markdown("## Trend Analysis")
            st.markdown("### Number of Notifications by Country")
            fig_pays = px.bar(grouped, x="notifying_country", y="Number of Notifications", title="Number of Notifications by Country")
            st.plotly_chart(fig_pays, use_container_width=True)

            # New: Distribution of hazards
            if "hazard_category" in df.columns:
                st.markdown("### Distribution of Hazard Categories")
                fig_dangers = px.histogram(grouped, x="hazard_category", y="Number of Notifications", title="Distribution of Hazard Categories")
                st.plotly_chart(fig_dangers, use_container_width=True)

            st.markdown("### Distribution of Notifications by Product Categories")
            fig_pie = px.pie(df, names='category', title="Distribution of Notifications by Product Categories")
            st.plotly_chart(fig_pie, use_container_width=True)

            # Integration of Groq with PandasAI for user interaction
            st.markdown("## Ask Questions About the Data")
            question = st.text_input("Ask a natural language question about the data:")

            if st.button("Analyze"):
                if question.strip():
                    try:
                        # Using Groq with PandasAI
                        response = pandas_ai.run(df, prompt=question)
                        st.write(response)
                    except Exception as e:
                        st.error(f"Error during analysis: {e}")
                else:
                    st.warning("Please ask a valid question.")
        else:
            st.error("No data available for the selected weeks.")

# Navigation
page = st.sidebar.radio("Navigation", ("Home", "Analysis"))

if page == "Home":
    page_accueil()
elif page == "Analysis":
    page_analyse()

