// F1 Race Predictor Frontend Client Logic

let currentRaceId = null;
let originalRaceData = null;
let accuracyChart = null;

// On document load
document.addEventListener("DOMContentLoaded", () => {
    loadDashboardMetrics();
    loadRacesCalendar();
});

// Fetch overall model accuracies and comparisons
async function loadDashboardMetrics() {
    try {
        const response = await fetch("/api/metrics");
        const data = await response.json();
        
        // Populate stats counters
        document.getElementById("val-before-acc").innerText = (data.before_accuracy * 100).toFixed(1) + "%";
        document.getElementById("val-after-acc").innerText = (data.after_accuracy * 100).toFixed(1) + "%";
        document.getElementById("val-overlap").innerText = data.after_top3_avg_overlap.toFixed(2) + " / 3";
        document.getElementById("val-races-count").innerText = data.total_races;
        
        // Render Chart
        renderPerformanceChart(data.comparisons);
        
    } catch (error) {
        console.error("Error loading dashboard metrics:", error);
    }
}

// Render Chart.js visualization comparing before and after qualifying predictions
function renderPerformanceChart(comparisons) {
    const ctx = document.getElementById("accuracyChart").getContext("2d");
    
    // Sort chronological order (by race_id number)
    const sortedComps = [...comparisons].sort((a, b) => {
        return parseInt(a.race_id.split('_')[1]) - parseInt(b.race_id.split('_')[1]);
    });
    
    const labels = sortedComps.map(c => c.race.replace(" Grand Prix", ""));
    
    // Convert boolean predictions to cumulative correct matches
    let beforeCumulative = 0;
    let afterCumulative = 0;
    
    const beforeData = [];
    const afterData = [];
    
    sortedComps.forEach(c => {
        if (c.before_correct) beforeCumulative++;
        if (c.after_correct) afterCumulative++;
        
        beforeData.push(beforeCumulative);
        afterData.push(afterCumulative);
    });

    if (accuracyChart) {
        accuracyChart.destroy();
    }

    // High fidelity neon colors for line charts
    accuracyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Before Qualifying (Cumulative Correct)',
                    data: beforeData,
                    borderColor: '#4f6d7a',
                    backgroundColor: 'rgba(79, 109, 122, 0.05)',
                    borderWidth: 3,
                    tension: 0.2,
                    pointBackgroundColor: '#4f6d7a',
                    pointHoverRadius: 6
                },
                {
                    label: 'After Qualifying (Cumulative Correct)',
                    data: afterData,
                    borderColor: '#e10600',
                    backgroundColor: 'rgba(225, 6, 0, 0.05)',
                    borderWidth: 3,
                    tension: 0.2,
                    pointBackgroundColor: '#e10600',
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#a0a0ab',
                        font: { family: 'Inter', size: 10 }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#a0a0ab', font: { size: 9 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#a0a0ab', stepSize: 1 }
                }
            }
        }
    });
}

// Fetch all 2025 races
async function loadRacesCalendar() {
    const listContainer = document.getElementById("races-list-container");
    listContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch("/api/races");
        const races = await response.json();
        
        listContainer.innerHTML = "";
        
        races.forEach(race => {
            const card = document.createElement("div");
            card.className = `race-item-card`;
            card.id = `race-card-${race.race_id}`;
            card.onclick = () => selectRace(race.race_id);
            
            const badgeClass = race.completed ? 'badge-completed' : 'badge-upcoming';
            const badgeText = race.completed ? 'Completed' : 'Upcoming';
            
            let winnerHtml = "";
            if (race.completed && race.actual_winner) {
                winnerHtml = `<span class="winner-indicator">🏆 Winner: ${race.actual_winner}</span>`;
            }
            
            card.innerHTML = `
                <div class="race-info">
                    <span class="race-name">${race.race}</span>
                    <span class="race-date">${formatDate(race.date)}</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.25rem;">
                    <span class="race-badge ${badgeClass}">${badgeText}</span>
                    ${winnerHtml}
                </div>
            `;
            
            listContainer.appendChild(card);
        });
        
    } catch (error) {
        listContainer.innerHTML = '<p class="text-secondary" style="padding: 1rem;">Failed to load races list.</p>';
        console.error("Error loading races calendar:", error);
    }
}

