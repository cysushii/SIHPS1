import networkx as nx
from sqlalchemy.orm import Session
from models.models import Student, FlaggedRecord

def analyze_graph_fraud(db: Session) -> list[dict]:
    """
    Graph Fraud Engine using NetworkX:
    - Nodes = students (std_ID), institutes (inst_ID), addresses (addr_ADDR)
    - Edges = 'enrolled_at' (student -> institute) and 'shares_address_with' (student -> address)
    - Uses nx.connected_components to find connected clusters.
    - Flags any cluster where 3+ distinct students (different apaar_ids) share the same
      address AND are enrolled at the same institute.
      Severity: 'needs_review' (Sybil / fraud ring signal).
    """
    students = db.query(Student).all()
    if not students:
        return []

    G = nx.Graph()

    for s in students:
        s_node = f"student_{s.id}"
        inst_node = f"institute_{s.institute_id}"

        G.add_node(s_node, node_type="student", id=s.id, apaar_id=s.apaar_id, name=s.name)
        G.add_node(inst_node, node_type="institute", id=s.institute_id)
        G.add_edge(s_node, inst_node, relation="enrolled_at")

        if s.address and s.address.strip():
            clean_addr = s.address.strip().lower()
            addr_node = f"address_{clean_addr}"
            G.add_node(addr_node, node_type="address", address=clean_addr)
            G.add_edge(s_node, addr_node, relation="shares_address_with")

    flagged_clusters = []

    # Find connected components
    for comp in nx.connected_components(G):
        subgraph = G.subgraph(comp)
        
        # Collect students in this component
        comp_students = [
            node for node, data in subgraph.nodes(data=True)
            if data.get("node_type") == "student"
        ]
        
        # If less than 3 students, skip
        if len(comp_students) < 3:
            continue

        # Group by (institute_id, address)
        # Check if 3+ students have the exact same address and institute
        inst_addr_groups = {}
        for s_node in comp_students:
            s_data = subgraph.nodes[s_node]
            s_id = s_data["id"]
            
            # Find institute neighbor
            inst_neighbors = [
                n for n in subgraph.neighbors(s_node)
                if subgraph.nodes[n].get("node_type") == "institute"
            ]
            # Find address neighbors
            addr_neighbors = [
                n for n in subgraph.neighbors(s_node)
                if subgraph.nodes[n].get("node_type") == "address"
            ]

            if inst_neighbors and addr_neighbors:
                inst_id = subgraph.nodes[inst_neighbors[0]]["id"]
                addr_val = subgraph.nodes[addr_neighbors[0]]["address"]
                key = (inst_id, addr_val)
                if key not in inst_addr_groups:
                    inst_addr_groups[key] = []
                inst_addr_groups[key].append(s_data)

        # Evaluate groups
        for (inst_id, addr_val), group in inst_addr_groups.items():
            unique_apaars = set(s["apaar_id"] for s in group)
            if len(unique_apaars) >= 3:
                student_ids = [s["id"] for s in group]
                cluster_key = f"cluster_inst_{inst_id}_addr_{addr_val}"
                reason = (
                    f"Sybil fraud ring alert: {len(unique_apaars)} distinct APAAR IDs "
                    f"share the same physical address ('{addr_val}') at Institute ID {inst_id}."
                )

                # Avoid duplicate flags
                existing = db.query(FlaggedRecord).filter(
                    FlaggedRecord.record_type == "Cluster",
                    FlaggedRecord.record_id == cluster_key,
                    FlaggedRecord.status == "open"
                ).first()

                if not existing:
                    flag = FlaggedRecord(
                        record_type="Cluster",
                        record_id=cluster_key,
                        flag_reason=reason,
                        severity="needs_review",
                        status="open"
                    )
                    db.add(flag)

                flagged_clusters.append({
                    "institute_id": inst_id,
                    "address": addr_val,
                    "student_count": len(unique_apaars),
                    "student_ids": student_ids,
                    "apaar_ids": list(unique_apaars),
                    "reason": reason,
                    "severity": "needs_review",
                })

    if flagged_clusters:
        db.commit()

    return flagged_clusters

