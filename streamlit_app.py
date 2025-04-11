# JsonInterfacer.py

import os
import json
import math
import streamlit as st
import plotly.graph_objects as go
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from collections import Counter, defaultdict

################################################
# 1) Agrégation (ancien aggregator.py) intégré
################################################

def load_extracted_data(json_file_path):
    if not os.path.exists(json_file_path):
        return []
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except:
        return []

def aggregate_all_data(all_data):
    aggregated = {
        "total_files": len(all_data),
        "files_all_present_count": 0,
        "files_not_all_present_count": 0,
        "absent_lists": [],
        "all_law_citations": set(),
        "sum_total_paragraphs": 0,
        "sum_total_words": 0,
        "speakers_global_counter": Counter(),
        "total_decisions": 0,
        "rapporteurs_count": Counter(),
        "presidents_count": Counter(),
        "total_decision_graphs": 0,
        "sum_timeline_points": 0,
        "transition_counter": Counter(),
        "vote_count": 0,
        "vote_result_counter": Counter(),
        "global_decision_graph": {
            "timeline_points": [],
            "transitions": {},
            "all_speakers": set()
        }
    }

    global_index = 0
    for item in all_data:
        pa = item.get("presence_absence")
        if pa:
            if pa.get("all_present", False):
                aggregated["files_all_present_count"] += 1
            else:
                aggregated["files_not_all_present_count"] += 1
            for ab in pa.get("absent_list", []):
                aggregated["absent_lists"].append(ab)

        alc = item.get("advanced_law_citations", [])
        for law_cit in alc:
            aggregated["all_law_citations"].add(law_cit)

        gs = item.get("global_stats")
        if gs:
            aggregated["sum_total_paragraphs"] += gs.get("total_paragraphs", 0)
            aggregated["sum_total_words"] += gs.get("total_words", 0)
            sp_count = gs.get("speakers_global_count", {})
            for spk, val in sp_count.items():
                aggregated["speakers_global_counter"][spk] += val

        decs = item.get("decisions", [])
        aggregated["total_decisions"] += len(decs)
        for dec in decs:
            rap = dec.get("rapporteur")
            if rap:
                aggregated["rapporteurs_count"][rap] += 1
            pres = dec.get("president")
            if pres:
                aggregated["presidents_count"][pres] += 1

        dgraphs = item.get("decision_graphs", [])
        aggregated["total_decision_graphs"] += len(dgraphs)
        for dg in dgraphs:
            tpoints = dg.get("timeline_points", [])
            aggregated["sum_timeline_points"] += len(tpoints)
            transitions = dg.get("transitions", {})

            for tp in tpoints:
                new_tp = {
                    "index": global_index,
                    "speaker": tp.get("speaker", "#unknown"),
                    "wordcount": tp.get("wordcount", 0),
                    "paragraph_snippet": tp.get("paragraph_snippet", "")
                }
                aggregated["global_decision_graph"]["timeline_points"].append(new_tp)
                aggregated["global_decision_graph"]["all_speakers"].add(new_tp["speaker"])
                global_index += 1

            for tkey, tval in transitions.items():
                aggregated["transition_counter"][tkey] += tval

        votes_list = item.get("votes", [])
        aggregated["vote_count"] += len(votes_list)
        for vt in votes_list:
            analysis = vt.get("analysis", {})
            res = analysis.get("result", "inconnu")
            aggregated["vote_result_counter"][res] += 1

    aggregated["all_law_citations"] = sorted(list(aggregated["all_law_citations"]))
    aggregated["speakers_global_counter"] = dict(aggregated["speakers_global_counter"])
    aggregated["rapporteurs_count"] = dict(aggregated["rapporteurs_count"])
    aggregated["presidents_count"] = dict(aggregated["presidents_count"])
    aggregated["transition_counter"] = dict(aggregated["transition_counter"])
    aggregated["vote_result_counter"] = dict(aggregated["vote_result_counter"])
    aggregated["global_decision_graph"]["transitions"] = dict(aggregated["transition_counter"])
    aggregated["global_decision_graph"]["all_speakers"] = list(aggregated["global_decision_graph"]["all_speakers"])

    return aggregated

################################################
# 2) Fonctions d'affichage de modules
################################################

def display_presence_absence(module_data):
    st.header("Présence / Absence")
    all_present = module_data.get("all_present", True)
    exceptions = module_data.get("exceptions", [])
    st.write("**Tous présents ?**", all_present)
    if not all_present:
        st.write("**Exceptions :**", exceptions)

def display_votes(module_data):
    st.header("Votes")
    if not module_data:
        st.write("Aucun vote détecté.")
        return
    for i, vote in enumerate(module_data):
        with st.expander(f"Vote {i+1}"):
            st.markdown(f"**Texte** : {vote.get('text','')}")
            analysis = vote.get("analysis", {})
            st.write("**Analyse :**", analysis)

