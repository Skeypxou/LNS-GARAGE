# ==========================================
# LNS GARAGE PRO - APPLICATION COMPLÈTE
# Fichier unique : app.py
# ==========================================

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="LNS GARAGE PRO",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS POUR DESIGN ERP MODERNE ---
st.markdown("""
<style>
    :root {
        --primary-color: #1E3A8A; /* Bleu professionnel */
        --bg-color: #F3F4F6;
    }
    /* Sidebar stylisée */
    [data-testid="stSidebar"] {
        background-color: var(--primary-color);
        color: white;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {
        color: white !important;
    }
    /* Boutons stylisés */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
    }
    /* Cartes statistiques (KPI) */
    .kpi-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTION BASE DE DONNÉES SQLITE ---
DB_PATH = "lns_garage_database.db"

def init_db():
    """Crée la base de données et toutes les tables si elles n'existent pas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table Utilisateurs (Module 20)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, pseudo TEXT UNIQUE, 
        mot_de_passe TEXT, role TEXT
    )""")

    # Table Clients (Module 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, prenom TEXT, 
        telephone TEXT, telephone2 TEXT, email TEXT, adresse TEXT, 
        ville TEXT, notes TEXT, date_creation DATE
    )""")

    # Table Véhicules (Module 3)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, 
        immatriculation TEXT, vin TEXT, marque TEXT, modele TEXT, 
        annee INTEGER, couleur TEXT, kilometrage INTEGER, carburant TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )""")

    # Table Réception (Module 4)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reception (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vehicule_id INTEGER, 
        date_entree DATE, kilometrage INTEGER, niveau_carburant TEXT, 
        observations TEXT, roue_secours BOOLEAN, cric BOOLEAN, 
        radio BOOLEAN, documents BOOLEAN, clees BOOLEAN, signature_client BLOB,
        FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
    )""")

    # Table Sinistres (Module 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sinistres (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vehicule_id INTEGER, 
        compagnie TEXT, numero_dossier TEXT, expert TEXT, date_expertise DATE, 
        montant_valide REAL, commentaires TEXT,
        FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
    )""")

    # Table Devis (Module 6)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devis (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vehicule_id INTEGER, 
        numero_devis TEXT, date_creation DATE, statut TEXT, 
        total_pieces REAL, total_mo REAL, tva REAL, total_ttc REAL,
        FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
    )""")

    # Table Ordres de Réparation (Module 7)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ordres_reparation (
        id INTEGER PRIMARY KEY AUTOINCREMENT, devis_id INTEGER, 
        numero_or TEXT, responsable TEXT, date_debut DATE, 
        date_fin DATE, statut TEXT,
        FOREIGN KEY(devis_id) REFERENCES devis(id)
    )""")

    # Table Suivi Atelier (Module 8)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suivi_atelier (
        id INTEGER PRIMARY KEY AUTOINCREMENT, or_id INTEGER, 
        etape_actuelle TEXT, progression INTEGER DEFAULT 0,
        FOREIGN KEY(or_id) REFERENCES ordres_reparation(id)
    )""")

    # Table Stock (Module 9)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT, type_article TEXT, 
        reference TEXT, designation TEXT, quantite INTEGER, 
        prix_achat REAL, prix_vente REAL, seuil_alerte INTEGER
    )""")

    # Table Fournisseurs (Module 11)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, telephone TEXT, 
        email TEXT, adresse TEXT
    )""")

    # Table Factures (Module 13)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT, devis_id INTEGER, 
        numero_facture TEXT, date_creation DATE, statut_paiement TEXT, 
        montant_paye REAL,
        FOREIGN KEY(devis_id) REFERENCES devis(id)
    )""")

    # Table Caisse (Module 14)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caisse (
        id INTEGER PRIMARY KEY AUTOINCREMENT, type_transaction TEXT, 
        montant REAL, date_transaction DATE, description TEXT, categorie TEXT
    )""")

    # Table Employés (Module 16)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, fonction TEXT, 
        telephone TEXT, salaire REAL
    )""")

    # Table Photos (Module 15)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vehicule_id INTEGER, 
        type_photo TEXT, chemin_fichier TEXT, date_upload DATE,
        FOREIGN KEY(vehicule_id) REFERENCES vehicules(id)
    )""")

    # Création d'un admin par défaut si la table est vide
    cursor.execute("SELECT * FROM utilisateurs WHERE role='Administrateur'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO utilisateurs (nom, pseudo, mot_de_passe, role) VALUES (?, ?, ?, ?)",
                       ('Admin LNS', 'admin', 'admin123', 'Administrateur'))

    conn.commit()
    conn.close()
def update_db_schema():
    """Vérifie et ajoute les colonnes manquantes pour les nouveaux modules."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Ajouter 'details_json' à la table devis (nécessaire pour le Module 6)
    cursor.execute("PRAGMA table_info(devis)")
    devis_columns = [col[1] for col in cursor.fetchall()]
    if 'details_json' not in devis_columns:
        cursor.execute("ALTER TABLE devis ADD COLUMN details_json TEXT")
        
    # 2. Ajouter 'vehicule_id' à la table ordres_reparation (nécessaire pour le Module 7)
    cursor.execute("PRAGMA table_info(ordres_reparation)")
    or_columns = [col[1] for col in cursor.fetchall()]
    if 'vehicule_id' not in or_columns:
        cursor.execute("ALTER TABLE ordres_reparation ADD COLUMN vehicule_id INTEGER")
        
    # 3. Créer la table accessoires si elle n'existe pas (CREATE IF NOT EXISTS est sûr)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accessoires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT,
            designation TEXT,
            prix_achat REAL,
            prix_vente REAL,
            quantite INTEGER,
            seuil_alerte INTEGER DEFAULT 10
        )
    """)
    
    # 4. Créer la table achats si elle n'existe pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id INTEGER,
            numero_bc TEXT,
            date_commande DATE,
            date_reception DATE,
            statut TEXT,
            designation TEXT,
            reference TEXT,
            quantite INTEGER,
            prix_unitaire REAL,
            montant_total REAL,
            notes TEXT,
            FOREIGN KEY(fournisseur_id) REFERENCES fournisseurs(id)
        )
    """)
        
    conn.commit()
    conn.close()
# Initialiser la DB au lancement
init_db()
update_db_schema()

def get_connection():
    return sqlite3.connect(DB_PATH)

# --- 4. MENU DE NAVIGATION ---
# Logo placeholder
try:
    st.sidebar.image("assets/logo.png", width=150)
except:
    st.sidebar.markdown("# 🚗 LNS GARAGE PRO")

st.sidebar.markdown("---")

menu_items = {
    "📊 Tableau de bord": "dashboard",
    "👤 Clients": "clients",
    "🚘 Véhicules": "vehicules",
    "📥 Réception Véhicule": "reception",
    "🛡️ Sinistres Assurance": "sinistres",
    "📝 Devis": "devis",
    "🔧 Ordres de Réparation": "ordres",
    "🏭 Suivi Atelier": "atelier",
    "📦 Stock": "stock",
    "🔩 Accessoires": "accessoires",
    "🏭 Fournisseurs": "fournisseurs",
    "🛒 Achats": "achats",
    "🧾 Facturation": "facturation",
    "💰 Caisse": "caisse",
    "📸 Galerie Photos": "photos",
    "👷 Employés": "employes",
    "📂 Documents": "documents",
    "📈 Statistiques": "statistiques",
    "📱 QR Code": "qrcode",
    "🔐 Multi-Utilisateurs": "users"
}

choice = st.sidebar.radio("Navigation", list(menu_items.keys()))
module_name = menu_items[choice]

# ==========================================
# DÉFINITION DES MODULES (FONCTIONS)
# ==========================================

# --- MODULE 1 : TABLEAU DE BORD ---
def show_dashboard():
    st.title("📊 Tableau de Bord - LNS GARAGE PRO")
    conn = get_connection()
    
    df_clients = pd.read_sql_query("SELECT COUNT(*) as count FROM clients", conn)
    df_vehicules = pd.read_sql_query("SELECT COUNT(*) as count FROM vehicules", conn)
    df_devis = pd.read_sql_query("SELECT COUNT(*) as count FROM devis WHERE statut='En attente'", conn)
    df_factures = pd.read_sql_query("SELECT COUNT(*) as count FROM factures WHERE statut_paiement='Impayée'", conn)
    
    nb_clients = df_clients['count'].values[0]
    nb_vehicules = df_vehicules['count'].values[0]
    nb_devis_attente = df_devis['count'].values[0]
    nb_factures_impayees = df_factures['count'].values[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"<div class='kpi-card'><h3>Clients</h3><h1>{nb_clients}</h1></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='kpi-card'><h3>Véhicules</h3><h1>{nb_vehicules}</h1></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='kpi-card'><h3>Devis en attente</h3><h1>{nb_devis_attente}</h1></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='kpi-card'><h3>Factures impayées</h3><h1>{nb_factures_impayees}</h1></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Analyse visuelle")
    
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        df_marques = pd.read_sql_query("SELECT marque, COUNT(*) as count FROM vehicules GROUP BY marque", conn)
        if not df_marques.empty:
            fig_marques = px.pie(df_marques, values='count', names='marque', title="Véhicules par Marque", hole=0.4)
            st.plotly_chart(fig_marques, use_container_width=True)
        else:
            st.info("Aucun véhicule enregistré pour afficher le graphique.")

    with col_graph2:
        df_caisse = pd.read_sql_query("SELECT categorie, SUM(montant) as total FROM caisse GROUP BY categorie", conn)
        if not df_caisse.empty:
            fig_caisse = px.bar(df_caisse, x='categorie', y='total', title="Flux Caisse par Catégorie", color='categorie')
            st.plotly_chart(fig_caisse, use_container_width=True)
        else:
            st.info("Aucune transaction en caisse pour afficher le graphique.")
            
    conn.close()

# --- MODULE 2 : CLIENTS ---
def show_clients():
    st.title("👤 Gestion des Clients")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Clients", "➕ Ajouter un Client", "🔍 Détails / Modifier"])
    
    with tab1:
        df = pd.read_sql_query("SELECT id, nom, prenom, telephone, email, ville FROM clients ORDER BY nom", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun client enregistré.")

    with tab2:
        with st.form("ajout_client"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom *")
                prenom = st.text_input("Prénom *")
                telephone = st.text_input("Téléphone *")
            with col2:
                telephone2 = st.text_input("Téléphone secondaire")
                email = st.text_input("Email")
                ville = st.text_input("Ville")
            
            adresse = st.text_area("Adresse")
            notes = st.text_area("Notes internes")
            
            submitted = st.form_submit_button("Enregistrer le client")
            if submitted:
                if nom and prenom and telephone:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO clients (nom, prenom, telephone, telephone2, email, adresse, ville, notes, date_creation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, DATE('now'))
                    """, (nom, prenom, telephone, telephone2, email, adresse, ville, notes))
                    conn.commit()
                    st.success(f"Client {nom} {prenom} ajouté avec succès !")
                else:
                    st.error("Les champs Nom, Prénom et Téléphone sont obligatoires.")

    with tab3:
        df_clients = pd.read_sql_query("SELECT id, nom, prenom FROM clients", conn)
        if not df_clients.empty:
            client_dict = df_clients.apply(lambda row: f"{row['nom']} {row['prenom']} (ID: {row['id']})", axis=1).tolist()
            client_choice = st.selectbox("Choisir un client", client_dict)
            client_id = int(client_choice.split("ID: ")[1].replace(")", ""))
            
            df_detail = pd.read_sql_query(f"SELECT * FROM clients WHERE id={client_id}", conn)
            client_data = df_detail.iloc[0]
            
            st.write(f"### Historique de {client_data['nom']} {client_data['prenom']}")
            df_vehicules_client = pd.read_sql_query(f"SELECT immatriculation, marque, modele FROM vehicules WHERE client_id={client_id}", conn)
            if not df_vehicules_client.empty:
                st.dataframe(df_vehicules_client, use_container_width=True)
            else:
                st.warning("Ce client n'a pas de véhicule enregistré.")
                
            with st.expander("Modifier ou Supprimer ce client"):
                with st.form("modif_client"):
                    m_nom = st.text_input("Nom", value=client_data['nom'])
                    m_prenom = st.text_input("Prénom", value=client_data['prenom'])
                    m_tel = st.text_input("Téléphone", value=client_data['telephone'])
                    
                    save = st.form_submit_button("Sauvegarder modifications")
                    if save:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE clients SET nom=?, prenom=?, telephone=? WHERE id=?",
                                       (m_nom, m_prenom, m_tel, client_id))
                        conn.commit()
                        st.success("Client modifié !")
                        st.rerun()
                
                if st.button("🗑️ Supprimer ce client"):
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM clients WHERE id={client_id}")
                    conn.commit()
                    st.warning("Client supprimé !")
                    st.rerun()
        else:
            st.info("Veuillez ajouter des clients d'abord.")
            
    conn.close()

