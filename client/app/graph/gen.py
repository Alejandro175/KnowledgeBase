import os
import networkx as nx
import matplotlib.pyplot as plt

def generate_graph_image(context_data, output_path='tmp-img/graph.png'):
    """
    Genera un'immagine del grafo dalle triple RDF

    Args:
        context_data: Lista di dict con 'subject', 'predicate', 'object'
                     dove subject e object hanno campi 'uri' e 'confidence'
        output_path: Percorso dove salvare l'immagine

    Returns:
        str: Percorso del file salvato
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    G = nx.DiGraph()
    node_confidences = {}
    subjects = set()
    objects = set()

    if context_data:
        for triple in context_data:
            subject_data = triple.get('subject')
            predicate = triple.get('predicate')
            object_data = triple.get('object')

            subject_uri = subject_data.get('uri')
            subject_conf = subject_data.get('confidence')
            object_uri = object_data.get('uri')
            object_conf = object_data.get('confidence')

            clear_subject = str(subject_uri.split("/")[-1])
            clear_object = str(object_uri.split("/")[-1])

            subjects.add(clear_subject)
            objects.add(clear_object)

            node_confidences[clear_subject] = subject_conf
            node_confidences[clear_object] = object_conf

            G.add_edge(clear_subject, clear_object, label=predicate)

        num_nodes = len(list(G.nodes()))
        base_height = 12
        fig_height = base_height + 0.25 * num_nodes
        fig_width = fig_height * 1.2
        plt.figure(figsize=(fig_width, fig_height))
        k_val = num_nodes/2

        pos = nx.fruchterman_reingold_layout(G, k=k_val, iterations=100)

        for node in objects:
            confidence = node_confidences.get(node)

            if confidence is None:
                nx.draw_networkx_nodes(
                    G, pos, nodelist=[node],
                    node_color='lightblue', node_size=3000,
                    alpha=1, linewidths=3
                )
            else:
                alpha = 0.2 + (confidence - 0.5) * (1 - 0.2) / (1 - 0.5)
                nx.draw_networkx_nodes(
                    G, pos, nodelist=[node],
                    node_color='blue', node_size=3000,
                    alpha=alpha, linewidths=1
                )

        for node in subjects:
            confidence = node_confidences.get(node)

            if confidence is None:
                nx.draw_networkx_nodes(
                    G, pos, nodelist=[node],
                    node_color='#FFD580', node_size=3000,
                    alpha=1, edgecolors='orange', linewidths=3
                )
            else:
                alpha = 0.2 + (confidence - 0.5) * (1 - 0.2) / (1 - 0.5)
                nx.draw_networkx_nodes(
                    G, pos, nodelist=[node],
                    node_color='red', node_size=3000,
                    alpha=alpha, linewidths=1
                )

        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, width=2, alpha=0.6)

        # Nodes labels
        nx.draw_networkx_labels(G, pos, font_size=16, font_weight='bold')

        # Edges labels
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=12, font_weight='bold')

    plt.margins(0.2)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=400, bbox_inches='tight', format='png')
    plt.close()

    return output_path


if __name__ == "__main__":
    # Esempio con i tuoi dati
    json_data = {
        "context": [
            {
                "subject": {
                    "uri": "http://www.semanticweb.org/mwonto/scanbox",
                    "confidence": 0.9930236339569092
                },
                "predicate": "isIndicatedByFile",
                "object": {
                    "uri": "malicious-javascript-file",
                    "confidence": 0.60
                }
            },
            {
                "subject": {
                    "uri": "scanbox",
                    "confidence": 0.9930236339569092
                },
                "predicate": "mentionedIn",
                "object": {
                    "uri": "alienvault-scanbox-report-2024.pdf",
                    "confidence": None
                }
            },
            {
                "subject": {
                    "uri": "scanbox",
                    "confidence": 0.9930236339569092
                },
                "predicate": "targets",
                "object": {
                    "uri": "sensitive-data",
                    "confidence": 0.9555
                }
            }

        ]
    }

    # Genera immagine
    output_file = generate_graph_image(json_data['context'], 'tmp-img/graph.png')
    print(f"Grafo salvato in: {output_file}")