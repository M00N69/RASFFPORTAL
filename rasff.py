import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import datetime
from Levenshtein import distance
from pandasai import SmartDataframe
from pandasai.connectors import PandasConnector
from pandasai.llm import GoogleGemini
from pandasai.responses.response_parser import ResponseParser

# Import lists from separate files (replace these with actual data)
from product_categories import product_categories
from hazards import hazards
from hazard_categories import hazard_categories
from notifying_countries import notifying_countries
from origin_countries import origin_countries

# Initialisation de Google Gemini avec l'API Key
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# Custom Response Parser to handle output
class OutputParser(ResponseParser):
    def __init__(self, context) -> None:
        super().__init__(context)
    
    def parse(self, result):
        if result['type'] == "dataframe":
            st.dataframe(result['value'])
        elif result['type'] == 'plot':
            st.image(result["value"])
        else:
            st.write(result['value'])
        return

# Fonction de nettoyage des données
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
    return "Autre"

def nettoyer_donnees(df):
    """Cleans and standardizes the data."""
    df["notifying_country"] = df["notifying_country"].apply(lambda x: x if x in notifying_countries else x)
    df["origin"] = df["origin"].apply(lambda x: x if x in origin_countries else x)
    df["category"] = df["category"].apply(lambda x: product_categories.get(x, x))

    if "hazards" in df.columns:
        df["hazards"] = df["hazards"].apply(corriger_dangers)
        df["hazard_category"] = df["hazards"].apply(mapper_danger_a_categorie)

    try:
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M:%S")
    except ValueError:
        st.warning("Impossible de convertir la colonne 'date' en date.")
    df = df.fillna("")
    return df

# Fonction pour télécharger les données
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

# Fonction pour récupérer la dernière semaine disponible
def obtenir_derniere_semaine_disponible():
    """Détermine la dernière semaine disponible."""
    maintenant = datetime.datetime.now()
    # Obtenir la semaine actuelle
    annee_actuelle, semaine_actuelle, _ = maintenant.isocalendar()
    
    # Si c'est le début de la semaine (ex. Lundi ou Mardi), on vérifie la semaine précédente
    if maintenant.weekday() < 3:  # Si c'est lundi ou mardi
        semaine_actuelle -= 1
    
    # Vérifier si la semaine actuelle ou précédente a des données disponibles
    for semaine in range(semaine_actuelle, 0, -1):  # Commencer par la semaine actuelle et revenir en arrière
        url = f"https://www.sirene-diffusion.fr/regia/000-rasff/{str(annee_actuelle)[2:]}/rasff-{annee_actuelle}-{str(semaine).zfill(2)}.xls"
        response = requests.head(url)
        if response.status_code == 200:
            return annee_actuelle, semaine  # On retourne la première semaine avec des données disponibles
    
    # Si aucune donnée pour l'année en cours, revenir à l'année précédente
    annee_prec = annee_actuelle - 1
    for semaine in range(52, 0, -1):  # Parcourir les semaines de l'année précédente
        url = f"https://www.sirene-diffusion.fr/regia/000-rasff/{str(annee_prec)[2:]}/rasff-{annee_prec}-{str(semaine).zfill(2)}.xls"
        response = requests.head(url)
        if response.status_code == 200:
            return annee_prec, semaine  # On retourne la première semaine avec des données de l'année précédente
    
    return annee_actuelle, semaine_actuelle  # Retour par défaut si aucune donnée n'est trouvée

# Fonction pour calculer des statistiques descriptives
def calculer_statistiques_descriptives(df):
    """Calculates descriptive statistics for the number of notifications per country and type of hazard."""
    grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='Nombre de notifications')
    stats = grouped['Nombre de notifications'].describe()
    return stats, grouped

# Fonction principale de l'application
def main():
    st.title("Analyseur de Données RASFF")

    # Obtenir la dernière semaine disponible
    annee, derniere_semaine = obtenir_derniere_semaine_disponible()
    
    st.write(f"Dernière semaine disponible : {derniere_semaine} de l'année {annee}")
    
    # Créer une liste d'options pour les semaines (de 1 jusqu'à la dernière semaine disponible)
    semaines_options = list(range(1, derniere_semaine + 1))

    # Vérifiez si la dernière semaine disponible est dans la liste des options
    if derniere_semaine not in semaines_options:
        st.warning(f"La dernière semaine ({derniere_semaine}) n'est pas dans la liste des options disponibles.")
        semaines = []  # Aucun par défaut si la semaine n'est pas disponible
    else:
        semaines = [derniere_semaine]  # Par défaut, sélectionner la dernière semaine disponible

    # Permettre à l'utilisateur de sélectionner plusieurs semaines ou de laisser vide pour la dernière semaine
    semaines = st.multiselect("Sélectionnez les semaines (ou laissez vide pour la dernière semaine)", 
                              semaines_options, 
                              default=semaines)

    if semaines:
        df = telecharger_et_nettoyer_donnees(annee, semaines)
        if not df.empty:
            # Créer des onglets
            tab1, tab2, tab3, tab4 = st.tabs(["Aperçu des données", "Statistiques descriptives", "Graphiques", "Analyse IA"])

            with tab1:
                st.markdown("## Données analysées")
                st.dataframe(df)

            with tab2:
                stats, grouped = calculer_statistiques_descriptives(df)
                st.markdown("## Statistiques descriptives sur les notifications")
                st.write(stats)
                st.markdown("### Nombre de notifications par pays et type de danger")
                st.dataframe(grouped)

            with tab3:
                # Graphique : Nombre de notifications par pays
                st.markdown("### Nombre de notifications par pays")
                fig_pays = px.bar(grouped, x="notifying_country", y="Nombre de notifications", title="Nombre de notifications par pays")
                st.plotly_chart(fig_pays, use_container_width=True)

                # Distribution des catégories de dangers
                if "hazard_category" in df.columns:
                    st.markdown("### Distribution des catégories de dangers")
                    fig_dangers = px.histogram(grouped, x="hazard_category", y="Nombre de notifications", title="Distribution des catégories de dangers")
                    st.plotly_chart(fig_dangers, use_container_width=True)

            with tab4:
                # Intégration avec Google Gemini pour l'interaction en langage naturel
                st.markdown("## Posez des questions à propos des données")
                prompt = st.text_input("Posez une question en langage naturel sur les données :")

                if st.button("Analyser"):
                    if prompt.strip():
                        try:
                            # Utilisation de Google Gemini via PandasAI pour analyser les données
                            llm = GoogleGemini(api_key=GOOGLE_API_KEY)
                            connector = PandasConnector({"original_df": df})
                            sdf = SmartDataframe(connector, {"enable_cache": False}, config={"llm": llm, "response_parser": OutputParser})
                            
                            response = sdf.chat(prompt)
                            st.write("Réponse :")
                            st.write(response)

                            # Afficher le code exécuté
                            st.markdown("### Code exécuté par PandasAI :")
                            st.code(sdf.last_code_executed)
                        except Exception as e:
                            st.error(f"Erreur lors de l'analyse : {e}")
                    else:
                        st.warning("Veuillez entrer une question valide.")
        else:
            st.error("Aucune donnée disponible pour les semaines sélectionnées.")

# Navigation
page = st.sidebar.radio("Navigation", ("Accueil", "Analyse"))

if page == "Accueil":
    st.title("Bienvenue dans l'Analyseur RASFF")
    st.write("Utilisez cette application pour analyser les données du système RASFF (Rapid Alert System for Food and Feed).")
elif page == "Analyse":
    main()

