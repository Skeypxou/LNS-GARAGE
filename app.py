import streamlit as st
import sqlite3
import pandas as pd

# -------------------
# Configuration
# -------------------

st.set_page_config(
    page_title="LNS GARAGE",
    page_icon="🚗",
    layout="wide"
)

# -------------------
# Logo
# -------------------

try:
    st.image("assets/logo.png", width=200)
except:
    st.title("LNS GARAGE")

st.title("Gestion de Tôlerie Automobile")

# -------------------
# Base de données
# -------------------

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# -------------------
# Création tables
# -------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS clients(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nom TEXT,
telephone TEXT,
adresse TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicules(
id INTEGER PRIMARY KEY AUTOINCREMENT,
client TEXT,
immatriculation TEXT,
marque TEXT,
modele TEXT,
couleur TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS devis(
id INTEGER PRIMARY KEY AUTOINCREMENT,
client TEXT,
vehicule TEXT,
montant REAL,
statut TEXT
)
""")

conn.commit()

# -------------------
# Menu
# -------------------

menu = st.sidebar.radio(
    "Navigation",
    [
        "Tableau de bord",
        "Clients",
        "Véhicules",
        "Devis"
    ]
)

# -------------------
# Dashboard
# -------------------

if menu == "Tableau de bord":

    nb_clients = cursor.execute(
        "SELECT COUNT(*) FROM clients"
    ).fetchone()[0]

    nb_vehicules = cursor.execute(
        "SELECT COUNT(*) FROM vehicules"
    ).fetchone()[0]

    nb_devis = cursor.execute(
        "SELECT COUNT(*) FROM devis"
    ).fetchone()[0]

    c1, c2, c3 = st.columns(3)

    c1.metric("Clients", nb_clients)
    c2.metric("Véhicules", nb_vehicules)
    c3.metric("Devis", nb_devis)

# -------------------
# Clients
# -------------------

elif menu == "Clients":

    st.header("Gestion des clients")

    nom = st.text_input("Nom")
    telephone = st.text_input("Téléphone")
    adresse = st.text_input("Adresse")

    if st.button("Ajouter client"):

        cursor.execute(
            """
            INSERT INTO clients(nom,telephone,adresse)
            VALUES(?,?,?)
            """,
            (nom, telephone, adresse)
        )

        conn.commit()
        st.success("Client ajouté")

    df = pd.read_sql_query(
        "SELECT * FROM clients",
        conn
    )

    st.dataframe(df)

# -------------------
# Véhicules
# -------------------

elif menu == "Véhicules":

    st.header("Gestion des véhicules")

    client = st.text_input("Client")

    immat = st.text_input("Immatriculation")
    marque = st.text_input("Marque")
    modele = st.text_input("Modèle")
    couleur = st.text_input("Couleur")

    if st.button("Ajouter véhicule"):

        cursor.execute(
            """
            INSERT INTO vehicules
            (client,immatriculation,marque,modele,couleur)
            VALUES(?,?,?,?,?)
            """,
            (
                client,
                immat,
                marque,
                modele,
                couleur
            )
        )

        conn.commit()

        st.success("Véhicule ajouté")

    df = pd.read_sql_query(
        "SELECT * FROM vehicules",
        conn
    )

    st.dataframe(df)

# -------------------
# Devis
# -------------------

elif menu == "Devis":

    st.header("Création devis")

    client = st.text_input("Client")

    vehicule = st.text_input("Véhicule")

    montant = st.number_input(
        "Montant",
        min_value=0.0
    )

    statut = st.selectbox(
        "Statut",
        [
            "En attente",
            "Accepté",
            "Refusé"
        ]
    )

    if st.button("Créer devis"):

        cursor.execute(
            """
            INSERT INTO devis
            (client,vehicule,montant,statut)
            VALUES(?,?,?,?)
            """,
            (
                client,
                vehicule,
                montant,
                statut
            )
        )

        conn.commit()

        st.success("Devis créé")

    df = pd.read_sql_query(
        "SELECT * FROM devis",
        conn
    )

    st.dataframe(df)
