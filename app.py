import streamlit as st
import itertools
import pandas as pd
import json

# --- CONFIG ---
SAVE_FILE = "joueurs.json"
NB_JOUEURS = 9
SEUIL_INDEX = 84.4

st.set_page_config(page_title="Sélection Golf ⛳", page_icon="⛳", layout="centered")

st.title("🏌️ Sélection des joueurs - Coupe de Golf")
st.write("Gérez vos joueurs, leurs disponibilités et trouvez automatiquement la meilleure combinaison conforme à l’index minimal.")

# ---------- chargement / sauvegarde ----------
def charger():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def sauvegarder(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------- sélection optimisée ----------
def calculer_selection(joueurs):
    dispos = [j for j in joueurs if j.get("dispo", False)]
    if len(dispos) < NB_JOUEURS:
        return None, "⚠️ Moins de 9 joueurs disponibles !"

    cap = [j for j in dispos if j.get("capitaine", False)]
    restants = [j for j in dispos if not j.get("capitaine", False)]

    if len(cap) > NB_JOUEURS:
        return None, "Trop de choix du capitaine (max 9)."

    n_restants = NB_JOUEURS - len(cap)
    meilleur_officiel = None
    meilleur_total = None
    meilleure_combinaison = None

    # essayer toutes les combinaisons des restants
    for combo in itertools.combinations(restants, n_restants):
        equipe = list(cap) + list(combo)
        total_reel = sum(float(j.get("index", 0)) for j in equipe)

        # calcul officiel : ramener max 2 index > 18.4 à 18.4
        au_dessus = sorted([j for j in equipe if j.get("index", 0) > 18.4], key=lambda x: x["index"], reverse=True)
        nb_assimiles = min(2, len(au_dessus))
        index_officiel = total_reel - sum(j["index"] for j in au_dessus[:nb_assimiles]) + (18.4 * nb_assimiles)

        # garder la meilleure (officiel >= seuil, la plus proche du seuil)
        if index_officiel >= SEUIL_INDEX:
            if meilleur_officiel is None or index_officiel < meilleur_officiel:
                meilleur_officiel = index_officiel
                meilleur_total = total_reel
                meilleure_combinaison = equipe

    # si aucune combinaison officielle >= seuil trouvée, choisir la meilleure dispo (les 9 meilleurs)
    if not meilleure_combinaison:
        meilleure_combinaison = sorted(dispos, key=lambda x: x["index"])[:NB_JOUEURS]
        meilleur_total = sum(j["index"] for j in meilleure_combinaison)
        au_dessus = sorted([j for j in meilleure_combinaison if j["index"] > 18.4], key=lambda x: x["index"], reverse=True)
        nb_assimiles = min(2, len(au_dessus))
        meilleur_officiel = meilleur_total - sum(j["index"] for j in au_dessus[:nb_assimiles]) + (18.4 * nb_assimiles)

    # préparer le texte
    texte = "🏌️ SÉLECTION DES 9 JOUEURS :\n\n"
    for j in sorted(meilleure_combinaison, key=lambda x: x["index"]):
        dispo_txt = "✅" if j.get("dispo", False) else "❌"
        texte += f"{j['nom']} - Index {j['index']} {dispo_txt}\n"

    texte += f"\nIndex global réel : {meilleur_total:.1f}"
    texte += f"\nIndex global officiel : {meilleur_officiel:.1f}\n"

    if meilleur_officiel >= SEUIL_INDEX:
        texte += f"\n✅ Objectif atteint (≥ {SEUIL_INDEX})"
    else:
        texte += f"\n❌ En dessous de {SEUIL_INDEX} : les choix du capitaine doivent être revus."

    return texte, None

# ---------- UI ----------
joueurs = charger()

with st.expander("➕ Ajouter un joueur"):
    nom = st.text_input("Nom du joueur")
    index = st.number_input("Index", step=0.1, format="%.1f")
    dispo = st.checkbox("Disponible", value=True)
    capitaine = st.checkbox("Choix du capitaine", value=False)
    if st.button("Ajouter joueur"):
        if nom.strip() == "":
            st.error("Le nom ne peut pas être vide.")
        else:
            joueurs.append({"nom": nom.strip(), "index": float(index), "dispo": dispo, "capitaine": capitaine})
            sauvegarder(joueurs)
            st.experimental_rerun()

st.subheader("📋 Liste des joueurs")

# tri manuel
col1, col2 = st.columns(2)
with col1:
    if st.button("🔤 Trier par nom (A→Z)"):
        joueurs = sorted(joueurs, key=lambda x: x["nom"].lower())
with col2:
    if st.button("📈 Trier par index (croissant)"):
        joueurs = sorted(joueurs, key=lambda x: x["index"])

# afficher et éditer
df = pd.DataFrame(joueurs)
edited_df = st.data_editor(
    df,
    column_config={
        "nom": st.column_config.TextColumn("Nom"),
        "index": st.column_config.NumberColumn("Index"),
        "dispo": st.column_config.CheckboxColumn("Disponible ?"),
        "capitaine": st.column_config.CheckboxColumn("Choix du capitaine ?"),
    },
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="editor"
)

# enregistrer les modifications faites via l'éditeur
if st.button("💾 Enregistrer les modifications"):
    joueurs = edited_df.to_dict("records")
    sauvegarder(joueurs)
    st.success("Modifications enregistrées !")

if st.button("🔍 Calculer la meilleure équipe"):
    texte, erreur = calculer_selection(joueurs)
    if erreur:
        st.error(erreur)
    else:
        st.text_area("📄 Résumé à copier :", texte, height=300)
        st.download_button("📋 Télécharger", texte, file_name="selection.txt")

if st.button("🗑️ Réinitialiser la liste"):
    joueurs = []
    sauvegarder(joueurs)
    st.experimental_rerun()
