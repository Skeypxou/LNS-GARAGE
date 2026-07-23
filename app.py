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

# Initialiser la DB au lancement
init_db()

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
            table_data.append(["MO", item['desc'], f"{item['qty']} H", f"{item['price']:.2f} €", f"{item['total']:.2f} €"])
            
    # Ajout Pièces
    for item in details.get('pieces', []):
        if item['qty'] > 0:
            table_data.append(["Pièce", f"{item.get('ref', '')} - {item['desc']}", f"{item['qty']}", f"{item['price']:.2f} €", f"{item['total']:.2f} €"])
            
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
        ["Total Main d'œuvre", f"{devis_info['total_mo']:.2f} €"],
        ["Total Pièces", f"{devis_info['total_pieces']:.2f} €"],
        ["Total Hors Taxe (HT)", f"{ht:.2f} €"],
        ["TVA (20%)", f"{devis_info['tva']:.2f} €"],
        ["Total TTC (À payer)", f"{devis_info['total_ttc']:.2f} €"]
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
                        st.write(f"Total: **{h * p:.2f} €**")
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
                    st.success(f"✅ Devis {numero_devis} sauvegardé ! Total TTC : {total_ttc:.2f} €")

    # --- TAB 3 : VOIR / PDF / MODIFIER ---
    with tab3:
        df_devis = pd.read_sql_query("""
            SELECT d.id, d.numero_devis, v.immatriculation, c.nom || ' ' || c.prenom as Client, d.statut, d.total_ttc
            FROM devis d
            JOIN vehicules v ON d.vehicule_id = v.id
            JOIN clients c ON v.client_id = c.id
        """, conn)
        
        if not df_devis.empty:
            devis_dict = df_devis.apply(lambda row: f"{row['numero_devis']} - {row['Client']} ({row['immatriculation']}) TTC: {row['total_ttc']}€ [ID:{row['id']}]", axis=1).tolist()
            devis_choice = st.selectbox("Choisir un devis", devis_dict)
            devis_id = int(devis_choice.split("[ID:")[1].replace("]", ""))
            
            # Récupération des données
            df_devis_detail = pd.read_sql_query(f"SELECT * FROM devis WHERE id={devis_id}", conn)
            devis_info = df_devis_detail.iloc[0].to_dict()
            
            veh_info = pd.read_sql_query(f"SELECT * FROM vehicules WHERE id={devis_info['vehicule_id']}", conn).iloc[0].to_dict()
            client_info = pd.read_sql_query(f"SELECT * FROM clients WHERE id={veh_info['client_id']}", conn).iloc[0].to_dict()
            
            # Affichage des infos
            st.write(f"**Statut actuel :** {devis_info['statut']} | **Total TTC :** {devis_info['total_ttc']} €")
            
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
                    devis_dict_filtered = df_devis_filtered.apply(lambda row: f"{row['numero_devis']} - {row['statut']} ({row['total_ttc']}€) [DevisID:{row['id']}]", axis=1).tolist()
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

def show_atelier():
    st.title("🏭 Suivi Atelier")
    st.info("🚧 Ce module est prêt à être développé !")

def show_stock():
    st.title("📦 Stock")
    st.info("🚧 Ce module est prêt à être développé !")

def show_accessoires():
    st.title("🔩 Accessoires")
    st.info("🚧 Ce module est prêt à être développé !")

def show_fournisseurs():
    st.title("🏭 Fournisseurs")
    st.info("🚧 Ce module est prêt à être développé !")

def show_achats():
    st.title("🛒 Achats")
    st.info("🚧 Ce module est prêt à être développé !")

def show_facturation():
    st.title("🧾 Facturation")
    st.info("🚧 Ce module est prêt à être développé !")

def show_caisse():
    st.title("💰 Caisse")
    st.info("🚧 Ce module est prêt à être développé !")

def show_photos():
    st.title("📸 Galerie Photos")
    st.info("🚧 Ce module est prêt à être développé !")

def show_employes():
    st.title("👷 Employés")
    st.info("🚧 Ce module est prêt à être développé !")

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
