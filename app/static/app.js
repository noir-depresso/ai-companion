//creates the interactive part of the website. 



const chatForm = document.querySelector("#chat-form");
// so query selectors find the first appearance of id with #XXXX in the document and puts it in the const variable
// im guessing the document is just what called it
const messagesElement = document.querySelector("#messages");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const clearHistoryButton = document.querySelector("#clear-history-button");
const copyAllButton = document.querySelector("#copy-all-button");
const temperatureInput = document.querySelector("#temperature-input");
const temperatureValue = document.querySelector("#temperature-value");
const loadingElement = document.querySelector("#loading");
const responseMetaElement = document.querySelector("#response-meta");
const errorElement = document.querySelector("#error");
const developerToggle = document.querySelector("#developer-toggle");
const developerPanel =document.querySelector("#developer-panel");
const developerClose = document.querySelector("#developer-close");
const saveStateButton = document.querySelector("#save-state-button");
const resetStateButton = document.querySelector("#reset-state-button");
const refreshPromptButton = document.querySelector("#refresh-prompt-button");
const developerStatus = document.querySelector("#developer-status");
const promptPreview = document.querySelector("#prompt-preview");
const interactionEventCount = document.querySelector("#interaction-event-count");
const interactionEventList = document.querySelector("#interaction-event-list");
const interactionEventStatus = document.querySelector("#interaction-event-status");
const refreshEventsButton = document.querySelector("#refresh-events-button");
const memoryCandidateCount = document.querySelector("#memory-candidate-count");
const memoryCandidateFilter = document.querySelector("#memory-candidate-filter");
const memoryCandidateList = document.querySelector("#memory-candidate-list");
const memoryCandidateStatus = document.querySelector("#memory-candidate-status");
const refreshCandidatesButton = document.querySelector("#refresh-candidates-button");
const extractMemoriesButton = document.querySelector("#extract-memories-button");
const candidateTabButton = document.querySelector("#candidate-tab-button");
const memoryTabButton = document.querySelector("#memory-tab-button");
const candidateTabPanel = document.querySelector("#candidate-tab-panel");
const memoryTabPanel = document.querySelector("#memory-tab-panel");
const memoryCount = document.querySelector("#memory-count");
const memoryList = document.querySelector("#memory-list");
const memoryStatus = document.querySelector("#memory-status");
const refreshMemoriesButton = document.querySelector("#refresh-memories-button");

let generationSettingsLoaded = false;
let memoryCandidates = [];
let storedMemories = [];
let interactionEvents = [];
sendButton.disabled = true;

const stateControls = {
    trust: {
        input: document.querySelector("#trust-slider"),
        output: document.querySelector("#trust-value"),
    },
    closeness: {
        input: document.querySelector("#closeness-slider"),
        output: document.querySelector("#closeness-value"),
    },
    respect: {
        input: document.querySelector("#respect-slider"),
        output: document.querySelector("#respect-value"),
    },
    comfort: {
        input: document.querySelector("#comfort-slider"),
        output: document.querySelector("#comfort-value"),
    },
    energy: {
        input: document.querySelector("#energy-slider"),
        output: document.querySelector("#energy-value"),
    },
    stress: {
        input: document.querySelector("#stress-slider"),
        output: document.querySelector("#stress-value"),
    },
};

const moodSelect =document.querySelector("#mood-select");
for (const control of Object.values(stateControls)) {
    control.input.addEventListener("input", () => {
        control.output.textContent = control.input.value;
    });
}


//alright this just created elements, made it a message object and gave it text to display
function addMessage(text, role) {
    const messageElement = document.createElement("div");

    messageElement.classList.add("message", role);
    messageElement.textContent = text;

    messagesElement.append(messageElement); //messages is referring to the const variable created
    //it appends the new mesaage so it will be displayed at the place where messages are displayed
    messagesElement.scrollTop = messagesElement.scrollHeight;
    //im guessing this resets the scroll to the bottom?
}

function setLoading(isLoading) {
    loadingElement.classList.toggle("hidden", !isLoading);
    messageInput.disabled = isLoading;
    sendButton.disabled = isLoading || !generationSettingsLoaded;
    clearHistoryButton.disabled = isLoading;
    copyAllButton.disabled = isLoading;
    temperatureInput.disabled = isLoading || !generationSettingsLoaded;
    //disable messaging and send buttons if it is loading. 
    //not sure how the toggle hidden works?? 
}

