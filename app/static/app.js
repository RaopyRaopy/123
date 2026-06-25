const state = {
  sessionId: crypto.randomUUID(),
  socket: null,
  socketReady: false,
  plannerMode: "rules",
};

// ── Global button ripple effect ──
document.addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  ripple.style.width = ripple.style.height = size + "px";
  ripple.style.left = (e.clientX - rect.left - size / 2) + "px";
  ripple.style.top = (e.clientY - rect.top - size / 2) + "px";
  btn.appendChild(ripple);
  ripple.addEventListener("animationend", () => ripple.remove());
});

// ── Staggered reveal helper ──
let messageCounter = 0;
function resetMessageCounter() { messageCounter = 0; }

const messageList = document.querySelector("#messageList");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const connectionState = document.querySelector("#connectionState");
const profileTags = document.querySelector("#profileTags");
const historyList = document.querySelector("#historyList");
const itineraryView = document.querySelector("#itineraryView");
const tripMeta = document.querySelector("#tripMeta");
const reminderList = document.querySelector("#reminderList");
const resetButton = document.querySelector("#resetButton");
const modeButtons = document.querySelectorAll("[data-mode]");
const mapContainer = document.querySelector("#mapContainer");
const amapContainer = document.querySelector("#amapContainer");
const nearbyPoiList = document.querySelector("#nearbyPoiList");

let amapInstance = null;
let amapReady = null;

function renderConnectionState() {
  const dotClass = state.socketReady ? "online" : "offline";
  const modeText = state.plannerMode === "agent" ? "Agent 模式" : "规则模式";
  const serviceText = state.socketReady ? "本地服务已连接" : "本地服务";
  connectionState.innerHTML = `<span class="connection-dot ${dotClass}"></span>${serviceText} · ${modeText}`;
}

