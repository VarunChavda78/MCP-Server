// ── State ─────────────────────────────────────────
const workflows = {};

// All possible pipeline steps in order
const PIPELINE_STEPS = [
    { id: "RECEIVED",           label: "Received",        icon: "1" },
    { id: "LOGS_FETCHED",       label: "Logs Fetched",    icon: "2" },
    { id: "LLM_COMPLETE",       label: "Analyzed",        icon: "3" },
    { id: "AWAITING_APPROVAL",  label: "Approval",        icon: "📧" },
    { id: "COMPLETED",          label: "Done",            icon: "\u2713" },
];

// Which steps are "in-progress" variants (map to their "done" counterpart)
const ACTIVE_STEPS = {
    "RECEIVED": true,
    "WAITING_FOR_GITHUB": true,
    "LOGS_FETCHED": true,
    "ANALYZING_LLM": true,
    "AWAITING_APPROVAL": true,
    "SENDING_SLACK": true,
    "UPDATING_SHEET": true,
    "CREATING_JIRA": true,
};

const DONE_STEPS = new Set([
    "RECEIVED", "LOGS_FETCHED", "LLM_COMPLETE",
    "SLACK_DONE", "SHEET_DONE", "JIRA_DONE", "COMPLETED",
    "APPROVED", "REJECTED",
]);

// Map in-progress step -> pipeline step id for marking active
const STEP_TO_PIPELINE = {
    "RECEIVED": "RECEIVED",
    "WAITING_FOR_GITHUB": "WAITING_FOR_GITHUB",
    "LOGS_FETCHED": "LOGS_FETCHED",
    "ANALYZING_LLM": "ANALYZING_LLM",
    "LLM_COMPLETE": "LLM_COMPLETE",
    "SENDING_SLACK": "SENDING_SLACK",
    "SLACK_DONE": "SENDING_SLACK",
    "UPDATING_SHEET": "UPDATING_SHEET",
    "SHEET_DONE": "UPDATING_SHEET",
    "CREATING_JIRA": "CREATING_JIRA",
    "JIRA_DONE": null,
    "COMPLETED": "COMPLETED",
    "TOOLS_PLANNED": "LLM_COMPLETE",
    "AWAITING_APPROVAL": "AWAITING_APPROVAL",
    "APPROVED": "AWAITING_APPROVAL",
    "REJECTED": "AWAITING_APPROVAL",
    "ERROR": null,
    "SKIPPED": null,
};

// Pipeline step -> which event marks it "done" (filled circle)
const PIPELINE_DONE_MAP = {
    "RECEIVED": "RECEIVED",
    "LOGS_FETCHED": "LOGS_FETCHED",
    "LLM_COMPLETE": "LLM_COMPLETE",
    "AWAITING_APPROVAL": "REJECTED", // REJECTED or APPROVED will mark this circle done
    "COMPLETED": "COMPLETED",
};

// Specific edge case for AWAITING_APPROVAL circle
function isPipelineStepDone(stepId, allDoneEvents) {
    if (stepId === "AWAITING_APPROVAL") {
        return allDoneEvents.has("APPROVED") || allDoneEvents.has("REJECTED");
    }
    const doneEvent = PIPELINE_DONE_MAP[stepId];
    return doneEvent && allDoneEvents.has(doneEvent);
}

// Tool name -> pipeline step id
const TOOL_STEP_MAP = {
    "send_slack_notification": "SENDING_SLACK",
    "update_tracking_sheet": "UPDATING_SHEET",
    "create_jira_issue": "CREATING_JIRA",
};

// ── DOM references ────────────────────────────────
const activeContainer = document.getElementById("active-workflows");
const completedContainer = document.getElementById("completed-workflows");
const connDot = document.getElementById("connection-status");
const connText = document.getElementById("connection-text");
const statsTotal = document.getElementById("stats-total");
const statsSuccess = document.getElementById("stats-success");
const statsFailure = document.getElementById("stats-failure");

// ── Initial load ──────────────────────────────────
fetch("/api/workflows")
    .then(r => r.json())
    .then(data => {
        Object.values(data).forEach(wf => {
            workflows[wf.run_id] = wf;
            renderWorkflow(wf);
        });
        updateStatistics();
    })
    .catch(err => console.error("Failed to load workflows:", err));

// ── SSE Connection ────────────────────────────────
let evtSource = null;

function connectSSE() {
    evtSource = new EventSource("/api/stream");

    evtSource.onopen = () => {
        connDot.className = "status-dot connected";
        connText.textContent = "Connected";
    };

    evtSource.onmessage = (event) => {
        const update = JSON.parse(event.data);
        const wf = update.workflow;
        workflows[wf.run_id] = wf;
        renderWorkflow(wf);
        updateStatistics();
    };

    evtSource.onerror = () => {
        connDot.className = "status-dot disconnected";
        connText.textContent = "Reconnecting...";
    };
}

connectSSE();

// ── Render ────────────────────────────────────────

