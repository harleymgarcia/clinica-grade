let selectedTime = null;

const doctorSelect = document.getElementById("doctor");
const dateInput = document.getElementById("date");
const searchButton = document.getElementById("searchButton");
const slotsContainer = document.getElementById("slots");
const availabilitySection = document.getElementById("availabilitySection");
const selectedTimeElement = document.getElementById("selectedTime");
const messageElement = document.getElementById("message");


async function loadDoctors() {
    try {
        const response = await fetch("doctors");

        if (!response.ok) {
            throw new Error("Não foi possível carregar os médicos.");
        }

        const doctors = await response.json();

        doctorSelect.innerHTML =
            '<option value="">Selecione um médico</option>';

        doctors.forEach((doctor) => {
            const option = document.createElement("option");

            option.value = doctor.id;
            option.textContent =
                `${doctor.name} — ${doctor.specialty}`;

            doctorSelect.appendChild(option);
        });

    } catch (error) {
        showMessage(error.message, "error");
    }
}


async function loadAvailability() {
    clearMessage();

    const doctorId = doctorSelect.value;
    const date = dateInput.value;

    if (!doctorId) {
        showMessage("Selecione um médico.", "error");
        return;
    }

    if (!date) {
        showMessage("Selecione uma data.", "error");
        return;
    }

    try {
        const response = await fetch(
            `available?date=${date}&doctor_id=${doctorId}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Não foi possível consultar os horários."
            );
        }

        renderSlots(data);

    } catch (error) {
        showMessage(error.message, "error");
    }
}


function renderSlots(data) {
    slotsContainer.innerHTML = "";
    selectedTime = null;
    selectedTimeElement.textContent = "nenhum";

    availabilitySection.classList.remove("hidden");

    if (!data.available_slots.length) {
        const text = document.createElement("p");

        text.textContent =
            data.reason || "Não há horários disponíveis nesta data.";

        slotsContainer.appendChild(text);
        return;
    }

    data.available_slots.forEach((time) => {
        const button = document.createElement("button");

        button.type = "button";
        button.className = "slot";
        button.textContent = time;

        button.addEventListener("click", () => {
            document
                .querySelectorAll(".slot")
                .forEach((item) => item.classList.remove("selected"));

            button.classList.add("selected");

            selectedTime = time;
            selectedTimeElement.textContent = time;
        });

        slotsContainer.appendChild(button);
    });
}


function showMessage(text, type) {
    messageElement.textContent = text;
    messageElement.className = `message ${type}`;
}


function clearMessage() {
    messageElement.textContent = "";
    messageElement.className = "message hidden";
}


searchButton.addEventListener("click", loadAvailability);

loadDoctors();


async function scheduleAppointment() {
    clearMessage();

    const doctorId = doctorSelect.value;
    const date = dateInput.value;
    const patientName = document.getElementById("patientName").value.trim();
    const patientEmail = document.getElementById("patientEmail").value.trim();

    if (!doctorId || !date || !selectedTime) {
        showMessage(
            "Selecione médico, data e horário.",
            "error"
        );
        return;
    }

    if (!patientName || !patientEmail) {
        showMessage(
            "Informe o nome e o e-mail do paciente.",
            "error"
        );
        return;
    }

    try {
        const response = await fetch("appointments", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                patient_name: patientName,
                patient_email: patientEmail,
                doctor_id: Number(doctorId),
                date: date,
                time: selectedTime,
                payment_type: "PRIVATE"
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Não foi possível realizar o agendamento."
            );
        }

        const confirmedTime = selectedTime;
        const doctorText =
            doctorSelect.options[doctorSelect.selectedIndex].text;
        const formattedDate =
            date.split("-").reverse().join("/");

        document.getElementById("patientName").value = "";
        document.getElementById("patientEmail").value = "";

        doctorSelect.value = "";
        dateInput.value = "";

        selectedTime = null;
        selectedTimeElement.textContent = "nenhum";

        slotsContainer.innerHTML = "";
        availabilitySection.classList.add("hidden");

        showMessage(
            `✓ Consulta agendada com sucesso! ${doctorText} — ${formattedDate} às ${confirmedTime}.`,
            "success"
        );

    } catch (error) {
        showMessage(error.message, "error");
    }
}


document
    .getElementById("scheduleButton")
    .addEventListener("click", scheduleAppointment);


function updateDateTime() {
    const element = document.getElementById("dateTime");

    if (!element) return;

    const now = new Date();

    const formatted = new Intl.DateTimeFormat(
        "pt-BR",
        {
            timeZone: "America/Sao_Paulo",
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    ).format(now);

    element.textContent = formatted;
}

updateDateTime();
setInterval(updateDateTime, 30000);
