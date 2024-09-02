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
    
    # Normaliser les noms de pays et d'origine
    def normaliser_pays(nom_pays):
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

    # Normaliser les catégories de produits
    def normaliser_categories_produits(categorie_produit):
        categories_produits_standardisees = {
            "alcoholic beverages": "Boissons alcoolisées",
            "animal by-products": "Sous-produits animaux",
            "bivalve molluscs and products thereof": "Mollusques bivalves et leurs produits",
            "cephalopods and products thereof": "Céphalopodes et leurs produits",
            "cereals and bakery products": "Céréales et produits de boulangerie",
            "cocoa and cocoa preparations, coffee and tea": "Cacao et préparations de cacao, café et thé",
            "compound feeds": "Aliments composés",
            "confectionery": "Confiserie",
            "crustaceans and products thereof": "Crustacés et leurs produits",
            "dietetic foods, food supplements and fortified foods": "Aliments diététiques, compléments alimentaires et aliments enrichis",
            "eggs and egg products": "Œufs et produits à base d'œufs",
            "fats and oils": "Graisses et huiles",
            "feed additives": "Additifs pour l'alimentation animale",
            "feed materials": "Matières premières pour aliments",
            "feed premixtures": "Prémélanges pour aliments",
            "fish and fish products": "Poissons et produits à base de poissons",
            "food additives and flavourings": "Additifs alimentaires et arômes",
            "food contact materials": "Matériaux en contact avec les aliments",
            "fruits and vegetables": "Fruits et légumes",
            "gastropods": "Gastéropodes",
            "herbs and spices": "Herbes et épices",
            "honey and royal jelly": "Miel et gelée royale",
            "ices and desserts": "Glaces et desserts",
            "live animals": "Animaux vivants",
            "meat and meat products (other than poultry)": "Viande et produits carnés (autres que volaille)",
            "milk and milk products": "Lait et produits laitiers",
            "natural mineral waters": "Eaux minérales naturelles",
            "non-alcoholic beverages": "Boissons non alcoolisées",
            "nuts, nut products and seeds": "Noix, produits à base de noix et graines",
            "other food product / mixed": "Autres produits alimentaires / mixtes",
            "pet food": "Aliments pour animaux de compagnie",
            "plant protection products": "Produits de protection des plantes",
            "poultry meat and poultry meat products": "Viande de volaille et produits à base de viande de volaille",
            "prepared dishes and snacks": "Plats préparés et snacks",
            "soups, broths, sauces and condiments": "Soupes, bouillons, sauces et condiments",
            "water for human consumption (other)": "Eau pour la consommation humaine (autres)",
            "wine": "Vin",
        }
        return categories_produits_standardisees.get(categorie_produit, categorie_produit)
    
    df["category"] = df["category"].apply(normaliser_categories_produits)

    # Normaliser les catégories de dangers
    def normaliser_categories_dangers(categorie_danger):
        categories_dangers_standardisees = {
            "GMO / novel food": "OGM / nouveau aliment",
            "TSEs": "EST",
            "adulteration / fraud": "Adultération / fraude",
            "allergens": "Allergènes",
            "biological contaminants": "Contaminants biologiques",
            "biotoxins (other)": "Biotoxines (autres)",
            "chemical contamination (other)": "Contamination chimique (autres)",
            "composition": "Composition",
            "environmental pollutants": "Polluants environnementaux",
            "feed additives": "Additifs pour l'alimentation animale",
            "food additives and flavourings": "Additifs alimentaires et arômes",
            "foreign bodies": "Corps étrangers",
            "genetically modified": "Génétiquement modifié",
            "heavy metals": "Métaux lourds",
            "industrial contaminants": "Contaminants industriels",
            "labelling absent/incomplete/incorrect": "Étiquetage absent/incomplet/incorrect",
            "migration": "Migration",
            "mycotoxins": "Mycotoxines",
            "natural toxins (other)": "Toxines naturelles (autres)",
            "non-pathogenic micro-organisms": "Micro-organismes non pathogènes",
            "not determined (other)": "Non déterminé (autres)",
            "novel food": "Nouveau aliment",
            "organoleptic aspects": "Aspects organoleptiques",
            "packaging defective / incorrect": "Emballage défectueux / incorrect",
            "parasitic infestation": "Infestation parasitaire",
            "pathogenic micro-organisms": "Micro-organismes pathogènes",
            "pesticide residues": "Résidus de pesticides",
            "poor or insufficient controls": "Contrôles insuffisants ou de mauvaise qualité",
            "radiation": "Radiation",
            "residues of veterinary medicinal": "Résidus de médicaments vétérinaires",
        }
        return categories_dangers_standardisees.get(categorie_danger, categorie_danger)
    
    df["hazards"] = df["hazards"].apply(normaliser_categories_dangers)

    # Appliquer la correction des dangers avec Levenshtein
    if "hazards" in df.columns:
        df["hazards"] = df.apply(lambda row: corriger_dangers(row['hazards']), axis=1)

    # Conversion des dates
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
            colonnes_a_afficher = ['notifying_country', 'category', 'hazards', 'date'] if 'hazards' in df.columns else ['notifying_country', 'category', 'date']
            df = df[colonnes_a_afficher]

            # Explication des données analysées
            st.markdown("## Données analysées")
            st.dataframe(df)
            st.markdown(
                """
                **Données analysées :**
                - `notifying_country` : Le pays ayant émis la notification.
                - `category` : Catégorie du produit ou matériel concerné par la notification.
                - `hazards` : (si disponible) Catégorie du danger rapporté dans la notification.
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
            fig_pays = px.bar(df, x="notifying_country", y=df.index, title="Nombre de notifications par pays", labels={'y': 'Nombre de notifications'})
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