function renderWorkflow(wf) {
    const cardId = `wf-${wf.run_id}`;
    let card = document.getElementById(cardId);

    if (!card) {
        card = createWorkflowCard(wf);
        // Hide empty state
        const emptyActive = document.getElementById("empty-active");
        if (emptyActive) emptyActive.style.display = "none";
    }

    updateWorkflowCard(card, wf);

    // Place in correct section
    const isFinished = wf.current_step === "COMPLETED" || wf.current_step === "ERROR" || wf.current_step === "SKIPPED" || wf.current_step === "REJECTED";

    if (isFinished) {
        if (card.parentElement !== completedContainer) {
            card.remove();
            completedContainer.prepend(card);
            card.classList.add("completed");
            const emptyCompleted = document.getElementById("empty-completed");
            if (emptyCompleted) emptyCompleted.style.display = "none";
        }
        // Show empty active if no active workflows
        const activeCards = activeContainer.querySelectorAll(".workflow-card");
        if (activeCards.length === 0) {
            const emptyActive = document.getElementById("empty-active");
            if (emptyActive) emptyActive.style.display = "";
        }
    } else {
        if (!card.parentElement || card.parentElement !== activeContainer) {
            activeContainer.prepend(card);
        }
    }
}

function createWorkflowCard(wf) {
    const card = document.createElement("div");
    card.className = "workflow-card";
    card.id = `wf-${wf.run_id}`;

    card.innerHTML = `
        <div class="card-header">
            <div class="card-header-left">
                <span class="repo-name">${escHtml(wf.repo)}</span>
                <span class="branch-badge">${escHtml(wf.branch)}</span>
            </div>
            <div class="card-header-right">
                <span class="run-id">Run #${escHtml(wf.run_id)}</span>
                <span class="status-badge running">Starting</span>
            </div>
        </div>
        <div class="progress-container">
            <div class="progress-bar-track">
                <div class="progress-bar-fill"></div>
            </div>
            <div class="progress-info">
                <span class="progress-text">0 / ${wf.steps_total} steps</span>
                <span class="progress-percent">0%</span>
            </div>
        </div>
        <div class="pipeline-container">
            <div class="pipeline-steps"></div>
        </div>
        <div class="card-details">
            <div class="analysis-box" style="display:none;">
                <div class="label">LLM Analysis</div>
                <div class="analysis-text"></div>
            </div>
            <div class="tool-results"></div>
            <div class="step-log">
                <button class="step-log-toggle">Show event log</button>
                <div class="step-log-entries"></div>
            </div>
        </div>
    `;

    // Toggle event log
    const toggle = card.querySelector(".step-log-toggle");
    const entries = card.querySelector(".step-log-entries");
    toggle.addEventListener("click", () => {
        entries.classList.toggle("open");
        toggle.textContent = entries.classList.contains("open") ? "Hide event log" : "Show event log";
    });

    return card;
}