// Selecting a race from the explorer panel
async function selectRace(raceId) {
    currentRaceId = raceId;
    
    // Highlight active card
    document.querySelectorAll(".race-item-card").forEach(c => c.classList.remove("active"));
    const activeCard = document.getElementById(`race-card-${raceId}`);
    if (activeCard) activeCard.classList.add("active");
    
    // Hide empty state, show workspace
    document.getElementById("empty-state-panel").classList.add("hidden");
    const workspace = document.getElementById("workspace-panel");
    workspace.classList.add("hidden");
    
    // Render detail loading state
    const consolePanel = document.getElementById("prediction-console");
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "loading-spinner";
    loadingDiv.id = "details-loading-spinner";
    consolePanel.appendChild(loadingDiv);
    
    try {
        const response = await fetch(`/api/race_details/${raceId}`);
        const raceData = await response.json();
        
        originalRaceData = raceData;
        
        // Remove loading state
        const spinner = document.getElementById("details-loading-spinner");
        if (spinner) spinner.remove();
        
        // Populate workspace elements
        document.getElementById("selected-race-title").innerText = raceData.race;
        document.getElementById("selected-race-date").innerText = `Race Date: ${formatDate(raceData.date)}`;
        
        const statusBadge = document.getElementById("race-status-badge");
        statusBadge.className = `workspace-badge ${raceData.completed ? 'badge-completed' : 'badge-upcoming'}`;
        statusBadge.innerText = raceData.completed ? 'Completed Results' : 'Upcoming / Custom Simulation';
        
        // Populate podium & standings
        updatePodiumAndStandings(raceData.drivers, raceData.completed);
        
        // Populate custom grid inputs
        populateCustomGridFields(raceData.drivers);
        
        // Show workspace
        workspace.classList.remove("hidden");
        switchTab('predictions'); // Switch to predictions tab by default
        
    } catch (error) {
        const spinner = document.getElementById("details-loading-spinner");
        if (spinner) spinner.remove();
        alert("Error loading race details: " + error.message);
        console.error("Error loading race details:", error);
    }
}

// Render the 3D podium and standings table
function updatePodiumAndStandings(drivers, completed) {
    // Sort by predicted After Qualifying model rank to build podium and default predicted table
    const afterRankedDrivers = [...drivers].sort((a, b) => a.after_rank - b.after_rank);
    
    // P1, P2, P3
    const p1 = afterRankedDrivers[0] || { driver: "--", team: "--", grid: "--" };
    const p2 = afterRankedDrivers[1] || { driver: "--", team: "--", grid: "--" };
    const p3 = afterRankedDrivers[2] || { driver: "--", team: "--", grid: "--" };
    
    document.getElementById("podium-p1-name").innerText = p1.driver;
    document.getElementById("podium-p1-team").innerText = p1.team;
    document.getElementById("podium-p1-grid").innerText = p1.grid;
    
    document.getElementById("podium-p2-name").innerText = p2.driver;
    document.getElementById("podium-p2-team").innerText = p2.team;
    document.getElementById("podium-p2-grid").innerText = p2.grid;
    
    document.getElementById("podium-p3-name").innerText = p3.driver;
    document.getElementById("podium-p3-team").innerText = p3.team;
    document.getElementById("podium-p3-grid").innerText = p3.grid;
    
    // Standings body
    const tbody = document.getElementById("standings-body");
    tbody.innerHTML = "";
    
    // Sort table rows: completed races by actual position; upcoming races by predicted after qualifying rank
    const tableSorted = [...drivers].sort((a, b) => {
        if (completed && a.actual_position && b.actual_position) {
            return a.actual_position - b.actual_position;
        }
        return a.after_rank - b.after_rank;
    });
    
    tableSorted.forEach((drv, idx) => {
        const row = document.createElement("tr");
        
        let rowHighlightClass = "";
        if ((completed && drv.actual_position === 1) || (!completed && drv.after_rank === 1)) {
            rowHighlightClass = "highlight-first";
        } else if ((completed && drv.actual_position === 2) || (!completed && drv.after_rank === 2)) {
            rowHighlightClass = "highlight-second";
        } else if ((completed && drv.actual_position === 3) || (!completed && drv.after_rank === 3)) {
            rowHighlightClass = "highlight-third";
        }
        
        row.className = rowHighlightClass;
        
        const displayPos = completed ? (drv.actual_position || "--") : (drv.after_rank);
        const actualPosText = completed ? (drv.actual_position || "Retired/DNF") : "--";
        
        row.innerHTML = `
            <td><div class="pos-indicator">${displayPos}</div></td>
            <td class="driver-tag-cell">${drv.driver}</td>
            <td class="team-cell">${drv.team}</td>
            <td style="text-align: center; font-weight: 500;">${drv.grid}</td>
            <td class="col-before" style="text-align: center; font-weight: 600; color: #4f6d7a;">${drv.before_rank}</td>
            <td class="col-after" style="text-align: center; font-weight: 600; color: var(--f1-red);">${drv.after_rank}</td>
            <td class="col-actual" style="text-align: center; font-weight: 700;">${actualPosText}</td>
        `;
        
        tbody.appendChild(row);
    });
}

