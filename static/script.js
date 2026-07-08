const state = {
    persons: [],
    editingPerson: null,
    cameraStream: null,
    matchTimer: null,
    isMatching: false,
};

const elements = {
    form: document.getElementById("personForm"),
    personId: document.getElementById("personId"),
    name: document.getElementById("name"),
    age: document.getElementById("age"),
    lastSeenLocation: document.getElementById("last_seen_location"),
    lastSeenDate: document.getElementById("last_seen_date"),
    contactInfo: document.getElementById("contact_info"),
    status: document.getElementById("status"),
    notes: document.getElementById("notes"),
    image: document.getElementById("image"),
    imagePreview: document.getElementById("imagePreview"),
    saveButton: document.getElementById("saveButton"),
    cancelEditButton: document.getElementById("cancelEditButton"),
    formMessage: document.getElementById("formMessage"),
    personsList: document.getElementById("personsList"),
    recordCount: document.getElementById("recordCount"),
    webcam: document.getElementById("webcam"),
    canvas: document.getElementById("captureCanvas"),
    startCameraButton: document.getElementById("startCameraButton"),
    stopCameraButton: document.getElementById("stopCameraButton"),
    matchResult: document.getElementById("matchResult"),
};

function showMessage(target, text, type = "info") {
    target.textContent = text;
    target.className = `message ${type}`;
    target.hidden = false;
}

function clearMessage(target) {
    target.textContent = "";
    target.className = "message";
    target.hidden = true;
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("Could not read selected image."));
        reader.readAsDataURL(file);
    });
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
        ? await response.json().catch(() => ({}))
        : { error: await response.text() };

    if (!response.ok) {
        const message = data.error || "Request failed.";
        throw new Error(message.length > 180 ? "Server error. Check the Flask console for details." : message);
    }

    return data;
}

function personPayload() {
    return {
        name: elements.name.value.trim(),
        age: elements.age.value,
        last_seen_location: elements.lastSeenLocation.value.trim(),
        last_seen_date: elements.lastSeenDate.value,
        contact_info: elements.contactInfo.value.trim(),
        status: elements.status.value,
        notes: elements.notes.value.trim(),
    };
}

function resetForm() {
    state.editingPerson = null;
    elements.form.reset();
    elements.personId.value = "";
    elements.imagePreview.removeAttribute("src");
    elements.imagePreview.classList.remove("visible");
    elements.image.required = true;
    elements.saveButton.textContent = "Save Person";
    elements.cancelEditButton.hidden = true;
    clearMessage(elements.formMessage);
}

function switchToCreateMode(message) {
    state.editingPerson = null;
    elements.personId.value = "";
    elements.image.required = true;
    elements.saveButton.textContent = "Save Person";
    elements.cancelEditButton.hidden = true;
    if (message) {
        showMessage(elements.formMessage, message, "error");
    }
}