function showError(message) {
    errorElement.textContent = message;
    errorElement.classList.toggle("hidden", !message);
}


function showResponseTime(elapsedSeconds) {
    if (elapsedSeconds === null) {
        responseMetaElement.textContent = "";
        responseMetaElement.classList.add("hidden");
        return;
    }

    responseMetaElement.textContent =
        `Response time: ${elapsedSeconds.toFixed(2)} seconds`;
    responseMetaElement.classList.remove("hidden");
}


async function readApiResponse(response, fallbackMessage) {
    const body = await response.text();
    let data = null;

    if (body) {
        try {
            data = JSON.parse(body);
        } catch (error) {
            if (response.ok) {
                throw new Error(fallbackMessage);
            }
        }
    }

    if (!response.ok) {
        const detail = data && typeof data.detail === "string"
            ? data.detail
            : body;
        throw new Error(detail || `${fallbackMessage} (${response.status})`);
    }

    return data;
}


async function loadGenerationSettings() {
    const response = await fetch("/settings");
    const settings = await response.json();

    if (!response.ok) {
        throw new Error(settings.detail || "Could not load generation settings.");
    }

    temperatureInput.min = String(settings.minimum_temperature);
    temperatureInput.max = String(settings.maximum_temperature);
    temperatureInput.step = String(settings.temperature_step);
    temperatureInput.value = String(settings.default_temperature);

    generationSettingsLoaded = true;
    sendButton.disabled = false;
    temperatureInput.disabled = false;
    updateTemperatureValue();
}


async function loadHistory() {
    const response = await fetch("/conversations/default/messages");
    //gets the messages. the api will see this and return the stuff. this is how front and back end communicate. http and api!
    const data = await response.json();
    //turn dictionaries into json

    if (!response.ok) {
        throw new Error(data.detail || "Could not load conversation history.");
    }

    messagesElement.textContent = "";

    for (const message of data.messages) {
        addMessage(message.content, message.role);
        //adds each message from the history (obtained through fetch) onto the display
    }
}


async function sendMessage(userMessage, temperature) {
    const response = await fetch("/chat", {
        //async function so waits until this is complete
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            //the type that will be communicated
        },
        body: JSON.stringify({
            message: userMessage,
            temperature: temperature,
        }),
        //body is the actual message or thing to be communicated
    });
    //WOW! it is communicating with the backend by using POST, an HTTP method. so it sends in a stream of json
    //stringify converts the message:userMessage dictionary to json so it is carriable
    //so everything is given to the api in chatrequest and the api responds with a chatresponse

    return readApiResponse(response, "The request failed.");
    //returns the whole ChatResponse, including the message and response time
}


async function refreshDeveloperPanelData() {
    await Promise.allSettled([
        loadDeveloperState(),
        loadPromptPreview(),
        loadInteractionEvents(),
        loadMemoryCandidates(),
        loadMemories(),
    ]);
}