# --- MODULE 3 : VÉHICULES ---
def show_vehicules():
    st.title("🚘 Gestion des Véhicules")
    conn = get_connection()
    
    tab1, tab2 = st.tabs(["📋 Liste des Véhicules", "➕ Ajouter un Véhicule"])
    
    with tab1:
        df = pd.read_sql_query("""
            SELECT v.immatriculation, v.marque, v.modele, v.annee, v.couleur, 
                   c.nom || ' ' || c.prenom as 'Propriétaire'
            FROM vehicules v 
            JOIN clients c ON v.client_id = c.id
            ORDER BY v.immatriculation
        """, conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun véhicule enregistré.")

    with tab2:
        df_clients = pd.read_sql_query("SELECT id, nom, prenom FROM clients", conn)
        if df_clients.empty:
            st.error("Vous devez ajouter un client avant d'ajouter un véhicule !")
        else:
            client_dict = df_clients.apply(lambda row: f"{row['nom']} {row['prenom']} (ID: {row['id']})", axis=1).tolist()
            client_choice = st.selectbox("Propriétaire du véhicule", client_dict)
            client_id = int(client_choice.split("ID: ")[1].replace(")", ""))
            
            with st.form("ajout_vehicule"):
                col1, col2 = st.columns(2)
                with col1:
                    immat = st.text_input("Immatriculation *")
                    vin = st.text_input("VIN (Numéro de châssis)")
                    marque = st.text_input("Marque *")
                    modele = st.text_input("Modèle *")
                with col2:
                    annee = st.number_input("Année", min_value=1900, max_value=2025, value=2020)
                    couleur = st.text_input("Couleur")
                    kilometrage = st.number_input("Kilométrage", min_value=0)
                    carburant = st.selectbox("Carburant", ["Diesel", "Essence", "Hybride", "Electrique", "GPL"])
                
                submitted = st.form_submit_button("Enregistrer le véhicule")
                if submitted:
                    if immat and marque and modele:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO vehicules (client_id, immatriculation, vin, marque, modele, annee, couleur, kilometrage, carburant)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (client_id, immat, vin, marque, modele, annee, couleur, kilometrage, carburant))
                        conn.commit()
                        st.success(f"Véhicule {immat} ajouté avec succès !")
                    else:
                        st.error("Immatriculation, Marque et Modèle sont obligatoires.")
                        
    conn.close()

