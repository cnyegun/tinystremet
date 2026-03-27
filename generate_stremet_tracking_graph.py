from graphviz import Digraph


def table_label(title, rows, header_color="#1f4b99"):
    body = "".join(
        f'<TR><TD ALIGN="LEFT" BALIGN="LEFT">{row}</TD></TR>' for row in rows
    )
    return f'''<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6">
    <TR><TD BGCOLOR="{header_color}"><FONT COLOR="white"><B>{title}</B></FONT></TD></TR>
    {body}
    </TABLE>>'''


def build_full_erd():
    dot = Digraph("stremet_tracking")
    dot.attr(rankdir="LR", splines="ortho", pad="0.3", nodesep="0.55", ranksep="1.0")
    dot.attr("graph", bgcolor="#f7f7f5")
    dot.attr("node", shape="plain", fontname="Helvetica")
    dot.attr(
        "edge", color="#555555", arrowsize="0.8", penwidth="1.2", fontname="Helvetica"
    )

    dot.node(
        "customers",
        table_label("customers", ["id (PK)", "customer_code", "name"], "#0f766e"),
    )
    dot.node(
        "jobs",
        table_label(
            "jobs",
            ["id (PK)", "job_code", "customer_id (FK)", "drawing_code", "description"],
            "#0f766e",
        ),
    )
    dot.node(
        "statuses",
        table_label("statuses", ["id (PK)", "code", "name"], "#7c3aed"),
    )
    dot.node(
        "locations",
        table_label(
            "locations",
            ["id (PK)", "name", "type", "parent_location_id (FK)"],
            "#7c3aed",
        ),
    )
    dot.node(
        "users",
        table_label("users", ["id (PK)", "name", "role"], "#7c3aed"),
    )
    dot.node(
        "workstations",
        table_label(
            "workstations",
            ["id (PK)", "code", "name", "location_id (FK)", "process_step"],
            "#7c3aed",
        ),
    )
    dot.node(
        "parts",
        table_label(
            "parts",
            [
                "id (PK)",
                "part_code (UNIQUE)",
                "job_id (FK)",
                "status_id (FK)",
                "current_location_id (FK)",
                "quantity",
                "created_at",
                "updated_at",
            ],
            "#b45309",
        ),
    )
    dot.node(
        "part_events",
        table_label(
            "part_events",
            [
                "id (PK)",
                "part_id (FK)",
                "event_type",
                "from_status_id (FK)",
                "to_status_id (FK)",
                "from_location_id (FK)",
                "to_location_id (FK)",
                "workstation_id (FK)",
                "user_id (FK)",
                "event_time",
                "notes",
            ],
            "#b45309",
        ),
    )
    dot.node(
        "assemblies",
        table_label(
            "assemblies",
            [
                "id (PK)",
                "assembly_code (UNIQUE)",
                "job_id (FK)",
                "status_id (FK)",
                "current_location_id (FK)",
                "created_at",
            ],
            "#b45309",
        ),
    )
    dot.node(
        "assembly_parts",
        table_label(
            "assembly_parts",
            ["id (PK)", "assembly_id (FK)", "part_id (FK)", "qty_used"],
            "#b45309",
        ),
    )

    dot.edge("customers", "jobs", label="1 to many")
    dot.edge("jobs", "parts", label="1 to many")
    dot.edge("jobs", "assemblies", label="1 to many")
    dot.edge("statuses", "parts", label="1 to many")
    dot.edge("locations", "parts", label="1 to many")
    dot.edge("locations", "assemblies", label="1 to many")
    dot.edge("statuses", "assemblies", label="1 to many")
    dot.edge("parts", "part_events", label="1 to many")
    dot.edge("users", "part_events", label="1 to many")
    dot.edge("workstations", "part_events", label="1 to many")
    dot.edge("locations", "workstations", label="1 to many")
    dot.edge("assemblies", "assembly_parts", label="1 to many")
    dot.edge("parts", "assembly_parts", label="1 to many")
    dot.edge("locations", "locations", label="parent / child", color="#888888")
    return dot


def build_pitch_diagram():
    dot = Digraph("stremet_tracking_pitch")
    dot.attr(rankdir="LR", splines="polyline", pad="0.35", nodesep="0.8", ranksep="1.1")
    dot.attr("graph", bgcolor="#f7f7f5")
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Helvetica",
        margin="0.18,0.12",
    )
    dot.attr(
        "edge", color="#4b5563", arrowsize="0.8", penwidth="1.5", fontname="Helvetica"
    )

    dot.node("job", "ERP Job\ncustomer + drawing", fillcolor="#d1fae5", color="#059669")
    dot.node(
        "part",
        "Tracked Part\none sheet-metal piece",
        fillcolor="#fde68a",
        color="#b45309",
    )
    dot.node(
        "event",
        "Tracking Events\nscan, move, process, pack",
        fillcolor="#fee2e2",
        color="#dc2626",
    )
    dot.node(
        "location",
        "Locations\nstorage, machine, packaging",
        fillcolor="#e9d5ff",
        color="#7c3aed",
    )
    dot.node(
        "assembly",
        "Final Product / Assembly\nmade from 1..many parts",
        fillcolor="#bfdbfe",
        color="#2563eb",
    )

    dot.edge("job", "part", label="creates parts")
    dot.edge("part", "event", label="produces history")
    dot.edge("event", "location", label="updates state")
    dot.edge("part", "assembly", label="many parts can join")
    dot.edge("location", "part", label="current location", dir="both")
    return dot


build_full_erd().render("stremet_tracking_erd", format="svg", cleanup=True)
build_full_erd().render("stremet_tracking_erd", format="png", cleanup=True)
build_pitch_diagram().render("stremet_tracking_pitch", format="svg", cleanup=True)
build_pitch_diagram().render("stremet_tracking_pitch", format="png", cleanup=True)
print("Generated ERD and pitch diagrams as SVG and PNG")