def display_global_stats(module_data):
    st.header("Statistiques globales (par fichier)")
    total_paragraphs = module_data.get("total_paragraphs", 0)
    total_words = module_data.get("total_words", 0)
    st.write(f"- **Nombre total de paragraphes** : {total_paragraphs}")
    st.write(f"- **Nombre total de mots** : {total_words}")

    global_chrono = module_data.get("global_chronology", [])
    if global_chrono:
        with st.expander("Voir la chronologie globale (FICHIER)"):
            for c in global_chrono:
                paragraph_index = c.get("paragraph_index")
                paragraph_text = c.get("paragraph_text", "")
                speakers = c.get("speakers", [])
                st.markdown(f"- **Paragraphe {paragraph_index}** : {paragraph_text[:80]}...")
                st.write(f"  Intervenant(s) : {speakers}")

    speakers_count = module_data.get("speakers_global_count", {})
    if speakers_count:
        with st.expander("Voir le décompte d'interventions par intervenant (global)"):
            st.json(speakers_count)

def display_questions(module_data):
    st.header("Questions")
    if not module_data:
        st.write("Aucune question détectée.")
        return

    for q_idx, question in enumerate(module_data):
        with st.expander(f"Question {q_idx+1}"):
            st.subheader("Statistiques de participants")
            participants_stats = question.get("participants_stats", {})
            st.json(participants_stats)

            st.subheader("Citations de lois")
            law_citations = question.get("law_citations", [])
            if law_citations:
                for law in law_citations:
                    st.write(f"- {law}")
            else:
                st.write("Aucune citation de loi.")

            st.subheader("Dates détectées dans les paragraphes")
            dates_paragraphs = question.get("dates_paragraphs", [])
            for d_p in dates_paragraphs:
                d_par = d_p.get("paragraph", "")
                d_list = d_p.get("dates", [])
                st.markdown(f"- **Paragraphe** : {d_par[:80]}...")
                st.write(f"  Dates : {d_list}")

def display_decisions(module_data):
    st.header("Décisions")
    if not module_data:
        st.write("Aucune décision détectée.")
        return
    for i, dec in enumerate(module_data):
        with st.expander(f"Décision {i+1} - {dec.get('decision_id','???')}"):
            st.write("**Rapporteur :**", dec.get("rapporteur"))
            st.write("**Président :**", dec.get("president"))
            st.write("**Membres présents :**", dec.get("members_present", []))
            wps = dec.get("words_per_speaker", {})
            st.write("**Moyenne de mots par prise de parole :**")
            st.json(wps)

def display_advanced_law_citations(module_data):
    st.header("Citations de lois avancées")
    if not module_data or not isinstance(module_data, list):
        st.write("Aucune citation de loi avancée détectée.")
        return

    formatted_citations = "\n".join([f"- **{citation.strip()}**" for citation in module_data])
    st.markdown(formatted_citations)

################################################
# 3) Graphes interactifs (Plotly + PyVis)
################################################

def merge_consecutive_timeline_points(timeline_points):
    if not timeline_points:
        return []
    merged = []
    current = timeline_points[0].copy()

    for point in timeline_points[1:]:
        if point.get("speaker") == current.get("speaker"):
            current["wordcount"] += point.get("wordcount", 0)
            snippet = point.get("paragraph_snippet", "")
            if snippet:
                current["paragraph_snippet"] += " ... " + snippet
            if point.get("has_vote") or current.get("has_vote"):
                current["has_vote"] = True
        else:
            merged.append(current)
            current = point.copy()

    merged.append(current)
    return merged