function setFormForEdit(person) {
    state.editingPerson = person;
    elements.personId.value = person.id;
    elements.name.value = person.name || "";
    elements.age.value = person.age || "";
    elements.lastSeenLocation.value = person.last_seen_location || "";
    elements.lastSeenDate.value = person.last_seen_date || "";
    elements.contactInfo.value = person.contact_info || "";
    elements.status.value = person.status || "missing";
    elements.notes.value = person.notes || "";
    elements.image.required = false;
    elements.saveButton.textContent = "Update Person";
    elements.cancelEditButton.hidden = false;

    if (person.photo) {
        elements.imagePreview.src = `data:image/jpeg;base64,${person.photo}`;
        elements.imagePreview.classList.add("visible");
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderPersons() {
    const total = state.persons.length;
    elements.recordCount.textContent = `${total} ${total === 1 ? "record" : "records"} saved`;

    if (!state.persons.length) {
        elements.personsList.innerHTML = "<p class=\"empty-state\">No records yet. Register a person to begin matching.</p>";
        return;
    }

    elements.personsList.innerHTML = state.persons.map((person) => `
        <article class="person-card">
            <img class="person-photo" src="data:image/jpeg;base64,${person.photo}" alt="${escapeHtml(person.name)}">
            <div class="person-details">
                <div class="person-heading">
                    <h3>${escapeHtml(person.name)}</h3>
                    <span class="status status-${person.status}">${escapeHtml(person.status)}</span>
                </div>
                <p>${person.age ? `${person.age} years old` : "Age not provided"}</p>
                <p>${escapeHtml(person.last_seen_location || "Last seen location not provided")}</p>
                <p>${escapeHtml(person.last_seen_date || "Last seen date not provided")}</p>
                <div class="card-actions">
                    <button type="button" class="small secondary" data-action="edit" data-id="${person.id}">Edit</button>
                    <button type="button" class="small danger" data-action="delete" data-id="${person.id}">Delete</button>
                </div>
            </div>
        </article>
    `).join("");
}

async function loadPersons() {
    const data = await apiRequest("/api/persons");
    state.persons = data.persons || [];
    if (state.editingPerson && !state.persons.some((person) => person.id === state.editingPerson.id)) {
        switchToCreateMode("That record no longer exists. Review the form, then save it as a new person.");
    }
    renderPersons();
}

async function savePerson(event) {
    event.preventDefault();
    clearMessage(elements.formMessage);

    const payload = personPayload();
    const selectedFile = elements.image.files[0];

    if (!state.editingPerson && !selectedFile) {
        showMessage(elements.formMessage, "Please select a clear face photo.", "error");
        return;
    }

    try {
        elements.saveButton.disabled = true;
        elements.saveButton.textContent = state.editingPerson ? "Updating..." : "Saving...";

        if (selectedFile) {
            payload.image = await fileToBase64(selectedFile);
        }

        const url = state.editingPerson ? `/api/persons/${state.editingPerson.id}` : "/api/persons";
        const method = state.editingPerson ? "PUT" : "POST";

        await apiRequest(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        showMessage(elements.formMessage, state.editingPerson ? "Person updated." : "Person registered.", "success");
        resetForm();
        await loadPersons();
    } catch (error) {
        if (state.editingPerson && error.message === "Person not found") {
            switchToCreateMode("That record was already deleted or cleared. Click Save Person to create it again.");
        } else {
            showMessage(elements.formMessage, error.message, "error");
        }
    } finally {
        elements.saveButton.disabled = false;
        elements.saveButton.textContent = state.editingPerson ? "Update Person" : "Save Person";
    }
}

async function handlePersonAction(event) {
    const button = event.target.closest("button[data-action]");
    if (!button) {
        return;
    }

    const person = state.persons.find((item) => item.id === button.dataset.id);
    if (!person) {
        return;
    }

    if (button.dataset.action === "edit") {
        setFormForEdit(person);
        return;
    }

    if (!confirm(`Delete ${person.name}?`)) {
        return;
    }

    await apiRequest(`/api/persons/${person.id}`, { method: "DELETE" });
    await loadPersons();
}

function drawFrameToCanvas() {
    const video = elements.webcam;
    const canvas = elements.canvas;
    const maxWidth = 480;
    const scale = Math.min(1, maxWidth / video.videoWidth);

    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.8);
}

function renderMatchResult(data) {
    if (data.matched) {
        const person = data.person;
        elements.matchResult.className = "match-result match";
        elements.matchResult.innerHTML = `
            <strong>Match found: ${escapeHtml(person.name)}</strong>
            <span>${data.confidence}% confidence, distance ${data.distance.toFixed(3)}</span>
            <span>${escapeHtml(person.last_seen_location || "No last seen location")} | ${escapeHtml(person.contact_info || "No contact info")}</span>
        `;
        return;
    }

    elements.matchResult.className = "match-result unknown";
    elements.matchResult.textContent = data.reason || "Unknown person";
}

async function matchCurrentFrame() {
    if (state.isMatching || !elements.webcam.videoWidth) {
        return;
    }

    state.isMatching = true;
    try {
        const image = drawFrameToCanvas();
        const data = await apiRequest("/api/match", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image }),
        });
        renderMatchResult(data);
    } catch (error) {
        elements.matchResult.className = "match-result error";
        elements.matchResult.textContent = error.message;
    } finally {
        state.isMatching = false;
    }
}

async function startCamera() {
    try {
        state.cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        elements.webcam.srcObject = state.cameraStream;
        elements.startCameraButton.disabled = true;
        elements.stopCameraButton.disabled = false;
        elements.matchResult.className = "match-result idle";
        elements.matchResult.textContent = "Scanning for faces...";
        state.matchTimer = window.setInterval(matchCurrentFrame, 1800);
    } catch (error) {
        elements.matchResult.className = "match-result error";
        elements.matchResult.textContent = "Camera access failed. Allow webcam permission and try again.";
    }
}

function stopCamera() {
    if (state.matchTimer) {
        window.clearInterval(state.matchTimer);
        state.matchTimer = null;
    }

    if (state.cameraStream) {
        state.cameraStream.getTracks().forEach((track) => track.stop());
        state.cameraStream = null;
    }

    elements.webcam.srcObject = null;
    elements.startCameraButton.disabled = false;
    elements.stopCameraButton.disabled = true;
    elements.matchResult.className = "match-result idle";
    elements.matchResult.textContent = "Camera is idle.";
}

elements.image.addEventListener("change", async () => {
    const file = elements.image.files[0];
    if (!file) {
        return;
    }

    elements.imagePreview.src = await fileToBase64(file);
    elements.imagePreview.classList.add("visible");
});

elements.form.addEventListener("submit", savePerson);
elements.cancelEditButton.addEventListener("click", resetForm);
elements.personsList.addEventListener("click", handlePersonAction);
elements.startCameraButton.addEventListener("click", startCamera);
elements.stopCameraButton.addEventListener("click", stopCamera);

loadPersons().catch((error) => {
    elements.personsList.innerHTML = `<p class="empty-state error-text">${error.message}</p>`;
    elements.recordCount.textContent = "API unavailable";
});
