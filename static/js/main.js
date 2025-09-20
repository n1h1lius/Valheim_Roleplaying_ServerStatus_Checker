const API_BASE = '';
const SERVER_IP = '159.223.189.211';
const QUERY_PORT = 2457;
const REFRESH_INTERVAL = 30000; // 30s, cámbialo si quieres

let lastServerStatus = null; // null = desconocido, true = online, false = offline

// Toggle section
function toggleSection(id) {
  const section = document.getElementById(id + "-container") || document.getElementById(id);
  if (section.style.display === "none") {
    section.style.display = "block";
  } else {
    section.style.display = "none";
  }
}

function toggleTheme() {
  const current = document.body.getAttribute("data-theme");
  document.body.setAttribute("data-theme", current === "dark" ? "light" : "dark");
  localStorage.setItem("theme", document.body.getAttribute("data-theme"));
}

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
}

async function fetchStatus() {
  document.getElementById('server-status').textContent = '⏳';
  try {
    const res = await fetch(`${API_BASE}/api/status?ip=${SERVER_IP}&query_port=${QUERY_PORT}`);
    const data = await res.json();
    const isOnline = data.ok;

    document.getElementById('server-status').textContent = isOnline ? '✅ Online' : '❌ Offline';
    document.getElementById('server-ip').textContent = data.ip;
    document.getElementById('player-count').textContent = data.player_count;
    document.getElementById('max-players').textContent = data.info.max_players || 'N/A';
    document.getElementById('ping').textContent = data.ping_ms;

    document.getElementById('server-info').innerHTML = `
      <div><b>Server Name:</b> ${data.info.server_name}</div>
      <div><b>Map Name:</b> ${data.info.map_name}</div>
      <div><b>Game Version:</b> ${data.info.version}</div>
      <div><b>Server Type:</b> ${data.info.server_type}</div>
    `;
    document.getElementById('mods-info').innerHTML = `<div><b>Keywords:</b> ${data.info.keywords || 'N/A'}</div>`;
    document.getElementById('ports-info').innerHTML = `<div><b>Game Port:</b> ${data.game_port}</div><div><b>Query Port:</b> ${data.query_port}</div>`;

    // Players table
    const playersTableBody = document.getElementById('players-table-body');
    if (isOnline && Array.isArray(data.players)) {
      playersTableBody.innerHTML = data.players.length > 0
        ? data.players.map(p => `
            <tr>
              <td>${p.name || 'N/A'}</td>
              <td>${p.score}</td>
              <td>${p.duration}</td>
              <td>${formatDuration(p.duration)}</td>
            </tr>
          `).join('')
        : `<tr><td colspan="4">No players online</td></tr>`;
    } else {
      playersTableBody.innerHTML = `<tr><td colspan="4">Server offline</td></tr>`;
    }

    document.getElementById('raw-json').textContent = JSON.stringify(data, null, 2);

    // 🚨 Notificación + sonido si el server estaba caído y ahora vuelve
    if (lastServerStatus === false && isOnline === true) {
      triggerNotification();
    }

    lastServerStatus = isOnline;

  } catch(err) {
    console.error(err);
  }
}

// 🚨 Notificación + sonido
function triggerNotification() {
  if (Notification.permission === "granted") {
    new Notification("✅ Valheim Server is ONLINE!", {
      body: "The server is back up and running!",
      icon: "/static/icon.png" // opcional, pon tu icono aquí
    });
  }
  // 🔊 Sonido
  const audio = new Audio("/static/notify.mp3"); // coloca el archivo en static/
  audio.play().catch(err => console.warn("Sound play blocked:", err));
}

function requestNotificationPermission() {
  if ("Notification" in window) {
    Notification.requestPermission().then(permission => {
      console.log("Notification permission:", permission);
    });
  }
}

function initUI() {
  const userLang = (navigator.language || 'en').slice(0,2);
  const t = translations[userLang] || translations.en;

  document.getElementById('title').textContent = t.title;
  document.getElementById('lbl-status').textContent = t.labels.status;
  document.getElementById('lbl-ip').textContent = t.labels.ip;
  document.getElementById('lbl-players').textContent = t.labels.players;
  document.getElementById('lbl-maxplayers').textContent = t.labels.maxplayers;
  document.getElementById('lbl-ping').textContent = t.labels.ping;

  document.getElementById('btn-server-info').textContent = t.sections.server_info;
  document.getElementById('btn-mods-info').textContent = t.sections.mods_info;
  document.getElementById('btn-ports-info').textContent = t.sections.ports_info;
  document.getElementById('btn-players-info').textContent = t.sections.players_info;
  document.getElementById('btn-refresh').textContent = t.sections.refresh;
  document.getElementById('btn-json').textContent = t.sections.show_json;

  // Theme init
  const savedTheme = localStorage.getItem("theme");
  if(savedTheme){
    document.body.setAttribute("data-theme", savedTheme);
  } else {
    document.body.setAttribute("data-theme", window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }
}

window.onload = () => {
  initUI();
  requestNotificationPermission();
  fetchStatus();
  setInterval(fetchStatus, REFRESH_INTERVAL); // 🔄 auto-refresh
};