def plot_decision_timeline_interactive(
    timeline_points,
    decision_id,
    file_key="",
    president=None,
    rapporteur=None,
    secretary_general=None
):
    """
    On trace lines+markers en Plotly, 
    en plaçant president, rapporteur, secretary_general
    tout en haut de l’axe vertical (dans cet ordre), puis le reste.

    Couleurs:
      - orange si speaker == president
      - red si speaker == rapporteur
      - purple si speaker == secretary_general
      - green si has_vote
      - bleu sinon
    """
    if not timeline_points:
        st.write(f"Aucun point de timeline pour la décision {decision_id}.")
        return

    merged_points = merge_consecutive_timeline_points(timeline_points)

    # 1) Récupère tous les speakers
    all_speakers = set(pt["speaker"] for pt in merged_points)

    # 2) Construire l'ordre voulu:
    #    president (si existe), rapporteur (si existe), secretary_general (si existe), puis le reste trié
    roles_order = []
    if president and president in all_speakers:
        roles_order.append(president)
    if secretary_general and secretary_general in all_speakers and secretary_general not in roles_order:
        roles_order.append(secretary_general)
    if rapporteur and rapporteur in all_speakers and rapporteur not in roles_order:
        roles_order.append(rapporteur)

    # Le reste:
    others = sorted(s for s in all_speakers if s not in roles_order)
    final_speakers = roles_order + others

    # On attribue un index Y à chacun
    speaker_to_y = {spk: i for i, spk in enumerate(final_speakers)}

    # 3) Préparer X, Y, couleurs, etc.
    x_vals, y_vals, sizes, colors, texts = [], [], [], [], []

    # Définir la logique de couleur
    def get_color(spk, has_vote):
        if spk == president:
            return "orange"
        if spk == rapporteur:
            return "red"
        if spk == secretary_general:
            return "purple"
        if has_vote:
            return "green"
        return "blue"

    # 4) Remplir
    for i, pt in enumerate(merged_points):
        spk = pt.get("speaker", "#unknown")
        wc = pt.get("wordcount", 0)
        snippet = pt.get("paragraph_snippet", "")
        has_vote = pt.get("has_vote", False)

        x_vals.append(i)
        y_vals.append(speaker_to_y.get(spk, 0))
        size = max(4, math.sqrt(wc)*4)
        col = get_color(spk, has_vote)
        colors.append(col)
        sizes.append(size)
        preview_snip = snippet[:100].replace('\n',' ')
        texts.append(f"Speaker: {spk}<br>Mots: {wc}<br>{preview_snip}")

    # 5) Construire le Scatter Plot (lines+markers)
    import plotly.graph_objects as go
    fig = go.Figure(
        data=go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            text=texts,
            hoverinfo='text',
            line=dict(color='silver', width=1),  # ligne argentée
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.8,
                line=dict(width=1, color='DarkSlateGrey')
            )
        )
    )

    # 6) Configuration de l’axe Y (on renverse pour avoir le premier en haut)
    fig.update_layout(
        title=f"Timeline (vertical=Speaker) - {decision_id}",
        xaxis_title="Séquence des segments",
        yaxis_title="Speakers (Rôles en haut)",
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(len(final_speakers))),
            ticktext=final_speakers,
            autorange='reversed'
        ),
        height=650
    )

    st.plotly_chart(fig, use_container_width=True)
    

def plot_speaker_transition_interactive(transitions_dict, all_speakers, decision_id):
    if not transitions_dict or not all_speakers:
        st.write(f"Aucune transition pour {decision_id}.")
        return

    G = nx.DiGraph()
    for sp in all_speakers:
        G.add_node(sp)
    for key, val in transitions_dict.items():
        raw = key.strip("()")
        parts = raw.split(",")
        if len(parts) == 2:
            a, b = parts
            G.add_edge(a, b, weight=val)

    net = Network(height="600px", width="100%", directed=True)
    net.barnes_hut(
        gravity=-20000,
        central_gravity=0.3,
        spring_length=250,
        spring_strength=0.001,
        damping=0.95
    )

    for node in G.nodes():
        net.add_node(node, label=node, size=35, font={"size":24})

    for (u,v) in G.edges():
        w = G[u][v]['weight']
        width = 1 + 0.5*w
        net.add_edge(u, v, value=w, width=width)

    html_contents = net.generate_html()
    st.subheader(f"Graphe transitions {decision_id}")
    st.components.v1.html(html_contents, height=650, scrolling=True)

def display_decision_graphs_interactive(
    module_data,
    file_key="",
    president=None,
    rapporteur=None,
    secretary_general=None
):
    """
    On ajoute la possibilité de passer president/rapporteur/secretary_general
    pour le timeline plot (couleurs).
    """
    st.header("Decision Graphs (Interactif)")
    if not module_data:
        st.write("Aucun 'decision_graphs' détecté.")
        return

    for i, dec_data in enumerate(module_data):
        dec_id = dec_data.get("decision_id", f"Q{i+1}")
        with st.expander(f"Decision Graph #{i+1} - {dec_id}"):
            timeline_points = dec_data.get("timeline_points", [])
            transitions_dict = dec_data.get("transitions", {})
            all_speakers = dec_data.get("all_speakers", [])

            timeline_checkbox_key = f"timeline_{file_key}_{i}"
            transition_checkbox_key = f"transition_{file_key}_{i}"

            if st.checkbox(f"Afficher timeline (Plotly) - {dec_id}", key=timeline_checkbox_key):
                plot_decision_timeline_interactive(
                    timeline_points=timeline_points,
                    decision_id=dec_id,
                    file_key=file_key,
                    president=president,
                    rapporteur=rapporteur,
                    secretary_general=secretary_general
                )

            if st.checkbox(f"Afficher transitions (PyVis) - {dec_id}", key=transition_checkbox_key):
                plot_speaker_transition_interactive(transitions_dict, all_speakers, dec_id)