async function clearHistory() {
    const response = await fetch("/conversations/default/messages", {
        method: "DELETE",
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Could not clear conversation history.");
    }

    messagesElement.textContent = "";
    showResponseTime(null);
}

async function copyAllMessages() {
    const messageElements = messagesElement.querySelectorAll(".message");

    if (messageElements.length === 0) {
        throw new Error("There are no messages to copy.");
    }

    const text = Array.from(messageElements)
        .map((messageElement) => {
            const role = messageElement.classList.contains("user")
                ? "You"
                : "Rin";

            return `${role}: ${messageElement.textContent}`;
        })
        .join("\n\n");

    await navigator.clipboard.writeText(text);
}

function getTemperature() {
    return Number(temperatureInput.value);
}

function updateTemperatureValue() {
    temperatureValue.textContent = getTemperature().toFixed(2);
}

//so now the "form", as in google forms or like surveys, will do something when the event "submit" happens
chatForm.addEventListener("submit", async (event) => { //by the way this is a lambda function
    event.preventDefault(); //stops the default action... idk like entering a new line or smth

    if (!generationSettingsLoaded) {
        return;
    }

    const userMessage = messageInput.value.trim();

    if (!userMessage) {
        return;
    }

    addMessage(userMessage, "user"); //from the textbox, the user message is projected onto the messages screen. like we are texting

    messageInput.value = "";
    showError("");
    showResponseTime(null);
    setLoading(true);
    //deletes the stuff in the textbox

    try {
        const chatResponse = await sendMessage(userMessage, getTemperature());
        addMessage(chatResponse.response, "assistant");
        showResponseTime(chatResponse.elapsed_seconds);

    } catch (error) {
        showError(error.message);
    } finally {
        if (!developerPanel.classList.contains("hidden")) {
            await refreshDeveloperPanelData();
        }
        setLoading(false);
        messageInput.focus();
    }
    //finishes off by getting the llm message, displaying it, and enabling stuff
});

messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

clearHistoryButton.addEventListener("click", async () => {
    const shouldClear = confirm("Clear this conversation history?");

    if (!shouldClear) {
        return;
    }

    showError("");
    setLoading(true);

    try {
        await clearHistory();
        if (!developerPanel.classList.contains("hidden")) {
            await refreshDeveloperPanelData();
        }
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
        messageInput.focus();
    }
});

copyAllButton.addEventListener("click", async () => {
    showError("");

    try {
        await copyAllMessages();
        copyAllButton.textContent = "Copied!";

        setTimeout(() => {
            copyAllButton.textContent = "Copy all";
        }, 1500);
    } catch (error) {
        showError(error.message);
    }
});

temperatureInput.addEventListener("input", () => {
    updateTemperatureValue();
});

loadHistory().catch((error) => {
    showError(error.message);
});

loadGenerationSettings().catch((error) => {
    showError(error.message);
});

developerToggle.addEventListener("click", async () => {
    developerPanel.classList.remove("hidden");

    await refreshDeveloperPanelData();
});

developerClose.addEventListener("click", () => {
    developerPanel.classList.add("hidden");
});


async function loadDeveloperState() {
    developerStatus.textContent = "Loading state...";

    try {
        const response = await fetch("/developer/state");

        if (!response.ok) {
            throw new Error(
                `State request failed: ${response.status}`
            );
        }

        const state = await response.json();

        setControlValue("trust", state.trust);
        setControlValue("closeness", state.closeness);
        setControlValue("respect", state.respect);
        setControlValue("comfort", state.comfort);
        setControlValue("energy", state.energy);
        setControlValue("stress", state.stress);

        moodSelect.value = state.mood;
        developerStatus.textContent = "State loaded.";
    } catch (error) {
        console.error(error);
        developerStatus.textContent =
            "Could not load developer state.";
    }
}

function setControlValue(name, value) {
    const control = stateControls[name];

    control.input.value = String(value);
    control.output.textContent = String(value);
}


function collectStateFromControls() {
    return {
        trust: Number(stateControls.trust.input.value),
        closeness: Number(
            stateControls.closeness.input.value
        ),
        respect: Number(stateControls.respect.input.value),
        comfort: Number(stateControls.comfort.input.value),
        mood: moodSelect.value,
        energy: Number(stateControls.energy.input.value),
        stress: Number(stateControls.stress.input.value),
    };
}


async function saveDeveloperState() {
    const state = collectStateFromControls();

    developerStatus.textContent = "Saving state...";

    try {
        const response = await fetch("/developer/state", {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(state),
        });

        if (!response.ok) {
            const errorBody = await response.text();

            throw new Error(
                `State update failed: ${response.status} ${errorBody}`
            );
        }

        const savedState = await response.json();

        developerStatus.textContent = "State saved.";
        console.log("Saved state:", savedState);

        await loadPromptPreview();
    } catch (error) {
        console.error(error);
        developerStatus.textContent =
            "Could not save developer state.";
    }
}

saveStateButton.addEventListener(
    "click",
    saveDeveloperState
);


async function resetDeveloperState() {
    developerStatus.textContent = "Resetting state...";

    try {
        const response = await fetch(
            "/developer/state/reset",
            {
                method: "POST",
            }
        );

        if (!response.ok) {
            throw new Error(
                `State reset failed: ${response.status}`
            );
        }

        await loadDeveloperState();
        await loadPromptPreview();

        developerStatus.textContent =
            "State reset to defaults.";
    } catch (error) {
        console.error(error);
        developerStatus.textContent =
            "Could not reset developer state.";
    }
}

resetStateButton.addEventListener(
    "click",
    resetDeveloperState
);

async function loadPromptPreview() {
    promptPreview.value = "Loading prompt...";

    try {
        const response = await fetch("/developer/prompt");

        if (!response.ok) {
            throw new Error(
                `Prompt request failed: ${response.status}`
            );
        }

        const data = await response.json();
        promptPreview.value = data.prompt;
    } catch (error) {
        console.error(error);
        promptPreview.value =
            "Could not load the prompt preview.";
    }
}

refreshPromptButton.addEventListener(
    "click",
    loadPromptPreview
);


function formatDelta(value) {
    return value > 0 ? `+${value}` : String(value);
}


function createInteractionEventCard(event) {
    const card = document.createElement("article");
    card.className = "interaction-event";

    const header = document.createElement("div");
    header.className = "interaction-event-header";

    const eventType = document.createElement("strong");
    eventType.textContent = formatCandidateLabel(event.event_type);

    const metadata = document.createElement("span");
    metadata.className = "section-meta";
    metadata.textContent = `Message #${event.message_id} | importance ${event.importance.toFixed(2)}`;
    header.append(eventType, metadata);

    const deltaList = document.createElement("div");
    deltaList.className = "interaction-deltas";
    const deltas = [
        ["Trust", event.trust_delta],
        ["Closeness", event.closeness_delta],
        ["Respect", event.respect_delta],
        ["Comfort", event.comfort_delta],
    ];

    for (const [label, value] of deltas) {
        const delta = document.createElement("span");
        delta.className = value > 0
            ? "delta-positive"
            : value < 0
                ? "delta-negative"
                : "delta-neutral";
        delta.textContent = `${label} ${formatDelta(value)}`;
        deltaList.append(delta);
    }

    const mood = document.createElement("p");
    mood.className = "interaction-mood";
    mood.textContent = `Suggested mood: ${formatCandidateLabel(event.suggested_mood)}`;

    const reason = document.createElement("p");
    reason.className = "interaction-reason";
    reason.textContent = event.reason;

    card.append(header, deltaList, mood, reason);
    return card;
}


function renderInteractionEvents() {
    interactionEventList.textContent = "";
    interactionEventCount.textContent = `${interactionEvents.length} recent ${interactionEvents.length === 1 ? "event" : "events"}`;

    if (interactionEvents.length === 0) {
        const empty = document.createElement("p");
        empty.className = "candidate-empty";
        empty.textContent = "No interaction events yet.";
        interactionEventList.append(empty);
        return;
    }

    for (const event of interactionEvents) {
        interactionEventList.append(createInteractionEventCard(event));
    }
}


async function loadInteractionEvents() {
    interactionEventStatus.textContent = "Loading state changes...";
    refreshEventsButton.disabled = true;

    try {
        const response = await fetch("/developer/interaction-events");
        interactionEvents = await readApiResponse(
            response,
            "Could not load state changes.",
        );
        renderInteractionEvents();
        interactionEventStatus.textContent = "New events show policy-approved deltas. Older rows may predate the guardrails.";
    } catch (error) {
        console.error(error);
        interactionEvents = [];
        renderInteractionEvents();
        interactionEventStatus.textContent = error.message;
    } finally {
        refreshEventsButton.disabled = false;
    }
}


refreshEventsButton.addEventListener("click", loadInteractionEvents);


function formatCandidateLabel(value) {
    return value
        .toLowerCase()
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}


function selectMemoryTab(tabName) {
    const showCandidates = tabName === "candidates";
    candidateTabPanel.classList.toggle("hidden", !showCandidates);
    memoryTabPanel.classList.toggle("hidden", showCandidates);
    candidateTabButton.classList.toggle("active", showCandidates);
    memoryTabButton.classList.toggle("active", !showCandidates);
    candidateTabButton.setAttribute("aria-selected", String(showCandidates));
    memoryTabButton.setAttribute("aria-selected", String(!showCandidates));
}


function createMemoryCard(memory) {
    const card = document.createElement("article");
    card.className = "candidate-card";

    const header = document.createElement("div");
    header.className = "candidate-card-header";

    const labels = document.createElement("div");
    labels.className = "candidate-labels";

    const typeBadge = document.createElement("span");
    typeBadge.className = "candidate-badge";
    typeBadge.textContent = formatCandidateLabel(memory.memory_type);

    const activeBadge = document.createElement("span");
    activeBadge.className = `candidate-badge ${memory.is_active ? "accepted" : "inactive"}`;
    activeBadge.textContent = memory.is_active ? "Active" : "Inactive";
    labels.append(typeBadge, activeBadge);

    const memoryId = document.createElement("span");
    memoryId.className = "section-meta";
    memoryId.textContent = `#${memory.id}`;
    header.append(labels, memoryId);

    const content = document.createElement("p");
    content.className = "candidate-content";
    content.textContent = memory.content;

    const metadata = document.createElement("div");
    metadata.className = "candidate-metadata";
    const sources = memory.source_message_ids.length > 0
        ? memory.source_message_ids.map((id) => `#${id}`).join(", ")
        : "none";
    metadata.append(
        `Importance: ${memory.importance.toFixed(2)}`,
        `Valence: ${memory.emotional_valence}`,
        `Sources: ${sources}`,
        `Updated: ${new Date(memory.updated_at).toLocaleString()}`,
    );

    card.append(header, content, metadata);
    return card;
}


function renderMemories() {
    memoryList.textContent = "";
    memoryCount.textContent = `${storedMemories.length} ${storedMemories.length === 1 ? "memory" : "memories"}`;

    if (storedMemories.length === 0) {
        const empty = document.createElement("p");
        empty.className = "candidate-empty";
        empty.textContent = "No stored memories yet.";
        memoryList.append(empty);
        return;
    }

    for (const memory of storedMemories) {
        memoryList.append(createMemoryCard(memory));
    }
}


async function loadMemories() {
    memoryStatus.textContent = "Loading memories...";
    refreshMemoriesButton.disabled = true;

    try {
        const response = await fetch("/developer/memories");
        storedMemories = await readApiResponse(response, "Could not load memories.");
        renderMemories();
        memoryStatus.textContent = "Memories loaded.";
    } catch (error) {
        console.error(error);
        storedMemories = [];
        renderMemories();
        memoryStatus.textContent = error.message;
    } finally {
        refreshMemoriesButton.disabled = false;
    }
}


candidateTabButton.addEventListener("click", () => selectMemoryTab("candidates"));
memoryTabButton.addEventListener("click", () => selectMemoryTab("memories"));
refreshMemoriesButton.addEventListener("click", loadMemories);


function renderMemoryCandidates() {
    const selectedStatus = memoryCandidateFilter.value;
    const visibleCandidates = memoryCandidates.filter((candidate) => {
        return selectedStatus === "ALL" || candidate.status === selectedStatus;
    });

    memoryCandidateList.textContent = "";

    const total = memoryCandidates.length;
    const visible = visibleCandidates.length;
    memoryCandidateCount.textContent = selectedStatus === "ALL"
        ? `${total} ${total === 1 ? "candidate" : "candidates"}`
        : `${visible} of ${total}`;

    if (visibleCandidates.length === 0) {
        const emptyElement = document.createElement("p");
        emptyElement.className = "candidate-empty";
        emptyElement.textContent = "No candidates in this view.";
        memoryCandidateList.append(emptyElement);
        return;
    }

    for (const candidate of visibleCandidates) {
        memoryCandidateList.append(createCandidateCard(candidate));
    }
}


function createCandidateCard(candidate) {
    const card = document.createElement("article");
    card.className = "candidate-card";

    const header = document.createElement("div");
    header.className = "candidate-card-header";

    const labels = document.createElement("div");
    labels.className = "candidate-labels";

    const typeBadge = document.createElement("span");
    typeBadge.className = "candidate-badge";
    typeBadge.textContent = formatCandidateLabel(candidate.memory_type);

    const statusBadge = document.createElement("span");
    statusBadge.className = `candidate-badge ${candidate.status.toLowerCase()}`;
    statusBadge.textContent = formatCandidateLabel(candidate.status);

    labels.append(typeBadge, statusBadge);

    const candidateId = document.createElement("span");
    candidateId.className = "section-meta";
    candidateId.textContent = `#${candidate.id}`;

    header.append(labels, candidateId);

    const content = document.createElement("p");
    content.className = "candidate-content";
    content.textContent = candidate.content;

    const metadata = document.createElement("div");
    metadata.className = "candidate-metadata";

    const importance = document.createElement("span");
    importance.textContent = `Importance: ${candidate.importance.toFixed(2)}`;

    const valence = document.createElement("span");
    valence.textContent = `Valence: ${candidate.emotional_valence}`;

    const sources = document.createElement("span");
    sources.textContent = candidate.source_message_ids.length > 0
        ? `Sources: ${candidate.source_message_ids.map((id) => `#${id}`).join(", ")}`
        : "Sources: none";

    metadata.append(importance, valence, sources);
    card.append(header, content, metadata);

    if (candidate.status === "PENDING") {
        const actions = document.createElement("div");
        actions.className = "candidate-actions";

        const rejectButton = document.createElement("button");
        rejectButton.type = "button";
        rejectButton.className = "reject-button";
        rejectButton.textContent = "Reject";

        const acceptButton = document.createElement("button");
        acceptButton.type = "button";
        acceptButton.className = "accept-button";
        acceptButton.textContent = "Accept";

        rejectButton.addEventListener("click", () => {
            reviewMemoryCandidate(candidate.id, "reject", [rejectButton, acceptButton]);
        });
        acceptButton.addEventListener("click", () => {
            reviewMemoryCandidate(candidate.id, "accept", [rejectButton, acceptButton]);
        });

        actions.append(rejectButton, acceptButton);
        card.append(actions);
    }

    return card;
}


async function loadMemoryCandidates() {
    memoryCandidateStatus.textContent = "Loading candidates...";
    refreshCandidatesButton.disabled = true;

    try {
        const response = await fetch("/developer/memory/candidates");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not load memory candidates.");
        }

        memoryCandidates = data;
        renderMemoryCandidates();
        memoryCandidateStatus.textContent = "Candidates loaded.";
    } catch (error) {
        console.error(error);
        memoryCandidateStatus.textContent = error.message;
        memoryCandidates = [];
        renderMemoryCandidates();
    } finally {
        refreshCandidatesButton.disabled = false;
    }
}


