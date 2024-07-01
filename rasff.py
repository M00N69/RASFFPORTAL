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
    # ... (Rest of the function remains the same) 

def page_accueil():
    # ... (Rest of the function remains the same) 

def page_analyse():
    """Affiche la page d'analyse."""
    st.title("Analyse des Données RASFF")

    # Téléchargement du fichier CSV ou Excel
    uploaded_file = st.file_uploader("Téléchargez un fichier CSV ou Excel RASFF", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            # Détecter le type de fichier
            if uploaded_file.name.endswith(".csv"):
                # Détecter l'encodage du fichier CSV
                encodage = chardet.detect(uploaded_file.read())['encoding']
                uploaded_file.seek(0)  # Rembobiner le fichier

                df = pd.read_csv(uploaded_file, encoding=encodage, quotechar='"')
            elif uploaded_file.name.endswith(".xlsx"):
                # Read the Excel file using openpyxl
                wb = openpyxl.load_workbook(uploaded_file)
                sheet = wb.active

                # Convert "reference" to string before creating DataFrame
                data = [[str(cell.value) for cell in row] for row in sheet.iter_rows()]
                df = pd.DataFrame(data, columns=sheet.row_values(1))

                # Handle "date" column (assuming it's formatted as text in Excel)
                df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S")  

            else:
                st.error("Type de fichier non pris en charge.")
                return

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
            # Now, the column "notifying_country" should be available 
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
