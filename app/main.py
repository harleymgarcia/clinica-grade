from datetime import date, time

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.errors import UniqueViolation

from app.database import get_connection
from app.services.holidays import is_holiday
from app.schemas import AppointmentCreate


app = FastAPI(
    title="Clinic Scheduler API",
    version="0.1.0",
)

app.mount(
    "/static",
    StaticFiles(directory="/opt/clinica_garde/app/static"),
    name="static",
)


@app.get("/")
def home():
    return FileResponse("/opt/clinica_garde/app/static/index.html")


AVAILABLE_SLOTS = [
    "08:00",
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
]

MORNING_SLOTS = {
    "08:00",
    "09:00",
    "10:00",
    "11:00",
    "12:00",
}

AFTERNOON_SLOTS = {
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
}


@app.get("/health")
def health():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database();")
            database = cur.fetchone()[0]

    return {
        "status": "ok",
        "database": database,
    }


@app.get("/available")
def available(
    date_value: date = Query(..., alias="date"),
    doctor_id: int | None = None,
):
    # Final de semana
    if date_value.weekday() >= 5:
        return {
            "date": date_value,
            "doctor_id": doctor_id,
            "available_slots": [],
            "reason": "Não realizamos agendamentos aos finais de semana.",
        }

    # Feriado
    try:
        holiday = is_holiday(date_value)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="O serviço de consulta de feriados está temporariamente indisponível.",
        ) from exc

    if holiday:
        return {
            "date": date_value,
            "doctor_id": doctor_id,
            "available_slots": [],
            "reason": "Não realizamos agendamentos em feriados.",
        }

    slots = AVAILABLE_SLOTS.copy()
    occupied_slots = set()

    with get_connection() as conn:
        with conn.cursor() as cur:

            if doctor_id is not None:
                # Confirma que o médico existe e está ativo
                cur.execute(
                    """
                    SELECT id, daily_limit
                    FROM doctors
                    WHERE id = %s
                      AND active = TRUE
                    """,
                    (doctor_id,),
                )

                doctor = cur.fetchone()

                if doctor is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Médico não encontrado ou inativo.",
                    )

                daily_limit = doctor[1]

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM appointments
                    WHERE doctor_id = %s
                      AND appointment_date = %s
                      AND status = 'SCHEDULED'
                    """,
                    (doctor_id, date_value),
                )

                scheduled_count = cur.fetchone()[0]

                if scheduled_count >= daily_limit:
                    return {
                        "date": date_value,
                        "doctor_id": doctor_id,
                        "available_slots": [],
                        "reason": "O médico atingiu o limite de consultas para esta data.",
                    }

                # Procura exceção de disponibilidade para aquela data
                cur.execute(
                    """
                    SELECT
                        morning_available,
                        afternoon_available
                    FROM doctor_availability
                    WHERE doctor_id = %s
                      AND date = %s
                    """,
                    (doctor_id, date_value),
                )

                availability = cur.fetchone()

                # Sem registro = disponível nos dois turnos
                morning_available = True
                afternoon_available = True

                if availability is not None:
                    morning_available = availability[0]
                    afternoon_available = availability[1]

                if not morning_available:
                    slots = [
                        slot
                        for slot in slots
                        if slot not in MORNING_SLOTS
                    ]

                if not afternoon_available:
                    slots = [
                        slot
                        for slot in slots
                        if slot not in AFTERNOON_SLOTS
                    ]

                cur.execute(
                    """
                    SELECT appointment_time
                    FROM appointments
                    WHERE appointment_date = %s
                      AND doctor_id = %s
                      AND status = 'SCHEDULED'
                    """,
                    (date_value, doctor_id),
                )

            else:
                cur.execute(
                    """
                    SELECT appointment_time
                    FROM appointments
                    WHERE appointment_date = %s
                      AND status = 'SCHEDULED'
                    """,
                    (date_value,),
                )

            for row in cur.fetchall():
                appointment_time = row[0]

                if isinstance(appointment_time, time):
                    occupied_slots.add(
                        appointment_time.strftime("%H:%M")
                    )

    available_slots = [
        slot
        for slot in slots
        if slot not in occupied_slots
    ]

    return {
        "date": date_value,
        "doctor_id": doctor_id,
        "available_slots": available_slots,
    }




@app.post("/appointments", status_code=201)
def create_appointment(data: AppointmentCreate):
    date_value = data.date
    time_value = data.time
    slot = time_value.strftime("%H:%M")

    # Horário válido
    if slot not in AVAILABLE_SLOTS:
        raise HTTPException(
            status_code=400,
            detail="O horário da consulta deve estar entre 08:00 e 17:00.",
        )

    # Final de semana
    if date_value.weekday() >= 5:
        raise HTTPException(
            status_code=400,
            detail="Não realizamos agendamentos aos finais de semana.",
        )

    # Feriado
    try:
        if is_holiday(date_value):
            raise HTTPException(
                status_code=400,
                detail="Não realizamos agendamentos em feriados.",
            )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="O serviço de consulta de feriados está temporariamente indisponível.",
        ) from exc

    if data.payment_type not in {"PRIVATE", "INSURANCE"}:
        raise HTTPException(
            status_code=400,
            detail="O tipo de atendimento deve ser particular ou convênio.",
        )

    if data.payment_type == "INSURANCE" and data.health_insurance_id is None:
        raise HTTPException(
            status_code=400,
            detail="Informe o convênio para este agendamento.",
        )

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Localiza ou cadastra o paciente
            patient_name = data.patient_name.strip()
            patient_email = str(data.patient_email).strip().lower()

            if not patient_name:
                raise HTTPException(
                    status_code=400,
                    detail="Informe o nome do paciente.",
                )

            cur.execute(
                """
                SELECT id
                FROM patients
                WHERE LOWER(email) = %s
                ORDER BY id
                LIMIT 1
                """,
                (patient_email,),
            )

            patient = cur.fetchone()

            if patient is None:
                cur.execute(
                    """
                    INSERT INTO patients (name, email)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (patient_name, patient_email),
                )
                patient_id = cur.fetchone()[0]
            else:
                patient_id = patient[0]

            # Impede mais de uma consulta ativa do mesmo paciente
            # com o mesmo médico na mesma data
            cur.execute(
                """
                SELECT id
                FROM appointments
                WHERE patient_id = %s
                  AND doctor_id = %s
                  AND appointment_date = %s
                  AND status = 'SCHEDULED'
                LIMIT 1
                """,
                (patient_id, data.doctor_id, date_value),
            )

            if cur.fetchone() is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Você já possui uma consulta agendada com este médico nesta data.",
                )

            # Médico + limite diário
            cur.execute(
                """
                SELECT id, daily_limit
                FROM doctors
                WHERE id = %s
                  AND active = TRUE
                """,
                (data.doctor_id,),
            )

            doctor = cur.fetchone()

            if doctor is None:
                raise HTTPException(
                    status_code=404,
                    detail="Médico não encontrado ou inativo.",
                )

            daily_limit = doctor[1]

            # Convênio
            if data.health_insurance_id is not None:
                cur.execute(
                    """
                    SELECT id
                    FROM health_insurances
                    WHERE id = %s
                      AND active = TRUE
                    """,
                    (data.health_insurance_id,),
                )

                if cur.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Convênio não encontrado ou inativo.",
                    )

            # Turnos
            cur.execute(
                """
                SELECT morning_available, afternoon_available
                FROM doctor_availability
                WHERE doctor_id = %s
                  AND date = %s
                """,
                (data.doctor_id, date_value),
            )

            availability = cur.fetchone()

            morning_available = True
            afternoon_available = True

            if availability is not None:
                morning_available = availability[0]
                afternoon_available = availability[1]

            if slot in MORNING_SLOTS and not morning_available:
                raise HTTPException(
                    status_code=409,
                    detail="O médico não está disponível no período da manhã.",
                )

            if slot in AFTERNOON_SLOTS and not afternoon_available:
                raise HTTPException(
                    status_code=409,
                    detail="O médico não está disponível no período da tarde.",
                )

            # Limite diário
            cur.execute(
                """
                SELECT COUNT(*)
                FROM appointments
                WHERE doctor_id = %s
                  AND appointment_date = %s
                  AND status = 'SCHEDULED'
                """,
                (data.doctor_id, date_value),
            )

            scheduled_count = cur.fetchone()[0]

            if scheduled_count >= daily_limit:
                raise HTTPException(
                    status_code=409,
                    detail="O médico atingiu o limite de consultas para esta data.",
                )

            # Gravação
            try:
                cur.execute(
                    """
                    INSERT INTO appointments (
                        patient_id,
                        doctor_id,
                        health_insurance_id,
                        payment_type,
                        appointment_date,
                        appointment_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        patient_id,
                        data.doctor_id,
                        data.health_insurance_id,
                        data.payment_type,
                        date_value,
                        time_value,
                    ),
                )

                appointment_id = cur.fetchone()[0]
                conn.commit()

            except UniqueViolation as exc:
                conn.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Este horário não está mais disponível.",
                ) from exc

    return {
        "id": appointment_id,
        "message": "Consulta agendada com sucesso.",
        "patient_id": patient_id,
        "doctor_id": data.doctor_id,
        "date": date_value,
        "time": slot,
        "payment_type": data.payment_type,
    }


@app.get("/appointments")
def list_appointments():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    p.name,
                    p.email,
                    d.id,
                    d.name,
                    d.specialty,
                    a.appointment_date,
                    a.appointment_time,
                    a.payment_type,
                    a.status
                FROM appointments a
                JOIN patients p
                  ON p.id = a.patient_id
                JOIN doctors d
                  ON d.id = a.doctor_id
                ORDER BY
                    a.appointment_date,
                    a.appointment_time
                """
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "patient_name": row[1],
            "patient_email": row[2],
            "doctor_id": row[3],
            "doctor_name": row[4],
            "specialty": row[5],
            "date": row[6],
            "time": row[7].strftime("%H:%M"),
            "payment_type": row[8],
            "status": row[9],
        }
        for row in rows
    ]


@app.get("/doctors")
def list_doctors():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, specialty, daily_limit
                FROM doctors
                WHERE active = TRUE
                ORDER BY name
                """
            )
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "specialty": row[2],
            "daily_limit": row[3],
        }
        for row in rows
    ]