// Populate the customizer inputs
function populateCustomGridFields(drivers) {
    const list = document.getElementById("custom-grid-list");
    list.innerHTML = "";
    
    // Sort drivers alphabetically for inputs
    const sortedDrivers = [...drivers].sort((a, b) => a.driver.localeCompare(b.driver));
    
    sortedDrivers.forEach(drv => {
        const row = document.createElement("div");
        row.className = "grid-input-row";
        
        row.innerHTML = `
            <div class="driver-detail">
                <span class="driver-tag-cell" style="font-size: 1.05rem;">${drv.driver}</span>
                <span class="team-cell" style="font-size: 0.8rem;">(${drv.team})</span>
            </div>
            <input type="number" class="custom-grid-num-input" 
                   data-driver="${drv.driver}" 
                   value="${drv.grid}" min="1" max="22">
        `;
        
        list.appendChild(row);
    });
}

// Handle Custom Predictions API submission
async function runCustomPrediction() {
    const runBtn = document.getElementById("btn-run-prediction");
    const originalText = runBtn.innerText;
    runBtn.innerText = "Simulating... 🏎";
    runBtn.disabled = true;
    
    const customGrids = {};
    document.querySelectorAll(".custom-grid-num-input").forEach(input => {
        customGrids[input.getAttribute("data-driver")] = parseInt(input.value) || 20;
    });
    
    try {
        const response = await fetch("/api/predict_custom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                race_id: currentRaceId,
                grids: customGrids
            })
        });
        
        const data = await response.json();
        
        if (data.error) throw new Error(data.error);
        
        // Show status badge as simulated
        const statusBadge = document.getElementById("race-status-badge");
        statusBadge.className = "workspace-badge badge-upcoming";
        statusBadge.innerText = "Custom Simulation Outcome";
        
        // Update standings and podium with simulated values (pretending completed = false so that it sorts by simulated outcome)
        updatePodiumAndStandings(data.drivers, false);
        
        // Switch tab back to standings
        switchTab('predictions');
        
    } catch (error) {
        alert("Simulation Error: " + error.message);
        console.error(error);
    } finally {
        runBtn.innerText = originalText;
        runBtn.disabled = false;
    }
}

// Reset fields to original grid positions
function resetCustomGrids() {
    if (originalRaceData) {
        populateCustomGridFields(originalRaceData.drivers);
        
        const statusBadge = document.getElementById("race-status-badge");
        statusBadge.className = `workspace-badge ${originalRaceData.completed ? 'badge-completed' : 'badge-upcoming'}`;
        statusBadge.innerText = originalRaceData.completed ? 'Completed Results' : 'Upcoming / Custom Simulation';
        
        updatePodiumAndStandings(originalRaceData.drivers, originalRaceData.completed);
    }
}

// Helper: Tab Switching
function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.add("hidden"));
    
    if (tabName === 'predictions') {
        document.getElementById("tab-btn-predictions").classList.add("active");
        document.getElementById("tab-predictions").classList.remove("hidden");
    } else if (tabName === 'customizer') {
        document.getElementById("tab-btn-customizer").classList.add("active");
        document.getElementById("tab-customizer").classList.remove("hidden");
    }
}

// Helper: Format Date
function formatDate(dateStr) {
    if (!dateStr) return "";
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateStr).toLocaleDateString(undefined, options);
}
