from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from psycopg.types.json import Json

from app.db import get_connection


class PartCreate(BaseModel):
    part_code: str
    job_code: str
    status_code: str
    location_code: str | None = None
    created_by_email: str
    notes: str | None = None


class PartEventCreate(BaseModel):
    event_type: str
    to_status_code: str | None = None
    to_location_code: str | None = None
    workstation_code: str | None = None
    user_email: str
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssemblyCreate(BaseModel):
    assembly_code: str
    job_code: str
    status_code: str
    location_code: str | None = None
    created_by_email: str
    part_codes: list[str]
    notes: str | None = None


def _fetch_one(cur, sql: str, params: tuple[Any, ...], error_message: str):
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=error_message)
    return row


def _resolve_status(cur, code: str):
    return _fetch_one(
        cur,
        "select id, code from statuses where code = %s",
        (code,),
        f"Unknown status: {code}",
    )


def _resolve_location(cur, code: str):
    return _fetch_one(
        cur,
        "select id, location_code from locations where location_code = %s",
        (code,),
        f"Unknown location: {code}",
    )


def _resolve_user(cur, email: str):
    return _fetch_one(
        cur,
        "select id, email from users where email = %s",
        (email,),
        f"Unknown user: {email}",
    )


def _resolve_job(cur, job_code: str):
    return _fetch_one(
        cur,
        "select id, job_code from jobs where job_code = %s",
        (job_code,),
        f"Unknown job: {job_code}",
    )


def _resolve_part(cur, part_code: str):
    return _fetch_one(
        cur,
        """
        select p.id, p.part_code, s.code as status_code, l.location_code
        from parts p
        join statuses s on s.id = p.status_id
        left join locations l on l.id = p.current_location_id
        where p.part_code = %s
        """,
        (part_code,),
        f"Unknown part: {part_code}",
    )