function updateWorkflowCard(card, wf) {
    // ── Status Badge ──
    const badge = card.querySelector(".status-badge");
    const hasBeenRejected = wf.steps_completed.includes("REJECTED");
    const hasBeenApproved = wf.steps_completed.includes("APPROVED");

    if (wf.current_step === "COMPLETED") {
        if (hasBeenRejected) {
            badge.className = "status-badge failed";
            badge.textContent = "Rejected";
        } else {
            badge.className = "status-badge success";
            badge.textContent = "Completed";
        }
        card.classList.remove("error");
    } else if (wf.current_step === "ERROR") {
        badge.className = "status-badge failed";
        badge.textContent = "Error";
        card.classList.add("error");
    } else if (wf.current_step === "SKIPPED") {
        badge.className = "status-badge success";
        badge.textContent = "Skipped";
    } else {
        badge.className = "status-badge running";
        badge.textContent = formatStepName(wf.current_step);
    }

    // ── Progress Bar ──
    const completed = wf.steps_completed.length;
    const total = wf.steps_total;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

    const fill = card.querySelector(".progress-bar-fill");
    fill.style.width = pct + "%";
    fill.className = "progress-bar-fill";
    if (wf.current_step === "COMPLETED") fill.classList.add("complete");
    if (wf.current_step === "ERROR") fill.classList.add("error");

    card.querySelector(".progress-text").textContent = `${completed} / ${total} steps`;
    card.querySelector(".progress-percent").textContent = pct + "%";

    // ── Pipeline Steps ──
    const pipelineEl = card.querySelector(".pipeline-steps");
    const visibleSteps = getVisibleSteps(wf);
    pipelineEl.innerHTML = "";

    const allDoneEvents = new Set(wf.steps.map(s => s.step));

    visibleSteps.forEach((step, i) => {
        if (i > 0) {
            const connector = document.createElement("div");
            connector.className = "step-connector";
            // Connector is "done" if the step it leads to is done
            const doneEvent = PIPELINE_DONE_MAP[step.id];
            if (doneEvent && allDoneEvents.has(doneEvent)) {
                connector.classList.add("done");
            } else if (step.id === STEP_TO_PIPELINE[wf.current_step]) {
                connector.classList.add("active");
            }
            pipelineEl.appendChild(connector);
        }

        const stepEl = document.createElement("div");
        stepEl.className = "pipeline-step";

        // Determine state
        const isDone = isPipelineStepDone(step.id, allDoneEvents);
        const isActive = step.id === STEP_TO_PIPELINE[wf.current_step] && !isDone;
        const isError = wf.current_step === "ERROR" && !isDone && isActive;

        if (isDone) stepEl.classList.add("done");
        else if (isError) stepEl.classList.add("error");
        else if (isActive) stepEl.classList.add("active");

        stepEl.innerHTML = `
            <div class="step-circle">${isDone ? "\u2713" : step.icon}</div>
            <div class="step-label">${step.label}</div>
        `;
        pipelineEl.appendChild(stepEl);
    });

    // ── Analysis ──
    const analysisBox = card.querySelector(".analysis-box");
    if (wf.analysis) {
        analysisBox.style.display = "";
        card.querySelector(".analysis-text").textContent = wf.analysis;
    }

    // ── Tool Results ──
    const toolResultsEl = card.querySelector(".tool-results");
    toolResultsEl.innerHTML = "";

    const toolIcons = {
        "send_slack_notification": "#",
        "update_tracking_sheet": "\u25A6",
        "create_jira_issue": "\u25C6",
    };

    wf.planned_tools.forEach(toolName => {
        const resultStep = wf.steps.find(s =>
            s.data && s.data.tool === toolName && (
                s.step === "SLACK_DONE" || s.step === "SHEET_DONE" || s.step === "JIRA_DONE"
            )
        );

        const div = document.createElement("div");
        div.className = "tool-result";
        const icon = toolIcons[toolName] || ">";
        const displayName = toolName.replace(/_/g, " ");
        const isRejected = wf.current_step === "REJECTED" || wf.steps_completed.includes("REJECTED");
        const statusText = resultStep ? (resultStep.data.result || "Done") : (isRejected ? "Rejected" : "Pending...");
        const statusClass = resultStep ? "tool-status" : (isRejected ? "tool-status rejected" : "tool-status pending");

        div.innerHTML = `
            <span class="tool-icon">${icon}</span>
            <span class="tool-name">${escHtml(displayName)}</span>
            <span class="${statusClass}">${escHtml(statusText)}</span>
        `;
        toolResultsEl.appendChild(div);
    });

    // ── Error display ──
    if (wf.error) {
        let errBox = card.querySelector(".error-box");
        if (!errBox) {
            errBox = document.createElement("div");
            errBox.className = "analysis-box error-box";
            errBox.innerHTML = `<div class="label" style="color:var(--accent-red)">Error</div><div class="error-text"></div>`;
            card.querySelector(".card-details").prepend(errBox);
        }
        errBox.querySelector(".error-text").textContent = wf.error;
    }

    // ── Step Log ──
    const logEntries = card.querySelector(".step-log-entries");
    logEntries.innerHTML = "";
    wf.steps.forEach(s => {
        const entry = document.createElement("div");
        entry.className = "step-log-entry";
        const time = new Date(s.timestamp).toLocaleTimeString();
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-step">${s.step}</span>
        `;
        logEntries.appendChild(entry);
    });
}

// ── Helpers ───────────────────────────────────────

function getVisibleSteps(wf) {
    return PIPELINE_STEPS; // Now matches our 5-milestone count perfectly
}

function formatStepName(step) {
    const names = {
        "RECEIVED": "Received",
        "WAITING_FOR_GITHUB": "Finalizing Logs...",
        "LOGS_FETCHED": "Logs Fetched",
        "ANALYZING_LLM": "Analyzing...",
        "LLM_COMPLETE": "Analyzed",
        "SENDING_SLACK": "Sending Slack...",
        "SLACK_DONE": "Slack Sent",
        "UPDATING_SHEET": "Updating Sheet...",
        "SHEET_DONE": "Sheet Updated",
        "CREATING_JIRA": "Creating Jira...",
        "JIRA_DONE": "Jira Created",
        "TOOLS_PLANNED": "Planning Tools",
        "AWAITING_APPROVAL": "Awaiting Approval",
        "APPROVED": "Approved",
        "REJECTED": "Rejected",
        "COMPLETED": "Completed",
        "ERROR": "Error",
        "SKIPPED": "Skipped",
    };
    return names[step] || step;
}

function escHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

function updateStatistics() {
    const list = Object.values(workflows);
    const total = list.length;
    const success = list.filter(wf => wf.status === "success").length;
    const failure = list.filter(wf => wf.status === "failure").length;

    if (statsTotal) statsTotal.textContent = total;
    if (statsSuccess) statsSuccess.textContent = success;
    if (statsFailure) statsFailure.textContent = failure;
}
