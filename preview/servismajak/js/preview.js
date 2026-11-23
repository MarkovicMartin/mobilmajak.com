(() => {
  const DATA = {
    meta: null,
    devices: null,
    services: null,
    locations: null,
    pages: null,
  };

  const DAY = ["", "Po", "Út", "St", "Čt", "Pá", "So", "Ne"];

  async function loadJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Nelze načíst ${path}`);
    return res.json();
  }

  async function ensureData(needed = ["meta", "devices"]) {
    const jobs = [];
    if (needed.includes("meta") && !DATA.meta) jobs.push(loadJson("data/meta.json").then((d) => (DATA.meta = d)));
    if (needed.includes("devices") && !DATA.devices) jobs.push(loadJson("data/devices.json").then((d) => (DATA.devices = d)));
    if (needed.includes("services") && !DATA.services) jobs.push(loadJson("data/services-by-category.json").then((d) => (DATA.services = d)));
    if (needed.includes("locations") && !DATA.locations) jobs.push(loadJson("data/locations.json").then((d) => (DATA.locations = d)));
    if (needed.includes("pages") && !DATA.pages) jobs.push(loadJson("data/pages.json").then((d) => (DATA.pages = d)));
    await Promise.all(jobs);
    return DATA;
  }

  function formatPrice(value, currency = "CZK") {
    if (value == null || value === "") return "—";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    const formatted = new Intl.NumberFormat("cs-CZ").format(n);
    return currency === "CZK" ? `${formatted} Kč` : `${formatted} ${currency}`;
  }

  function liveBase() {
    return (DATA.meta && DATA.meta.liveBase) || "https://servismajak.cz";
  }

  function liveDeviceUrl(url) {
    return `${liveBase()}/zarizeni/${url}`;
  }

  function livePageUrl(slug) {
    return `${liveBase()}/${slug}`;
  }

  function findNodeByUrl(url, nodes = null, trail = []) {
    const list = nodes || (DATA.devices && DATA.devices.roots) || [];
    for (const node of list) {
      const next = trail.concat(node);
      if (node.url === url) return { node, trail: next };
      const hit = findNodeByUrl(url, node.children || [], next);
      if (hit) return hit;
    }
    return null;
  }

  function findNodeById(id, nodes = null, trail = []) {
    const list = nodes || (DATA.devices && DATA.devices.roots) || [];
    for (const node of list) {
      const next = trail.concat(node);
      if (String(node.id) === String(id)) return { node, trail: next };
      const hit = findNodeById(id, node.children || [], next);
      if (hit) return hit;
    }
    return null;
  }

  function servicesFor(categoryId) {
    if (!DATA.services) return [];
    return DATA.services[String(categoryId)] || [];
  }

  function shortServiceTitle(title, deviceTitle) {
    let t = title || "";
    if (deviceTitle) {
      const prefixes = [
        `${deviceTitle} - `,
        `${deviceTitle} – `,
        `Apple ${deviceTitle} - `,
        `Apple ${deviceTitle} – `,
      ];
      for (const p of prefixes) {
        if (t.startsWith(p)) return t.slice(p.length);
      }
    }
    const dash = t.indexOf(" - ");
    if (dash > 0 && dash < 40) return t.slice(dash + 3);
    return t;
  }

  function hoursLabel(hours) {
    if (!hours || !hours.length) return "Otevírací dobu upřesníme na pobočce";
    const byDay = {};
    hours.forEach((h) => {
      const key = `${h.opensAt}–${h.closesAt}`;
      byDay[h.day] = key;
    });
    const parts = [];
    for (let d = 1; d <= 7; d += 1) {
      const slot = byDay[d];
      if (!slot || slot === "00:00–00:00") continue;
      parts.push(`${DAY[d]} ${slot}`);
    }
    return parts.join(" · ") || "Zavřeno / dle dohody";
  }

  function phoneLink(phone) {
    if (!phone) return "";
    const digits = String(phone).replace(/\D/g, "");
    const nice = digits.startsWith("420") ? `+${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 9)} ${digits.slice(9)}` : `+${digits}`;
    return `<a href="tel:+${digits}">${nice.trim()}</a>`;
  }

  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function renderRoots(target) {
    const roots = DATA.devices.roots || [];
    target.innerHTML = "";
    const grid = el('<div class="device-type-grid"></div>');
    roots.forEach((root) => {
      grid.appendChild(
        el(`<a class="device-type-card" href="katalog.html?c=${encodeURIComponent(root.url)}">
          ${root.img ? `<img class="device-type-ico" src="${root.img}" alt="">` : `<span class="device-type-ico">◆</span>`}
          <strong>${root.title}</strong>
          <span>vybrat značku</span>
        </a>`)
      );
    });
    target.appendChild(grid);
  }

  function renderChildren(target, node, trail) {
    const children = node.children || [];
    target.innerHTML = "";
    const grid = el('<div class="brand-grid"></div>');
    children
      .slice()
      .sort((a, b) => (a.sortId || 0) - (b.sortId || 0) || a.title.localeCompare(b.title, "cs"))
      .forEach((child) => {
        const kidCount = (child.children || []).length;
        const hint = kidCount ? "vybrat model" : "zobrazit opravy";
        grid.appendChild(
          el(`<a class="brand-card" href="katalog.html?c=${encodeURIComponent(child.url)}">
            ${child.img ? `<img src="${child.img}" alt="" style="max-height:36px;width:auto;margin-bottom:.4rem">` : ""}
            <strong>${child.title}</strong>
            <span>${hint}</span>
          </a>`)
        );
      });
    target.appendChild(grid);
  }

  const SERVICE_GROUPS = [
    {
      id: "mech",
      title: "Mechanické poškození",
      hint: "Displej, kryt, tlačítka, voda",
      ico: "◫",
      test: (t) =>
        /displej|lcd|oled|kryt|sklo|sklick|tlačit|tlacit|oxidac|kapalin|vod[aeě]|lepen/.test(t),
    },
    {
      id: "audio",
      title: "Problémy se zvukem",
      hint: "Sluchátko, zvonek, reproduktor",
      ico: "♪",
      test: (t) => /sluchatk|zvonek|reproduktor/.test(t) && !/nabij|mikrofon/.test(t),
    },
    {
      id: "charge",
      title: "Problémy s nabíjením",
      hint: "Baterie, nabíjení, konektor",
      ico: "ϟ",
      test: (t) => /bater|nabij|konektor|mikrofon/.test(t),
    },
    {
      id: "camera",
      title: "Problémy s kamerou",
      hint: "Přední i zadní fotoaparát",
      ico: "◎",
      test: (t) => /fotoapar|kamer|sklick/.test(t),
    },
    {
      id: "soft",
      title: "Software a data",
      hint: "Záloha, kód, diagnostika",
      ico: "⌘",
      test: (t) => /zaloh|softwar|kod|diagnost|bezpecnost/.test(t),
    },
    {
      id: "other",
      title: "Další opravy",
      hint: "Ostatní servisní úkony",
      ico: "◆",
      test: () => true,
    },
  ];

  function classifyService(title) {
    const t = normalize(title);
    for (const g of SERVICE_GROUPS) {
      if (g.id === "other") continue;
      if (g.test(t)) return g.id;
    }
    return "other";
  }

  function renderServices(target, node) {
    const list = servicesFor(node.id)
      .slice()
      .sort((a, b) => Number(a.price || 0) - Number(b.price || 0) || String(a.title).localeCompare(String(b.title), "cs"));
    target.innerHTML = "";
    if (!list.length) {
      target.appendChild(el(`<p class="hero-copy">Pro tento model teď nemáme nabídku oprav.</p>`));
      return;
    }

    const buckets = {};
    SERVICE_GROUPS.forEach((g) => {
      buckets[g.id] = [];
    });
    list.forEach((svc) => {
      buckets[classifyService(svc.title)].push(svc);
    });

    const board = el('<div class="service-board"></div>');
    SERVICE_GROUPS.forEach((g) => {
      const items = buckets[g.id];
      if (!items.length) return;
      const group = el(`<section class="service-group">
        <div class="service-group-head">
          <span class="ico">${g.ico}</span>
          <div>
            <h2>${g.title}</h2>
            <p>${g.hint}</p>
          </div>
        </div>
      </section>`);
      items.forEach((svc) => {
        const title = shortServiceTitle(svc.title, node.title);
        group.appendChild(
          el(`<a class="service-row" href="oprava-v2.html">
            <span><strong>${title}</strong></span>
            <b class="price">${formatPrice(svc.price, svc.currency)}</b>
            <span class="book">Rezervovat</span>
          </a>`)
        );
      });
      board.appendChild(group);
    });
    target.appendChild(board);
  }

  function renderCatalogPage() {
    const params = new URLSearchParams(location.search);
    const url = params.get("c");
    const crumb = document.querySelector("[data-crumb]");
    const title = document.querySelector("[data-title]");
    const lead = document.querySelector("[data-lead]");
    const mount = document.querySelector("[data-catalog]");
    if (!mount) return;

    if (!url) {
      if (crumb) crumb.textContent = "Výběr zařízení";
      if (title) title.textContent = "Jaké zařízení chcete opravit?";
      if (lead) lead.textContent = "Vyberte typ zařízení a pak model.";
      renderRoots(mount);
      return;
    }

    const hit = findNodeByUrl(url);
    if (!hit) {
      if (title) title.textContent = "Zařízení nenalezeno";
      mount.innerHTML = `<p><a href="katalog.html">← Zpět na výběr</a></p>`;
      return;
    }

    const { node, trail } = hit;
    if (crumb) {
      crumb.innerHTML = trail
        .map((n, i) =>
          i === trail.length - 1
            ? n.title
            : `<a href="katalog.html?c=${encodeURIComponent(n.url)}">${n.title}</a>`
        )
        .join(" / ");
    }
    if (title) title.textContent = node.title;
    const kids = node.children || [];
    const svcs = servicesFor(node.id);
    if (lead) {
      if (kids.length) lead.textContent = "Vyberte značku nebo model.";
      else if (svcs.length) lead.textContent = "";
      else lead.textContent = "Pro tento model teď nemáme nabídku oprav.";
      lead.hidden = !lead.textContent;
    }

    if (kids.length) renderChildren(mount, node, trail);
    else renderServices(mount, node, trail);
  }

  function renderLocations(target, { limit = 99 } = {}) {
    if (!target || !DATA.locations) return;
    target.innerHTML = "";
    DATA.locations.slice(0, limit).forEach((loc) => {
      const name = loc.name.replace(/^Mobil Maják\s*-\s*/i, "");
      const maps = loc.gps
        ? `https://www.google.com/maps/search/?api=1&query=${loc.gps.lat},${loc.gps.lng}`
        : "#";
      const phone = phoneLink(loc.contact && loc.contact.phone);
      target.appendChild(
        el(`<article class="branch-card">
          <span class="status">● ${hoursLabel(loc.openingHours).includes("Zavřeno") ? "Dle otevírací doby" : "Otevřeno"}</span>
          <h3>${name}</h3>
          <p>${loc.address}, ${loc.city}${loc.postCode ? ` · ${loc.postCode}` : ""}</p>
          <p>${phone}${loc.contact && loc.contact.email ? ` · <a href="mailto:${loc.contact.email}">${loc.contact.email}</a>` : ""}</p>
          <p style="color:var(--muted);font-size:.82rem;font-weight:600">${hoursLabel(loc.openingHours)}</p>
          <a href="${maps}" target="_blank" rel="noopener">Trasa a mapa <span>→</span></a>
        </article>`)
      );
    });
  }

  function renderPages(target, { limit = 12 } = {}) {
    if (!target || !DATA.pages) return;
    const pages = (Array.isArray(DATA.pages) ? DATA.pages : DATA.pages.items || [])
      .filter((p) => p.active !== false)
      .slice(0, limit);
    target.innerHTML = "";
    pages.forEach((p) => {
      target.appendChild(
        el(`<article class="article" style="display:block">
          <small>${p.shortTitle || "Rada"}</small>
          <h3>${p.title}</h3>
          <p>${p.description || "Rada ze servisu."}</p>
        </article>`)
      );
    });
  }

  function normalize(s) {
    return String(s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function searchCatalog(query, { limit = 40 } = {}) {
    const q = normalize(query).trim();
    if (!q) return { devices: [], services: [], pages: [] };
    const tokens = q.split(/\s+/).filter(Boolean);
    const match = (text) => {
      const n = normalize(text);
      return tokens.every((t) => n.includes(t));
    };

    const devices = [];
    const walk = (nodes, trail) => {
      (nodes || []).forEach((n) => {
        const path = trail.concat(n);
        if (match(n.title) || match(path.map((x) => x.title).join(" "))) {
          devices.push({ node: n, trail: path });
        }
        walk(n.children || [], path);
      });
    };
    walk(DATA.devices.roots, []);

    const services = [];
    Object.entries(DATA.services || {}).forEach(([cid, list]) => {
      list.forEach((svc) => {
        if (match(svc.title)) {
          const hit = findNodeById(cid);
          services.push({ svc, categoryId: cid, trail: hit ? hit.trail : [] });
        }
      });
    });

    const pages = (Array.isArray(DATA.pages) ? DATA.pages : [])
      .filter((p) => match(p.title) || match(p.description) || match(p.slug))
      .map((p) => ({ page: p }));

    return {
      devices: devices.slice(0, limit),
      services: services.slice(0, limit),
      pages: pages.slice(0, 10),
    };
  }

  function renderSearch() {
    const params = new URLSearchParams(location.search);
    const q = params.get("q") || "";
    const input = document.querySelector('#q, input[name="q"]');
    if (input && !input.value) input.value = q;
    const title = document.querySelector("[data-search-title]");
    const mount = document.querySelector("[data-search-results]");
    if (!mount) return;
    if (title) title.textContent = q ? `Výsledky pro „${q}“` : "Zadejte hledaný výraz";
    if (!q) {
      mount.innerHTML = `<p class="hero-copy">Zkuste např. <a href="hledani-v2.html?q=iphone%2013%20displej">iPhone 13 displej</a> nebo <a href="hledani-v2.html?q=samsung%20baterie">Samsung baterie</a>.</p>`;
      return;
    }
    const { devices, services, pages } = searchCatalog(q);
    const parts = [];
    if (devices.length) {
      parts.push(`<p class="category-label">Zařízení (${devices.length})</p>`);
      devices.forEach(({ node, trail }) => {
        const path = trail
          .slice(0, -1)
          .map((t) => t.title)
          .join(" · ");
        parts.push(`<a class="result" href="katalog.html?c=${encodeURIComponent(node.url)}"><span><strong>${node.title}</strong><span>${path || "Katalog"}</span></span><span>Opravy →</span></a>`);
      });
    }
    if (services.length) {
      parts.push(`<p class="category-label">Opravy (${services.length})</p>`);
      services.forEach(({ svc, trail }) => {
        const device = trail[trail.length - 1];
        const href = device ? `katalog.html?c=${encodeURIComponent(device.url)}` : liveBase();
        parts.push(`<a class="result" href="${href}"><span><strong>${shortServiceTitle(svc.title, device && device.title)}</strong><span>${svc.title}</span></span><span class="result-price">${formatPrice(svc.price, svc.currency)}</span></a>`);
      });
    }
    if (pages.length) {
      parts.push(`<p class="category-label">Rady</p>`);
      pages.forEach(({ page }) => {
        parts.push(`<div class="result"><span><strong>${page.title}</strong><span>${page.description || "Rada ze servisu"}</span></span></div>`);
      });
    }
    if (!parts.length) parts.push(`<p>Nic nenalezeno. Zkuste kratší dotaz, nebo otevřete <a href="katalog.html">katalog</a>.</p>`);
    mount.innerHTML = parts.join("");
  }

  function collectModels(brand) {
    const out = [];
    // Jen listy = konkrétní modely, žádné mezikategorie / řady
    const walk = (n) => {
      const kids = n.children || [];
      if (!kids.length) {
        out.push({ value: String(n.id), label: n.title, url: n.url, title: n.title });
        return;
      }
      kids.forEach(walk);
    };
    (brand.children || []).forEach(walk);
    if (!(brand.children || []).length) {
      out.push({ value: String(brand.id), label: brand.title, url: brand.url, title: brand.title });
    }
    const seen = new Set();
    return out
      .filter((m) => (seen.has(m.value) ? false : (seen.add(m.value), true)))
      .sort((a, b) => a.label.localeCompare(b.label, "cs"));
  }

  function pickPreferredService(list, ecosystem) {
    // Z exportu MyRepair: u Apple nejvíc „displej“, u Android „baterie“
    const order =
      ecosystem === "android"
        ? ["bater", "displej", "lcd", "oled", "nabij", "konektor", "kryt", "sklo"]
        : ["displej", "lcd", "oled", "bater", "nabij", "konektor", "kryt", "sklo"];
    const rank = (title) => {
      const t = normalize(title);
      const idx = order.findIndex((k) => t.includes(k));
      return idx === -1 ? 50 : idx;
    };
    return list
      .slice()
      .sort((a, b) => rank(a.title) - rank(b.title) || Number(a.price || 0) - Number(b.price || 0))[0] || null;
  }

  function detectBrowserEcosystem() {
    const ua = navigator.userAgent || "";
    const isSafari = /Safari/i.test(ua) && !/Chrome|Chromium|CriOS|Edg|OPR|Firefox|Android/i.test(ua);
    const isChromeFamily = /Chrome|Chromium|CriOS|Edg|OPR/i.test(ua) || /Android/i.test(ua);
    if (isSafari || /iPhone|iPad/i.test(ua)) return "apple";
    if (isChromeFamily) return "android";
    return "apple";
  }

  function pickPopularModel(models, ecosystem) {
    if (!models.length) return null;
    const scored = models.map((m) => {
      const t = normalize(m.title);
      let score = servicesFor(m.value).length;
      if (ecosystem === "apple") {
        if (/^iphone 15$/.test(t)) score += 100;
        else if (/iphone 15/.test(t)) score += 80;
        else if (/iphone 14/.test(t)) score += 60;
        else if (/iphone 13/.test(t)) score += 40;
        else if (/iphone/.test(t)) score += 10;
      } else {
        if (/galaxy s24/.test(t)) score += 100;
        else if (/galaxy s23/.test(t)) score += 80;
        else if (/galaxy a5[45]/.test(t) || /galaxy a3[45]/.test(t)) score += 50;
        else if (/galaxy s2[0-9]/.test(t)) score += 40;
        else if (/galaxy/.test(t)) score += 15;
        else if (/redmi|poco|xiaomi/.test(t)) score += 8;
      }
      return { m, score };
    });
    scored.sort((a, b) => b.score - a.score);
    return scored[0].m;
  }

  async function detectVisitorDevice() {
    const ua = navigator.userAgent || "";
    const ecosystem = detectBrowserEcosystem();
    const isIPad = /iPad/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const isIPhone = /iPhone/.test(ua);
    const isAndroid = /Android/.test(ua);
    const isTablet = isIPad || (isAndroid && !/Mobile/.test(ua));
    let modelHint = "";
    let brandHint = "";
    try {
      if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
        const hi = await navigator.userAgentData.getHighEntropyValues(["model", "platform"]);
        modelHint = hi.model || "";
        if (/iPhone|iPad|Macintosh/i.test(hi.platform || "") || isIPhone || isIPad) brandHint = "Apple";
        else if (/Android/i.test(hi.platform || "") || isAndroid) brandHint = "Samsung";
      }
    } catch (_) {
      /* ignore */
    }
    if (!brandHint) {
      if (isIPhone || isIPad || ecosystem === "apple") brandHint = "Apple";
      else if (/Samsung/i.test(ua)) brandHint = "Samsung";
      else if (/Xiaomi|Redmi|POCO/i.test(ua)) brandHint = "Xiaomi";
      else if (/Huawei/i.test(ua)) brandHint = "Huawei";
      else if (/Honor/i.test(ua)) brandHint = "Honor";
      else if (isAndroid || ecosystem === "android") brandHint = "Samsung";
    }
    return {
      kind: isTablet ? "tablet" : "phone",
      ecosystem,
      brandHint,
      modelHint: String(modelHint || "").trim(),
    };
  }

  function matchModel(models, hint) {
    if (!hint || !models.length) return null;
    const n = normalize(hint);
    return (
      models.find((m) => normalize(m.title) === n) ||
      models.find((m) => normalize(m.label) === n) ||
      models.find((m) => normalize(m.title).includes(n) || n.includes(normalize(m.title))) ||
      models.find((m) => normalize(m.label).includes(n)) ||
      null
    );
  }

  function createCombo(mount, { hint, placeholder, onChange }) {
    mount.innerHTML = "";
    mount.classList.add("finder-combo");
    const trigger = el(`<button type="button" class="finder-combo-trigger"><span><strong>${placeholder}</strong><small>${hint}</small></span></button>`);
    const panel = el(`<div class="finder-combo-panel" hidden>
      <input type="search" placeholder="Psát pro hledání…" autocomplete="off">
      <ul class="finder-combo-list"></ul>
    </div>`);
    mount.appendChild(trigger);
    mount.appendChild(panel);
    const input = panel.querySelector("input");
    const listEl = panel.querySelector("ul");
    let options = [];
    let value = "";
    let enabled = true;

    const close = () => {
      mount.classList.remove("is-open");
      panel.hidden = true;
    };
    const open = () => {
      if (!enabled) return;
      document.querySelectorAll(".finder-combo.is-open").forEach((c) => {
        if (c !== mount) {
          c.classList.remove("is-open");
          const p = c.querySelector(".finder-combo-panel");
          if (p) p.hidden = true;
        }
      });
      mount.classList.add("is-open");
      panel.hidden = false;
      input.value = "";
      renderList("");
      input.focus();
    };

    const renderList = (q) => {
      const nq = normalize(q);
      const filtered = options.filter((o) => !nq || normalize(o.label).includes(nq));
      listEl.innerHTML = "";
      if (!filtered.length) {
        listEl.appendChild(el(`<li class="finder-combo-empty">Nic nenalezeno</li>`));
        return;
      }
      filtered.slice(0, 80).forEach((o) => {
        const li = document.createElement("li");
        const btn = el(`<button type="button">${o.label}</button>`);
        if (String(o.value) === String(value)) btn.classList.add("is-active");
        btn.addEventListener("click", () => {
          value = o.value;
          trigger.querySelector("strong").textContent = o.label;
          close();
          onChange(o);
        });
        li.appendChild(btn);
        listEl.appendChild(li);
      });
    };

    trigger.addEventListener("click", () => {
      if (mount.classList.contains("is-open")) close();
      else open();
    });
    input.addEventListener("input", () => renderList(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    return {
      setOptions(next, { keepValue = false } = {}) {
        options = next || [];
        enabled = options.length > 0;
        mount.classList.toggle("is-disabled", !enabled);
        if (!keepValue || !options.some((o) => String(o.value) === String(value))) {
          value = "";
          trigger.querySelector("strong").textContent = placeholder;
        } else {
          const cur = options.find((o) => String(o.value) === String(value));
          if (cur) trigger.querySelector("strong").textContent = cur.label;
        }
      },
      setValue(val) {
        const opt = options.find((o) => String(o.value) === String(val));
        if (!opt) return false;
        value = opt.value;
        trigger.querySelector("strong").textContent = opt.label;
        onChange(opt);
        return true;
      },
      getValue: () => value,
      close,
    };
  }

  function initFinder() {
    const root = document.querySelector("[data-finder]");
    if (!root) return;
    const priceEl = root.querySelector("[data-finder-price]");
    const btn = root.querySelector("[data-finder-btn]");
    const roots = (DATA.devices.roots || []).slice().sort((a, b) => (a.sortId || 0) - (b.sortId || 0));
    let selectedType = null;
    let selectedBrand = null;
    let selectedModel = null;
    let selectedService = null;
    let modelsById = {};
    let ecosystem = detectBrowserEcosystem();

    const syncBtn = () => {
      if (!btn) return;
      if (selectedService && selectedModel) {
        btn.href = "oprava-v2.html";
        btn.textContent = "Zobrazit detail opravy";
      } else if (selectedModel) {
        btn.href = `katalog.html?c=${encodeURIComponent(selectedModel.url)}`;
        btn.textContent = "Zobrazit opravy modelu";
      } else if (selectedBrand) {
        btn.href = `katalog.html?c=${encodeURIComponent(selectedBrand.url)}`;
        btn.textContent = "Zobrazit značku";
      } else {
        btn.href = "katalog.html";
        btn.textContent = "Vybrat v katalogu";
      }
    };

    const serviceCombo = createCombo(root.querySelector('[data-combo="service"]'), {
      hint: "Vybraná oprava",
      placeholder: "Vyberte opravu",
      onChange: (opt) => {
        selectedService = opt.raw;
        if (priceEl) priceEl.textContent = opt.raw ? formatPrice(opt.raw.price, opt.raw.currency) : "";
        syncBtn();
      },
    });

    const modelCombo = createCombo(root.querySelector('[data-combo="model"]'), {
      hint: "Vybraný model",
      placeholder: "Vyberte model",
      onChange: (opt) => {
        selectedModel = opt;
        selectedService = null;
        if (priceEl) priceEl.textContent = "";
        const list = servicesFor(opt.value)
          .slice()
          .sort((a, b) => Number(a.price || 0) - Number(b.price || 0) || String(a.title).localeCompare(String(b.title), "cs"));
        serviceCombo.setOptions(
          list.map((s) => ({
            value: String(s.id),
            label: shortServiceTitle(s.title, opt.title),
            raw: s,
          }))
        );
        const preferred = pickPreferredService(list, ecosystem);
        if (preferred) serviceCombo.setValue(String(preferred.id));
        syncBtn();
      },
    });

    const brandCombo = createCombo(root.querySelector('[data-combo="brand"]'), {
      hint: "Vybraná značka",
      placeholder: "Vyberte značku",
      onChange: (opt) => {
        selectedBrand = opt.node;
        selectedModel = null;
        selectedService = null;
        ecosystem = normalize(opt.node.title) === "apple" ? "apple" : "android";
        if (priceEl) priceEl.textContent = "";
        const models = collectModels(opt.node);
        modelsById = Object.fromEntries(models.map((m) => [m.value, m]));
        modelCombo.setOptions(models);
        serviceCombo.setOptions([]);
        syncBtn();
      },
    });

    const typeCombo = createCombo(root.querySelector('[data-combo="type"]'), {
      hint: "Typ zařízení",
      placeholder: "Vyberte typ",
      onChange: (opt) => {
        selectedType = opt.node;
        selectedBrand = null;
        selectedModel = null;
        selectedService = null;
        if (priceEl) priceEl.textContent = "";
        const brands = (opt.node.children || [])
          .slice()
          .sort((a, b) => (a.sortId || 0) - (b.sortId || 0) || a.title.localeCompare(b.title, "cs"));
        brandCombo.setOptions(brands.map((b) => ({ value: String(b.id), label: b.title, node: b })));
        modelCombo.setOptions([]);
        serviceCombo.setOptions([]);
        syncBtn();
      },
    });

    typeCombo.setOptions(roots.map((r) => ({ value: String(r.id), label: r.title, node: r })));
    brandCombo.setOptions([]);
    modelCombo.setOptions([]);
    serviceCombo.setOptions([]);
    syncBtn();

    document.addEventListener("click", (e) => {
      if (e.target.closest(".finder-combo")) return;
      root.querySelectorAll(".finder-combo.is-open").forEach((c) => {
        c.classList.remove("is-open");
        const p = c.querySelector(".finder-combo-panel");
        if (p) p.hidden = true;
      });
    });

    // Prefill: konkrétní model ze zařízení, jinak Safari→Apple / Chrome→Android z katalogu
    (async () => {
      const det = await detectVisitorDevice();
      ecosystem = det.ecosystem || ecosystem;
      const typeNode =
        roots.find((r) => (det.kind === "tablet" ? /tablet/i.test(r.title) : /telefon/i.test(r.title))) ||
        roots[0];
      if (!typeNode) return;
      typeCombo.setValue(String(typeNode.id));

      const brands = typeNode.children || [];
      const apple = brands.find((b) => normalize(b.title) === "apple");
      const samsung = brands.find((b) => normalize(b.title) === "samsung");
      let brand =
        (det.modelHint &&
          det.brandHint &&
          brands.find((b) => normalize(b.title).includes(normalize(det.brandHint)))) ||
        null;
      if (!brand && det.modelHint) {
        brand = brands.find((b) => normalize(b.title).includes(normalize(det.brandHint || "")));
      }
      if (!brand) {
        brand =
          ecosystem === "android"
            ? samsung || brands.find((b) => normalize(b.title) !== "apple") || brands[0]
            : apple || brands[0];
      }
      if (!brand) return;
      brandCombo.setValue(String(brand.id));

      const models = collectModels(brand);
      let model = det.modelHint ? matchModel(models, det.modelHint) : null;
      if (!model) model = pickPopularModel(models, ecosystem);
      if (model) modelCombo.setValue(model.value);
    })();
  }

  async function fillHomeDemo() {
    await ensureData(["meta", "devices", "services", "locations", "pages"]);
    initFinder();
    const branches = document.querySelector("[data-home-branches]");
    if (branches) renderLocations(branches, { limit: 6 });
    const articles = document.querySelector("[data-home-articles]");
    if (articles) renderPages(articles, { limit: 3 });
    const rating = document.querySelectorAll("[data-rating-count]");
    rating.forEach((n) => {
      n.textContent = DATA.meta.rating.count;
    });
  }

  function parseLiveSearchHtml(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const products = [];
    doc.querySelectorAll('[data-search-section="products"] a.site-search-result').forEach((a) => {
      const title = (a.querySelector(".site-search-result-title") || {}).textContent || "";
      const price = (a.querySelector(".site-search-result-meta") || {}).textContent || "";
      const href = a.getAttribute("href") || "";
      if (!href || !title.trim()) return;
      products.push({
        title: title.trim().replace(/\s+/g, " "),
        price: price.trim(),
        href,
      });
    });
    return products;
  }

  async function fetchLiveProductHits(q) {
    const url = `${liveBase()}/ajax/search?q=${encodeURIComponent(q)}`;
    const res = await fetch(url, { credentials: "omit" });
    if (!res.ok) throw new Error(`search ${res.status}`);
    return parseLiveSearchHtml(await res.text());
  }

  function productSuggestHtml(products, limit = 6) {
    return products.slice(0, limit).map((p) => {
      const clean = p.title.replace(/\s+Servis na\b.*$/i, "").trim();
      const label = shortServiceTitle(clean);
      return `<a href="${p.href}"><span><strong>${label}</strong><small>${clean}</small></span><span class="price">${p.price || "Detail"}</span></a>`;
    });
  }

  function initHeroSearch() {
    const root = document.querySelector("[data-hero-search]");
    if (!root) return;
    const input = root.querySelector("#hero-q");
    const results = root.querySelector("[data-hero-results]");
    const go = root.querySelector("[data-hero-go]");
    if (!input || !results) return;
    let req = 0;

    const render = async () => {
      const q = input.value.trim();
      const my = ++req;
      if (q.length < 2) {
        results.hidden = true;
        results.innerHTML = "";
        return;
      }
      results.hidden = false;
      results.innerHTML = `<div class="hero-search-empty">Hledám…</div>`;
      try {
        const products = await fetchLiveProductHits(q);
        if (my !== req) return;
        const parts = productSuggestHtml(products, 6);
        if (!parts.length) {
          results.innerHTML = `<div class="hero-search-empty">Nic nenalezeno. Zkuste jiný model nebo závadu.</div>`;
        } else {
          results.innerHTML = parts.join("");
        }
      } catch (err) {
        if (my !== req) return;
        console.error(err);
        results.innerHTML = `<div class="hero-search-empty">Vyhledávání teď nejde načíst. Zkuste to znovu.</div>`;
      }
    };

    let timer = null;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(render, 180);
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        clearTimeout(timer);
        render();
      }
    });
    if (go) go.addEventListener("click", () => {
      clearTimeout(timer);
      render();
    });
    root.querySelectorAll("[data-chip]").forEach((btn) => {
      btn.addEventListener("click", () => {
        input.value = btn.getAttribute("data-chip") || "";
        input.focus();
        clearTimeout(timer);
        render();
      });
    });
  }

  function initTopSearch() {
    const form = document.querySelector("form.top-search");
    if (!form || form.dataset.suggestReady === "1") return;
    form.dataset.suggestReady = "1";
    const input = form.querySelector('input[name="q"], #q, input[type="search"]');
    if (!input) return;

    form.classList.add("has-suggest");
    const panel = document.createElement("div");
    panel.className = "top-search-suggest";
    panel.hidden = true;
    panel.setAttribute("role", "listbox");
    panel.setAttribute("aria-label", "Návrhy oprav");
    form.appendChild(panel);

    let req = 0;
    let hits = [];

    const hide = () => {
      panel.hidden = true;
      panel.innerHTML = "";
      hits = [];
    };

    const goFirst = () => {
      const first = panel.querySelector("a");
      if (first && first.href) {
        window.location.href = first.href;
        return true;
      }
      return false;
    };

    const render = async () => {
      const q = input.value.trim();
      const my = ++req;
      if (q.length < 2) {
        hide();
        return;
      }
      panel.hidden = false;
      panel.innerHTML = `<div class="top-search-empty">Hledám…</div>`;
      try {
        const products = await fetchLiveProductHits(q);
        if (my !== req) return;
        hits = products;
        const parts = productSuggestHtml(products, 7);
        if (!parts.length) {
          panel.innerHTML = `<div class="top-search-empty">Nic nenalezeno</div>
            <a class="top-search-all" href="hledani-v2.html?q=${encodeURIComponent(q)}">Zobrazit všechna hledání →</a>`;
        } else {
          panel.innerHTML =
            parts.join("") +
            `<a class="top-search-all" href="hledani-v2.html?q=${encodeURIComponent(q)}">Všechna hledání →</a>`;
        }
      } catch (err) {
        if (my !== req) return;
        console.error(err);
        panel.innerHTML = `<div class="top-search-empty">Vyhledávání nejde načíst</div>`;
      }
    };

    let timer = null;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(render, 160);
    });
    input.addEventListener("focus", () => {
      if (input.value.trim().length >= 2 && panel.innerHTML) panel.hidden = false;
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        hide();
        return;
      }
      if (e.key === "Enter") {
        if (hits.length) {
          e.preventDefault();
          goFirst();
        }
      }
    });
    form.addEventListener("submit", (e) => {
      if (hits.length) {
        e.preventDefault();
        goFirst();
      }
    });
    document.addEventListener("click", (e) => {
      if (!form.contains(e.target)) hide();
    });
  }

  async function boot() {
    const page = document.body.dataset.page;
    initTopSearch();
    try {
      if (page === "katalog") {
        await ensureData(["meta", "devices", "services"]);
        renderCatalogPage();
      } else if (page === "vyber") {
        await ensureData(["meta", "devices"]);
        renderRoots(document.querySelector("[data-catalog]"));
      } else if (page === "pobocky") {
        await ensureData(["meta", "locations"]);
        renderLocations(document.querySelector("[data-locations]"));
      } else if (page === "blog") {
        await ensureData(["meta", "pages"]);
        renderPages(document.querySelector("[data-pages]"), { limit: 20 });
      } else if (page === "hledani") {
        await ensureData(["meta", "devices", "services", "pages"]);
        renderSearch();
      } else if (page === "home") {
        await fillHomeDemo();
      } else if (page === "hero-a") {
        await ensureData(["meta", "devices", "services"]);
        initHeroSearch();
      }
    } catch (err) {
      console.error(err);
      const mount = document.querySelector("[data-catalog], [data-search-results], [data-locations], [data-pages]");
      if (mount) mount.innerHTML = `<p>Data se nepodařilo načíst.</p>`;
    }
  }

  window.ServisPreview = {
    ensureData,
    formatPrice,
    liveDeviceUrl,
    searchCatalog,
    boot,
  };

  document.addEventListener("DOMContentLoaded", boot);
})();
