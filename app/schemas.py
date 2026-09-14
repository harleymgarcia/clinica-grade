from datetime import date, time

from pydantic import BaseModel, EmailStr


class AppointmentCreate(BaseModel):
    patient_name: str
    patient_email: EmailStr
    doctor_id: int
    date: date
    time: time
    payment_type: str = "PRIVATE"
    health_insurance_id: int | None = None