# --- MODULES EN ATTENTE (Placeholders) ---
# Quand tu seras prêt, on remplira ces fonctions avec le code complet !
# --- MODULE 4 : RÉCEPTION VÉHICULE ---
def show_reception():
    st.title("📥 Réception Véhicule")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Réceptions", "➕ Nouvelle Réception", "🔍 Détails / Modifier"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        # On joint les tables pour afficher le véhicule et le client
        query = """
        SELECT r.id, v.immatriculation, v.marque, v.modele, 
               c.nom || ' ' || c.prenom as 'Client', 
               r.date_entree, r.observations
        FROM reception r
        JOIN vehicules v ON r.vehicule_id = v.id
        JOIN clients c ON v.client_id = c.id
        ORDER BY r.date_entree DESC
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune réception enregistrée pour le moment.")

    # --- TAB 2 : NOUVELLE RÉCEPTION ---
    with tab2:
        df_vehicules = pd.read_sql_query("""
            SELECT v.id, v.immatriculation, v.marque, v.modele, c.nom, c.prenom 
            FROM vehicules v JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if df_vehicules.empty:
            st.error("⚠️ Vous devez ajouter un client et un véhicule avant de faire une réception !")
        else:
            # Créer un menu déroulant pour choisir le véhicule
            veh_dict = df_vehicules.apply(lambda row: f"{row['immatriculation']} - {row['marque']} {row['modele']} ({row['nom']} {row['prenom']}) [ID:{row['id']}]", axis=1).tolist()
            veh_choice = st.selectbox("Véhicule reçu", veh_dict)
            veh_id = int(veh_choice.split("[ID:")[1].replace("]", ""))
            
            with st.form("new_reception"):
                st.subheader("🚗 Informations d'entrée")
                col1, col2 = st.columns(2)
                with col1:
                    date_entree = st.date_input("Date d'entrée *")
                    kilometrage = st.number_input("Kilométrage à l'entrée", min_value=0, step=1)
                with col2:
                    niveau_carburant = st.selectbox("Niveau carburant", ["Plein", "3/4", "1/2", "1/4", "Vide", "Inconnu"])
                    
                observations = st.text_area("Observations / Description du problème par le client")
                
                st.subheader("✅ Checklist Véhicule")
                col3, col4, col5 = st.columns(3)
                with col3:
                    roue_secours = st.checkbox("Roue de secours")
                    cric = st.checkbox("Cric")
                with col4:
                    radio = st.checkbox("Radio / Autoradio")
                    documents = st.checkbox("Documents (CG, Assurance)")
                with col5:
                    clees = st.checkbox("Clés (doublon)")
                    
                st.subheader("✍️ Signature Client")
                # Note: Pour une signature dessinée, il faudrait ajouter la librairie streamlit-drawable-canvas.
                # Ici on utilise un checkbox + texte pour rester 100% compatible avec tes consignes initiales.
                signature_check = st.checkbox("Le client confirme la remise du véhicule et la véracité de la checklist")
                signature_nom = st.text_input("Nom et Prénom du signataire (si checkbox coché)")
                
                submitted = st.form_submit_button("📥 Enregistrer la Réception")
                if submitted:
                    if date_entree and signature_check and signature_nom:
                        cursor = conn.cursor()
                        # Les checkboxes renvoient True/False, SQLite préfère 1/0, on convertit avec int()
                        cursor.execute("""
                            INSERT INTO reception (vehicule_id, date_entree, kilometrage, niveau_carburant, observations, 
                            roue_secours, cric, radio, documents, clees, signature_client)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (veh_id, str(date_entree), kilometrage, niveau_carburant, observations, 
                              int(roue_secours), int(cric), int(radio), int(documents), int(clees), signature_nom))
                        conn.commit()
                        st.success("✅ Fiche de réception enregistrée avec succès !")
                    else:
                        st.error("❌ La date, la confirmation de signature et le nom du signataire sont obligatoires.")

    # --- TAB 3 : DÉTAILS / MODIFIER ---
    with tab3:
        df_receptions = pd.read_sql_query("""
            SELECT r.id, v.immatriculation, v.marque, c.nom || ' ' || c.prenom as Client, r.date_entree
            FROM reception r
            JOIN vehicules v ON r.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if not df_receptions.empty:
            recep_dict = df_receptions.apply(lambda row: f"{row['date_entree']} - {row['immatriculation']} ({row['Client']}) [ID:{row['id']}]", axis=1).tolist()
            recep_choice = st.selectbox("Choisir une fiche de réception", recep_dict)
            recep_id = int(recep_choice.split("[ID:")[1].replace("]", ""))
            
            # Récupérer les détails
            df_detail = pd.read_sql_query(f"SELECT * FROM reception WHERE id={recep_id}", conn)
            detail = df_detail.iloc[0]
            
            # Afficher les détails proprement
            st.write(f"**Véhicule ID:** {detail['vehicule_id']} | **Date entrée:** {detail['date_entree']}")
            st.write(f"**Kilométrage:** {detail['kilometrage']} km | **Carburant:** {detail['niveau_carburant']}")
            st.write(f"**Observations:** {detail['observations']}")
            
            st.markdown("---")
            st.write("**Checklist :**")
            checklist_items = {"Roue de secours": detail['roue_secours'], "Cric": detail['cric'], 
                               "Radio": detail['radio'], "Documents": detail['documents'], "Clés": detail['clees']}
            for item, val in checklist_items.items():
                icon = "✅" if val else "❌"
                st.write(f"{icon} {item}")
                
            st.write(f"**Signataire :** {detail['signature_client']}")
            
            # Option Modifier / Supprimer
            with st.expander("🔧 Modifier ou Supprimer cette fiche"):
                with st.form("modif_reception"):
                    m_obs = st.text_area("Observations", value=detail['observations'])
                    m_km = st.number_input("Kilométrage", value=int(detail['kilometrage']))
                    
                    m_roue = st.checkbox("Roue de secours", value=bool(detail['roue_secours']))
                    m_cric = st.checkbox("Cric", value=bool(detail['cric']))
                    m_radio = st.checkbox("Radio", value=bool(detail['radio']))
                    m_docs = st.checkbox("Documents", value=bool(detail['documents']))
                    m_clees = st.checkbox("Clés", value=bool(detail['clees']))
                    
                    save = st.form_submit_button("Sauvegarder modifications")
                    if save:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE reception SET observations=?, kilometrage=?, roue_secours=?, cric=?, radio=?, documents=?, clees=?
                            WHERE id=?
                        """, (m_obs, m_km, int(m_roue), int(m_cric), int(m_radio), int(m_docs), int(m_clees), recep_id))
                        conn.commit()
                        st.success("Fiche modifiée !")
                        st.rerun()
                
                if st.button("🗑️ Supprimer cette fiche de réception", type="secondary"):
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM reception WHERE id={recep_id}")
                    conn.commit()
                    st.warning("Fiche supprimée !")
                    st.rerun()
        else:
            st.info("Aucune réception à modifier pour le moment.")
            
    conn.close()

def show_sinistres():
    st.title("🛡️ Sinistres Assurance")
    st.info("🚧 Ce module est prêt à être développé ! Demande-moi de coder le Module 5 : Sinistres.")

# --- FONCTION GÉNÉRATION PDF ---
def generate_devis_pdf(devis_info, client_info, vehicule_info, details):
    # S'assurer que le dossier pdf existe
    if not os.path.exists("pdf"):
        os.makedirs("pdf")
        
    pdf_path = f"pdf/Devis_{devis_info['numero_devis']}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    
    styles = getSampleStyleSheet()
    elements = []
    
    # En-tête
    elements.append(Paragraph("LNS GARAGE PRO - DEVIS", styles['Title']))
    elements.append(Spacer(1, 15))
    
    # Informations générales
    info_data = [
        [f"Client: {client_info['nom']} {client_info['prenom']}", f"Date: {devis_info['date_creation']}"],
        [f"Adresse: {client_info.get('adresse', 'N/A')}", f"N° Devis: {devis_info['numero_devis']}"],
        [f"Véhicule: {vehicule_info['marque']} {vehicule_info['modele']}", f"Immat: {vehicule_info['immatriculation']}"],
        [f"Carburant: {vehicule_info.get('carburant', 'N/A')}", f"Statut: {devis_info['statut']}"]
    ]
    info_table = Table(info_data, colWidths=[120*mm, 60*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tableau des travaux et pièces
    table_data = [["Type", "Description", "Quantité", "Prix Unitaire", "Total"]]
    
    # Ajout Main d'œuvre
    for item in details.get('mo', []):
        if item['qty'] > 0:
            table_data.append(["MO", item['desc'], f"{item['qty']} H", f"{item['price']:.2f} dzd", f"{item['total']:.2f} dzd"])
            
    # Ajout Pièces
    for item in details.get('pieces', []):
        if item['qty'] > 0:
            table_data.append(["Pièce", f"{item.get('ref', '')} - {item['desc']}", f"{item['qty']}", f"{item['price']:.2f} dzd", f"{item['total']:.2f} dzd"])
            
    items_table = Table(table_data, colWidths=[20*mm, 70*mm, 25*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # Totaux
    ht = devis_info['total_mo'] + devis_info['total_pieces']
    totals_data = [
        ["Total Main d'œuvre", f"{devis_info['total_mo']:.2f} dzd"],
        ["Total Pièces", f"{devis_info['total_pieces']:.2f} dzd"],
        ["Total Hors Taxe (HT)", f"{ht:.2f} dzd"],
        ["TVA (20%)", f"{devis_info['tva']:.2f} dzd"],
        ["Total TTC (À payer)", f"{devis_info['total_ttc']:.2f} dzd"]
    ]
    totals_table = Table(totals_data, colWidths=[120*mm, 50*mm])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    elements.append(totals_table)
    
    # Pied de page
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Signature du Garage:", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Signature du Client (Bon pour accord):", styles['Normal']))
    
    doc.build(elements)
    return pdf_path

# --- MODULE 6 : DEVIS ---
def show_devis():
    st.title("📝 Gestion des Devis")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Devis", "➕ Créer un Devis", "🔍 Voir / PDF / Modifier"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        query = """
        SELECT d.numero_devis, v.immatriculation, c.nom || ' ' || c.prenom as Client, 
               d.date_creation, d.statut, d.total_ttc
        FROM devis d
        JOIN vehicules v ON d.vehicule_id = v.id
        JOIN clients c ON v.client_id = c.id
        ORDER BY d.date_creation DESC
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun devis créé pour le moment.")

    # --- TAB 2 : CRÉATION ---
    with tab2:
        df_vehicules = pd.read_sql_query("""
            SELECT v.id, v.immatriculation, v.marque, v.modele, c.nom, c.prenom 
            FROM vehicules v JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if df_vehicules.empty:
            st.error("⚠️ Vous devez ajouter un client et un véhicule avant de créer un devis !")
        else:
            veh_dict = df_vehicules.apply(lambda row: f"{row['immatriculation']} - {row['marque']} {row['modele']} ({row['nom']} {row['prenom']}) [ID:{row['id']}]", axis=1).tolist()
            veh_choice = st.selectbox("Véhicule concerné", veh_dict)
            veh_id = int(veh_choice.split("[ID:")[1].replace("]", ""))
            
            with st.form("new_devis"):
                col_date, col_num, col_statut = st.columns(3)
                with col_date:
                    date_creation = st.date_input("Date du devis *")
                with col_num:
                    # Génération automatique du numéro
                    last_id = pd.read_sql_query("SELECT MAX(id) as max_id FROM devis", conn)['max_id'].values[0]
                    if last_id is None: last_id = 0
                    numero_devis = st.text_input("N° Devis", value=f"DEV-{last_id+1:04d}")
                with col_statut:
                    statut = st.selectbox("Statut", ["En attente", "Validé", "Refusé"])
                
                st.markdown("---")
                st.subheader("🔧 Main d'œuvre")
                mo_tasks = ["Débosselage", "Redressage", "Soudure", "Préparation", "Peinture", "Polissage"]
                mo_details_list = []
                
                for task in mo_tasks:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        h = st.number_input(f"{task} (Heures)", min_value=0.0, step=0.5, key=f"mo_h_{task}")
                    with col2:
                        p = st.number_input(f"Prix / H", min_value=0.0, value=45.0, format="%.2f", key=f"mo_p_{task}")
                    with col3:
                        st.write(f"Total: **{h * p:.2f} dzd**")
                    mo_details_list.append({"desc": task, "qty": h, "price": p, "total": h * p})
                
                st.markdown("---")
                st.subheader("🔩 Pièces et Fournitures")
                pieces_details_list = []
                
                # 5 lignes de pièces pré-définies pour simplifier l'interface
                for i in range(5):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        ref = st.text_input(f"Réf. Pièce {i+1}", key=f"p_ref_{i}")
                    with col2:
                        des = st.text_input(f"Désignation Pièce {i+1}", key=f"p_des_{i}")
                    with col3:
                        qty = st.number_input(f"Qté Pièce {i+1}", min_value=0, step=1, key=f"p_qty_{i}")
                    with col4:
                        px = st.number_input(f"Prix Pièce {i+1}", min_value=0.0, format="%.2f", key=f"p_px_{i}")
                    
                    if qty > 0 and des:
                        pieces_details_list.append({"ref": ref, "desc": des, "qty": qty, "price": px, "total": qty * px})
                
                submitted = st.form_submit_button("📊 Calculer et Sauvegarder le Devis")
                if submitted:
                    # Calculs
                    total_mo = sum(item['total'] for item in mo_details_list)
                    total_pieces = sum(item['total'] for item in pieces_details_list)
                    total_ht = total_mo + total_pieces
                    tva = total_ht * 0.20
                    total_ttc = total_ht + tva
                    
                    # Préparation du JSON pour les détails
                    details_json = json.dumps({"mo": mo_details_list, "pieces": pieces_details_list})
                    
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO devis (vehicule_id, numero_devis, date_creation, statut, total_pieces, total_mo, tva, total_ttc, details_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (veh_id, numero_devis, str(date_creation), statut, total_pieces, total_mo, tva, total_ttc, details_json))
                    conn.commit()
                    st.success(f"✅ Devis {numero_devis} sauvegardé ! Total TTC : {total_ttc:.2f} dzd")

    # --- TAB 3 : VOIR / PDF / MODIFIER ---
    with tab3:
        df_devis = pd.read_sql_query("""
            SELECT d.id, d.numero_devis, v.immatriculation, c.nom || ' ' || c.prenom as Client, d.statut, d.total_ttc
            FROM devis d
            JOIN vehicules v ON d.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if not df_devis.empty:
            devis_dict = df_devis.apply(lambda row: f"{row['numero_devis']} - {row['Client']} ({row['immatriculation']}) TTC: {row['total_ttc']}dzd [ID:{row['id']}]", axis=1).tolist()
            devis_choice = st.selectbox("Choisir un devis", devis_dict)
            devis_id = int(devis_choice.split("[ID:")[1].replace("]", ""))
            
            # Récupération des données
            df_devis_detail = pd.read_sql_query(f"SELECT * FROM devis WHERE id={devis_id}", conn)
            devis_info = df_devis_detail.iloc[0].to_dict()
            
            veh_info = pd.read_sql_query(f"SELECT * FROM vehicules WHERE id={devis_info['vehicule_id']}", conn).iloc[0].to_dict()
            client_info = pd.read_sql_query(f"SELECT * FROM clients WHERE id={veh_info['client_id']}", conn).iloc[0].to_dict()
            
            # Affichage des infos
            st.write(f"**Statut actuel :** {devis_info['statut']} | **Total TTC :** {devis_info['total_ttc']} dzd")
            
            # Bouton Génération PDF
            if st.button("📄 Générer / Télécharger le PDF"):
                details = json.loads(devis_info['details_json'])
                pdf_path = generate_devis_pdf(devis_info, client_info, veh_info, details)
                
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                st.download_button(
                    label="⬇️ Télécharger le Devis PDF",
                    data=pdf_bytes,
                    file_name=f"Devis_{devis_info['numero_devis']}.pdf",
                    mime="application/pdf"
                )
            
            # Modifier le statut
            with st.expander("🔄 Modifier le statut du devis"):
                new_statut = st.selectbox("Nouveau statut", ["En attente", "Validé", "Refusé", "Facturé"], index=["En attente", "Validé", "Refusé", "Facturé"].index(devis_info['statut']))
                if st.button("Sauvegarder le nouveau statut"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE devis SET statut=? WHERE id=?", (new_statut, devis_id))
                    conn.commit()
                    st.success("Statut mis à jour !")
                    st.rerun()

        else:
            st.info("Aucun devis à afficher pour le moment.")
            
    conn.close()

# --- MODULE 7 : ORDRES DE RÉPARATION ---
def show_ordres():
    st.title("🔧 Ordres de Réparation (OR)")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Ordres", "➕ Créer un Ordre", "🔍 Suivi / Modifier"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        # On joint les tables OR, Devis, Véhicules et Clients
        query = """
        SELECT o.numero_or, d.numero_devis, v.immatriculation, 
               c.nom || ' ' || c.prenom as 'Client', 
               o.responsable, o.statut, o.date_debut, o.date_fin
        FROM ordres_reparation o
        LEFT JOIN devis d ON o.devis_id = d.id
        JOIN vehicules v ON o.vehicule_id = v.id
        JOIN clients c ON v.client_id = c.id
        ORDER BY o.date_debut DESC
        """
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Ajouter des icônes visuelles pour les statuts
            def statut_icon(val):
                if val == "En attente": return "⏳ En attente"
                elif val == "En cours": return "🔄 En cours"
                elif val == "Suspendu": return "⏸️ Suspendu"
                elif val == "Terminé": return "✅ Terminé"
                else: return val
                
            df['statut'] = df['statut'].apply(statut_icon)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun ordre de réparation créé pour le moment.")

    # --- TAB 2 : CRÉATION ---
    with tab2:
        # Récupérer les véhicules
        df_vehicules = pd.read_sql_query("""
            SELECT v.id, v.immatriculation, v.marque, v.modele, c.nom, c.prenom 
            FROM vehicules v JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if df_vehicules.empty:
            st.error("⚠️ Vous devez ajouter un client et un véhicule avant de créer un OR !")
        else:
            # Récupérer les devis existants pour proposer la transformation Devis -> OR
            df_devis = pd.read_sql_query("SELECT id, numero_devis, vehicule_id, statut, total_ttc FROM devis", conn)
            
            with st.form("new_or"):
                st.subheader("Association Véhicule / Devis")
                
                # Sélection du véhicule
                veh_dict = df_vehicules.apply(lambda row: f"{row['immatriculation']} - {row['marque']} {row['modele']} ({row['nom']} {row['prenom']}) [VehID:{row['id']}]", axis=1).tolist()
                veh_choice = st.selectbox("Véhicule concerné", veh_dict)
                veh_id = int(veh_choice.split("[VehID:")[1].replace("]", ""))
                
                # Sélection du devis (Optionnel mais recommandé)
                # Filtrer les devis pour le véhicule sélectionné
                df_devis_filtered = df_devis[df_devis['vehicule_id'] == veh_id]
                
                devis_options = ["Aucun devis (Travaux internes)"]
                if not df_devis_filtered.empty:
                    devis_dict_filtered = df_devis_filtered.apply(lambda row: f"{row['numero_devis']} - {row['statut']} ({row['total_ttc']}dzd) [DevisID:{row['id']}]", axis=1).tolist()
                    devis_options.extend(devis_dict_filtered)
                
                devis_choice = st.selectbox("Associer à un Devis ?", devis_options)
                
                devis_id = None
                if devis_choice != "Aucun devis (Travaux internes)":
                    devis_id = int(devis_choice.split("[DevisID:")[1].replace("]", ""))
                
                st.markdown("---")
                st.subheader("Planification du Travail")
                
                # Génération automatique du numéro OR
                last_id_or = pd.read_sql_query("SELECT MAX(id) as max_id FROM ordres_reparation", conn)['max_id'].values[0]
                if last_id_or is None: last_id_or = 0
                default_numero_or = f"OR-{last_id_or+1:04d}"
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    numero_or = st.text_input("N° Ordre de Réparation *", value=default_numero_or)
                    responsable = st.text_input("Responsable / Chef d'atelier *")
                with col2:
                    date_debut = st.date_input("Date de début prévue *")
                with col3:
                    date_fin = st.date_input("Date de fin prévue *")
                    
                statut = st.selectbox("Statut initial", ["En attente", "En cours", "Suspendu", "Terminé"])
                
                submitted = st.form_submit_button("🛠️ Créer l'Ordre de Réparation")
                if submitted:
                    if numero_or and responsable and date_debut and date_fin:
                        # Vérifier que date_fin >= date_debut
                        if str(date_fin) < str(date_debut):
                            st.error("❌ La date de fin prévue doit être après la date de début !")
                        else:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO ordres_reparation (devis_id, vehicule_id, numero_or, responsable, date_debut, date_fin, statut)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (devis_id, veh_id, numero_or, responsable, str(date_debut), str(date_fin), statut))
                            conn.commit()
                            st.success(f"✅ Ordre de Réparation {numero_or} créé avec succès !")
                    else:
                        st.error("❌ Le numéro, le responsable et les dates sont obligatoires.")

    # --- TAB 3 : SUIVI / MODIFIER ---
    with tab3:
        df_ordres = pd.read_sql_query("""
            SELECT o.id, o.numero_or, v.immatriculation, c.nom || ' ' || c.prenom as Client, o.statut
            FROM ordres_reparation o
            JOIN vehicules v ON o.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if not df_ordres.empty:
            or_dict = df_ordres.apply(lambda row: f"{row['numero_or']} - {row['Client']} ({row['immatriculation']}) Statut: {row['statut']} [ORID:{row['id']}]", axis=1).tolist()
            or_choice = st.selectbox("Choisir un Ordre de Réparation", or_dict)
            or_id = int(or_choice.split("[ORID:")[1].replace("]", ""))
            
            # Récupérer les détails
            df_detail = pd.read_sql_query(f"SELECT * FROM ordres_reparation WHERE id={or_id}", conn)
            detail = df_detail.iloc[0]
            
            # Affichage visuel du statut
            statut_color = {
                "En attente": "🟡", "En cours": "🔵", "Suspendu": "🔴", "Terminé": "🟢"
            }
            current_color = statut_color.get(detail['statut'], "⚪")
            
            st.write(f"### {current_color} Ordre N° {detail['numero_or']}")
            st.write(f"**Responsable :** {detail['responsable']} | **Période :** {detail['date_debut']} au {detail['date_fin']}")
            
            # Formulaire de mise à jour rapide (Statut et Dates)
            with st.form("update_or"):
                st.subheader("Mise à jour du Suivi")
                new_statut = st.selectbox("Statut des travaux", 
                                          ["En attente", "En cours", "Suspendu", "Terminé"], 
                                          index=["En attente", "En cours", "Suspendu", "Terminé"].index(detail['statut']))
                
                col1, col2 = st.columns(2)
                with col1:
                    new_debut = st.date_input("Nouvelle date de début", value=pd.to_datetime(detail['date_debut']))
                with col2:
                    new_fin = st.date_input("Nouvelle date de fin prévue", value=pd.to_datetime(detail['date_fin']))
                
                new_resp = st.text_input("Responsable", value=detail['responsable'])
                
                save = st.form_submit_button("Sauvegarder les modifications")
                if save:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE ordres_reparation SET statut=?, date_debut=?, date_fin=?, responsable=? WHERE id=?
                    """, (new_statut, str(new_debut), str(new_fin), new_resp, or_id))
                    conn.commit()
                    st.success("Ordre de réparation mis à jour !")
                    st.rerun()
                    
            # Bouton Supprimer
            st.markdown("---")
            if st.button("🗑️ Supprimer cet Ordre de Réparation"):
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM ordres_reparation WHERE id={or_id}")
                conn.commit()
                st.warning("Ordre supprimé !")
                st.rerun()
                
        else:
            st.info("Aucun ordre de réparation à suivre pour le moment.")
            
    conn.close()

# --- MODULE 8 : SUIVI ATELIER ---
def show_atelier():
    st.title("🏭 Suivi Atelier - Progression des Travaux")
    conn = get_connection()
    
    # Définition des étapes obligatoires du workflow garage
    etapes_atelier = [
        "Réception", 
        "Diagnostic", 
        "Tôlerie", 
        "Préparation", 
        "Peinture", 
        "Remontage", 
        "Contrôle Qualité", 
        "Livraison"
    ]
    
    tab1, tab2 = st.tabs(["🚜 Tableau de l'Atelier", "📊 Progression Détaillée"])
    
    # --- TAB 1 : TABLEAU DE L'ATELIER ---
    with tab1:
        # Afficher les véhicules actuellement dans l'atelier (OR non terminés)
        query = """
        SELECT o.numero_or, v.immatriculation, v.marque, v.modele, 
               c.nom || ' ' || c.prenom as 'Client', 
               o.statut, o.responsable
        FROM ordres_reparation o
        JOIN vehicules v ON o.vehicule_id = v.id
        JOIN clients c ON v.client_id = c.id
        WHERE o.statut != 'Terminé'
        ORDER BY o.date_debut ASC
        """
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("🎉 Aucun véhicule en cours de réparation dans l'atelier !")
    
    # --- TAB 2 : PROGRESSION DÉTAILLÉE ---
    with tab2:
        # Récupérer les OR actifs
        df_or_actifs = pd.read_sql_query("""
            SELECT o.id, o.numero_or, v.immatriculation, v.marque, c.nom || ' ' || c.prenom as Client
            FROM ordres_reparation o
            JOIN vehicules v ON o.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
            WHERE o.statut != 'Terminé'
        """, conn)
        
        if df_or_actifs.empty:
            st.info("Aucun véhicule à suivre pour le moment.")
        else:
            # Menu pour choisir le véhicule
            or_dict = df_or_actifs.apply(lambda row: f"{row['numero_or']} - {row['immatriculation']} ({row['Client']}) [ORID:{row['id']}]", axis=1).tolist()
            or_choice = st.selectbox("Choisir un Ordre de Réparation à suivre", or_dict)
            or_id = int(or_choice.split("[ORID:")[1].replace("]", ""))
            
            # Récupérer ou créer les infos de suivi pour cet OR
            df_suivi = pd.read_sql_query(f"SELECT * FROM suivi_atelier WHERE or_id={or_id}", conn)
            
            # Si le véhicule n'a pas encore de suivi, on le crée à l'étape "Réception"
            if df_suivi.empty:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO suivi_atelier (or_id, etape_actuelle, progression)
                    VALUES (?, ?, ?)
                """, (or_id, etapes_atelier[0], 12))
                conn.commit()
                # Recharger les données
                df_suivi = pd.read_sql_query(f"SELECT * FROM suivi_atelier WHERE or_id={or_id}", conn)
            
            suivi_data = df_suivi.iloc[0]
            current_etape = suivi_data['etape_actuelle']
            current_progress = int(suivi_data['progression'])
            current_etape_index = etapes_atelier.index(current_etape) if current_etape in etapes_atelier else 0
            
            # Affichage visuel des étapes (Les colonnes avec les icônes)
            st.markdown("---")
            cols = st.columns(len(etapes_atelier))
            
            for i, etape in enumerate(etapes_atelier):
                with cols[i]:
                    if i < current_etape_index:
                        # Etape terminée
                        st.markdown(f"<div style='text-align: center; background-color: #d4edda; padding: 10px; border-radius: 5px; color: black;'><b>✅</b><br>{etape}</div>", unsafe_allow_html=True)
                    elif i == current_etape_index:
                        # Etape en cours
                        st.markdown(f"<div style='text-align: center; background-color: #cce5ff; padding: 10px; border-radius: 5px; color: black; border: 2px solid #1E3A8A;'><b>🔧</b><br><b>{etape}</b></div>", unsafe_allow_html=True)
                    else:
                        # Etape à venir
                        st.markdown(f"<div style='text-align: center; background-color: #f8f9fa; padding: 10px; border-radius: 5px; color: grey;'><b>⬜</b><br>{etape}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Barre de progression globale
            st.progress(current_progress / 100, text=f"Progression globale : {current_progress}%")
            
            # Formulaire pour avancer le véhicule
            st.subheader("🚀 Avancer le véhicule dans l'atelier")
            
            with st.form("update_etape"):
                # Calcul de l'étape suivante
                next_etape_index = current_etape_index + 1 if current_etape_index < len(etapes_atelier) - 1 else current_etape_index
                
                new_etape = st.selectbox(
                    "Définir l'étape actuelle :", 
                    etapes_atelier, 
                    index=current_etape_index
                )
                
                submitted = st.form_submit_button("Mettre à jour la progression")
                if submitted:
                    new_etape_index = etapes_atelier.index(new_etape)
                    # Calcul du pourcentage : 8 étapes = 12.5% par étape (on arrondit)
                    new_progress = int((new_etape_index + 1) * (100 / len(etapes_atelier)))
                    
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE suivi_atelier SET etape_actuelle=?, progression=? WHERE or_id=?
                    """, (new_etape, new_progress, or_id))
                    conn.commit()
                    
                    # Si on passe à "Livraison", on termine automatiquement l'Ordre de Réparation
                    if new_etape == "Livraison":
                        cursor.execute("UPDATE ordres_reparation SET statut='Terminé' WHERE id=?", (or_id,))
                        conn.commit()
                        st.balloons() # Petit effet visuel de réussite !
                        st.success("🎉 Véhicule livré ! L'Ordre de Réparation est maintenant marqué comme TERMINÉ.")
                    else:
                        st.success(f"✅ Progression mise à jour : Étape **{new_etape}** ({new_progress}%)")
                    
                    st.rerun() # Rafraîchir la page pour voir les couleurs changer immédiatement

    conn.close()

# --- MODULE 9 : STOCK ---
def show_stock():
    st.title("📦 Gestion du Stock")
    conn = get_connection()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Inventaire", "➕ Entrée Stock", "➖ Sortie Stock", "⚠️ Alertes & Statistiques"])
    
    # --- TAB 1 : INVENTAIRE ---
    with tab1:
        # Filtre par type d'article
        filtre_type = st.selectbox("Filtrer par catégorie", ["Tous", "Consommable", "Pièce"], key="filtre_stock")
        
        if filtre_type == "Tous":
            query = "SELECT id, type_article, reference, designation, quantite, prix_achat, prix_vente, seuil_alerte FROM stock ORDER BY designation"
        else:
            query = f"SELECT id, type_article, reference, designation, quantite, prix_achat, prix_vente, seuil_alerte FROM stock WHERE type_article='{filtre_type}' ORDER BY designation"
            
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Ajouter une colonne visuelle pour le statut du stock
            def check_stock(row):
                if row['quantite'] <= row['seuil_alerte']:
                    return "🔴 Stock Faible"
                elif row['quantite'] == 0:
                    return "⚫ Rupture"
                else:
                    return "🟢 OK"
            
            df['Statut'] = df.apply(check_stock, axis=1)
            
            # Réorganiser les colonnes pour l'affichage
            df_display = df[['Statut', 'type_article', 'reference', 'designation', 'quantite', 'prix_achat', 'prix_vente']]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun article en stock pour le moment.")

    # --- TAB 2 : ENTRÉE STOCK ---
    with tab2:
        action = st.radio("Choisir l'action", ["Ajouter un nouvel article", "Réapprovisionner un article existant"])
        
        if action == "Ajouter un nouvel article":
            with st.form("add_article"):
                st.subheader("🆕 Nouvel Article")
                col1, col2 = st.columns(2)
                with col1:
                    type_article = st.selectbox("Type d'article *", ["Consommable", "Pièce"])
                    reference = st.text_input("Référence (ex: PCH-AV01)")
                    designation = st.text_input("Désignation / Nom * (ex: Pare-chocs avant)")
                with col2:
                    quantite = st.number_input("Quantité initiale *", min_value=0, step=1)
                    prix_achat = st.number_input("Prix d'achat unitaire (dzd)", min_value=0.0, format="%.2f")
                    prix_vente = st.number_input("Prix de vente unitaire (dzd)", min_value=0.0, format="%.2f")
                    seuil_alerte = st.number_input("Seuil d'alerte (quantité min) *", min_value=0, step=1, value=5)
                
                submitted = st.form_submit_button("Ajouter au catalogue")
                if submitted:
                    if designation and quantite >= 0:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO stock (type_article, reference, designation, quantite, prix_achat, prix_vente, seuil_alerte)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (type_article, reference, designation, quantite, prix_achat, prix_vente, seuil_alerte))
                        conn.commit()
                        st.success(f"✅ Article '{designation}' ajouté avec {quantite} unités !")
                    else:
                        st.error("❌ La désignation et la quantité sont obligatoires.")

        elif action == "Réapprovisionner un article existant":
            df_existing = pd.read_sql_query("SELECT id, designation, quantite FROM stock", conn)
            if df_existing.empty:
                st.warning("Le catalogue est vide. Ajoutez d'abord un nouvel article.")
            else:
                art_dict = df_existing.apply(lambda row: f"{row['designation']} (Stock actuel: {row['quantite']}) [ID:{row['id']}]", axis=1).tolist()
                art_choice = st.selectbox("Article à réapprovisionner", art_dict)
                art_id = int(art_choice.split("[ID:")[1].replace("]", ""))
                
                qty_add = st.number_input("Quantité ajoutée", min_value=1, step=1)
                new_buy_price = st.number_input("Nouveau prix d'achat (si changé)", min_value=0.0, format="%.2f")
                
                if st.button("📥 Réapprovisionner"):
                    cursor = conn.cursor()
                    # On met à jour la quantité et le prix d'achat (le prix peut fluctuer)
                    cursor.execute("""
                        UPDATE stock SET quantite = quantite + ?, prix_achat = ? WHERE id = ?
                    """, (qty_add, new_buy_price, art_id))
                    conn.commit()
                    st.success(f"✅ Stock mis à jour ! {qty_add} unités ajoutées.")

    # --- TAB 3 : SORTIE STOCK ---
    with tab3:
        df_existing = pd.read_sql_query("SELECT id, designation, quantite FROM stock WHERE quantite > 0", conn)
        if df_existing.empty:
            st.warning("Aucun article disponible en stock pour une sortie.")
        else:
            art_dict = df_existing.apply(lambda row: f"{row['designation']} (Dispo: {row['quantite']}) [ID:{row['id']}]", axis=1).tolist()
            art_choice = st.selectbox("Article à consommer / sortir", art_dict)
            art_id = int(art_choice.split("[ID:")[1].replace("]", ""))
            
            qty_remove = st.number_input("Quantité sortie", min_value=1, step=1)
            
            if st.button("📤 Sortir du stock"):
                # Vérifier qu'on ne sort pas plus que ce qu'on a
                current_qty = df_existing[df_existing['id'] == art_id]['quantite'].values[0]
                if qty_remove > current_qty:
                    st.error(f"❌ Impossible ! Vous essayez de sortir {qty_remove} unités, mais il n'y en a que {current_qty} en stock.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE stock SET quantite = quantite - ? WHERE id = ?
                    """, (qty_remove, art_id))
                    conn.commit()
                    st.success(f"✅ {qty_remove} unité(s) sorties du stock !")
                    if (current_qty - qty_remove) <= 5: # Valeur d'alerte générique
                        st.warning("⚠️ Attention, le stock de cet article est maintenant bas !")

    # --- TAB 4 : ALERTES & STATS ---
    with tab4:
        st.subheader("⚠️ Articles en Stock Faible ou en Rupture")
        df_alertes = pd.read_sql_query("SELECT designation, quantite, seuil_alerte FROM stock WHERE quantite <= seuil_alerte", conn)
        if not df_alertes.empty:
            st.dataframe(df_alertes, use_container_width=True, hide_index=True)
        else:
            st.info("🎉 Aucune alerte de stock faible ! Tout est bien approvisionné.")
            
        st.markdown("---")
        st.subheader("📊 Valeur du Stock par Catégorie")
        
        df_stats = pd.read_sql_query("""
            SELECT type_article, SUM(quantite * prix_achat) as Valeur_Total_Achat, SUM(quantite) as Total_Unites
            FROM stock
            GROUP BY type_article
        """, conn)
        
        if not df_stats.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig_px = px.pie(df_stats, values='Valeur_Total_Achat', names='type_article', 
                               title="Répartition de la Valeur d'Achat du Stock (dzd)", hole=0.4)
                st.plotly_chart(fig_px, use_container_width=True)
            with col2:
                fig_bar = px.bar(df_stats, x='type_article', y='Total_Unites', 
                                 title="Nombre d'Unités par Catégorie", color='type_article')
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Aucune donnée statistique disponible pour le moment.")

    conn.close()

# --- MODULE 10 : ACCESSOIRES ---
def show_accessoires():
    st.title("🔩 Catalogue & Gestion des Accessoires")
    conn = get_connection()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Catalogue & Marge", "➕ Ajouter un Accessoire", "🔄 Entrée / Sortie", "📊 Statistiques"])
    
    # --- TAB 1 : CATALOGUE ---
    with tab1:
        search_term = st.text_input("🔍 Rechercher un accessoire (nom ou référence)")
        
        if search_term:
            query = f"SELECT * FROM accessoires WHERE designation LIKE '%{search_term}%' OR reference LIKE '%{search_term}%' ORDER BY designation"
        else:
            query = "SELECT * FROM accessoires ORDER BY designation"
            
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Calcul automatique de la Marge
            df['Marge_dzd'] = df['prix_vente'] - df['prix_achat']
            df['Marge_%'] = ((df['prix_vente'] - df['prix_achat']) / df['prix_achat']) * 100
            df['Marge_%'] = df['Marge_%'].round(1)
            
            # Alerte visuelle stock
            def check_stock_accessoire(row):
                if row['quantite'] == 0: return "⚫ Rupture"
                elif row['quantite'] <= row['seuil_alerte']: return "🔴 Bas"
                else: return "🟢 OK"
            df['Stock'] = df.apply(check_stock_accessoire, axis=1)
            
            # Affichage propre
            df_display = df[['Stock', 'reference', 'designation', 'quantite', 'prix_achat', 'prix_vente', 'Marge_dzd', 'Marge_%']]
            df_display.columns = ['Stock', 'Référence', 'Désignation', 'Qté', 'Prix Achat', 'Prix Vente', 'Marge (dzd)', 'Marge (%)']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Catalogue vide. Ajoutez vos accessoires courants (clips, rivets, joints...) !")

    # --- TAB 2 : AJOUTER ---
    with tab2:
        with st.form("add_accessoire"):
            st.subheader("🆕 Nouvel Accessoire au Catalogue")
            col1, col2 = st.columns(2)
            with col1:
                reference = st.text_input("Référence * (ex: CLP-UNIV)")
                designation = st.text_input("Désignation / Nom * (ex: Clip universel pare-chocs)")
                quantite = st.number_input("Quantité initiale *", min_value=0, step=1)
            with col2:
                prix_achat = st.number_input("Prix d'achat unitaire (dzd) *", min_value=0.0, format="%.2f")
                prix_vente = st.number_input("Prix de vente unitaire (dzd) *", min_value=0.0, format="%.2f")
                seuil_alerte = st.number_input("Seuil d'alerte stock", min_value=0, step=1, value=10)
                
            submitted = st.form_submit_button("Ajouter au Catalogue")
            if submitted:
                if designation and prix_achat > 0 and prix_vente > 0:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO accessoires (reference, designation, prix_achat, prix_vente, quantite, seuil_alerte)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (reference, designation, prix_achat, prix_vente, quantite, seuil_alerte))
                    conn.commit()
                    st.success(f"✅ Accessoire '{designation}' ajouté au catalogue !")
                else:
                    st.error("❌ La désignation et les prix sont obligatoires.")

    # --- TAB 3 : ENTRÉE / SORTIE ---
    with tab3:
        df_existing = pd.read_sql_query("SELECT id, reference, designation, quantite FROM accessoires", conn)
        if df_existing.empty:
            st.warning("Aucun accessoire dans le catalogue pour effectuer un mouvement.")
        else:
            st.subheader("Mouvement de stock rapide")
            art_dict = df_existing.apply(lambda row: f"{row['reference']} - {row['designation']} (Stock: {row['quantite']}) [ID:{row['id']}]", axis=1).tolist()
            art_choice = st.selectbox("Choisir l'accessoire", art_dict)
            art_id = int(art_choice.split("[ID:")[1].replace("]", ""))
            
            col1, col2 = st.columns(2)
            with col1:
                qty_add = st.number_input("➕ Quantité ENTRÉE (Réappro)", min_value=0, step=1, key="acc_in")
                if st.button("📥 Valider Entrée", key="btn_acc_in"):
                    if qty_add > 0:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE accessoires SET quantite = quantite + ? WHERE id = ?", (qty_add, art_id))
                        conn.commit()
                        st.success(f"✅ {qty_add} unité(s) ajoutées au stock !")
                        st.rerun()
                    else:
                        st.warning("Entrez une quantité supérieure à 0.")
                        
            with col2:
                qty_remove = st.number_input("➖ Quantité SORTIE (Conso)", min_value=0, step=1, key="acc_out")
                if st.button("📤 Valider Sortie", key="btn_acc_out"):
                    current_qty = df_existing[df_existing['id'] == art_id]['quantite'].values[0]
                    if qty_remove > 0 and qty_remove <= current_qty:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE accessoires SET quantite = quantite - ? WHERE id = ?", (qty_remove, art_id))
                        conn.commit()
                        st.success(f"✅ {qty_remove} unité(s) sorties du stock !")
                        st.rerun()
                    elif qty_remove > current_qty:
                        st.error(f"❌ Stock insuffisant ! Il n'y a que {current_qty} unités.")
                    else:
                        st.warning("Entrez une quantité supérieure à 0.")

    # --- TAB 4 : STATISTIQUES ---
    with tab4:
        df_stats = pd.read_sql_query("SELECT designation, quantite, prix_achat, prix_vente FROM accessoires", conn)
        if not df_stats.empty:
            st.subheader("💰 Top Marge : Les accessoires qui te rapportent le plus")
            df_stats['Marge_dzd'] = df_stats['prix_vente'] - df_stats['prix_achat']
            df_stats = df_stats.sort_values(by='Marge_dzd', ascending=False)
            
            fig_marge = px.bar(df_stats.head(10), x='designation', y='Marge_dzd', 
                               title="Top 10 Accessoires par Marge Unitaire (dzd)",
                               color='Marge_dzd', color_continuous_scale='Greens')
            st.plotly_chart(fig_marge, use_container_width=True)
            
            st.subheader("⚠️ Accessoires à commander urgently (Stock Faible)")
            df_alertes = pd.read_sql_query(f"SELECT reference, designation, quantite, seuil_alerte FROM accessoires WHERE quantite <= seuil_alerte", conn)
            if not df_alertes.empty:
                st.dataframe(df_alertes, use_container_width=True, hide_index=True)
            else:
                st.info("🎉 Tous les accessoires sont suffisamment stockés !")
        else:
            st.info("Aucune donnée statistique disponible.")

    conn.close()

# --- MODULE 11 : FOURNISSEURS ---
def show_fournisseurs():
    st.title("🏭 Gestion des Fournisseurs")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Fournisseurs", "➕ Ajouter un Fournisseur", "🔍 Modifier / Supprimer"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        # Utilisation de f""" ... """ pour éviter les erreurs de syntaxe sur de longues requêtes
        query = f"""
            SELECT id, nom, telephone, email, adresse 
            FROM fournisseurs 
            ORDER BY nom
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            st.dataframe(df[['nom', 'telephone', 'email', 'adresse']], use_container_width=True, hide_index=True)
        else:
            st.info("Aucun fournisseur enregistré pour le moment.")

    # --- TAB 2 : AJOUTER ---
    with tab2:
        with st.form("ajout_fournisseur"):
            st.subheader("🆕 Nouveau Fournisseur")
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom de l'entreprise / Fournisseur *")
                telephone = st.text_input("Téléphone *")
            with col2:
                email = st.text_input("Email")
                adresse = st.text_area("Adresse")
            
            submitted = st.form_submit_button("Enregistrer le fournisseur")
            if submitted:
                if nom and telephone:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO fournisseurs (nom, telephone, email, adresse)
                        VALUES (?, ?, ?, ?)
                    """, (nom, telephone, email, adresse))
                    conn.commit()
                    st.success(f"✅ Fournisseur '{nom}' ajouté avec succès !")
                else:
                    st.error("❌ Le Nom et le Téléphone sont obligatoires.")

    # --- TAB 3 : MODIFIER / SUPPRIMER ---
    with tab3:
        query_list = f"""
            SELECT id, nom FROM fournisseurs
        """
        df_fournisseurs = pd.read_sql_query(query_list, conn)
        
        if not df_fournisseurs.empty:
            fournisseur_dict = df_fournisseurs.apply(
                lambda row: f"{row['nom']} (ID: {row['id']})", axis=1
            ).tolist()
            
            fournisseur_choice = st.selectbox("Choisir un fournisseur à modifier", fournisseur_dict)
            # Extraction de l'ID plus sécurisée
            fournisseur_id = int(fournisseur_choice.split("ID: ")[1].replace(")", ""))
            
            # Requête avec f""" """
            query_detail = f"""
                SELECT * FROM fournisseurs 
                WHERE id = {fournisseur_id}
            """
            df_detail = pd.read_sql_query(query_detail, conn)
            fournisseur_data = df_detail.iloc[0]
            
            st.markdown("---")
            with st.form("modif_fournisseur"):
                st.subheader(f"Modifier : {fournisseur_data['nom']}")
                col1, col2 = st.columns(2)
                with col1:
                    m_nom = st.text_input("Nom *", value=fournisseur_data['nom'])
                    m_tel = st.text_input("Téléphone *", value=fournisseur_data['telephone'])
                with col2:
                    m_email = st.text_input("Email", value=fournisseur_data['email'] if fournisseur_data['email'] else "")
                    m_adresse = st.text_area("Adresse", value=fournisseur_data['adresse'] if fournisseur_data['adresse'] else "")
                
                save = st.form_submit_button("💾 Sauvegarder les modifications")
                if save:
                    if m_nom and m_tel:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE fournisseurs SET nom=?, telephone=?, email=?, adresse=? WHERE id=?
                        """, (m_nom, m_tel, m_email, m_adresse, fournisseur_id))
                        conn.commit()
                        st.success("✅ Fournisseur modifié avec succès !")
                        st.rerun()
                    else:
                        st.error("❌ Le Nom et le Téléphone restent obligatoires.")
            
            st.markdown("---")
            st.warning("⚠️ La suppression est définitive.")
            if st.button(f"🗑️ Supprimer {fournisseur_data['nom']}"):
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM fournisseurs WHERE id={fournisseur_id}")
                conn.commit()
                st.success(f"Fournisseur '{fournisseur_data['nom']}' supprimé !")
                st.rerun()
                
        else:
            st.info("Veuillez ajouter des fournisseurs d'abord pour pouvoir les modifier.")
            
    conn.close()
# --- MODULE 12 : ACHATS ---
def show_achats():
    st.title("🛒 Gestion des Achats & Commandes")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Suivi des Commandes", "➕ Nouveau Bon de Commande", "📥 Réception & Intégration Stock"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        statut_filter = st.selectbox("Filtrer par statut", ["Tous", "Commandé", "En attente", "Reçu"], key="filter_achat")
        
        base_query = f"""
            SELECT a.id, a.numero_bc, f.nom as Fournisseur, a.designation, a.reference, 
                   a.quantite, a.montant_total, a.statut, a.date_commande
            FROM achats a
            LEFT JOIN fournisseurs f ON a.fournisseur_id = f.id
        """
        
        if statut_filter != "Tous":
            query = base_query + f" WHERE a.statut = '{statut_filter}' ORDER BY a.date_commande DESC"
        else:
            query = base_query + " ORDER BY a.date_commande DESC"
            
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Ajouter des icônes de statut
            def statut_icon_achat(val):
                if val == "Commandé": return "🟡 Commandé"
                elif val == "En attente": return "⏸️ En attente"
                elif val == "Reçu": return "✅ Reçu"
                else: return val
            df['statut'] = df['statut'].apply(statut_icon_achat)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune commande trouvée pour ce filtre.")

    # --- TAB 2 : NOUVEAU BON DE COMMANDE ---
    with tab2:
        df_fournisseurs = pd.read_sql_query("SELECT id, nom FROM fournisseurs", conn)
        if df_fournisseurs.empty:
            st.error("⚠️ Vous devez d'abord ajouter des Fournisseurs (Module 11) avant de pouvoir commander !")
        else:
            fournisseur_dict = df_fournisseurs.apply(lambda row: f"{row['nom']} (ID: {row['id']})", axis=1).tolist()
            
            with st.form("new_achat"):
                st.subheader("🆕 Créer un Bon de Commande (BC)")
                
                # Générer numéro BC automatique
                last_id_achat = pd.read_sql_query("SELECT MAX(id) as max_id FROM achats", conn)['max_id'].values[0]
                if last_id_achat is None: last_id_achat = 0
                default_numero_bc = f"BC-{last_id_achat+1:04d}"
                
                col1, col2 = st.columns(2)
                with col1:
                    fournisseur_choice = st.selectbox("Fournisseur *", fournisseur_dict)
                    fournisseur_id = int(fournisseur_choice.split("ID: ")[1].replace(")", ""))
                    numero_bc = st.text_input("N° Bon de Commande *", value=default_numero_bc)
                    date_commande = st.date_input("Date de commande *")
                    
                with col2:
                    designation = st.text_input("Désignation de l'article * (ex: Pare-chocs BMW)")
                    reference = st.text_input("Référence fournisseur (ex: PCH-BMW-01)")
                    quantite = st.number_input("Quantité commandée *", min_value=1, step=1)
                    prix_unitaire = st.number_input("Prix unitaire d'achat (€) *", min_value=0.0, format="%.2f")
                    
                notes = st.text_area("Notes / Instructions pour le fournisseur")
                
                submitted = st.form_submit_button("🛒 Valider la Commande")
                if submitted:
                    if designation and quantite and prix_unitaire and numero_bc:
                        montant_total = quantite * prix_unitaire
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO achats (fournisseur_id, numero_bc, date_commande, date_reception, statut, designation, reference, quantite, prix_unitaire, montant_total, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (fournisseur_id, numero_bc, str(date_commande), None, "Commandé", designation, reference, quantite, prix_unitaire, montant_total, notes))
                        conn.commit()
                        st.success(f"✅ Bon de Commande {numero_bc} créé ! Montant : {montant_total:.2f} €")
                    else:
                        st.error("❌ Les champs Fournisseur, Désignation, Quantité et Prix sont obligatoires.")

    # --- TAB 3 : RÉCEPTION & INTÉGRATION STOCK ---
    with tab3:
        st.subheader("📥 Réceptionner une commande et l'intégrer au Stock")
        st.info("💡 Quand tu réceptionnes une commande, l'application va automatiquement chercher l'article dans ton Stock (Module 9) par sa référence et ajouter la quantité. Si l'article n'existe pas encore, elle le créera !")
        
        # Afficher les commandes non reçues
        query_a_recevoir = f"""
            SELECT a.id, a.numero_bc, f.nom as Fournisseur, a.designation, a.reference, a.quantite, a.statut
            FROM achats a
            LEFT JOIN fournisseurs f ON a.fournisseur_id = f.id
            WHERE a.statut IN ('Commandé', 'En attente')
        """
        df_a_recevoir = pd.read_sql_query(query_a_recevoir, conn)
        
        if df_a_recevoir.empty:
            st.success("🎉 Toutes les commandes ont été réceptionnées !")
        else:
            achat_dict = df_a_recevoir.apply(
                lambda row: f"{row['numero_bc']} - {row['designation']} (Qté: {row['quantite']}) [AchatID:{row['id']}]", axis=1
            ).tolist()
            
            achat_choice = st.selectbox("Commande à réceptionner", achat_dict)
            achat_id = int(achat_choice.split("[AchatID:")[1].replace("]", ""))
            
            achat_data = df_a_recevoir[df_a_recevoir['id'] == achat_id].iloc[0]
            ref_article = achat_data['reference']
            qty_article = int(achat_data['quantite'])
            designation_article = achat_data['designation']
            
            if st.button(f"✅ Confirmer la réception de {qty_article} x {designation_article}"):
                cursor = conn.cursor()
                
                # 1. Mettre à jour le statut de l'achat
                cursor.execute("""
                    UPDATE achats SET statut = 'Reçu', date_reception = DATE('now') WHERE id = ?
                """, (achat_id,))
                
                # 2. Vérifier si l'article existe déjà dans le stock par sa référence
                query_check_stock = f"""
                    SELECT id, quantite FROM stock WHERE reference = '{ref_article}'
                """
                df_check = pd.read_sql_query(query_check_stock, conn)
                
                if not df_check.empty:
                    # L'article existe : on augmente la quantité
                    stock_id = df_check.iloc[0]['id']
                    cursor.execute("""
                        UPDATE stock SET quantite = quantite + ? WHERE id = ?
                    """, (qty_article, stock_id))
                    st.success(f"📦 Stock mis à jour ! +{qty_article} unités ajoutées à l'article existant (Réf: {ref_article}).")
                else:
                    # L'article n'existe pas dans le stock : on le crée avec un prix de vente estimé (double du prix d'achat)
                    prix_achat = float(achat_data['prix_unitaire']) if 'prix_unitaire' in achat_data else 0.0
                    prix_vente_estime = prix_achat * 2.0 # Marge standard de 100%
                    
                    # On détermine le type (Pièce par défaut si c'est un pare-chocs/capot, etc.)
                    type_article = "Pièce"
                    
                    cursor.execute("""
                        INSERT INTO stock (type_article, reference, designation, quantite, prix_achat, prix_vente, seuil_alerte)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (type_article, ref_article, designation_article, qty_article, prix_achat, prix_vente_estime, 2))
                    st.success(f"🆕 Nouvel article créé dans le Stock : {designation_article} (Qté: {qty_article}, Prix vente estimé: {prix_vente_estime:.2f} €).")
                
                conn.commit()
                st.rerun()

    conn.close()

# --- MODULE 13 : FACTURATION ---
def show_facturation():
    st.title("🧾 Facturation & Paiements")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📋 Liste des Factures", "➕ Transformer un Devis en Facture", "💰 Paiement & PDF"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        query = f"""
            SELECT f.id, f.numero_facture, c.nom || ' ' || c.prenom as Client, 
                   v.immatriculation, f.date_creation, f.statut_paiement, d.total_ttc, f.montant_paye
            FROM factures f
            JOIN devis d ON f.devis_id = d.id
            JOIN vehicules v ON d.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
            ORDER BY f.date_creation DESC
        """
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            def statut_paiement_icon(val):
                if val == "Payée": return "🟢 Payée"
                elif val == "Partiellement payée": return "🟡 Partielle"
                elif val == "Impayée": return "🔴 Impayée"
                else: return val
                
            df['statut_paiement'] = df['statut_paiement'].apply(statut_paiement_icon)
            df['Reste à Payer'] = df['total_ttc'] - df['montant_paye']
            
            df_display = df[['numero_facture', 'Client', 'immatriculation', 'date_creation', 'statut_paiement', 'total_ttc', 'montant_paye', 'Reste à Payer']]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune facture émise pour le moment.")

    # --- TAB 2 : TRANSFORMATION DEVIS -> FACTURE ---
    with tab2:
        st.subheader("🔄 Transformer un Devis validé en Facture")
        st.warning("⚠️ Seuls les devis avec le statut 'Validé' ou 'En attente' peuvent être facturés.")
        
        # Chercher les devis non encore facturés
        query_devis_dispo = f"""
            SELECT d.id, d.numero_devis, c.nom || ' ' || c.prenom as Client, v.immatriculation, d.statut, d.total_ttc
            FROM devis d
            JOIN vehicules v ON d.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
            WHERE d.id NOT IN (SELECT devis_id FROM factures WHERE devis_id IS NOT NULL)
            AND d.statut IN ('Validé', 'En attente')
        """
        df_devis_dispo = pd.read_sql_query(query_devis_dispo, conn)
        
        if df_devis_dispo.empty:
            st.info("🎉 Tous les devis validés ont déjà été facturés, ou aucun devis n'est validé.")
        else:
            devis_dict = df_devis_dispo.apply(
                lambda row: f"{row['numero_devis']} - {row['Client']} ({row['immatriculation']}) TTC: {row['total_ttc']}€ [DevisID:{row['id']}]", axis=1
            ).tolist()
            
            devis_choice = st.selectbox("Choisir le Devis à facturer", devis_dict)
            devis_id = int(devis_choice.split("[DevisID:")[1].replace("]", ""))
            
            # Générer numéro facture auto
            last_id_fac = pd.read_sql_query("SELECT MAX(id) as max_id FROM factures", conn)['max_id'].values[0]
            if last_id_fac is None: last_id_fac = 0
            default_numero_fac = f"FAC-{last_id_fac+1:04d}"
            
            col1, col2 = st.columns(2)
            with col1:
                numero_facture = st.text_input("N° Facture *", value=default_numero_fac)
            with col2:
                date_facture = st.date_input("Date d'émission *")
                
            if st.button("🧾 Créer la Facture"):
                if numero_facture and date_facture:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO factures (devis_id, numero_facture, date_creation, statut_paiement, montant_paye)
                        VALUES (?, ?, ?, ?, ?)
                    """, (devis_id, numero_facture, str(date_facture), "Impayée", 0.0))
                    conn.commit()
                    st.success(f"✅ Facture {numero_facture} créée avec succès ! Elle est actuellement Impayée.")
                else:
                    st.error("❌ Le numéro et la date sont obligatoires.")

    # --- TAB 3 : PAIEMENT & PDF ---
    with tab3:
        query_factures = f"""
            SELECT f.id, f.numero_facture, c.nom || ' ' || c.prenom as Client, f.statut_paiement, d.total_ttc, f.montant_paye
            FROM factures f
            JOIN devis d ON f.devis_id = d.id
            JOIN vehicules v ON d.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
        """
        df_factures = pd.read_sql_query(query_factures, conn)
        
        if df_factures.empty:
            st.info("Aucune facture à gérer.")
        else:
            fac_dict = df_factures.apply(
                lambda row: f"{row['numero_facture']} - {row['Client']} (Statut: {row['statut_paiement']}) [FacID:{row['id']}]", axis=1
            ).tolist()
            
            fac_choice = st.selectbox("Choisir une Facture", fac_dict)
            fac_id = int(fac_choice.split("[FacID:")[1].replace("]", ""))
            
            facture_data = df_factures[df_factures['id'] == fac_id].iloc[0]
            total_ttc = facture_data['total_ttc']
            montant_paye_actuel = facture_data['montant_paye']
            reste_a_payer = total_ttc - montant_paye_actuel
            
            st.markdown("---")
            st.subheader(f"💰 Gestion du Paiement : {facture_data['numero_facture']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total TTC", f"{total_ttc:.2f} €")
            with col2:
                st.metric("Montant Payé", f"{montant_paye_actuel:.2f} €")
            with col3:
                st.metric("Reste à Payer", f"{reste_a_payer:.2f} €", delta=f"-{reste_a_payer:.2f} €" if reste_a_payer > 0 else "0 €")
            
            # Enregistrer un paiement
            with st.form("paiement_form"):
                montant_paiement = st.number_input("Montant du paiement reçu (€)", min_value=0.0, format="%.2f")
                submitted = st.form_submit_button("✅ Enregistrer le paiement")
                
                if submitted:
                    if montant_paiement > 0:
                        nouveau_montant_paye = montant_paye_actuel + montant_paiement
                        
                        # Déterminer le nouveau statut
                        if nouveau_montant_paye >= total_ttc:
                            nouveau_statut = "Payée"
                            nouveau_montant_paye = total_ttc # On plafonne si le client paie trop
                        elif nouveau_montant_paye > 0:
                            nouveau_statut = "Partiellement payée"
                        else:
                            nouveau_statut = "Impayée"
                            
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE factures SET montant_paye = ?, statut_paiement = ? WHERE id = ?
                        """, (nouveau_montant_paye, nouveau_statut, fac_id))
                        conn.commit()
                        st.success(f"✅ Paiement de {montant_paiement:.2f} € enregistré ! Statut : {nouveau_statut}")
                        st.rerun()
                    else:
                        st.error("❌ Le montant doit être supérieur à 0.")
            
            st.markdown("---")
            st.subheader("📄 Générer la Facture PDF")
            if st.button("📥 Télécharger la Facture PDF"):
                # Récupérer toutes les données liées
                df_fac_detail = pd.read_sql_query(f"SELECT * FROM factures WHERE id={fac_id}", conn)
                facture_info = df_fac_detail.iloc[0].to_dict()
                
                devis_id_linked = facture_info['devis_id']
                df_devis_detail = pd.read_sql_query(f"SELECT * FROM devis WHERE id={devis_id_linked}", conn)
                devis_info = df_devis_detail.iloc[0].to_dict()
                
                veh_id_linked = devis_info['vehicule_id']
                veh_info = pd.read_sql_query(f"SELECT * FROM vehicules WHERE id={veh_id_linked}", conn).iloc[0].to_dict()
                client_info = pd.read_sql_query(f"SELECT * FROM clients WHERE id={veh_info['client_id']}", conn).iloc[0].to_dict()
                
                details = json.loads(devis_info['details_json'])
                
                pdf_path = generate_facture_pdf(facture_info, devis_info, client_info, veh_info, details)
                
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                st.download_button(
                    label="⬇️ Cliquer ici pour télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"Facture_{facture_info['numero_facture']}.pdf",
                    mime="application/pdf"
                )

    conn.close()

# --- MODULE 14 : CAISSE ---
def show_caisse():
    st.title("💰 Gestion de Caisse & Trésorerie")
    conn = get_connection()
    
    tab1, tab2, tab3 = st.tabs(["📊 Journal de Caisse", "➕ Nouvelle Transaction", "📈 Rapports & Solde"])
    
    # --- TAB 1 : JOURNAL ---
    with tab1:
        # Filtres
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            filtre_type = st.selectbox("Type de transaction", ["Tous", "Entrée", "Sortie"], key="filter_caisse_type")
        with col_filter2:
            filtre_periode = st.selectbox("Période", ["Aujourd'hui", "7 jours", "30 jours", "Tout"], key="filter_caisse_periode")
            
        # Construction de la requête avec filtres
        base_query = f"""
            SELECT id, date_transaction, type_transaction, categorie, description, montant 
            FROM caisse
        """
        conditions = []
        
        if filtre_type != "Tous":
            conditions.append(f"type_transaction = '{filtre_type}'")
            
        if filtre_periode == "Aujourd'hui":
            conditions.append("date_transaction = DATE('now')")
        elif filtre_periode == "7 jours":
            conditions.append("date_transaction >= DATE('now', '-7 days')")
        elif filtre_periode == "30 jours":
            conditions.append("date_transaction >= DATE('now', '-30 days')")
            
        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            
        query = base_query + where_clause + " ORDER BY date_transaction DESC, id DESC"
        
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Formater pour l'affichage
            def format_montant(row):
                if row['type_transaction'] == 'Entrée':
                    return f"+{row['montant']:.2f} €"
                else:
                    return f"-{row['montant']:.2f} €"
            df['Montant Formaté'] = df.apply(format_montant, axis=1)
            
            df_display = df[['date_transaction', 'type_transaction', 'categorie', 'description', 'Montant Formaté']]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune transaction trouvée pour cette période.")

    # --- TAB 2 : NOUVELLE TRANSACTION ---
    with tab2:
        with st.form("new_transaction"):
            st.subheader("🧾 Enregistrer un mouvement d'argent")
            
            type_transaction = st.radio("Type de mouvement *", ["Entrée (Encaissement)", "Sortie (Décaissement)"])
            
            col1, col2 = st.columns(2)
            with col1:
                date_transaction = st.date_input("Date de l'opération *")
                # Catégories dynamiques selon le type
                if type_transaction == "Entrée (Encaissement)":
                    categorie = st.selectbox("Catégorie *", ["Paiement Client", "Vente directe", "Autre revenu"])
                else:
                    categorie = st.selectbox("Catégorie *", ["Achat Fournisseur", "Salaire Employé", "Charges (Loyer/EDF)", "Autre dépense"])
                    
            with col2:
                montant = st.number_input("Montant (€) *", min_value=0.0, format="%.2f")
                description = st.text_area("Description / Référence * (ex: FAC-0001, Salaire Janvier)")
                
            submitted = st.form_submit_button("✅ Enregistrer la transaction")
            if submitted:
                # Déterminer le vrai type pour la DB
                db_type = "Entrée" if "Entrée" in type_transaction else "Sortie"
                
                if montant > 0 and description and date_transaction:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO caisse (type_transaction, montant, date_transaction, description, categorie)
                        VALUES (?, ?, ?, ?, ?)
                    """, (db_type, montant, str(date_transaction), description, categorie))
                    conn.commit()
                    st.success(f"✅ Transaction de {montant:.2f} € ({db_type}) enregistrée dans la caisse !")
                else:
                    st.error("❌ Le montant, la date et la description sont obligatoires.")

    # --- TAB 3 : RAPPORTS & SOLDE ---
    with tab3:
        st.subheader("📊 Santé Financière du Garage")
        
        # Récupérer toutes les données pour les calculs globaux
        df_all = pd.read_sql_query("SELECT * FROM caisse", conn)
        
        if df_all.empty:
            st.info("Aucune donnée financière à analyser pour le moment.")
        else:
            # Calculs des KPI
            total_entrees = df_all[df_all['type_transaction'] == 'Entrée']['montant'].sum()
            total_sorties = df_all[df_all['type_transaction'] == 'Sortie']['montant'].sum()
            solde_actuel = total_entrees - total_sorties
            
            # Affichage des Cartes KPI
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="📈 Total Entrées", value=f"{total_entrees:.2f} €")
            with col2:
                st.metric(label="📉 Total Sorties", value=f"{total_sorties:.2f} €")
            with col3:
                # Delta coloré : Vert si positif, Rouge si négatif
                delta_color = "normal" if solde_actuel >= 0 else "inverse"
                st.metric(label="💎 SOLDE NET", value=f"{solde_actuel:.2f} €", delta=f"{solde_actuel:.2f} €", delta_color=delta_color)
                
            st.markdown("---")
            
            # Préparation des graphiques Plotly
            # 1. Graphique Barres : Entrées vs Sorties par mois
            df_all['Mois'] = pd.to_datetime(df_all['date_transaction']).dt.to_period('M').astype(str)
            
            df_grouped = df_all.groupby(['Mois', 'type_transaction'])['montant'].sum().reset_index()
            
            fig_cashflow = px.bar(df_grouped, x='Mois', y='montant', color='type_transaction',
                                 title="Flux de Trésorerie Mensuel (Entrées vs Sorties)",
                                 barmode='group',
                                 color_discrete_map={'Entrée': '#2ecc71', 'Sortie': '#e74c3c'})
            st.plotly_chart(fig_cashflow, use_container_width=True)
            
            # 2. Graphique Camembert : Répartition des Sorties (Où va l'argent ?)
            df_sorties = df_all[df_all['type_transaction'] == 'Sortie']
            if not df_sorties.empty:
                df_cat_sorties = df_sorties.groupby('categorie')['montant'].sum().reset_index()
                
                fig_expenses = px.pie(df_cat_sorties, values='montant', names='categorie', 
                                     title="Répartition des Dépenses par Catégorie",
                                     hole=0.4)
                st.plotly_chart(fig_expenses, use_container_width=True)

    conn.close()

