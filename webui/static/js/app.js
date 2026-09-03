const VC = {
  state: {},
  options: {},
  apiKey: "",
  saveTimer: null,
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

function icon(name) {
  const svg = {
    video: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3Z" fill="currentColor" stroke="none"/>',
    api: '<rect x="6" y="6" width="12" height="12" rx="3"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m12 0h4M2 15h4m12 0h4"/>',
    cutting: '<circle cx="6" cy="7" r="3"/><circle cx="6" cy="17" r="3"/><path d="m8.5 8.5 10 7M8.5 15.5l10-7"/>',
    captions: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 10h4m2 0h4M7 14h3m2 0h5"/>',
    face: '<path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3m13 5h3a2 2 0 0 0 2-2v-3M8.5 10a3.5 3.5 0 0 1 7 0v1.5a3.5 3.5 0 0 1-7 0Z"/>',
    generate: '<path d="m12 3 1.2 4.2L17 9l-3.8 1.8L12 15l-1.2-4.2L7 9l3.8-1.8ZM18.5 14l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7Z" fill="currentColor" stroke="none"/>',
    sliders: '<path d="M4 6h16M4 12h10M4 18h13"/><circle cx="14" cy="6" r="2" fill="currentColor"/><circle cx="20" cy="12" r="2" fill="currentColor"/><circle cx="11" cy="18" r="2" fill="currentColor"/>',
    subtitles: '<path d="M4 6h16v12H4z"/><path d="M7 10h10M7 14h7"/>',
    folder: '<path d="M3 7h6l2 2h10v10H3z"/>',
    segments: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    actions: '<path d="M5 3v18l15-9z" fill="currentColor" stroke="none"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none"/>',
    terminal: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m7 10 3 2-3 2M13 14h4"/>',
    gallery: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M4 7h16M10 7V5h4v2m-5 0l.5 12h5L15 7"/>',
  }[name] || "";
  const fill = name === "generate" || name === "actions" || name === "stop" ? ' data-fill="1"' : "";
  return `<span class="vc-icon" aria-hidden="true"><svg viewBox="0 0 24 24"${fill}>${svg}</svg></span>`;
}

function $(id) {
  return document.getElementById(id);
}

function setTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("vc-theme", next);
  const btn = $("vc-theme-toggle");
  if (btn) btn.textContent = next === "light" ? "Dark" : "Light";
}

function showView(name) {
  document.querySelectorAll(".vc-view").forEach((el) => {
    const active = el.id === `view-${name}`;
    el.hidden = !active;
    el.classList.toggle("is-active", active);
  });
  document.querySelectorAll(".vc-nav-item").forEach((btn) => {
    btn.classList.toggle("vc-nav-active", btn.dataset.view === name);
  });
  const heading = {
    create: { eyebrow: "New production", title: "Create your next short", copy: "Choose the source, tune clip selection, and control framing and captions in one focused workspace.", num: "01", meta: "Workspace" },
    editor: { eyebrow: "Caption studio", title: "Edit cues and re-burn", copy: "Load a project file, fix timing and wording, then render captions onto a clip.", num: "02", meta: "Editor" },
    library: { eyebrow: "Archive", title: "Browse finished clips", copy: "Open a project gallery and review the shorts already on disk.", num: "03", meta: "Library" },
    settings: { eyebrow: "Workspace", title: "Providers and defaults", copy: "Set the AI backend, API key, and model used for clip selection.", num: "04", meta: "Settings" },
  }[name];
  if (!heading) return;
  const root = document.querySelector(".vc-workspace-heading");
  if (!root) return;
  root.querySelector(".vc-eyebrow").textContent = heading.eyebrow;
  root.querySelector("h1").textContent = heading.title;
  root.querySelector("p").textContent = heading.copy;
  root.querySelector(".vc-workspace-meta span").textContent = heading.num;
  root.querySelector(".vc-workspace-meta small").textContent = heading.meta;
}