###################################
# 4) Dictionnaire de displayers
###################################
MODULE_DISPLAYERS = {
    "presence_absence": display_presence_absence,
    "votes": display_votes,
    "global_stats": display_global_stats,
    "questions": display_questions,
    "decisions": display_decisions,
    "decision_graphs": display_decision_graphs_interactive,
    "advanced_law_citations": display_advanced_law_citations
}

###################################
# 5) Main Streamlit
###################################
def main():
    st.title("Explorateur : Fichiers / Global + Graph Interactif")

    json_file_path = "extracted_data_modular_all_modules.json"
    mode = st.sidebar.radio("Mode d'affichage", ["Vue par fichier", "Vue globale"])

    if not os.path.exists(json_file_path):
        st.error(f"Fichier JSON introuvable : {json_file_path}")
        return

    all_data = load_extracted_data(json_file_path)
    if not all_data:
        st.warning("Le JSON est vide ou invalide.")
        return

    agg = aggregate_all_data(all_data)

    # ---- VUE GLOBALE ----
    if mode == "Vue globale":
        st.header("Statistiques globales")
        st.write(f"**Total Files** : {agg['total_files']}")
        st.write(f"**Total Decisions** : {agg['total_decisions']}")
        st.write(f"**Total Decision Graphs** : {agg['total_decision_graphs']}")
        st.write(f"**Total Votes** : {agg['vote_count']}")

        st.subheader("Présence Absence")
        st.write(f"files_all_present_count = {agg['files_all_present_count']}")
        st.write(f"files_not_all_present_count = {agg['files_not_all_present_count']}")
        st.write("absent_lists (extrait) :", agg['absent_lists'][:10])

        st.subheader("Lois citées (extrait)")
        st.write(agg["all_law_citations"][:10])

        st.subheader("Global Stats (paragraphs/words)")
        st.write(f"sum_total_paragraphs = {agg['sum_total_paragraphs']}")
        st.write(f"sum_total_words = {agg['sum_total_words']}")

        st.subheader("Speakers global (extrait)")
        spc = list(agg["speakers_global_counter"].items())[:10]
        st.json(dict(spc))

        st.subheader("Rapporteurs (cumulés)")
        st.json(agg["rapporteurs_count"])

        st.subheader("Présidents (cumulés)")
        st.json(agg["presidents_count"])

        st.subheader("Transitions (extrait)")
        trans_items = list(agg["transition_counter"].items())[:10]
        st.json(dict(trans_items))

        st.subheader("Votes (résultats)")
        st.json(agg["vote_result_counter"])

        # Graphes glo
        gdg = agg["global_decision_graph"]
        if st.checkbox("Afficher timeline global (Plotly)"):
            tpoints = gdg["timeline_points"]
            plot_decision_timeline_interactive(
                timeline_points=tpoints,
                decision_id="GLOBAL",
                file_key="GLOBAL"
            )
        if st.checkbox("Afficher transitions global (PyVis)"):
            transitions_dict = gdg["transitions"]
            all_sp = gdg["all_speakers"]
            plot_speaker_transition_interactive(transitions_dict, all_sp, "GLOBAL")
        return

    # ---- VUE PAR FICHIER ----
    st.header("Vue par fichier")
    file_names = [item["file"] for item in all_data if "file" in item]
    if not file_names:
        st.warning("Aucun fichier dans le JSON.")
        return

    selected_file = st.selectbox("Sélectionnez un fichier :", file_names)
    data_item = next((x for x in all_data if x.get("file") == selected_file), None)
    if not data_item:
        st.warning("Données non trouvées pour ce fichier.")
        return

    st.subheader(f"Contenu pour '{selected_file}' :")

    # Rôles extraits du module "module_roles_extraction" :
    # -> on va les passer au display_decision_graphs_interactive pour colorer
    the_president = data_item.get("president", "")
    the_rapporteur = data_item.get("rapporteur", "")
    the_secgen = data_item.get("secretary_general", "")

    # On ignore certaines clés simples
    ignore_keys = {"file", "error", "president", "rapporteur", "secretary_general"}

    for key, mod_data in data_item.items():
        if key in ignore_keys:
            continue
        display_func = MODULE_DISPLAYERS.get(key, None)
        if display_func:
            if key == "decision_graphs":
                display_decision_graphs_interactive(
                    mod_data,
                    file_key=selected_file,
                    president=the_president,
                    rapporteur=the_rapporteur,
                    secretary_general=the_secgen
                )
            else:
                display_func(mod_data)
        else:
            st.header(f"{key} (module inconnu)")
            st.json(mod_data)

    # On affiche quand même un petit rappel des rôles
    st.subheader("Rôles dans ce PV")
    st.write(f"**Président** : {the_president}")
    st.write(f"**Rapporteur** : {the_rapporteur}")
    st.write(f"**Secrétaire Général** : {the_secgen}")


if __name__ == "__main__":
    main()
