import { apiRequest, getUser } from './api.js';
import { logout } from './auth.js';

function setGreeting(containerId, title) {
  const user = getUser();
  const target = document.getElementById(containerId);
  if (!target) {
    return;
  }

  const name = user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() : '';
  target.textContent = name ? `${title} - ${name}` : title;
}

function wireCommonUi() {
  const logoutButton = document.getElementById('logout-btn');
  if (logoutButton) {
    logoutButton.addEventListener('click', logout);
  }

  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById(tab);
      if (panel) {
        panel.classList.add('active');
      }
    });
  });
}

function renderAlerts(targetId, rows) {
  const target = document.getElementById(targetId);
  if (!target) {
    return;
  }

  target.innerHTML = '';
  if (!rows || rows.length === 0) {
    target.innerHTML = '<p class="muted">No active alerts.</p>';
    return;
  }

  rows.slice(0, 8).forEach((row) => {
    const div = document.createElement('div');
    div.className = `alert-row ${row.severity || 'low'}`;
    div.innerHTML = `
      <strong>${row.warehouse_name || row.facility_name || 'Facility'}</strong>
      <p>${row.message || 'No details available.'}</p>
    `;
    target.appendChild(div);
  });
}

async function loadStats(targetId, includeForecast = true) {
  const target = document.getElementById(targetId);
  if (!target) {
    return [];
  }

  const rows = await apiRequest('/facility-ops/stats/');
  target.innerHTML = '';
  rows.slice(0, 6).forEach((row) => {
    const card = document.createElement('article');
    card.className = 'card';
    const forecastMessage = includeForecast
      ? 'Forecast: loading...'
      : 'Forecast: disabled for reporter tier.';
    card.innerHTML = `
      <h3>${row.warehouse_name}</h3>
      <p class="kpi">${row.patient_footfall} patients</p>
      <p class="muted">Beds ${row.beds_occupied}/${row.beds_total} | Doctors ${row.doctors_present}/${row.doctors_scheduled}</p>
      <p id="forecast-${row.warehouse}" class="muted">${forecastMessage}</p>
    `;
    target.appendChild(card);
  });

  return rows;
}

async function loadForecastForStats(statsRows) {
  const inventory = await apiRequest('/products/inventory/');
  const byWarehouse = {};
  inventory.forEach((item) => {
    if (!byWarehouse[item.warehouse]) {
      byWarehouse[item.warehouse] = item;
    }
  });

  for (const row of statsRows.slice(0, 6)) {
    const firstProduct = byWarehouse[row.warehouse];
    const target = document.getElementById(`forecast-${row.warehouse}`);
    if (!target || !firstProduct) {
      continue;
    }

    try {
      const forecast = await apiRequest(`/ai/forecast/${row.warehouse}/${firstProduct.product}/`);
      target.textContent = `Forecast: ${forecast.recommendation}`;
    } catch (error) {
      target.textContent = 'Forecast: unavailable for this facility.';
    }
  }
}

function wireAssistant(formId, inputId, outputId) {
  const form = document.getElementById(formId);
  const input = document.getElementById(inputId);
  const output = document.getElementById(outputId);
  if (!form || !input || !output) {
    return;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) {
      return;
    }

    output.innerHTML += `<div class="bubble user">${query}</div>`;
    input.value = '';

    try {
      const data = await apiRequest('/ai/assistant/', {
        method: 'POST',
        body: { query },
      });

      output.innerHTML += `<div class="bubble ai">${data.answer}</div>`;
      output.scrollTop = output.scrollHeight;
    } catch (error) {
      output.innerHTML += `<div class="bubble ai">Assistant error: ${error.message}</div>`;
    }
  });
}

function wireOcr(formId, fileId, resultId) {
  const form = document.getElementById(formId);
  const fileInput = document.getElementById(fileId);
  const result = document.getElementById(resultId);
  if (!form || !fileInput || !result) {
    return;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      return;
    }

    const payload = new FormData();
    payload.append('image', file);

    try {
      const data = await apiRequest('/ai/ocr-intake/', {
        method: 'POST',
        body: payload,
      });
      result.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      result.textContent = `OCR failed: ${error.message}`;
    }
  });
}

async function loadRedistribution(targetId) {
  const target = document.getElementById(targetId);
  if (!target) {
    return;
  }

  try {
    const rows = await apiRequest('/ai/redistribution-suggestions/');
    if (!rows.length) {
      target.innerHTML = '<p class="muted">No suggestions currently.</p>';
      return;
    }

    target.innerHTML = '';
    rows.slice(0, 8).forEach((row) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <h3>${row.product}</h3>
        <p>${row.from_warehouse_name} -> ${row.to_warehouse_name}</p>
        <p class="kpi">${row.suggested_quantity}</p>
        <p class="muted">${row.reasoning}</p>
      `;
      target.appendChild(card);
    });
  } catch (error) {
    target.innerHTML = `<p class="muted">Could not load redistribution data: ${error.message}</p>`;
  }
}

async function loadAlertsPanels() {
  const facilityAlerts = await apiRequest('/facility-ops/alerts/');
  renderAlerts('alerts-feed', facilityAlerts);

  const inventoryAlerts = await apiRequest('/analytics/inventory-alerts/');
  renderAlerts('inventory-alert-feed', inventoryAlerts);
}

export async function initAdminDashboard() {
  wireCommonUi();
  setGreeting('page-title', 'Tier 1 Admin Dashboard');
  wireAssistant('assistant-form', 'assistant-query', 'assistant-feed');
  wireOcr('ocr-form', 'ocr-file', 'ocr-result');

  const statsRows = await loadStats('stats-grid');
  await Promise.all([
    loadAlertsPanels(),
    loadForecastForStats(statsRows),
    loadRedistribution('redistribution-grid'),
  ]);
}

export async function initFacilityDashboard() {
  wireCommonUi();
  setGreeting('page-title', 'Tier 2 Facility Dashboard');
  wireAssistant('assistant-form', 'assistant-query', 'assistant-feed');
  wireOcr('ocr-form', 'ocr-file', 'ocr-result');

  const statsRows = await loadStats('stats-grid');
  await Promise.all([
    loadAlertsPanels(),
    loadForecastForStats(statsRows),
  ]);
}

export async function initReporterDashboard() {
  wireCommonUi();
  setGreeting('page-title', 'Tier 3 Reporter Dashboard');

  await loadStats('stats-grid', false);
  await Promise.all([
    loadAlertsPanels(),
  ]);
}
