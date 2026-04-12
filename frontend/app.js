// ── State ─────────────────────────────────────────
const workflows = {};

// All possible pipeline steps in order
const PIPELINE_STEPS = [
    { id: "RECEIVED",           label: "Received",        icon: "1" },
    { id: "WAITING_FOR_GITHUB", label: "Finalizing Logs", icon: "⌛" },
    { id: "LOGS_FETCHED",       label: "Logs Fetched",    icon: "2" },
    { id: "ANALYZING_LLM",      label: "Analyzing",       icon: "3" },
    { id: "LLM_COMPLETE",       label: "Analyzed",        icon: "4" },
    { id: "SENDING_SLACK",      label: "Slack",           icon: "5" },
    { id: "UPDATING_SHEET",     label: "Sheet",           icon: "6" },
    { id: "CREATING_JIRA",      label: "Jira",            icon: "7" },
    { id: "COMPLETED",          label: "Done",            icon: "\u2713" },
];

// Which steps are "in-progress" variants (map to their "done" counterpart)
const ACTIVE_STEPS = {
    "RECEIVED": true,
    "WAITING_FOR_GITHUB": true,
    "LOGS_FETCHED": true,
    "ANALYZING_LLM": true,
    "SENDING_SLACK": true,
    "UPDATING_SHEET": true,
    "CREATING_JIRA": true,
};

const DONE_STEPS = new Set([
    "RECEIVED", "LOGS_FETCHED", "LLM_COMPLETE",
    "SLACK_DONE", "SHEET_DONE", "JIRA_DONE", "COMPLETED",
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
    "JIRA_DONE": "CREATING_JIRA",
    "COMPLETED": "COMPLETED",
    "TOOLS_PLANNED": "LLM_COMPLETE",
    "ERROR": null,
    "SKIPPED": null,
};

// Pipeline step -> which "done" event marks it complete
const PIPELINE_DONE_MAP = {
    "RECEIVED": "RECEIVED",
    "WAITING_FOR_GITHUB": "LOGS_FETCHED",
    "LOGS_FETCHED": "LOGS_FETCHED",
    "ANALYZING_LLM": "LLM_COMPLETE",
    "LLM_COMPLETE": "LLM_COMPLETE",
    "SENDING_SLACK": "SLACK_DONE",
    "UPDATING_SHEET": "SHEET_DONE",
    "CREATING_JIRA": "JIRA_DONE",
    "COMPLETED": "COMPLETED",
};

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
    const isFinished = wf.current_step === "COMPLETED" || wf.current_step === "ERROR" || wf.current_step === "SKIPPED";

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
    if (wf.current_step === "COMPLETED") {
        badge.className = "status-badge success";
        badge.textContent = "Completed";
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
        const doneEvent = PIPELINE_DONE_MAP[step.id];
        const isDone = doneEvent && allDoneEvents.has(doneEvent);
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
        const statusText = resultStep ? (resultStep.data.result || "Done") : "Pending...";
        const statusClass = resultStep ? "tool-status" : "tool-status pending";

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
    // Base steps always shown
    const base = PIPELINE_STEPS.slice(0, 4); // RECEIVED through LLM_COMPLETE

    // Tool steps: show only the planned ones (or all if not yet planned)
    const toolSteps = [];
    if (wf.planned_tools.length > 0) {
        wf.planned_tools.forEach(toolName => {
            const stepId = TOOL_STEP_MAP[toolName];
            const pStep = PIPELINE_STEPS.find(s => s.id === stepId);
            if (pStep) toolSteps.push(pStep);
        });
    } else {
        // Before TOOLS_PLANNED, show all tool steps as possibilities
        const allDoneEvents = new Set(wf.steps.map(s => s.step));
        if (allDoneEvents.has("ANALYZING_LLM") || allDoneEvents.has("LLM_COMPLETE")) {
            // LLM phase reached, show default tools
            toolSteps.push(...PIPELINE_STEPS.slice(4, 7));
        }
    }

    // Final step
    const done = PIPELINE_STEPS.find(s => s.id === "COMPLETED");

    return [...base, ...toolSteps, done];
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
