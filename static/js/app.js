let priceChart = null;

// Search + filter
document.getElementById("search").addEventListener("input", filterTable);
document.getElementById("filter-action").addEventListener("change", filterTable);

function filterTable() {
  const search = document.getElementById("search").value.toLowerCase();
  const action = document.getElementById("filter-action").value;
  document.querySelectorAll("#market-table tbody tr").forEach(row => {
    const name = row.dataset.name || "";
    const act  = row.dataset.action || "";
    const matchSearch = !search || name.includes(search);
    const matchAction = !action || act === action;
    row.style.display = matchSearch && matchAction ? "" : "none";
  });
}

async function showChart(itemId, itemName) {
  const modal = document.getElementById("chart-modal");
  modal.classList.remove("hidden");
  document.getElementById("modal-title").textContent = `Historique — ${itemName}`;

  const res = await fetch(`/api/item/${itemId}/history`);
  const history = await res.json();

  const labels = history.map(h => h.date);
  const prices = history.map(h => h.price);

  if (priceChart) priceChart.destroy();

  const ctx = document.getElementById("price-chart").getContext("2d");
  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Prix",
        data: prices,
        borderColor: "#6c63ff",
        backgroundColor: "rgba(108,99,255,0.08)",
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.y.toLocaleString("fr-FR")} 💰`
          }
        }
      },
      scales: {
        x: { ticks: { color: "#8892b0" }, grid: { color: "#2a2f4a" } },
        y: { ticks: { color: "#8892b0" }, grid: { color: "#2a2f4a" } }
      }
    }
  });

  // Fetch recommendation for this item
  const itemsRes = await fetch("/api/items");
  const items = await itemsRes.json();
  const rec = items.find(i => i.id === itemId);
  if (rec) {
    const color = rec.action === "acheter" ? "#22c55e" : rec.action === "vendre" ? "#ef4444" : "#f59e0b";
    document.getElementById("modal-rec").innerHTML = `
      <strong style="color:${color}">${rec.action.toUpperCase()}</strong>
      &nbsp;·&nbsp; Confiance : ${rec.confidence}%
      &nbsp;·&nbsp; ${rec.reason}
    `;
  }
}

function closeChart() {
  document.getElementById("chart-modal").classList.add("hidden");
  if (priceChart) { priceChart.destroy(); priceChart = null; }
}

async function refreshData() {
  const res = await fetch("/api/items");
  const items = await res.json();
  const tbody = document.querySelector("#market-table tbody");
  tbody.innerHTML = items.map(item => `
    <tr class="row-${item.action}" data-action="${item.action}" data-name="${item.name.toLowerCase()}" data-id="${item.id}"
        onclick="showChart('${item.id}', '${item.name}')">
      <td><strong>${item.name}</strong></td>
      <td>${item.current_price.toLocaleString("fr-FR")} 💰</td>
      <td>${item.avg_price.toLocaleString("fr-FR")}</td>
      <td>${item.min_price.toLocaleString("fr-FR")}</td>
      <td>${item.max_price.toLocaleString("fr-FR")}</td>
      <td class="trend ${item.trend_pct > 0 ? "trend-up" : item.trend_pct < 0 ? "trend-down" : ""}">
        ${item.trend_pct > 0 ? "▲" : item.trend_pct < 0 ? "▼" : "—"} ${item.trend_pct.toFixed(1)}%
      </td>
      <td><span class="badge badge-${item.action}">${item.action}</span></td>
      <td>
        <div class="confidence-bar"><div class="confidence-fill" style="width:${item.confidence}%"></div></div>
        ${item.confidence}%
      </td>
      <td class="reason-cell">${item.reason}</td>
    </tr>
  `).join("");
  filterTable();
}

// Close modal on outside click
document.getElementById("chart-modal").addEventListener("click", e => {
  if (e.target === e.currentTarget) closeChart();
});

// Auto-refresh every 60s
setInterval(refreshData, 60_000);
