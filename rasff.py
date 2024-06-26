import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
import plotly.express as px
import chardet
from io import StringIO

st.set_page_config(
    page_title="Analyseur RASFF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

def nettoyer_donnees(df):
    # Normalisation des noms de pays
    def normaliser_pays(nom_pays):
        pays_standardises = {
            "France": "France",
            "United Kingdom": "Royaume-Uni",
            "Türkiye": "Turquie"
        }
        return pays_standardises.get(nom_pays, nom_pays)

    df["notifying_country"] = df["notifying_country"].apply(normaliser_pays)
    df["origin"] = df["origin"].apply(normaliser_pays)

    # Correction des noms de dangers
    def corriger_dangers(nom_danger):
        dangers_standardises = [
            "chlorpyrifos",
            "chlorpyrifos-ethyl",
            "Salmonella",
            "Salmonella spp.",
            "Salmonella Enteritidis"
        ]
        best_match = process.extractOne(nom_danger, dangers_standardises, scorer=fuzz.token_set_ratio)
        return best_match[0] if best_match[1] >= 80 else nom_danger

    df["hazards"] = df["hazards"].apply(corriger_dangers)

    # Conversion des colonnes date
    for colonne in ["reference", "date"]:
        try:
            df[colonne] = pd.to_datetime(df[colonne])
        except ValueError:
            st.warning(f"Impossible de convertir la colonne '{colonne}' en date.")

    # Gestion des valeurs manquantes
    df = df.fillna("")

    return df

def page_accueil():
    st.title("Analyseur de Données RASFF")
    st.markdown("## Bienvenue !")
    st.markdown(
        """
        Cet outil permet d'analyser les données du système RASFF. 
        Explorez les tendances, identifiez les risques et comprenez les problèmes de sécurité alimentaire.
        """
    )

def page_analyse():
    st.title("Analyse des Données RASFF")
    uploaded_file = st.file_uploader("Téléchargez un fichier CSV ou Excel RASFF", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            df = nettoyer_donnees(df)

            colonnes_a_afficher = st.multiselect("Sélectionnez les colonnes à afficher", df.columns)
            df = df[colonnes_a_afficher]

            # Affichage des données filtrées
            st.dataframe(df)
            # Statistiques descriptives
            st.write(df.describe())

            # Graphique à barres
            fig = px.bar(df, x='notifying_country', y='reference', title="Notifications par pays")
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))
if page == "Accueil":
    page_accueil()
elif page == "Analyse":
    page_analyse()