function loadAmap() {
  if (amapReady) return amapReady;
  amapReady = fetch("/api/config/amap-key")
    .then(r => r.json())
    .then(d => {
      if (!d.ok) throw new Error("no key");
      if (d.securityCode) {
        window._AMapSecurityConfig = { securityJsCode: d.securityCode };
      }
      return new Promise((resolve, reject) => {
        if (window.AMap && window.AMap.Map) { resolve(window.AMap); return; }
        const script = document.createElement("script");
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${d.key}`;
        script.onload = () => {
          const check = () => {
            if (window.AMap && window.AMap.Map) resolve(window.AMap);
            else setTimeout(check, 100);
          };
          check();
        };
        script.onerror = () => reject(new Error("amap script load failed"));
        document.head.appendChild(script);
      });
    })
    .catch(err => { console.warn("Amap load failed:", err); amapReady = null; return null; });
  return amapReady;
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/chat`);
  state.socket = socket;

  socket.addEventListener("open", () => {
    state.socketReady = true;
    renderConnectionState();
  });

  socket.addEventListener("close", () => {
    state.socketReady = false;
    renderConnectionState();
    if (planningElement) {
      hidePlanning();
      appendMessage("assistant", "本地服务连接中断，请再发送一次。");
    }
  });

  socket.addEventListener("message", (event) => {
    hidePlanning();
    const payload = JSON.parse(event.data);
    handleAssistant(payload);
  });
}

async function loadProfile() {
  const response = await fetch("/api/profile/demo-user");
  const data = await response.json();
  renderProfile(data);
}

function renderProfile(data) {
  profileTags.innerHTML = "";
  const tags = data.profile?.tags || [];
  for (const tag of tags) {
    const item = document.createElement("span");
    item.className = "tag";
    item.textContent = tag;
    profileTags.appendChild(item);
  }

  historyList.innerHTML = "";
  for (const trip of data.trip_history || []) {
    const item = document.createElement("article");
    item.className = "history-item";
    item.innerHTML = `<strong>${escapeHtml(trip.destination || "历史行程")}</strong><span>${escapeHtml(trip.note || "")}</span>`;
    historyList.appendChild(item);
  }
}

function setPlannerMode(mode, announce = false) {
  if (!["rules", "agent"].includes(mode)) return;
  state.plannerMode = mode;
  modeButtons.forEach((button) => {
    const active = button.dataset.mode === mode;
    button.setAttribute("aria-pressed", String(active));
  });
  renderConnectionState();
  if (announce) {
    toast(mode === "agent" ? "已切换到 Agent 模式" : "已切换到规则模式");
  }
}

function appendMessage(role, content) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.textContent = content;
  item.style.animationDelay = `${messageCounter * 0.06}s`;
  messageCounter++;
  messageList.appendChild(item);
  messageList.scrollTo({ top: messageList.scrollHeight, behavior: "smooth" });
  return item;
}

let planningElement = null;

function showPlanning() {
  // Remove any existing planning indicator
  hidePlanning();

  // Chat loading bubble
  planningElement = document.createElement("div");
  planningElement.className = "message planning";
  planningElement.innerHTML =
    '规划中<span class="planning-dots"><span></span><span></span><span></span></span>';
  messageList.appendChild(planningElement);
  messageList.scrollTo({ top: messageList.scrollHeight, behavior: "smooth" });

  // Itinerary panel loading state
  tripMeta.textContent = "规划中...";
  tripMeta.classList.add("planning-meta");
  itineraryView.innerHTML = `<div class="planning-state">
    <div>
      <div class="planning-spinner"></div>
      <p>正在为你规划行程...</p>
    </div>
  </div>`;
  itineraryView.className = "itinerary-view";
}

function hidePlanning() {
  if (planningElement) {
    planningElement.remove();
    planningElement = null;
  }
  tripMeta.classList.remove("planning-meta");
}

function renderMemoryHits(hits) {
  if (!hits?.length) return;
  const strip = document.createElement("div");
  strip.className = "memory-strip";
  for (const hit of hits.slice(0, 4)) {
    const item = document.createElement("span");
    item.textContent = `${hit.title}: ${hit.detail}`;
    strip.appendChild(item);
  }
  messageList.appendChild(strip);
  messageList.scrollTop = messageList.scrollHeight;
}

function handleAssistant(payload) {
  state.sessionId = payload.session_id || state.sessionId;
  appendMessage("assistant", payload.reply);
  renderMemoryHits(payload.memory_hits);
  renderItinerary(payload.itinerary, payload, payload.map_markers);
  renderMap(payload.map_markers);
  renderNearbyPois(payload.nearby_pois);
  renderReminders(payload.reminders);
  loadProfile();
}

async function sendMessage(message) {
  appendMessage("user", message);
  input.value = "";
  input.style.height = "auto";

  showPlanning();

  const payload = {
    user_id: "demo-user",
    session_id: state.sessionId,
    message,
    mode: state.plannerMode,
  };

  if (state.socketReady) {
    state.socket.send(JSON.stringify(payload));
    return;
  }

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    hidePlanning();
    handleAssistant(await response.json());
  } catch (error) {
    hidePlanning();
    appendMessage("assistant", "本地服务暂时没有返回结果，请检查后端是否已启动。");
    toast("本地服务请求失败");
    console.error("Chat request failed:", error);
  }
}

function renderItinerary(itinerary, payload = {}, mapMarkers = []) {
  itineraryView.innerHTML = "";

  if (!itinerary) {
    tripMeta.textContent =
      payload.debug?.intent === "not_collected" ? "暂未收录" : "待生成";
    itineraryView.className = "itinerary-view";
    const emptyDiv = document.createElement("div");
    emptyDiv.className = "empty-state";
    emptyDiv.innerHTML = `<div>
      <div class="empty-illustration">&#128747;</div>
      <p>${payload.debug?.intent === "not_collected" ? "该城市暂未收录" : "还没有行程"}</p>
      <p style="font-size:12px;color:var(--slate);margin-top:4px">
        ${payload.debug?.intent === "not_collected" ? "试试其他城市吧" : "开始对话来规划你的旅行"}
      </p>
    </div>`;
    itineraryView.appendChild(emptyDiv);
    return;
  }

  tripMeta.textContent = `${itinerary.destination} · ${itinerary.days}天`;
  itineraryView.className = "itinerary-view";

  const summary = document.createElement("div");
  summary.className = "trip-summary";
  const budget = itinerary.budget ? ` 预算 ${itinerary.budget} 元。` : "";
  summary.textContent = `${itinerary.summary}${budget}`;
  itineraryView.appendChild(summary);

  if (itinerary.highlights?.length) {
    const row = document.createElement("div");
    row.className = "highlights-row";
    for (const h of itinerary.highlights) {
      const tag = document.createElement("span");
      tag.textContent = h;
      row.appendChild(tag);
    }
    itineraryView.appendChild(row);
  }

  if (itinerary.avoid?.length) {
    const avoid = document.createElement("div");
    avoid.className = "avoid-list";
    for (const item of itinerary.avoid) {
      const tag = document.createElement("span");
      tag.textContent = "避雷: " + item;
      avoid.appendChild(tag);
    }
    itineraryView.appendChild(avoid);
  }

  for (const day of itinerary.day_plans) {
    const card = document.createElement("article");
    card.className = "day-card";
    const marker = mapMarkers.find(m => m.day === day.day);
    let foodsHtml = "";
    if (marker?.nearby_foods?.length) {
      foodsHtml = `<div class="food-list"><div class="food-header">附近美食</div>` +
        marker.nearby_foods.map(f =>
          `<div class="food-item"><span class="food-dot"></span><span class="food-name">${escapeHtml(f.name)}</span><span class="food-cat">${escapeHtml(f.category || '')}</span></div>`
        ).join("") + `</div>`;
    }
    card.innerHTML = `
      <header>
        <h3>D${day.day} ${escapeHtml(day.city)}</h3>
        <small>${escapeHtml(day.theme)}</small>
      </header>
      <ul>
        <li>上午：${escapeHtml(day.morning)}</li>
        <li>下午：${escapeHtml(day.afternoon)}</li>
        <li>晚上：${escapeHtml(day.evening)}</li>
        <li>交通：${escapeHtml(day.transport)}</li>
        <li>天气：${escapeHtml(day.weather_tip)}</li>
      </ul>
      ${foodsHtml}
    `;
    itineraryView.appendChild(card);
  }
}

async function renderMap(markers) {
  if (!markers?.length) {
    mapContainer.classList.add("hidden");
    if (amapInstance) { amapInstance.destroy(); amapInstance = null; }
    return;
  }

  const AMap = await loadAmap();
  if (!AMap) {
    mapContainer.classList.add("hidden");
    return;
  }

  mapContainer.classList.remove("hidden");

  if (amapInstance) { amapInstance.destroy(); amapInstance = null; }

  // Amap REST API returns GCJ-02 natively — no conversion needed
  const map = new AMap.Map("amapContainer", {
    zoom: 13,
    center: [markers[0].lng, markers[0].lat],
    resizeEnable: true,
  });
  amapInstance = map;

  markers.forEach((m, i) => {
    const content = `<div class="amap-marker-dot" style="background:${i === 0 ? '#2C1810' : '#B8935C'}">${m.day}</div>`;
    const marker = new AMap.Marker({
      position: [m.lng, m.lat],
      content: content,
      offset: new AMap.Pixel(-14, -14),
    });
    marker.setMap(map);
    if (m.name) {
      marker.setLabel({
        content: `<span class="amap-label">${escapeHtml(m.name)}</span>`,
        direction: "bottom",
        offset: new AMap.Pixel(0, 6),
      });
    }
    // rich info window on click
    if (m.morning || m.afternoon) {
      let foodsHtml = "";
      if (m.nearby_foods?.length) {
        foodsHtml = `<div class="food-list"><div class="food-header">附近美食</div>` +
          m.nearby_foods.map(f =>
            `<div class="food-item"><span class="food-dot"></span><span class="food-name">${escapeHtml(f.name)}</span><span class="food-cat">${escapeHtml(f.category || '')}</span></div>`
          ).join("") + `</div>`;
      }
      const infoHtml = `
        <div class="info-window">
          <div class="iw-header">D${m.day} ${escapeHtml(m.name)} <span>${escapeHtml(m.theme || '')}</span></div>
          <div class="iw-list">
            ${m.morning ? `<div class="iw-row"><span class="iw-icon">&#9788;</span>上午：${escapeHtml(m.morning)}</div>` : ''}
            ${m.afternoon ? `<div class="iw-row"><span class="iw-icon">&#9789;</span>下午：${escapeHtml(m.afternoon)}</div>` : ''}
            ${m.evening ? `<div class="iw-row"><span class="iw-icon">&#9790;</span>晚上：${escapeHtml(m.evening)}</div>` : ''}
            ${m.transport ? `<div class="iw-row"><span class="iw-icon">&#9992;</span>交通：${escapeHtml(m.transport)}</div>` : ''}
          </div>
          ${foodsHtml}
        </div>`;
      marker.on("click", () => {
        const iw = new AMap.InfoWindow({ content: infoHtml, offset: new AMap.Pixel(0, -36) });
        iw.open(map, marker.getPosition());
      });
    }
  });

  // draw driving route between consecutive stops
  if (markers.length >= 2) {
    const DrivingRoute = AMap.DrivingRoute;
    if (DrivingRoute) {
      for (let i = 0; i < markers.length - 1; i++) {
        const dr = new DrivingRoute({
          map: map,
          policy: AMap.DrivingPolicy.LEAST_TIME,
          hideMarkers: true,
          autoFitView: false,
          lineOptions: { strokeColor: "#C2856B", strokeWeight: 3, strokeOpacity: 0.7, strokeStyle: "dashed" },
        });
        dr.search(
          [markers[i].lng, markers[i].lat],
          [markers[i + 1].lng, markers[i + 1].lat],
          (status, result) => { /* quiet */ }
        );
      }
    }
  }

  if (markers.length > 1) {
    map.setFitView(null, false, [80, 60, 80, 80]);
  }
}

function renderNearbyPois(pois) {
  nearbyPoiList.innerHTML = "";
  if (!pois?.length) {
    nearbyPoiList.classList.add("hidden");
    return;
  }
  nearbyPoiList.classList.remove("hidden");
  const header = document.createElement("div");
  header.className = "poi-header";
  header.textContent = "附近推荐";
  nearbyPoiList.appendChild(header);

  const icons = ["🏛", "🌳", "☕", "🍜", "📸", "🏯"];
  for (let i = 0; i < pois.length; i++) {
    const poi = pois[i];
    const item = document.createElement("div");
    item.className = "nearby-poi-item";
    item.innerHTML = `
      <span class="poi-icon">${icons[i % icons.length]}</span>
      <div>
        <div class="poi-name">${escapeHtml(poi.name)}</div>
        <div class="poi-addr">${escapeHtml(poi.address || poi.category || "")}</div>
      </div>
    `;
    nearbyPoiList.appendChild(item);
  }
}

function renderReminders(reminders) {
  reminderList.innerHTML = "";
  for (const reminder of reminders || []) {
    const item = document.createElement("article");
    item.className = "reminder-item";
    item.innerHTML = `<strong>${escapeHtml(reminder.timing)} · ${escapeHtml(reminder.title)}</strong><span>${escapeHtml(reminder.detail)}</span>`;
    reminderList.appendChild(item);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ── Events ──
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message) sendMessage(message);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 140) + "px";
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    const message = input.value.trim();
    if (message) sendMessage(message);
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    sendMessage(button.dataset.prompt);
    toast("已发送快捷指令");
  });
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setPlannerMode(button.dataset.mode, true);
  });
});

resetButton.addEventListener("click", () => {
  messageList.innerHTML = "";
  resetMessageCounter();
  itineraryView.className = "itinerary-view";
  itineraryView.innerHTML = `<div class="empty-state">
    <div>
      <div class="empty-illustration">&#128747;</div>
      <p>还没有行程</p>
      <p style="font-size:12px;color:var(--slate);margin-top:4px">开始对话来规划你的旅行</p>
    </div>
  </div>`;
  reminderList.innerHTML = "";
  tripMeta.textContent = "待生成";
  state.sessionId = crypto.randomUUID();
  mapContainer.classList.add("hidden");
  if (amapInstance) { amapInstance.destroy(); amapInstance = null; }
  nearbyPoiList.classList.add("hidden");
  nearbyPoiList.innerHTML = "";
  toast("对话已清空");
});

const clearPrefsButton = document.querySelector("#clearPrefsButton");
clearPrefsButton.addEventListener("click", async () => {
  if (!confirm("确定要清除所有偏好记忆和反馈吗？此操作不可撤销。")) return;
  try {
    const resp = await fetch("/api/profile/demo-user/preferences", { method: "DELETE" });
    const data = await resp.json();
    if (data.ok) {
      profileTags.innerHTML = "";
      historyList.innerHTML = "";
      toast(data.message || "偏好记忆已清除");
      loadProfile();
    }
  } catch {
    toast("清除失败，请稍后重试");
  }
});

// ── Init ──
appendMessage(
  "assistant",
  "你好！我支持重庆、北京、上海、成都、杭州、西安、广州、桂林、苏州和长沙的旅行规划。告诉我你想去的城市、天数和预算吧。"
);
setPlannerMode(state.plannerMode);
connectSocket();
loadProfile();