def _serialize_part(cur, part_id: int):
    cur.execute(
        """
        select
            p.part_code,
            j.job_code,
            s.code as status_code,
            l.location_code,
            p.notes,
            p.created_at,
            p.updated_at
        from parts p
        join jobs j on j.id = p.job_id
        join statuses s on s.id = p.status_id
        left join locations l on l.id = p.current_location_id
        where p.id = %s
        """,
        (part_id,),
    )
    row = cur.fetchone()
    return {
        "part_code": row["part_code"],
        "job_code": row["job_code"],
        "status_code": row["status_code"],
        "location_code": row["location_code"],
        "notes": row["notes"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Stremet Tracker API")

    @app.get("/health")
    def healthcheck():
        return {"ok": True}

    @app.post("/parts", status_code=201)
    def create_part(payload: PartCreate):
        with get_connection() as conn, conn.cursor() as cur:
            job = _resolve_job(cur, payload.job_code)
            status = _resolve_status(cur, payload.status_code)
            user = _resolve_user(cur, payload.created_by_email)
            location_id = None
            if payload.location_code:
                location = _resolve_location(cur, payload.location_code)
                location_id = location["id"]

            cur.execute(
                "select 1 from parts where part_code = %s",
                (payload.part_code,),
            )
            if cur.fetchone() is not None:
                raise HTTPException(
                    status_code=409, detail=f"Part already exists: {payload.part_code}"
                )

            cur.execute(
                """
                insert into parts (part_code, job_id, status_id, current_location_id, notes, created_by, updated_by)
                values (%s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    payload.part_code,
                    job["id"],
                    status["id"],
                    location_id,
                    payload.notes,
                    user["id"],
                    user["id"],
                ),
            )
            part_id = cur.fetchone()["id"]
            conn.commit()
            return _serialize_part(cur, part_id)

    @app.post("/parts/{part_code}/events", status_code=201)
    def create_part_event(part_code: str, payload: PartEventCreate):
        with get_connection() as conn, conn.cursor() as cur:
            part = _resolve_part(cur, part_code)
            user = _resolve_user(cur, payload.user_email)

            status = None
            location = None
            workstation = None
            if payload.to_status_code:
                status = _resolve_status(cur, payload.to_status_code)
            if payload.to_location_code:
                location = _resolve_location(cur, payload.to_location_code)
            if payload.workstation_code:
                workstation = _fetch_one(
                    cur,
                    "select id, workstation_code from workstations where workstation_code = %s",
                    (payload.workstation_code,),
                    f"Unknown workstation: {payload.workstation_code}",
                )

            cur.execute(
                """
                insert into part_events (
                    part_id,
                    event_type,
                    from_status_id,
                    to_status_id,
                    from_location_id,
                    to_location_id,
                    workstation_id,
                    user_id,
                    notes,
                    metadata
                )
                values (
                    %s,
                    %s,
                    (select id from statuses where code = %s),
                    %s,
                    (select id from locations where location_code = %s),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    part["id"],
                    payload.event_type,
                    part["status_code"],
                    status["id"] if status else None,
                    part["location_code"],
                    location["id"] if location else None,
                    workstation["id"] if workstation else None,
                    user["id"],
                    payload.notes,
                    Json(payload.metadata),
                ),
            )

            cur.execute(
                """
                update parts
                set status_id = coalesce(%s, status_id),
                    current_location_id = coalesce(%s, current_location_id),
                    updated_by = %s,
                    updated_at = now()
                where id = %s
                """,
                (
                    status["id"] if status else None,
                    location["id"] if location else None,
                    user["id"],
                    part["id"],
                ),
            )
            conn.commit()
            updated = _serialize_part(cur, part["id"])
            return {
                "part_code": updated["part_code"],
                "current_status_code": updated["status_code"],
                "current_location_code": updated["location_code"],
            }

    @app.post("/assemblies", status_code=201)
    def create_assembly(payload: AssemblyCreate):
        if not payload.part_codes:
            raise HTTPException(status_code=422, detail="part_codes must not be empty")

        with get_connection() as conn, conn.cursor() as cur:
            job = _resolve_job(cur, payload.job_code)
            status = _resolve_status(cur, payload.status_code)
            user = _resolve_user(cur, payload.created_by_email)
            location_id = None
            if payload.location_code:
                location = _resolve_location(cur, payload.location_code)
                location_id = location["id"]

            cur.execute(
                "select 1 from assemblies where assembly_code = %s",
                (payload.assembly_code,),
            )
            if cur.fetchone() is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Assembly already exists: {payload.assembly_code}",
                )

            part_ids = []
            for code in payload.part_codes:
                part = _resolve_part(cur, code)
                part_ids.append((code, part["id"]))

            cur.execute(
                """
                insert into assemblies (assembly_code, job_id, status_id, current_location_id, notes, created_by, updated_by)
                values (%s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    payload.assembly_code,
                    job["id"],
                    status["id"],
                    location_id,
                    payload.notes,
                    user["id"],
                    user["id"],
                ),
            )
            assembly_id = cur.fetchone()["id"]
            for _, part_id in part_ids:
                cur.execute(
                    "insert into assembly_parts (assembly_id, part_id, qty_used) values (%s, %s, 1)",
                    (assembly_id, part_id),
                )
            conn.commit()
            return {
                "assembly_code": payload.assembly_code,
                "job_code": payload.job_code,
                "status_code": payload.status_code,
                "location_code": payload.location_code,
                "part_codes": payload.part_codes,
            }

    @app.post("/demo/seed", status_code=201)
    def seed_demo_data():
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "insert into customers (customer_code, name) values (%s, %s) returning id",
                ("DEMO-CUST-01", "Demo Industrial Customer"),
            )
            customer_id = cur.fetchone()["id"]
            cur.execute(
                """
                insert into jobs (job_code, customer_id, drawing_code, description)
                values (%s, %s, %s, %s)
                returning id
                """,
                (
                    "DEMO-JOB-100",
                    customer_id,
                    "DWG-BRACKET-XL",
                    "Large enclosure bracket",
                ),
            )
            job_id = cur.fetchone()["id"]
            cur.execute(
                """
                insert into users (email, full_name, role)
                values
                    (%s, %s, %s),
                    (%s, %s, %s)
                returning id, email
                """,
                (
                    "operator.alpha@stremet.demo",
                    "Operator Alpha",
                    "operator",
                    "lead.beta@stremet.demo",
                    "Lead Beta",
                    "supervisor",
                ),
            )
            users = cur.fetchall()
            user_by_email = {row["email"]: row["id"] for row in users}
            created_status = _resolve_status(cur, "created")
            in_process_status = _resolve_status(cur, "in_process")
            assembled_status = _resolve_status(cur, "assembled")
            raw = _resolve_location(cur, "ZONE_RAW")
            bend = _resolve_location(cur, "WS_BEND_01")
            assembly = _resolve_location(cur, "ZONE_ASSEMBLY")
            pack = _resolve_location(cur, "ZONE_PACK")

            demo_parts = [
                (
                    "DEMO-PART-001",
                    created_status["id"],
                    raw["id"],
                    "Freshly cut side panel",
                ),
                (
                    "DEMO-PART-002",
                    in_process_status["id"],
                    bend["id"],
                    "Bending in progress",
                ),
                (
                    "DEMO-PART-003",
                    created_status["id"],
                    raw["id"],
                    "Back plate waiting for weld",
                ),
                (
                    "DEMO-PART-004",
                    created_status["id"],
                    raw["id"],
                    "Mounting bracket ready for assembly",
                ),
            ]
            inserted_part_ids = []
            for part_code, status_id, location_id, notes in demo_parts:
                cur.execute(
                    """
                    insert into parts (part_code, job_id, status_id, current_location_id, notes, created_by, updated_by)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        part_code,
                        job_id,
                        status_id,
                        location_id,
                        notes,
                        user_by_email["operator.alpha@stremet.demo"],
                        user_by_email["operator.alpha@stremet.demo"],
                    ),
                )
                inserted_part_ids.append((part_code, cur.fetchone()["id"]))

            cur.execute(
                """
                insert into part_events (
                    part_id, event_type, from_status_id, to_status_id,
                    from_location_id, to_location_id, workstation_id, user_id, notes, metadata
                ) values (
                    %s,
                    'moved',
                    %s,
                    %s,
                    %s,
                    %s,
                    (select id from workstations where workstation_code = 'BEND_01'),
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    inserted_part_ids[1][1],
                    created_status["id"],
                    in_process_status["id"],
                    raw["id"],
                    bend["id"],
                    user_by_email["operator.alpha@stremet.demo"],
                    "Operator scanned part into bending",
                    Json({"scan_source": "barcode", "station": "BEND_01"}),
                ),
            )

            cur.execute(
                """
                insert into assemblies (assembly_code, job_id, status_id, current_location_id, notes, created_by, updated_by)
                values (%s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    "DEMO-ASM-001",
                    job_id,
                    assembled_status["id"],
                    assembly["id"],
                    "Partial frame assembly ready for packaging",
                    user_by_email["lead.beta@stremet.demo"],
                    user_by_email["lead.beta@stremet.demo"],
                ),
            )
            assembly_id = cur.fetchone()["id"]
            for _, part_id in inserted_part_ids[:3]:
                cur.execute(
                    "insert into assembly_parts (assembly_id, part_id, qty_used) values (%s, %s, 1)",
                    (assembly_id, part_id),
                )

            cur.execute(
                "update assemblies set current_location_id = %s, updated_at = now() where id = %s",
                (pack["id"], assembly_id),
            )

            conn.commit()
            return {
                "parts_created": len(demo_parts),
                "assemblies_created": 1,
                "job_code": "DEMO-JOB-100",
                "assembly_code": "DEMO-ASM-001",
            }

    return app


app = create_app()
