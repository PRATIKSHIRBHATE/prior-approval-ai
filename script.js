let currentThreadId = localStorage.getItem("claim_thread_id") || null;
let latestResultMarkdown = "";

const EXAMPLES = {
    valid: {
        narrative: "Customer states vehicle has an oil leak from the rear end. Found oil leak at pinion seal on rear differential. Recommend replacing pinion seal and refilling differential oil.",
        parts: "Pinion seal\nDifferential oil\nCrush sleeve"
    },
    suspicious: {
        narrative: "Customer states vehicle has an oil leak from the rear end. Found oil leak at pinion seal on rear differential. Recommend replacing pinion seal.",
        parts: "Pinion seal\nDifferential oil\nSpark plug set\nAlarm/keyless lock system kit"
    },
    mixed: {
        narrative: "Customer reports engine overheating. Found thermostat stuck closed in cooling system. Recommend replacing thermostat and refilling coolant.",
        parts: "Thermostat\nCoolant\nThermostat gasket\nBrake pad set"
    }
};

function setExample(type) {
    const ex = EXAMPLES[type];
    document.getElementById("narrativeInput").value = ex.narrative;
    document.getElementById("partsInput").value = ex.parts;
}

function setLoading(isLoading) {
    const btn = document.getElementById("sendBtn");
    const text = document.getElementById("btnText");
    const loader = document.getElementById("btnLoader");
    btn.disabled = isLoading;
    if (isLoading) {
        text.classList.add("hidden");
        loader.classList.remove("hidden");
    } else {
        text.classList.remove("hidden");
        loader.classList.add("hidden");
    }
}

function showError(msg) {
    const box = document.getElementById("errorBox");
    box.textContent = msg;
    box.classList.remove("hidden");
}

function hideError() {
    const box = document.getElementById("errorBox");
    box.classList.add("hidden");
    box.textContent = "";
}

function decisionColor(decision) {
    if (decision === "AUTO_APPROVE") return "#22c55e";
    if (decision === "FLAG") return "#ef4444";
    return "#f59e0b";
}

function decisionEmoji(decision) {
    if (decision === "AUTO_APPROVE") return "✅";
    if (decision === "FLAG") return "🚩";
    return "⚠️";
}

function renderResults(data) {
    // Decision banner
    const banner = document.getElementById("decisionBanner");
    const color = decisionColor(data.decision);
    banner.style.borderLeftColor = color;
    banner.innerHTML = `
        <span class="decision-emoji">${decisionEmoji(data.decision)}</span>
        <div>
            <div class="decision-label">${data.decision}</div>
            <div class="decision-score">Overall Score: ${(data.overall_score * 100).toFixed(1)}%</div>
        </div>
    `;

    // Parts table
    const table = document.getElementById("partsTable");
    let html = `<table>
        <thead><tr><th>Part</th><th>Score</th><th>Status</th><th>Reason</th></tr></thead>
        <tbody>`;
    for (const pr of data.part_results) {
        const score = pr.relevance_score;
        const pct = (score * 100).toFixed(0);
        let status = "✅ Justified";
        let cls = "score-good";
        if (score < 0.3) { status = "🚩 Unjustified"; cls = "score-bad"; }
        else if (score <= 0.8) { status = "⚠️ Review"; cls = "score-warn"; }
        html += `<tr>
            <td>${pr.part_name}</td>
            <td class="${cls}">${pct}%</td>
            <td>${status}</td>
            <td>${pr.reason}</td>
        </tr>`;
    }
    html += "</tbody></table>";
    table.innerHTML = html;

    // Explanation
    const resultBox = document.getElementById("resultBox");
    if (typeof marked !== "undefined") {
        resultBox.innerHTML = marked.parse(data.explanation || "No explanation provided.");
    } else {
        resultBox.innerText = data.explanation || "No explanation provided.";
    }
    latestResultMarkdown = data.explanation || "";

    // Thread
    document.getElementById("threadInfo").textContent = `Thread ID: ${data.thread_id}`;

    // Show
    const section = document.getElementById("resultSection");
    section.classList.remove("hidden");
    section.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitClaim() {
    hideError();
    const narrative = document.getElementById("narrativeInput").value.trim();
    const partsRaw = document.getElementById("partsInput").value.trim();

    if (!narrative) { showError("Please enter the technician narrative."); return; }
    if (!partsRaw) { showError("Please enter at least one requested part."); return; }

    const parts = partsRaw.split("\n").map(p => p.trim()).filter(p => p);
    if (parts.length === 0) { showError("Please enter at least one valid part."); return; }

    setLoading(true);
    try {
        const resp = await fetch("/api/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ narrative, parts, thread_id: currentThreadId })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.error || "Something went wrong.");
        currentThreadId = data.thread_id;
        localStorage.setItem("claim_thread_id", currentThreadId);
        renderResults(data);
    } catch (e) {
        showError(e.message);
    } finally {
        setLoading(false);
    }
}

function copyResult() {
    const box = document.getElementById("resultBox");
    const text = box.innerText;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(".copy-btn");
        const old = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = old, 1400);
    }).catch(() => showError("Could not copy result."));
}

function downloadPDF() {
    const content = document.getElementById("pdfContent");
    if (!content) { showError("No results to download."); return; }
    const btn = document.querySelector(".download-btn");
    const old = btn.textContent;
    btn.textContent = "Preparing PDF...";
    btn.disabled = true;
    html2pdf().set({
        margin: 0.5, filename: "claim-validation-report.pdf",
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: "#ffffff" },
        jsPDF: { unit: "in", format: "a4", orientation: "portrait" },
    }).from(content).save().then(() => {
        btn.textContent = old; btn.disabled = false;
    }).catch(() => { btn.textContent = old; btn.disabled = false; showError("Could not download PDF."); });
}

document.addEventListener("keydown", e => { if (e.ctrlKey && e.key === "Enter") submitClaim(); });