# --- MODULE 15 : GALERIE PHOTOS ---
import time # Nécessaire pour générer des noms de fichiers uniques

def show_photos():
    st.title("📸 Galerie Photos - Avant / Pendant / Après")
    conn = get_connection()
    
    # S'assurer que le dossier photos existe
    if not os.path.exists("photos"):
        os.makedirs("photos")
    
    tab1, tab2, tab3 = st.tabs(["🖼️ Galerie Globale", "➕ Ajouter des Photos", "🔍 Galerie Véhicule"])
    
    # --- TAB 1 : GALERIE GLOBALE ---
    with tab1:
        filtre_type = st.selectbox("Filtrer par type", ["Tous", "Avant réparation", "Pendant réparation", "Après réparation"], key="filter_photo_type")
        
        base_query = f"""
            SELECT p.id, v.immatriculation, p.type_photo, p.chemin_fichier, p.date_upload
            FROM photos p
            JOIN vehicules v ON p.vehicule_id = v.id
        """
        
        if filtre_type != "Tous":
            query = base_query + f" WHERE p.type_photo = '{filtre_type}' ORDER BY p.date_upload DESC"
        else:
            query = base_query + " ORDER BY p.date_upload DESC"
            
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Affichage en grille (3 colonnes)
            cols = st.columns(3)
            for index, row in df.iterrows():
                col_idx = index % 3
                with cols[col_idx]:
                    try:
                        st.image(row['chemin_fichier'], caption=f"{row['immatriculation']} - {row['type_photo']} ({row['date_upload']})")
                    except:
                        st.error(f"Image introuvable : {row['chemin_fichier']}")
        else:
            st.info("Aucune photo dans la galerie pour le moment.")

    # --- TAB 2 : AJOUTER DES PHOTOS ---
    with tab2:
        df_vehicules = pd.read_sql_query("""
            SELECT v.id, v.immatriculation, v.marque, v.modele, c.nom || ' ' || c.prenom as Client
            FROM vehicules v JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if df_vehicules.empty:
            st.error("⚠️ Vous devez ajouter un client et un véhicule avant d'importer des photos !")
        else:
            veh_dict = df_vehicules.apply(lambda row: f"{row['immatriculation']} - {row['marque']} {row['modele']} ({row['Client']}) [VehID:{row['id']}]", axis=1).tolist()
            veh_choice = st.selectbox("Véhicule concerné *", veh_dict)
            veh_id = int(veh_choice.split("[VehID:")[1].replace("]", ""))
            
            type_photo = st.selectbox("Type de photo *", ["Avant réparation", "Pendant réparation", "Après réparation"])
            
            # Upload multiple files
            uploaded_files = st.file_uploader("Choisir des photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
            
            if uploaded_files:
                st.warning(f"Vous avez sélectionné {len(uploaded_files)} photo(s). Cliquez sur le bouton ci-dessous pour les sauvegarder.")
                
                if st.button("💾 Sauvegarder les photos sur le serveur"):
                    cursor = conn.cursor()
                    count_saved = 0
                    
                    for uploaded_file in uploaded_files:
                        # Générer un nom de fichier unique pour éviter les conflits (ex: immat_type_timestamp.jpg)
                        timestamp = int(time.time())
                        extension = uploaded_file.name.split('.')[-1]
                        safe_immat = df_vehicules[df_vehicules['id'] == veh_id]['immatriculation'].values[0].replace(" ", "_")
                        filename = f"{safe_immat}_{type_photo.split(' ')[0]}_{timestamp}_{count_saved}.{extension}"
                        
                        filepath = os.path.join("photos", filename)
                        
                        # Sauvegarder physiquement le fichier
                        with open(filepath, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                            
                        # Sauvegarder le chemin dans la DB
                        cursor.execute("""
                            INSERT INTO photos (vehicule_id, type_photo, chemin_fichier, date_upload)
                            VALUES (?, ?, ?, DATE('now'))
                        """, (veh_id, type_photo, filepath))
                        
                        count_saved += 1
                        
                    conn.commit()
                    st.success(f"✅ {count_saved} photo(s) ajoutées avec succès dans la galerie !")

    # --- TAB 3 : GALERIE VÉHICULE ---
    with tab3:
        df_veh_list = pd.read_sql_query("""
            SELECT v.id, v.immatriculation, c.nom || ' ' || c.prenom as Client
            FROM vehicules v JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if not df_veh_list.empty:
            veh_dict_detail = df_veh_list.apply(lambda row: f"{row['immatriculation']} ({row['Client']}) [VehID:{row['id']}]", axis=1).tolist()
            veh_choice_detail = st.selectbox("Choisir un véhicule pour voir sa galerie", veh_dict_detail)
            veh_id_detail = int(veh_choice_detail.split("[VehID:")[1].replace("]", ""))
            
            # Récupérer les photos de ce véhicule
            df_veh_photos = pd.read_sql_query(f"""
                SELECT id, type_photo, chemin_fichier, date_upload 
                FROM photos WHERE vehicule_id = {veh_id_detail}
            """, conn)
            
            if not df_veh_photos.empty:
                st.subheader("🟢 Avant Réparation")
                df_avant = df_veh_photos[df_veh_photos['type_photo'] == "Avant réparation"]
                if not df_avant.empty:
                    cols_avant = st.columns(min(len(df_avant), 3))
                    for i, row in df_avant.iterrows():
                        with cols_avant[i % 3]:
                            try: st.image(row['chemin_fichier'])
                            except: st.error("Image introuvable")
                else:
                    st.info("Aucune photo 'Avant' pour ce véhicule.")
                    
                st.subheader("🟡 Pendant Réparation")
                df_pendant = df_veh_photos[df_veh_photos['type_photo'] == "Pendant réparation"]
                if not df_pendant.empty:
                    cols_pendant = st.columns(min(len(df_pendant), 3))
                    for i, row in df_pendant.iterrows():
                        with cols_pendant[i % 3]:
                            try: st.image(row['chemin_fichier'])
                            except: st.error("Image introuvable")
                else:
                    st.info("Aucune photo 'Pendant' pour ce véhicule.")
                    
                st.subheader("🔴 Après Réparation")
                df_apres = df_veh_photos[df_veh_photos['type_photo'] == "Après réparation"]
                if not df_apres.empty:
                    cols_apres = st.columns(min(len(df_apres), 3))
                    for i, row in df_apres.iterrows():
                        with cols_apres[i % 3]:
                            try: st.image(row['chemin_fichier'])
                            except: st.error("Image introuvable")
                else:
                    st.info("Aucune photo 'Après' pour ce véhicule.")
                    
                # Option Suppression
                st.markdown("---")
                st.subheader("🗑️ Supprimer une photo")
                photo_dict = df_veh_photos.apply(lambda row: f"{row['type_photo']} - {row['date_upload']} ({row['chemin_fichier']}) [PhotoID:{row['id']}]", axis=1).tolist()
                photo_choice = st.selectbox("Photo à supprimer", photo_dict)
                photo_id = int(photo_choice.split("[PhotoID:")[1].replace("]", ""))
                
                if st.button("Supprimer cette photo"):
                    filepath_to_del = df_veh_photos[df_veh_photos['id'] == photo_id]['chemin_fichier'].values[0]
                    
                    # Supprimer le fichier physique
                    if os.path.exists(filepath_to_del):
                        os.remove(filepath_to_del)
                        
                    # Supprimer de la DB
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM photos WHERE id = {photo_id}")
                    conn.commit()
                    st.success("Photo supprimée avec succès !")
                    st.rerun()
            else:
                st.info("Aucune photo enregistrée pour ce véhicule pour le moment.")
        else:
            st.info("Aucun véhicule enregistré.")

    conn.close()

# --- MODULE 16 : EMPLOYÉS ---
def show_employes():
    st.title("👷 Gestion des Employés & Productivité")
    conn = get_connection()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Liste des Employés", "➕ Ajouter un Employé", "🔍 Modifier / Supprimer", "📊 Productivité"])
    
    # --- TAB 1 : LISTE ---
    with tab1:
        df = pd.read_sql_query("SELECT id, nom, fonction, telephone, salaire FROM employes ORDER BY nom", conn)
        if not df.empty:
            # Formater le salaire pour l'affichage
            df['Salaire (€)'] = df['salaire'].apply(lambda x: f"{x:.2f} €")
            df_display = df[['nom', 'fonction', 'telephone', 'Salaire (€)']]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun employé enregistré pour le moment.")

    # --- TAB 2 : AJOUTER ---
    with tab2:
        with st.form("add_employe"):
            st.subheader("🆕 Nouvel Employé")
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom complet * (ex: Jean Dupont)")
                fonction = st.selectbox("Fonction / Rôle *", ["Chef d'atelier", "Tôlier", "Peintre", "Préparateur", "Réceptionniste", "Comptable"])
            with col2:
                telephone = st.text_input("Téléphone")
                salaire = st.number_input("Salaire mensuel (€) *", min_value=0.0, format="%.2f")
                
            submitted = st.form_submit_button("✅ Ajouter l'employé")
            if submitted:
                if nom and fonction and salaire > 0:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO employes (nom, fonction, telephone, salaire)
                        VALUES (?, ?, ?, ?)
                    """, (nom, fonction, telephone, salaire))
                    conn.commit()
                    st.success(f"✅ Employé {nom} ajouté avec succès !")
                else:
                    st.error("❌ Le Nom, la Fonction et le Salaire sont obligatoires.")

    # --- TAB 3 : MODIFIER / SUPPRIMER ---
    with tab3:
        df_emp_list = pd.read_sql_query("SELECT id, nom FROM employes", conn)
        if df_emp_list.empty:
            st.info("Aucun employé à modifier.")
        else:
            emp_dict = df_emp_list.apply(lambda row: f"{row['nom']} (ID: {row['id']})", axis=1).tolist()
            emp_choice = st.selectbox("Choisir un employé", emp_dict)
            emp_id = int(emp_choice.split("ID: ")[1].replace(")", ""))
            
            df_detail = pd.read_sql_query(f"SELECT * FROM employes WHERE id={emp_id}", conn)
            detail = df_detail.iloc[0]
            
            with st.form("modif_employe"):
                col1, col2 = st.columns(2)
                with col1:
                    m_nom = st.text_input("Nom *", value=detail['nom'])
                    m_fonction = st.selectbox("Fonction *", ["Chef d'atelier", "Tôlier", "Peintre", "Préparateur", "Réceptionniste", "Comptable"], index=["Chef d'atelier", "Tôlier", "Peintre", "Préparateur", "Réceptionniste", "Comptable"].index(detail['fonction']))
                with col2:
                    m_tel = st.text_input("Téléphone", value=detail['telephone'] if detail['telephone'] else "")
                    m_salaire = st.number_input("Salaire (€) *", min_value=0.0, format="%.2f", value=float(detail['salaire']))
                
                save = st.form_submit_button("💾 Sauvegarder")
                if save:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE employes SET nom=?, fonction=?, telephone=?, salaire=? WHERE id=?
                    """, (m_nom, m_fonction, m_tel, m_salaire, emp_id))
                    conn.commit()
                    st.success("✅ Employé modifié !")
                    st.rerun()
            
            st.markdown("---")
            if st.button(f"🗑️ Supprimer {detail['nom']}"):
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM employes WHERE id={emp_id}")
                conn.commit()
                st.success("Employé supprimé !")
                st.rerun()

    # --- TAB 4 : PRODUCTIVITÉ ---
    with tab4:
        st.subheader("📊 Suivi des Performances par Employé")
        st.info("💡 L'application relie automatiquement le nom de l'employé aux Ordres de Réparation (Module 7) pour calculer son chiffre d'affaires généré.")
        
        df_emp_perf = pd.read_sql_query("SELECT id, nom, fonction, salaire FROM employes", conn)
        
        if df_emp_perf.empty:
            st.warning("Ajoutez des employés pour voir leurs statistiques.")
        else:
            # Calculer les stats pour chaque employé
            stats_data = []
            for index, emp in df_emp_perf.iterrows():
                emp_nom = emp['nom']
                
                # Compter les OR terminés par cet employé
                query_or_count = f"""
                    SELECT COUNT(id) as total_or, SUM(total_ttc) as ca_genere
                    FROM ordres_reparation o
                    LEFT JOIN devis d ON o.devis_id = d.id
                    WHERE o.responsable = '{emp_nom}' AND o.statut = 'Terminé'
                """
                df_stats = pd.read_sql_query(query_or_count, conn)
                
                total_or = df_stats['total_or'].values[0] if df_stats['total_or'].values[0] is not None else 0
                ca_genere = df_stats['ca_genere'].values[0] if df_stats['ca_genere'].values[0] is not None else 0.0
                
                stats_data.append({
                    'Nom': emp_nom,
                    'Fonction': emp['fonction'],
                    'Salaire': emp['salaire'],
                    'OR Terminés': total_or,
                    'CA Généré': ca_genere,
                    'ROI (CA - Salaire)': ca_genere - emp['salaire']
                })
                
            df_perf_display = pd.DataFrame(stats_data)
            
            # Afficher les KPI Globaux
            total_salaire = df_perf_display['Salaire'].sum()
            total_ca_team = df_perf_display['CA Généré'].sum()
            roi_net = total_ca_team - total_salaire
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="💸 Total Salaires", value=f"{total_salaire:.2f} €")
            with col2:
                st.metric(label="📈 CA Généré par l'atelier", value=f"{total_ca_team:.2f} €")
            with col3:
                delta_color = "normal" if roi_net >= 0 else "inverse"
                st.metric(label="💎 Rentabilité Atelier (CA - Salaires)", value=f"{roi_net:.2f} €", delta=f"{roi_net:.2f} €", delta_color=delta_color)
                
            st.markdown("---")
            st.subheader("Détail par Employé")
            st.dataframe(df_perf_display, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🏆 Classement par Chiffre d'affaires Généré")
            df_perf_sorted = df_perf_display.sort_values(by='CA Généré', ascending=False)
            
            fig_perf = px.bar(df_perf_sorted, x='Nom', y='CA Généré', 
                              title="CA Généré par Employé (OR Terminés)",
                              color='Fonction', text='CA Généré')
            fig_perf.update_traces(texttemplate='%{text:.2f} €', textposition='outside')
            st.plotly_chart(fig_perf, use_container_width=True)

    conn.close()

def show_documents():
    st.title("📂 Documents")
    st.info("🚧 Ce module est prêt à être développé !")

def show_statistiques():
    st.title("📈 Statistiques")
    st.info("🚧 Ce module est prêt à être développé !")

def show_qrcode():
    st.title("📱 QR Code")
    st.info("🚧 Ce module est prêt à être développé !")

def show_users():
    st.title("🔐 Multi-Utilisateurs")
    st.info("🚧 Ce module est prêt à être développé !")


# ==========================================
# EXÉCUTION PRINCIPALE
# ==========================================

# Appeler la fonction du module choisi
if module_name == "dashboard":
    show_dashboard()
elif module_name == "clients":
    show_clients()
elif module_name == "vehicules":
    show_vehicules()
elif module_name == "reception":
    show_reception()
elif module_name == "sinistres":
    show_sinistres()
elif module_name == "devis":
    show_devis()
elif module_name == "ordres":
    show_ordres()
elif module_name == "atelier":
    show_atelier()
elif module_name == "stock":
    show_stock()
elif module_name == "accessoires":
    show_accessoires()
elif module_name == "fournisseurs":
    show_fournisseurs()
elif module_name == "achats":
    show_achats()
elif module_name == "facturation":
    show_facturation()
elif module_name == "caisse":
    show_caisse()
elif module_name == "photos":
    show_photos()
elif module_name == "employes":
    show_employes()
elif module_name == "documents":
    show_documents()
elif module_name == "statistiques":
    show_statistiques()
elif module_name == "qrcode":
    show_qrcode()
elif module_name == "users":
    show_users()