function fillSelect(el, values, selected) {
  if (!el) return;
  el.innerHTML = "";
  (values || []).forEach((value) => {
    const opt = document.createElement("option");
    if (Array.isArray(value)) {
      opt.value = value[1];
      opt.textContent = value[0];
    } else {
      opt.value = value;
      opt.textContent = value;
    }
    el.appendChild(opt);
  });
  if (selected != null && [...el.options].some((o) => o.value === String(selected))) {
    el.value = selected;
  }
  bindDropdown(el);
}

function closeDropdowns(except) {
  document.querySelectorAll(".vc-dropdown-list").forEach((list) => {
    if (list !== except) list.hidden = true;
  });
}

function bindDropdown(select) {
  if (!select || select.tagName !== "SELECT") return;
  let wrap = select.closest(".vc-dropdown");
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.className = "vc-dropdown";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    const list = document.createElement("div");
    list.className = "vc-dropdown-list";
    list.hidden = true;
    wrap.appendChild(list);
    select.addEventListener("mousedown", (event) => {
      event.preventDefault();
      renderDropdown(select);
      const open = list.hidden;
      closeDropdowns(list);
      list.hidden = !open;
      if (!list.hidden) select.focus();
    });
    select.addEventListener("keydown", (event) => {
      if (event.key === "Escape") list.hidden = true;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        renderDropdown(select);
        list.hidden = !list.hidden;
      }
    });
  }
  renderDropdown(select);
}

function renderDropdown(select) {
  const list = select.parentElement?.querySelector(".vc-dropdown-list");
  if (!list) return;
  list.innerHTML = "";
  [...select.options].forEach((opt) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vc-dropdown-option" + (opt.value === select.value ? " is-active" : "");
    btn.textContent = opt.textContent;
    btn.addEventListener("click", () => {
      select.value = opt.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      list.hidden = true;
      renderDropdown(select);
    });
    list.appendChild(btn);
  });
}

function enhanceSelects(root = document) {
  root.querySelectorAll("select.vc-select").forEach(bindDropdown);
}

function fieldValue(el) {
  if (!el) return undefined;
  if (el.type === "checkbox") return el.checked;
  if (el.type === "number" || el.dataset.num === "1") {
    const n = Number(el.value);
    return Number.isFinite(n) ? n : el.value;
  }
  return el.value;
}

function setField(el, value) {
  if (!el) return;
  if (el.type === "radio") return;
  if (el.type === "checkbox") {
    el.checked = Boolean(value);
    return;
  }
  if (el.type === "file") return;
  if (value == null) return;
  el.value = value;
}

function collectNamed(root) {
  const data = {};
  root.querySelectorAll("[name]").forEach((el) => {
    if (el.disabled || el.type === "file") return;
    if (el.type === "radio" && !el.checked) return;
    data[el.name] = fieldValue(el);
  });
  return data;
}

function scheduleSave(payload) {
  clearTimeout(VC.saveTimer);
  VC.saveTimer = setTimeout(() => {
    api("/api/settings", { method: "POST", body: JSON.stringify({ data: payload }) }).catch(() => {});
  }, 350);
}

document.addEventListener("DOMContentLoaded", async () => {
  const savedTheme = localStorage.getItem("vc-theme") || "dark";
  setTheme(savedTheme);
  $("vc-theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    setTheme(next);
    api("/api/settings", { method: "POST", body: JSON.stringify({ data: { theme: next } }) }).catch(() => {});
  });
  document.querySelectorAll(".vc-nav-item").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  try {
    const boot = await api("/api/ui-state");
    VC.state = boot.state || {};
    VC.options = boot.options || {};
    VC.apiKey = boot.api_key || "";
    if (window.initCreate) window.initCreate();
    if (window.initEditor) window.initEditor();
    if (window.initLibrary) window.initLibrary();
    if (window.initSettings) window.initSettings();
    enhanceSelects();
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".vc-dropdown")) closeDropdowns();
    });
  } catch (err) {
    $("view-create").innerHTML = `<section class="vc-card"><h3>Startup error</h3><p class="vc-help">${err.message}</p></section>`;
  }
});