async function extractMemoryCandidates() {
    memoryCandidateStatus.textContent = "Extracting from the latest 8 messages...";
    extractMemoriesButton.disabled = true;
    refreshCandidatesButton.disabled = true;

    try {
        const response = await fetch("/developer/memory/extract", {
            method: "POST",
        });
        const created = await readApiResponse(
            response,
            "Could not extract memory candidates.",
        );
        await loadMemoryCandidates();
        memoryCandidateStatus.textContent = created.length === 0
            ? "Extraction completed with no strong candidates."
            : `Created ${created.length} ${created.length === 1 ? "candidate" : "candidates"}.`;
    } catch (error) {
        console.error(error);
        memoryCandidateStatus.textContent = error.message;
    } finally {
        extractMemoriesButton.disabled = false;
        refreshCandidatesButton.disabled = false;
    }
}


async function reviewMemoryCandidate(candidateId, action, buttons) {
    memoryCandidateStatus.textContent = `${formatCandidateLabel(action)}ing candidate...`;

    for (const button of buttons) {
        button.disabled = true;
    }

    try {
        const response = await fetch(
            `/developer/memory/candidates/${candidateId}/${action}`,
            { method: "POST" },
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Could not ${action} candidate.`);
        }

        memoryCandidates = memoryCandidates.map((candidate) => {
            return candidate.id === data.id ? data : candidate;
        });
        renderMemoryCandidates();
        if (action === "accept") {
            await loadMemories();
        }
        memoryCandidateStatus.textContent = `Candidate ${formatCandidateLabel(data.status).toLowerCase()}.`;
    } catch (error) {
        console.error(error);
        memoryCandidateStatus.textContent = error.message;

        for (const button of buttons) {
            button.disabled = false;
        }
    }
}


memoryCandidateFilter.addEventListener("change", renderMemoryCandidates);
extractMemoriesButton.addEventListener("click", extractMemoryCandidates);
refreshCandidatesButton.addEventListener("click", loadMemoryCandidates);
