let renderUI = (manifest) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const pages = manifest.pages || [];
  const navigation = manifest.navigation || {};
  const appPermissions = manifest.app_permissions || {};
  const explicitPermissionsEnabled = appPermissions && appPermissions.enabled === true;
  const declaredPermissionMatrix = manifest && typeof manifest.permissions === "object" && manifest.permissions ? manifest.permissions : {};
  const activePage = navigation.active_page || null;
  const sidebarItems = Array.isArray(navigation.sidebar) ? navigation.sidebar : [];
  const emptyMessage = "Run your app to see it here.";
  const collectionRender = window.N3UIRender || {};
  const renderListElement = collectionRender.renderListElement;
  const renderTableElement = collectionRender.renderTableElement;
  const renderFormElement = collectionRender.renderFormElement;
  const renderChatElement = collectionRender.renderChatElement;
  const renderChartElement = collectionRender.renderChartElement;
  const renderCitationChipsElement = collectionRender.renderCitationChipsElement;
  const renderSourcePreviewElement = collectionRender.renderSourcePreviewElement;
  const renderTrustIndicatorElement = collectionRender.renderTrustIndicatorElement;
  const renderScopeSelectorElement = collectionRender.renderScopeSelectorElement;
  const renderUploadElement = collectionRender.renderUploadElement;
  const renderIngestionStatusElement = collectionRender.renderIngestionStatusElement;
  const renderRuntimeErrorElement = collectionRender.renderRuntimeErrorElement;
  const renderCapabilitiesElement = collectionRender.renderCapabilitiesElement;
  const renderStateInspectorElement = collectionRender.renderStateInspectorElement;
  const renderRunDiffElement = collectionRender.renderRunDiffElement || window.renderRunDiffElement;
  const renderDiagnosticsElement = collectionRender.renderDiagnosticsElement || window.renderDiagnosticsElement;
  const overlayRegistry = new Map();
  const LAYOUT_SLOTS = ["header", "sidebar_left", "main", "drawer_right", "footer"];
  const diagnosticsEnabled = Boolean(manifest && manifest.diagnostics_enabled) || manifest.mode === "studio";
  const diagnosticsVisibilityByPage = new Map();
  const loadedPluginAssets = window.N3LoadedPluginAssets || (window.N3LoadedPluginAssets = { js: {}, css: {} });
  if (!uiContainer) return;
  ensurePluginAssets(manifest);
  const pageEntries = (pages || [])
    .filter((p) => p && p.name)
    .map((p, idx) => ({
      name: String(p.name),
      slug: p && p.slug ? String(p.slug) : String(p.name),
      page: p,
      index: idx,
    }));
  const pageBySlug = new Map(pageEntries.map((entry) => [entry.slug, entry]));
  const pageByName = new Map(pageEntries.map((entry) => [entry.name, entry]));
  const actionsById = manifest && typeof manifest.actions === "object" && manifest.actions ? manifest.actions : {};
  const keyboardShortcutMap = new Map();

  function hasAppPermission(permission) {
    if (!explicitPermissionsEnabled) return true;
    if (typeof permission !== "string" || !permission) return false;
    return declaredPermissionMatrix[permission] === true;
  }

  function normalizeShortcut(value) {
    if (typeof value !== "string") return "";
    const parts = value
      .split("+")
      .map((part) => String(part || "").trim().toLowerCase())
      .filter(Boolean);
    const modifiers = parts.filter((part) => ["ctrl", "shift", "alt", "meta"].includes(part)).sort();
    const keys = parts.filter((part) => !["ctrl", "shift", "alt", "meta"].includes(part));
    if (!keys.length) return modifiers.join("+");
    return [...modifiers, ...keys].join("+");
  }

  function shortcutFromEvent(event) {
    const parts = [];
    if (event.ctrlKey) parts.push("ctrl");
    if (event.shiftKey) parts.push("shift");
    if (event.altKey) parts.push("alt");
    if (event.metaKey) parts.push("meta");
    const key = String(event.key || "").toLowerCase();
    if (key && !["control", "shift", "alt", "meta"].includes(key)) {
      parts.push(key);
    }
    return normalizeShortcut(parts.join("+"));
  }

  function registerShortcut(shortcut, actionId) {
    const normalized = normalizeShortcut(shortcut);
    if (!normalized || typeof actionId !== "string" || !actionId) return;
    const current = keyboardShortcutMap.get(normalized) || [];
    if (!current.includes(actionId)) {
      keyboardShortcutMap.set(normalized, [...current, actionId]);
    }
  }

  function registerKeyboardShortcuts() {
    if (typeof window === "undefined" || typeof window.addEventListener !== "function") return;
    keyboardShortcutMap.clear();
    Object.values(actionsById).forEach((action) => {
      if (!action || typeof action !== "object") return;
      const actionId = typeof action.id === "string" && action.id ? action.id : "";
      if (!actionId) return;
      const actionType = action.type || "";
      if (actionType === "layout.shortcut") {
        registerShortcut(action.shortcut || action.target, actionId);
      } else if (action.event === "keyboard_shortcut" && typeof action.target === "string") {
        registerShortcut(action.target, actionId);
      }
    });
    const handlerKey = "__n3KeyboardShortcutHandler";
    const previous = window[handlerKey];
    if (typeof previous === "function") {
      window.removeEventListener("keydown", previous);
    }
    const handler = (event) => {
      const combo = shortcutFromEvent(event);
      if (!combo || !keyboardShortcutMap.has(combo)) return;
      const actionIds = keyboardShortcutMap.get(combo) || [];
      if (!actionIds.length) return;
      event.preventDefault();
      actionIds.forEach((actionId) => {
        const action = actionsById[actionId];
        if (!action) return;
        handleAction(action, { shortcut: combo }, document.activeElement);
      });
    };
    window[handlerKey] = handler;
    window.addEventListener("keydown", handler);
  }

  function resolvePageEntry(value) {
    if (!value) return null;
    return pageBySlug.get(value) || pageByName.get(value) || null;
  }

  function ensurePluginAssets(nextManifest) {
    const plugins = nextManifest && nextManifest.ui && Array.isArray(nextManifest.ui.plugins) ? nextManifest.ui.plugins : [];
    plugins.forEach((plugin) => {
      if (!plugin || typeof plugin !== "object") return;
      const assets = plugin.assets || {};
      const jsAssets = Array.isArray(assets.js) ? assets.js : [];
      const cssAssets = Array.isArray(assets.css) ? assets.css : [];
      cssAssets.forEach((url) => loadPluginStyle(url));
      jsAssets.forEach((url) => loadPluginScript(url));
    });
  }

  function loadPluginStyle(url) {
    if (typeof url !== "string" || !url) return;
    if (loadedPluginAssets.css[url]) return;
    loadedPluginAssets.css[url] = true;
    const existing = document.querySelector(`link[data-n3-plugin-asset="${url}"]`);
    if (existing) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = url;
    link.dataset.n3PluginAsset = url;
    document.head.appendChild(link);
  }

  function loadPluginScript(url) {
    if (typeof url !== "string" || !url) return;
    if (loadedPluginAssets.js[url]) return;
    loadedPluginAssets.js[url] = true;
    const existing = document.querySelector(`script[data-n3-plugin-asset="${url}"]`);
    if (existing) return;
    const script = document.createElement("script");
    script.src = url;
    script.async = false;
    script.defer = true;
    script.dataset.n3PluginAsset = url;
    document.head.appendChild(script);
  }

  function resolvePageSlug(value) {
    const entry = resolvePageEntry(value);
    return entry ? entry.slug : "";
  }

  function diagnosticsElements(page) {
    if (!page || typeof page !== "object") return [];
    const blocks = page.diagnostics_blocks;
    return Array.isArray(blocks) ? blocks : [];
  }

  function diagnosticsVisibleForPage(page) {
    const slug = resolvePageSlug(page && (page.slug || page.name));
    return diagnosticsVisibilityByPage.get(slug) === true;
  }

  function setDiagnosticsVisibleForPage(page, visible) {
    const slug = resolvePageSlug(page && (page.slug || page.name));
    if (!slug) return;
    diagnosticsVisibilityByPage.set(slug, Boolean(visible));
  }

  const activeSlug = activePage ? resolvePageSlug(activePage.slug || activePage.name) : "";
  const navigationLocked = Boolean(activeSlug);
  let currentPageSlug = "";

  function readRouteSlug() {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search || "");
    return resolvePageSlug(params.get("page"));
  }

  function writeRouteSlug(slug, options = {}) {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (slug) {
      url.searchParams.set("page", slug);
    } else {
      url.searchParams.delete("page");
    }
    const push = options.push === true;
    const state = { ...(window.history ? window.history.state : null), n3PageSlug: slug || "" };
    if (window.history && window.history.replaceState) {
      if (push && typeof window.history.pushState === "function") {
        window.history.pushState(state, "", url.toString());
      } else {
        window.history.replaceState(state, "", url.toString());
      }
    } else {
      window.location.search = url.search;
    }
  }

  function buildPageUrl(slug) {
    if (typeof window === "undefined") return "";
    const url = new URL(window.location.href);
    if (slug) {
      url.searchParams.set("page", slug);
    } else {
      url.searchParams.delete("page");
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  const currentSelection = select ? select.value : "";
  const urlSelection = readRouteSlug();
  const initialSelection =
    activeSlug || urlSelection || resolvePageSlug(currentSelection) || (pageEntries[0] ? pageEntries[0].slug : "");
  if (select) {
    select.innerHTML = "";
    pageEntries.forEach((entry, idx) => {
      const opt = document.createElement("option");
      opt.value = entry.slug;
      opt.textContent = entry.page && entry.page.diagnostics ? `${entry.name} (Diagnostics)` : entry.name;
      if (entry.slug === initialSelection || (!initialSelection && idx === 0)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
    select.disabled = navigationLocked;
  }
  registerKeyboardShortcuts();
  function renderChildren(container, children, pageName) {
    (children || []).forEach((child) => {
      if (child && child.visible === false) return;
      const node = renderElement(child, pageName);
      applyThemeClasses(node, child);
      container.appendChild(node);
    });
  }
  function applyPageTheme(page) {
    if (typeof applyThemeBundle !== "function") return;
    const bundle = manifest && typeof manifest.theme === "object" ? { ...manifest.theme } : {};
    const pageTheme = page && typeof page.ui_theme === "object" ? page.ui_theme : null;
    if (pageTheme && typeof pageTheme.color_scheme === "string") {
      bundle.color_scheme = pageTheme.color_scheme;
    }
    applyThemeBundle(bundle);
  }
  function applyLocaleSettings() {
    const i18n = manifest && typeof manifest.i18n === "object" ? manifest.i18n : {};
    const direction = i18n && typeof i18n.direction === "string" ? i18n.direction : "ltr";
    const locale = i18n && typeof i18n.locale === "string" ? i18n.locale : "en";
    if (document && document.documentElement) {
      document.documentElement.setAttribute("dir", direction === "rtl" ? "rtl" : "ltr");
      document.documentElement.setAttribute("lang", locale);
    }
    if (document && document.body) {
      document.body.dataset.locale = locale;
      document.body.dataset.direction = direction === "rtl" ? "rtl" : "ltr";
    }
  }
  function applyThemeClasses(node, el) {
    if (!node || !node.classList || !el) return;
    const size = typeof el.size === "string" ? el.size : null;
    const radius = typeof el.radius === "string" ? el.radius : null;
    const density = typeof el.density === "string" ? el.density : null;
    const font = typeof el.font === "string" ? el.font : null;
    if (size) node.classList.add(`n3-size-${size}`);
    if (radius) node.classList.add(`n3-radius-${radius}`);
    if (density) node.classList.add(`n3-density-${density}`);
    if (font) node.classList.add(`n3-font-${font}`);
  }
  function _focusable(container) {
    return Array.from(
      container.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter((el) => !el.disabled && el.offsetParent !== null);
  }
  function _focusFirst(container) {
    const focusable = _focusable(container);
    if (focusable.length) {
      focusable[0].focus();
      return;
    }
    if (container && container.focus) container.focus();
  }
  function openOverlay(targetId, opener) {
    const entry = overlayRegistry.get(targetId);
    if (!entry) return;
    entry.returnFocus = opener || document.activeElement;
    entry.container.classList.remove("hidden");
    entry.container.setAttribute("aria-hidden", "false");
    const trapFocus =
      entry.type === "modal" ||
      (entry.type === "drawer" &&
        typeof window !== "undefined" &&
        Boolean(window.matchMedia) &&
        window.matchMedia("(max-width: 960px)").matches);
    if (trapFocus) {
      if (!entry.trapHandler) {
        entry.trapHandler = (e) => {
          if (e.key !== "Tab") return;
          const focusable = _focusable(entry.panel);
          if (!focusable.length) {
            e.preventDefault();
            entry.panel.focus();
            return;
          }
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        };
        entry.panel.addEventListener("keydown", entry.trapHandler);
      }
    }
    _focusFirst(entry.panel);
  }
  function closeOverlay(targetId) {
    const entry = overlayRegistry.get(targetId);
    if (!entry) return;
    entry.container.classList.add("hidden");
    entry.container.setAttribute("aria-hidden", "true");
    if (entry.trapHandler) {
      entry.panel.removeEventListener("keydown", entry.trapHandler);
      entry.trapHandler = null;
    }
    if (entry.returnFocus && entry.returnFocus.focus) {
      entry.returnFocus.focus();
    }
    entry.returnFocus = null;
  }

  function setLayoutDrawerOpen(targetId, open) {
    if (typeof targetId !== "string" || !targetId) return false;
    const drawer = uiContainer.querySelector(`[data-layout-drawer-id="${targetId}"]`);
    if (!drawer) return false;
    drawer.dataset.open = open ? "true" : "false";
    drawer.setAttribute("aria-hidden", open ? "false" : "true");
    return true;
  }

  function applyInteractionBindings(node, el) {
    if (!node || !el) return;
    const bindings = node.bindings;
    if (!bindings || typeof bindings !== "object") return;
    if (typeof bindings.selected_item === "string" && bindings.selected_item) {
      el.dataset.selectedItemPath = bindings.selected_item;
    }
    if (typeof bindings.keyboard_shortcut === "string" && bindings.keyboard_shortcut) {
      const fallbackAction = typeof bindings.on_click === "string" ? bindings.on_click : null;
      if (fallbackAction) {
        registerShortcut(bindings.keyboard_shortcut, fallbackAction);
      }
    }
    if (typeof bindings.on_click === "string" && bindings.on_click) {
      const targetActionId = bindings.on_click;
      el.classList.add("n3-interactive");
      if (!el.hasAttribute("tabindex")) {
        el.setAttribute("tabindex", "0");
      }
      el.onclick = (event) => {
        event.stopPropagation();
        const action = actionsById[targetActionId];
        if (action) {
          handleAction(action, { source_element_id: node.id || null }, event.currentTarget);
          return;
        }
        executeAction(targetActionId, { source_element_id: node.id || null });
      };
      el.onkeydown = (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        el.click();
      };
    }
  }
  function navigateToPage(value, options = {}) {
    if (navigationLocked) return;
    const slug = resolvePageSlug(value);
    if (!slug) return;
    if (slug === currentPageSlug) return;
    if (select) {
      select.value = slug;
    }
    writeRouteSlug(slug, { push: options.push === true });
    renderPage(slug, { skipRouteSync: true });
  }
  function handleAction(action, payload, opener) {
    if (!action || !action.id) return;
    if (action.enabled === false) return { ok: false };
    const actionType = action.type || "call_flow";
    if (actionType === "open_modal" || actionType === "open_drawer") {
      openOverlay(action.target, opener);
      return { ok: true };
    }
    if (actionType === "close_modal" || actionType === "close_drawer") {
      closeOverlay(action.target);
      return { ok: true };
    }
    if (actionType === "layout.drawer.open") {
      setLayoutDrawerOpen(action.target, true);
      return { ok: true };
    }
    if (actionType === "layout.drawer.close") {
      setLayoutDrawerOpen(action.target, false);
      return { ok: true };
    }
    if (actionType === "layout.drawer.toggle") {
      const drawer = uiContainer.querySelector(`[data-layout-drawer-id="${action.target}"]`);
      if (!drawer) return { ok: false };
      const nextOpen = drawer.dataset.open !== "true";
      setLayoutDrawerOpen(action.target, nextOpen);
      return { ok: true };
    }
    if (actionType === "layout.sticky.show" || actionType === "layout.sticky.hide" || actionType === "layout.sticky.toggle") {
      const sticky = uiContainer.querySelector(`[data-layout-sticky-id="${action.target}"]`);
      if (!sticky) return { ok: false };
      const current = sticky.dataset.visible !== "false";
      const nextVisible =
        actionType === "layout.sticky.show" ? true : actionType === "layout.sticky.hide" ? false : !current;
      sticky.dataset.visible = nextVisible ? "true" : "false";
      sticky.style.display = nextVisible ? "" : "none";
      return { ok: true };
    }
    if (actionType === "layout.selection.set") {
      const path = (payload && payload.path) || action.path || "";
      if (typeof path === "string" && path) {
        const nodes = uiContainer.querySelectorAll(`[data-selected-item-path="${path}"]`);
        nodes.forEach((node) => node.classList.add("selected"));
      }
      return { ok: true };
    }
    if (actionType === "layout.shortcut") {
      const actionPayload = action && typeof action.payload === "object" && action.payload ? action.payload : {};
      const dispatchActionId = typeof actionPayload.dispatch_action_id === "string" ? actionPayload.dispatch_action_id : "";
      if (dispatchActionId && actionsById[dispatchActionId]) {
        return handleAction(actionsById[dispatchActionId], payload, opener);
      }
      const targetActionId = typeof actionPayload.target_action === "string" ? actionPayload.target_action : "";
      if (targetActionId) {
        return executeAction(targetActionId, payload);
      }
      return { ok: true };
    }
    if (actionType === "layout.interaction") {
      if (typeof action.target === "string" && action.target) {
        return executeAction(action.target, payload);
      }
      return { ok: false };
    }
    if (actionType === "component.chat.send" || actionType === "component.ingestion.retry") {
      if (typeof action.target === "string" && action.target) {
        return executeAction(action.target, payload);
      }
      return executeAction(action.id, payload);
    }
    if (actionType === "component.document.select") {
      const selectedId = payload && typeof payload.document_id === "string" ? payload.document_id : "";
      if (!selectedId) return { ok: false };
      const rows = uiContainer.querySelectorAll("[data-document-id]");
      rows.forEach((row) => {
        row.classList.toggle("selected", row.dataset.documentId === selectedId);
      });
      if (typeof action.target === "string" && action.target) {
        return executeAction(action.target, payload);
      }
      return { ok: true };
    }
    if (actionType === "component.citation.open") {
      const selectedId = payload && typeof payload.citation_id === "string" ? payload.citation_id : "";
      const rows = uiContainer.querySelectorAll("[data-citation-id]");
      rows.forEach((row) => {
        row.classList.toggle("selected", selectedId && row.dataset.citationId === selectedId);
      });
      if (typeof action.target === "string" && action.target) {
        setLayoutDrawerOpen(action.target, true);
      }
      return { ok: true };
    }
    if (actionType === "open_page") {
      if (!hasAppPermission("navigation.change_page")) return { ok: false };
      if (navigationLocked) return { ok: false };
      navigateToPage(action.target, { push: true });
      return { ok: true };
    }
    if (actionType === "go_back") {
      if (!hasAppPermission("navigation.change_page")) return { ok: false };
      if (typeof window !== "undefined" && window.history && typeof window.history.back === "function") {
        window.history.back();
      }
      return { ok: true };
    }
    return executeAction(action.id, payload);
  }
  function activateTabByLabel(container, label) {
    if (!container) return false;
    const tabs = container.querySelectorAll(".ui-tabs");
    const target = typeof label === "string" ? label.trim().toLowerCase() : "";
    if (!target) return false;
    for (const tabsNode of tabs) {
      if (typeof tabsNode.n3SetActiveTabByLabel === "function" && tabsNode.n3SetActiveTabByLabel(label)) {
        return true;
      }
      const buttons = Array.from(tabsNode.querySelectorAll(".ui-tab"));
      const button = buttons.find((item) => String(item.textContent || "").trim().toLowerCase() === target);
      if (button) {
        button.click();
        return true;
      }
    }
    return false;
  }
  function focusCitationInDrawer(entry) {
    const drawer = uiContainer.querySelector(".n3-layout-drawer");
    if (!drawer) return false;
    activateTabByLabel(drawer, "Citations");
    const title = entry && typeof entry.title === "string" ? entry.title.trim().toLowerCase() : "";
    const sourceId = entry && typeof entry.source_id === "string" ? entry.source_id.trim().toLowerCase() : "";
    const listRows = Array.from(drawer.querySelectorAll(".ui-list-item"));
    let target = null;
    listRows.forEach((row) => {
      row.classList.remove("selected");
      if (target) return;
      const primary = row.querySelector(".ui-list-primary");
      const meta = row.querySelector(".ui-list-meta");
      const primaryValue = String((primary && primary.textContent) || "").trim().toLowerCase();
      const metaValue = String((meta && meta.textContent) || "").trim().toLowerCase();
      if ((title && primaryValue === title) || (sourceId && (metaValue === sourceId || primaryValue === sourceId))) {
        target = row;
      }
    });
    if (target) {
      target.classList.add("selected");
      if (typeof target.scrollIntoView === "function") target.scrollIntoView({ block: "nearest" });
      return true;
    }
    return false;
  }
  function focusDrawerPreviewForCitation(entry, opener) {
    const drawer = uiContainer.querySelector(".n3-layout-drawer");
    if (drawer) {
      activateTabByLabel(drawer, "Preview");
    }
    if (collectionRender && typeof collectionRender.openCitationPreview === "function") {
      collectionRender.openCitationPreview(entry, opener, [entry]);
      return true;
    }
    return false;
  }
  collectionRender.focusCitationInDrawer = focusCitationInDrawer;
  collectionRender.focusDrawerPreviewForCitation = focusDrawerPreviewForCitation;
  function renderOverlay(el, pageName) {
    const overlayId = el.id || "";
    const overlay = document.createElement("div");
    overlay.className = `ui-overlay ui-${el.type} hidden`;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-hidden", "true");
    overlay.setAttribute("aria-modal", el.type === "modal" ? "true" : "false");
    overlay.tabIndex = -1;
    if (overlayId) overlay.dataset.overlayId = overlayId;
    const panel = document.createElement("div");
    panel.className = "ui-overlay-panel";
    panel.tabIndex = -1;
    const header = document.createElement("div");
    header.className = "ui-overlay-header";
    const title = document.createElement("div");
    title.className = "ui-overlay-title";
    title.textContent = el.label || (el.type === "modal" ? "Modal" : "Drawer");
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn small ghost";
    closeBtn.textContent = "Close";
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      if (overlayId) closeOverlay(overlayId);
    };
    header.appendChild(title);
    header.appendChild(closeBtn);
    panel.appendChild(header);
    const body = document.createElement("div");
    body.className = "ui-overlay-body";
    renderChildren(body, el.children, pageName);
    panel.appendChild(body);
    overlay.appendChild(panel);
    if (overlayId) {
      overlayRegistry.set(overlayId, {
        id: overlayId,
        type: el.type,
        container: overlay,
        panel: panel,
        returnFocus: null,
        trapHandler: null,
      });
    }
    return overlay;
  }
  function renderElement(el, pageName) {
    if (!el) return document.createElement("div");
    if (el.type === "section") {
      const section = document.createElement("div");
      section.className = "ui-element ui-section";
      if (el.label) {
        const header = document.createElement("div");
        header.className = "ui-section-title";
        header.textContent = el.label;
        section.appendChild(header);
      }
      renderChildren(section, el.children, pageName);
      return section;
    }
    if (el.type === "card_group") {
      const group = document.createElement("div");
      group.className = "ui-card-group";
      renderChildren(group, el.children, pageName);
      return group;
    }
    if (el.type === "tabs") {
      const tabs = Array.isArray(el.children) ? el.children.filter((tab) => tab && tab.visible !== false) : [];
      const wrapper = document.createElement("div");
      wrapper.className = "ui-tabs";
      if (!tabs.length) {
        const empty = document.createElement("div");
        empty.textContent = "No tabs available.";
        wrapper.appendChild(empty);
        return wrapper;
      }
      const tabList = document.createElement("div");
      tabList.className = "ui-tabs-header";
      tabList.setAttribute("role", "tablist");
      const panels = [];
      const tabButtons = [];
      const defaultLabel = el.active || el.default || tabs[0].label;
      let activeIndex = tabs.findIndex((tab) => tab.label === defaultLabel);
      if (activeIndex < 0) activeIndex = 0;

      function setActive(nextIndex) {
        activeIndex = nextIndex;
        tabButtons.forEach((btn, idx) => {
          const isActive = idx === activeIndex;
          btn.classList.toggle("active", isActive);
          btn.setAttribute("aria-selected", isActive ? "true" : "false");
          btn.tabIndex = isActive ? 0 : -1;
        });
        panels.forEach((panel, idx) => {
          panel.hidden = idx !== activeIndex;
        });
      }

      tabs.forEach((tab, idx) => {
        const label = tab.label || `Tab ${idx + 1}`;
        const tabId = `${el.element_id || "tabs"}-tab-${idx}`;
        const panelId = `${el.element_id || "tabs"}-panel-${idx}`;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ui-tab";
        btn.textContent = label;
        btn.id = tabId;
        btn.setAttribute("role", "tab");
        btn.setAttribute("aria-controls", panelId);
        btn.onclick = () => setActive(idx);
        btn.onkeydown = (e) => {
          if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
          e.preventDefault();
          const next = e.key === "ArrowRight" ? idx + 1 : idx - 1;
          const wrapped = (next + tabs.length) % tabs.length;
          tabButtons[wrapped].focus();
          setActive(wrapped);
        };
        tabButtons.push(btn);
        tabList.appendChild(btn);

        const panel = document.createElement("div");
        panel.className = "ui-tab-panel";
        panel.id = panelId;
        panel.setAttribute("role", "tabpanel");
        panel.setAttribute("aria-labelledby", tabId);
        renderChildren(panel, tab.children, pageName);
        panels.push(panel);
      });

      wrapper.appendChild(tabList);
      panels.forEach((panel) => wrapper.appendChild(panel));
      wrapper.n3SetActiveTab = (index) => setActive(index);
      wrapper.n3SetActiveTabByLabel = (label) => {
        const target = typeof label === "string" ? label.trim().toLowerCase() : "";
        if (!target) return false;
        const tabIndex = tabs.findIndex((tab) => String(tab.label || "").trim().toLowerCase() === target);
        if (tabIndex < 0) return false;
        setActive(tabIndex);
        return true;
      };
      setActive(activeIndex);
      return wrapper;
    }
    if (el.type === "modal" || el.type === "drawer") {
      return renderOverlay(el, pageName);
    }
    if (el.type === "card") {
      const card = document.createElement("div");
      card.className = "ui-element ui-card";
      if (el.label) {
        const header = document.createElement("div");
        header.className = "ui-card-title";
        header.textContent = el.label;
        card.appendChild(header);
      }
      if (el.stat) {
        const stat = document.createElement("div");
        stat.className = "ui-card-stat";
        const value = document.createElement("div");
        value.className = "ui-card-stat-value";
        const rawValue = el.stat.value;
        if (rawValue === null || rawValue === undefined) {
          value.textContent = "-";
        } else if (typeof rawValue === "string") {
          value.textContent = rawValue;
        } else {
          try {
            value.textContent = JSON.stringify(rawValue);
          } catch {
            value.textContent = String(rawValue);
          }
        }
        stat.appendChild(value);
        if (el.stat.label) {
          const label = document.createElement("div");
          label.className = "ui-card-stat-label";
          label.textContent = el.stat.label;
          stat.appendChild(label);
        }
        card.appendChild(stat);
      }
      renderChildren(card, el.children, pageName);
      if (Array.isArray(el.actions) && el.actions.length) {
        const actions = document.createElement("div");
        actions.className = "ui-card-actions";
        el.actions.forEach((action) => {
          const enabled = action.enabled !== false;
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn small";
          btn.textContent = action.label || "Run";
          btn.disabled = !enabled;
          btn.onclick = (e) => {
            e.stopPropagation();
            if (!enabled) return;
            handleAction(action, {}, e.currentTarget);
          };
          actions.appendChild(btn);
        });
        card.appendChild(actions);
      }
      return card;
    }
    if (el.type === "layout.stack") {
      const stack = document.createElement("div");
      stack.className = "n3-layout-stack";
      const direction = el.direction === "horizontal" ? "horizontal" : "vertical";
      stack.dataset.direction = direction;
      if (direction === "horizontal") stack.classList.add("horizontal");
      renderChildren(stack, el.children, pageName);
      return stack;
    }
    if (el.type === "layout.row") {
      const row = document.createElement("div");
      row.className = "n3-layout-row";
      renderChildren(row, el.children, pageName);
      return row;
    }
    if (el.type === "layout.col") {
      const col = document.createElement("div");
      col.className = "n3-layout-col";
      renderChildren(col, el.children, pageName);
      return col;
    }
    if (el.type === "layout.grid") {
      const grid = document.createElement("div");
      grid.className = "n3-layout-grid";
      const columns = Number(el.columns) || 1;
      const safeColumns = Math.max(columns, 1);
      grid.style.setProperty("--n3-grid-columns", String(safeColumns));
      renderChildren(grid, el.children, pageName);
      return grid;
    }
    if (el.type === "layout.sidebar") {
      const wrapper = document.createElement("div");
      wrapper.className = "n3-layout-sidebar";
      const hasLegacyBranches = Array.isArray(el.sidebar) || Array.isArray(el.main);
      const sidebarItems = Array.isArray(el.sidebar)
        ? el.sidebar.filter((child) => child && child.visible !== false)
        : Array.isArray(el.children)
          ? el.children.filter((child) => child && child.visible !== false)
          : [];
      const mainItems = Array.isArray(el.main) ? el.main.filter((child) => child && child.visible !== false) : [];
      if (sidebarItems.length) {
        const sidebar = document.createElement("aside");
        sidebar.className = "n3-layout-sidebar-pane";
        renderChildren(sidebar, sidebarItems, pageName);
        wrapper.appendChild(sidebar);
      }
      if (hasLegacyBranches) {
        const main = document.createElement("div");
        main.className = "n3-layout-main-pane";
        renderChildren(main, mainItems, pageName);
        wrapper.appendChild(main);
      }
      applyInteractionBindings(el, wrapper);
      return wrapper;
    }
    if (el.type === "layout.main") {
      const main = document.createElement("section");
      main.className = "n3-layout-main";
      renderChildren(main, el.children, pageName);
      applyInteractionBindings(el, main);
      return main;
    }
    if (el.type === "layout.drawer") {
      const drawer = document.createElement("section");
      drawer.className = "n3-layout-drawer";
      const drawerSide = el.side === "left" ? "left" : "right";
      drawer.dataset.side = drawerSide;
      const showWhen = el.show_when && el.show_when.result === true;
      const openState = typeof el.open_state === "boolean" ? el.open_state : showWhen;
      drawer.dataset.open = openState ? "true" : "false";
      drawer.setAttribute("aria-hidden", openState ? "false" : "true");
      if (el.id) drawer.dataset.layoutDrawerId = el.id;
      if (el.title) {
        const header = document.createElement("div");
        header.className = "n3-layout-drawer-header";
        const title = document.createElement("div");
        title.className = "n3-layout-drawer-title";
        title.textContent = el.title;
        header.appendChild(title);
        drawer.appendChild(header);
      }
      const body = document.createElement("div");
      body.className = "n3-layout-drawer-body";
      renderChildren(body, el.children, pageName);
      drawer.appendChild(body);
      applyInteractionBindings(el, drawer);
      return drawer;
    }
    if (el.type === "layout.sticky") {
      const sticky = document.createElement("div");
      sticky.className = "n3-layout-sticky";
      const position = el.position === "bottom" ? "bottom" : "top";
      sticky.dataset.position = position;
       if (el.id) sticky.dataset.layoutStickyId = el.id;
      const visible = typeof el.visible === "boolean" ? el.visible : true;
      sticky.dataset.visible = visible ? "true" : "false";
      if (!visible) sticky.style.display = "none";
      if (position === "bottom") sticky.classList.add("bottom");
      renderChildren(sticky, el.children, pageName);
      applyInteractionBindings(el, sticky);
      return sticky;
    }
    if (el.type === "layout.scroll_area") {
      const scrollArea = document.createElement("div");
      scrollArea.className = "n3-layout-scroll-area";
      const axis = el.axis === "horizontal" ? "horizontal" : "vertical";
      scrollArea.dataset.axis = axis;
      if (axis === "horizontal") scrollArea.classList.add("horizontal");
      renderChildren(scrollArea, el.children, pageName);
      applyInteractionBindings(el, scrollArea);
      return scrollArea;
    }
    if (el.type === "layout.two_pane") {
      const wrapper = document.createElement("div");
      wrapper.className = "n3-layout-two-pane";
      const primary = document.createElement("div");
      primary.className = "n3-layout-two-pane-primary";
      const secondary = document.createElement("div");
      secondary.className = "n3-layout-two-pane-secondary";
      renderChildren(primary, el.primary || [], pageName);
      renderChildren(secondary, el.secondary || [], pageName);
      wrapper.appendChild(primary);
      wrapper.appendChild(secondary);
      applyInteractionBindings(el, wrapper);
      return wrapper;
    }
    if (el.type === "layout.three_pane") {
      const wrapper = document.createElement("div");
      wrapper.className = "n3-layout-three-pane";
      const left = document.createElement("div");
      left.className = "n3-layout-three-pane-left";
      const center = document.createElement("div");
      center.className = "n3-layout-three-pane-center";
      const right = document.createElement("div");
      right.className = "n3-layout-three-pane-right";
      renderChildren(left, el.left || [], pageName);
      renderChildren(center, el.center || [], pageName);
      renderChildren(right, el.right || [], pageName);
      wrapper.appendChild(left);
      wrapper.appendChild(center);
      wrapper.appendChild(right);
      applyInteractionBindings(el, wrapper);
      return wrapper;
    }
    if (el.type === "component.form") {
      const form = document.createElement("section");
      form.className = "n3-component-form";
      form.dataset.formName = el.name || "";
      if (el.wizard) form.classList.add("wizard");
      if (Array.isArray(el.sections) && el.sections.length) {
        const sectionBar = document.createElement("div");
        sectionBar.className = "n3-component-form-sections";
        el.sections.forEach((label) => {
          const chip = document.createElement("span");
          chip.className = "n3-component-form-section";
          chip.textContent = label;
          sectionBar.appendChild(chip);
        });
        form.appendChild(sectionBar);
      }
      renderChildren(form, el.children || [], pageName);
      applyInteractionBindings(el, form);
      return form;
    }
    if (el.type === "component.table") {
      const table = document.createElement("section");
      table.className = "n3-component-table";
      table.dataset.tableName = el.name || "";
      table.dataset.reorderableColumns = el.reorderable_columns ? "true" : "false";
      table.dataset.fixedHeader = el.fixed_header ? "true" : "false";
      renderChildren(table, el.children || [], pageName);
      applyInteractionBindings(el, table);
      return table;
    }
    if (el.type === "component.card") {
      const card = document.createElement("section");
      card.className = "n3-component-card";
      card.dataset.cardName = el.name || "";
      const header = document.createElement("div");
      header.className = "n3-component-card-header";
      header.textContent = el.name || "Card";
      card.appendChild(header);
      const body = document.createElement("div");
      body.className = "n3-component-card-body";
      const collapsed = Boolean(el.collapsed);
      if (collapsed) body.style.display = "none";
      renderChildren(body, el.children || [], pageName);
      card.appendChild(body);
      if (el.expandable) {
        header.classList.add("expandable");
        header.onclick = () => {
          const hidden = body.style.display === "none";
          body.style.display = hidden ? "" : "none";
        };
      }
      applyInteractionBindings(el, card);
      return card;
    }
    if (el.type === "component.tabs") {
      const tabs = document.createElement("section");
      tabs.className = "n3-component-tabs";
      tabs.dataset.tabsName = el.name || "";
      if (typeof el.dynamic_from_state === "string") {
        tabs.dataset.dynamicFromState = el.dynamic_from_state;
      }
      renderChildren(tabs, el.children || [], pageName);
      applyInteractionBindings(el, tabs);
      return tabs;
    }
    if (el.type === "component.media") {
      const media = document.createElement("section");
      media.className = "n3-component-media";
      media.dataset.mediaName = el.name || "";
      media.dataset.inlineCrop = el.inline_crop ? "true" : "false";
      media.dataset.annotation = el.annotation ? "true" : "false";
      renderChildren(media, el.children || [], pageName);
      applyInteractionBindings(el, media);
      return media;
    }
    if (el.type === "component.chat_thread") {
      const thread = document.createElement("section");
      thread.className = "n3-component-chat-thread";
      if (el.title) {
        const title = document.createElement("div");
        title.className = "n3-chat-title";
        title.textContent = el.title;
        thread.appendChild(title);
      }
      const messages = Array.isArray(el.messages) ? el.messages : [];
      messages.forEach((entry) => {
        if (!entry || typeof entry !== "object") return;
        const message = document.createElement("article");
        message.className = "n3-chat-message";
        message.dataset.role = entry.role || "assistant";
        message.dataset.status = entry.status || "complete";
        const content = document.createElement("div");
        content.className = "n3-chat-content";
        content.textContent = typeof entry.content === "string" ? entry.content : "";
        message.appendChild(content);
        const citations = Array.isArray(entry.citations) ? entry.citations : [];
        if (citations.length) {
          const row = document.createElement("div");
          row.className = "n3-chat-citations";
          citations.forEach((citationId) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "n3-chat-citation";
            button.textContent = String(citationId);
            button.onclick = (event) => {
              event.preventDefault();
              const actionId = el.bindings && typeof el.bindings.on_click === "string" ? el.bindings.on_click : null;
              if (!actionId) return;
              const action = actionsById[actionId];
              if (action) {
                handleAction(action, { citation_id: String(citationId), message_id: entry.id || null }, button);
              } else {
                executeAction(actionId, { citation_id: String(citationId), message_id: entry.id || null });
              }
            };
            row.appendChild(button);
          });
          message.appendChild(row);
        }
        thread.appendChild(message);
      });
      if (el.streaming) {
        const streaming = document.createElement("div");
        streaming.className = "n3-chat-streaming";
        streaming.textContent = "Streaming...";
        thread.appendChild(streaming);
      }
      applyInteractionBindings(el, thread);
      return thread;
    }
    if (el.type === "component.citation_panel") {
      const panel = document.createElement("section");
      panel.className = "n3-component-citation-panel";
      const citations = Array.isArray(el.citations) ? el.citations : [];
      const selectedId = typeof el.selected_id === "string" ? el.selected_id : "";
      citations.forEach((entry) => {
        if (!entry || typeof entry !== "object") return;
        const row = document.createElement("button");
        row.type = "button";
        row.className = "n3-citation-item";
        row.dataset.citationId = entry.id || "";
        if (selectedId && entry.id === selectedId) row.classList.add("selected");
        const title = document.createElement("div");
        title.className = "n3-citation-title";
        title.textContent = entry.title || entry.id || "Citation";
        row.appendChild(title);
        if (entry.snippet) {
          const snippet = document.createElement("div");
          snippet.className = "n3-citation-snippet";
          snippet.textContent = entry.snippet;
          row.appendChild(snippet);
        }
        if (Number.isInteger(entry.page)) {
          const page = document.createElement("div");
          page.className = "n3-citation-page";
          page.textContent = `Page ${entry.page}`;
          row.appendChild(page);
        }
        row.onclick = (event) => {
          event.preventDefault();
          const actionId = el.bindings && typeof el.bindings.on_click === "string" ? el.bindings.on_click : null;
          if (!actionId) return;
          const payload = { citation_id: entry.id || null, source_id: entry.source_id || null };
          const action = actionsById[actionId];
          if (action) {
            handleAction(action, payload, row);
          } else {
            executeAction(actionId, payload);
          }
        };
        panel.appendChild(row);
      });
      applyInteractionBindings(el, panel);
      return panel;
    }
    if (el.type === "component.document_library") {
      const panel = document.createElement("section");
      panel.className = "n3-component-document-library";
      const docs = Array.isArray(el.documents) ? el.documents : [];
      const selectedId = typeof el.selected_document_id === "string" ? el.selected_document_id : "";
      const selectActionId =
        (el.actions && typeof el.actions.select === "string" && el.actions.select) ||
        (el.bindings && typeof el.bindings.on_click === "string" && el.bindings.on_click) ||
        "";
      const deleteActionId = el.actions && typeof el.actions.delete === "string" ? el.actions.delete : "";
      docs.forEach((entry) => {
        if (!entry || typeof entry !== "object") return;
        const row = document.createElement("div");
        row.className = "n3-document-item";
        row.dataset.documentId = entry.id || "";
        if (selectedId && entry.id === selectedId) row.classList.add("selected");
        const selectBtn = document.createElement("button");
        selectBtn.type = "button";
        selectBtn.className = "n3-document-select";
        selectBtn.textContent = entry.name || entry.id || "Document";
        selectBtn.onclick = (event) => {
          event.preventDefault();
          if (!selectActionId) return;
          const payload = { document_id: entry.id || null };
          const action = actionsById[selectActionId];
          if (action) {
            handleAction(action, payload, selectBtn);
          } else {
            executeAction(selectActionId, payload);
          }
        };
        row.appendChild(selectBtn);
        if (deleteActionId) {
          const deleteBtn = document.createElement("button");
          deleteBtn.type = "button";
          deleteBtn.className = "n3-document-delete";
          deleteBtn.textContent = "Delete";
          deleteBtn.onclick = (event) => {
            event.preventDefault();
            const payload = { document_id: entry.id || null };
            const action = actionsById[deleteActionId];
            if (action) {
              handleAction(action, payload, deleteBtn);
            } else {
              executeAction(deleteActionId, payload);
            }
          };
          row.appendChild(deleteBtn);
        }
        panel.appendChild(row);
      });
      applyInteractionBindings(el, panel);
      return panel;
    }
    if (el.type === "component.ingestion_progress") {
      const progress = document.createElement("section");
      progress.className = "n3-component-ingestion-progress";
      const status = document.createElement("div");
      status.className = "n3-ingestion-status";
      status.textContent = `Status: ${el.status || "idle"}`;
      progress.appendChild(status);
      const meter = document.createElement("progress");
      meter.max = 100;
      meter.value = Number.isInteger(el.percent) ? el.percent : 0;
      meter.className = "n3-ingestion-meter";
      progress.appendChild(meter);
      const percent = document.createElement("div");
      percent.className = "n3-ingestion-percent";
      percent.textContent = `${meter.value}%`;
      progress.appendChild(percent);
      const errors = Array.isArray(el.errors) ? el.errors : [];
      errors.forEach((messageText) => {
        const line = document.createElement("div");
        line.className = "n3-ingestion-error";
        line.textContent = String(messageText);
        progress.appendChild(line);
      });
      if (el.bindings && typeof el.bindings.on_click === "string" && el.bindings.on_click) {
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "n3-ingestion-retry";
        retry.textContent = "Retry";
        retry.onclick = (event) => {
          event.preventDefault();
          const actionId = el.bindings.on_click;
          const action = actionsById[actionId];
          if (action) {
            handleAction(action, { source_component: el.id || null }, retry);
          } else {
            executeAction(actionId, { source_component: el.id || null });
          }
        };
        progress.appendChild(retry);
      }
      applyInteractionBindings(el, progress);
      return progress;
    }
    if (el.type === "component.explain_mode") {
      if (el.studio_only === true && manifest.mode !== "studio") {
        const hidden = document.createElement("div");
        hidden.className = "n3-component-explain-mode hidden";
        return hidden;
      }
      const explain = document.createElement("section");
      explain.className = "n3-component-explain-mode";
      if (el.visible === false) {
        explain.style.display = "none";
      }
      const entries = Array.isArray(el.entries) ? el.entries : [];
      entries.forEach((entry) => {
        if (!entry || typeof entry !== "object") return;
        const block = document.createElement("article");
        block.className = "n3-explain-entry";
        const id = document.createElement("div");
        id.className = "n3-explain-id";
        id.textContent = entry.chunk_id || "chunk";
        block.appendChild(id);
        const score = document.createElement("div");
        score.className = "n3-explain-score";
        score.textContent = `score ${Number(entry.score || 0).toFixed(3)}`;
        block.appendChild(score);
        if (entry.text) {
          const text = document.createElement("div");
          text.className = "n3-explain-text";
          text.textContent = String(entry.text);
          block.appendChild(text);
        }
        explain.appendChild(block);
      });
      applyInteractionBindings(el, explain);
      return explain;
    }
    if (el.type === "component.literal") {
      const text = document.createElement("div");
      text.className = "n3-component-literal";
      text.textContent = typeof el.text === "string" ? el.text : "";
      applyInteractionBindings(el, text);
      return text;
    }
    if (el.type === "theme.settings_page") {
      const wrapper = document.createElement("section");
      wrapper.className = "ui-element n3-theme-settings";
      const header = document.createElement("div");
      header.className = "n3-theme-settings-header";
      const title = document.createElement("div");
      title.className = "n3-theme-settings-title";
      title.textContent = "Theme settings";
      const subtitle = document.createElement("div");
      subtitle.className = "n3-theme-settings-subtitle";
      subtitle.textContent = "Adjust size, corners, density, font, and color scheme.";
      header.appendChild(title);
      header.appendChild(subtitle);
      wrapper.appendChild(header);

      const fieldOrder = ["size", "radius", "density", "font", "color_scheme"];
      const fieldLabels = {
        size: "Size",
        radius: "Corner radius",
        density: "Density",
        font: "Font size",
        color_scheme: "Color scheme",
      };
      const fallbackOptions = {
        size: ["compact", "normal", "comfortable"],
        radius: ["none", "sm", "md", "lg", "full"],
        density: ["tight", "regular", "airy"],
        font: ["sm", "md", "lg"],
        color_scheme: ["light", "dark", "system"],
      };
      const current = typeof el.current === "object" && el.current ? el.current : {};
      const options = typeof el.options === "object" && el.options ? el.options : {};
      const controls = document.createElement("div");
      controls.className = "n3-theme-settings-controls";
      const selects = {};

      function collectSettings() {
        const settings = {};
        fieldOrder.forEach((field) => {
          const select = selects[field];
          if (!select) return;
          settings[field] = select.value;
        });
        return settings;
      }

      function submitSettings(target) {
        const actionId = el.action_id || el.id;
        if (!actionId) return;
        handleAction({ id: actionId }, { settings: collectSettings() }, target || wrapper);
      }

      fieldOrder.forEach((field) => {
        const row = document.createElement("label");
        row.className = "n3-theme-setting";
        const label = document.createElement("span");
        label.className = "n3-theme-setting-label";
        label.textContent = fieldLabels[field] || field;
        const select = document.createElement("select");
        select.className = "n3-theme-setting-select";
        select.setAttribute("aria-label", label.textContent);
        const entries = Array.isArray(options[field]) ? options[field] : fallbackOptions[field] || [];
        entries.forEach((value) => {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = value.replace(/_/g, " ");
          select.appendChild(option);
        });
        if (current[field]) {
          select.value = current[field];
        }
        select.onchange = (e) => submitSettings(e.currentTarget);
        selects[field] = select;
        row.appendChild(label);
        row.appendChild(select);
        controls.appendChild(row);
      });

      wrapper.appendChild(controls);
      return wrapper;
    }
    if (el.type === "conditional.if") {
      const fragment = document.createDocumentFragment();
      const condition = el.condition || {};
      const showThen = condition.result === true;
      const branch = showThen ? el.then_children : el.else_children;
      renderChildren(fragment, branch, pageName);
      return fragment;
    }
    if (el.type === "row") {
      const row = document.createElement("div");
      row.className = "ui-row";
      renderChildren(row, el.children, pageName);
      return row;
    }
    if (el.type === "column") {
      const col = document.createElement("div");
      col.className = "ui-column";
      renderChildren(col, el.children, pageName);
      return col;
    }
    if (el.type === "divider") {
      const hr = document.createElement("hr");
      hr.className = "ui-divider";
      return hr;
    }
    if (el.type === "image") {
      const wrapper = document.createElement("div");
      wrapper.className = "ui-element ui-image-wrapper";
      const src = typeof el.src === "string" ? el.src : "";
      const name = el.media_name || "";
      if (src) {
        const img = document.createElement("img");
        img.className = "ui-image";
        img.src = src;
        img.alt = el.alt || name || "";
        img.loading = "lazy";
        wrapper.appendChild(img);
        return wrapper;
      }
      const placeholder = document.createElement("div");
      placeholder.className = "ui-image";
      const label = name ? `image: ${name}` : "image";
      placeholder.textContent = el.missing ? `${label} (missing)` : label;
      if (el.missing && el.fix_hint) {
        placeholder.title = el.fix_hint;
      }
      wrapper.appendChild(placeholder);
      return wrapper;
    }
    if (el.type === "audio") {
      const wrapper = document.createElement("div");
      wrapper.className = "ui-element ui-audio-wrapper";
      const src = typeof el.src === "string" ? el.src : "";
      const name = typeof el.media_name === "string" ? el.media_name : "";
      const label = typeof el.label === "string" ? el.label : name || "audio";
      if (label) {
        const title = document.createElement("div");
        title.className = "ui-audio-label";
        title.textContent = label;
        wrapper.appendChild(title);
      }
      if (src) {
        const audio = document.createElement("audio");
        audio.className = "ui-audio";
        audio.controls = true;
        audio.preload = "metadata";
        audio.src = src;
        audio.setAttribute("aria-label", label);
        wrapper.appendChild(audio);
        if (typeof el.transcript === "string" && el.transcript) {
          const transcript = document.createElement("div");
          transcript.className = "ui-audio-transcript";
          transcript.textContent = el.transcript;
          wrapper.appendChild(transcript);
        }
        return wrapper;
      }
      const placeholder = document.createElement("div");
      placeholder.className = "ui-audio";
      placeholder.textContent = el.missing ? `${label} (missing)` : label;
      if (el.missing && el.fix_hint) {
        placeholder.title = el.fix_hint;
      }
      wrapper.appendChild(placeholder);
      return wrapper;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";
    if (typeof el.type === "string" && el.type) wrapper.dataset.elementType = el.type;
    if (typeof el.id === "string" && el.id) wrapper.dataset.elementId = el.id;
    if (typeof el.element_id === "string" && el.element_id) wrapper.dataset.elementId = el.element_id;
    if (el.type === "title") {
      const h = document.createElement("h3");
      h.textContent = el.value;
      wrapper.appendChild(h);
    } else if (el.type === "text") {
      const value = typeof el.value === "string" ? el.value : String(el.value || "");
      if (value.startsWith("$ ")) {
        const pre = document.createElement("pre");
        pre.className = "n3-codeblock";
        pre.textContent = value;
        wrapper.appendChild(pre);
      } else {
        const p = document.createElement("p");
        p.textContent = value;
        wrapper.appendChild(p);
      }
    } else if (el.type === "error") {
      const box = document.createElement("div");
      box.className = "empty-state status-error";
      const message = typeof el.message === "string" ? el.message : String(el.message || "");
      const text = document.createElement("div");
      text.textContent = message;
      box.appendChild(text);
      wrapper.appendChild(box);
    } else if (el.type === "input") {
      const form = document.createElement("form");
      form.className = "ui-element ui-input";
      const input = document.createElement("input");
      input.type = "text";
      const enabled = el.enabled !== false;
      const labelText = el.name ? String(el.name) : "Input";
      input.placeholder = labelText;
      input.setAttribute("aria-label", labelText);
      input.disabled = !enabled;
      const button = document.createElement("button");
      button.type = "submit";
      button.className = "btn small";
      button.textContent = "Send";
      button.disabled = !enabled;
      form.appendChild(input);
      form.appendChild(button);
      form.onsubmit = async (e) => {
        e.preventDefault();
        if (!enabled) return;
        const value = input.value || "";
        if (!value) return;
        const action = el.action || {};
        const actionId = el.action_id || el.id;
        const inputField = action.input_field || el.name || "input";
        await handleAction(
          {
            id: actionId,
            type: action.type || "call_flow",
            flow: action.flow,
            target: action.target,
          },
          { [inputField]: value },
          button
        );
        input.value = "";
      };
      return form;
    } else if (el.type === "button") {
      const actions = document.createElement("div");
      actions.className = "ui-buttons";
      const btn = document.createElement("button");
      const enabled = el.enabled !== false;
      btn.className = "btn primary";
      btn.textContent = el.label;
      btn.disabled = !enabled;
      btn.onclick = (e) => {
        e.stopPropagation();
        if (!enabled) return;
        const action = el.action || {};
        const actionId = el.action_id || el.id;
        handleAction(
          {
            id: actionId,
            type: action.type || "call_flow",
            flow: action.flow,
            target: action.target,
          },
          {},
          e.currentTarget
        );
      };
      actions.appendChild(btn);
      wrapper.appendChild(actions);
    } else if (el.type === "link") {
      const action = el.action || {};
      const target = action.target || el.target;
      const slug = resolvePageSlug(target);
      const link = document.createElement("a");
      link.className = "ui-link";
      link.textContent = el.label || "Open page";
      link.href = buildPageUrl(slug);
      link.onclick = (e) => {
        e.preventDefault();
        const actionId = el.action_id || el.id;
        handleAction(
          {
            id: actionId,
            type: action.type || "open_page",
            target: target,
          },
          {},
          e.currentTarget
        );
      };
      wrapper.appendChild(link);
    } else if (el.type === "form") {
      if (typeof renderFormElement === "function") {
        return renderFormElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Form renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "chat") {
      if (typeof renderChatElement === "function") {
        return renderChatElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Chat renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "citation_chips") {
      if (typeof renderCitationChipsElement === "function") {
        return renderCitationChipsElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Citations renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "source_preview") {
      if (typeof renderSourcePreviewElement === "function") {
        return renderSourcePreviewElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Source preview renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "trust_indicator") {
      if (typeof renderTrustIndicatorElement === "function") {
        return renderTrustIndicatorElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Trust indicator renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "scope_selector") {
      if (typeof renderScopeSelectorElement === "function") {
        return renderScopeSelectorElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Scope selector renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "upload") {
      if (typeof renderUploadElement === "function") {
        return renderUploadElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Upload renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "ingestion_status") {
      if (typeof renderIngestionStatusElement === "function") {
        return renderIngestionStatusElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Ingestion status renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "runtime_error") {
      if (typeof renderRuntimeErrorElement === "function") {
        return renderRuntimeErrorElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Runtime error renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "capabilities") {
      if (typeof renderCapabilitiesElement === "function") {
        return renderCapabilitiesElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Capabilities renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "state_inspector") {
      if (typeof renderStateInspectorElement === "function") {
        return renderStateInspectorElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "State inspector renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "retrieval_explain") {
      if (typeof renderRetrievalExplainElement === "function") {
        return renderRetrievalExplainElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Retrieval explain renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "audit_viewer") {
      if (typeof renderAuditViewerElement === "function") {
        return renderAuditViewerElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Audit viewer renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "run_diff") {
      if (typeof renderRunDiffElement === "function") {
        return renderRunDiffElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Run diff renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "diagnostics_panel") {
      if (typeof renderDiagnosticsElement === "function") {
        return renderDiagnosticsElement(el);
      }
      const empty = document.createElement("div");
      empty.textContent = "Diagnostics renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "custom_component") {
      wrapper.classList.add("ui-custom-component");
      if (typeof el.plugin === "string" && el.plugin) wrapper.dataset.plugin = el.plugin;
      if (typeof el.component === "string" && el.component) wrapper.dataset.component = el.component;
      const nodes = Array.isArray(el.nodes) ? el.nodes : [];
      if (!nodes.length) {
        const empty = document.createElement("div");
        empty.className = "ui-custom-component-empty";
        empty.textContent = "Custom component has no rendered nodes.";
        wrapper.appendChild(empty);
      } else {
        nodes.forEach((node, idx) => {
          const item = document.createElement("div");
          item.className = "ui-custom-component-node";
          const nodeType = node && typeof node === "object" && typeof node.type === "string" ? node.type : "node";
          item.dataset.nodeType = nodeType;
          item.dataset.nodeIndex = String(idx);
          const preview = node && typeof node === "object" && typeof node.text === "string" ? node.text : nodeType;
          item.textContent = String(preview);
          wrapper.appendChild(item);
        });
      }
      const detail = {
        element: wrapper,
        page: pageName,
        plugin: el.plugin || "",
        component: el.component || "",
        props: el.props || {},
        nodes: nodes,
      };
      wrapper.dispatchEvent(new CustomEvent("n3:plugin-component", { bubbles: true, detail: detail }));
      if (window.N3PluginRuntime && typeof window.N3PluginRuntime.renderComponent === "function") {
        try {
          window.N3PluginRuntime.renderComponent(detail);
        } catch (_err) {
          wrapper.dataset.pluginRenderError = "true";
        }
      }
    } else if (el.type === "list") {
      if (typeof renderListElement === "function") {
        return renderListElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "List renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "table") {
      if (typeof renderTableElement === "function") {
        return renderTableElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Table renderer unavailable.";
      wrapper.appendChild(empty);
    } else if (el.type === "chart") {
      if (typeof renderChartElement === "function") {
        return renderChartElement(el, handleAction);
      }
      const empty = document.createElement("div");
      empty.textContent = "Chart renderer unavailable.";
      wrapper.appendChild(empty);
    }
    return wrapper;
  }

  function normalizeLayout(page) {
    if (!page || typeof page !== "object" || typeof page.layout !== "object" || page.layout === null) {
      return null;
    }
    const normalized = {};
    LAYOUT_SLOTS.forEach((slot) => {
      normalized[slot] = Array.isArray(page.layout[slot]) ? page.layout[slot] : [];
    });
    return normalized;
  }

  function splitOverlayItems(elements) {
    const result = { items: [], overlays: [] };
    (elements || []).forEach((el) => {
      if (!el || el.visible === false) return;
      if (el.type === "modal" || el.type === "drawer") {
        result.overlays.push(el);
      } else {
        result.items.push(el);
      }
    });
    return result;
  }

  function appendRenderedItems(container, elements, pageName) {
    (elements || []).forEach((el) => {
      if (!el || el.visible === false) return;
      const node = renderElement(el, pageName);
      applyThemeClasses(node, el);
      container.appendChild(node);
    });
  }

  function buildDiagnosticsSection(page) {
    if (!diagnosticsEnabled) return null;
    const blocks = diagnosticsElements(page).filter((entry) => entry && entry.visible !== false);
    if (!blocks.length) return null;
    const section = document.createElement("section");
    section.className = "n3-diagnostics";
    const header = document.createElement("div");
    header.className = "n3-diagnostics-header";
    const title = document.createElement("div");
    title.className = "n3-diagnostics-title";
    title.textContent = "Diagnostics";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "btn small ghost n3-diagnostics-toggle";
    const body = document.createElement("div");
    body.className = "n3-diagnostics-body";
    appendRenderedItems(body, blocks, page.name);

    function applyVisible(visible) {
      toggle.textContent = visible ? "Hide Explain" : "Show Explain";
      toggle.setAttribute("aria-expanded", visible ? "true" : "false");
      body.classList.toggle("hidden", !visible);
    }

    const initialVisible = diagnosticsVisibleForPage(page);
    applyVisible(initialVisible);
    toggle.onclick = () => {
      const nextVisible = !diagnosticsVisibleForPage(page);
      setDiagnosticsVisibleForPage(page, nextVisible);
      applyVisible(nextVisible);
    };
    header.appendChild(title);
    header.appendChild(toggle);
    section.appendChild(header);
    section.appendChild(body);
    return section;
  }

  function renderNavigationSidebar(activeSlugForPage) {
    if (!sidebarItems.length) return null;
    const nav = document.createElement("nav");
    nav.className = "n3-navigation-sidebar";
    nav.setAttribute("aria-label", "Primary navigation");
    nav.setAttribute("role", "navigation");
    const list = document.createElement("ul");
    list.className = "n3-navigation-list";
    sidebarItems.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const target = resolvePageSlug(entry.target_slug || entry.target_name);
      if (!target) return;
      const item = document.createElement("li");
      item.className = "n3-navigation-list-item";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "n3-navigation-item";
      button.textContent = entry.label || entry.target_name || target;
      const isActive = target === activeSlugForPage;
      button.classList.toggle("active", isActive);
      if (isActive) {
        button.setAttribute("aria-current", "page");
      } else {
        button.removeAttribute("aria-current");
      }
      button.onclick = (event) => {
        event.preventDefault();
        navigateToPage(target, { push: true });
      };
      button.onkeydown = (event) => {
        if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
        event.preventDefault();
        const focusable = Array.from(list.querySelectorAll(".n3-navigation-item"));
        const currentIndex = focusable.indexOf(button);
        if (currentIndex < 0 || !focusable.length) return;
        const step = event.key === "ArrowDown" ? 1 : -1;
        const nextIndex = (currentIndex + step + focusable.length) % focusable.length;
        focusable[nextIndex].focus();
      };
      item.appendChild(button);
      list.appendChild(item);
    });
    if (!list.children.length) return null;
    nav.appendChild(list);
    return nav;
  }

  function renderLayoutPage(page, mountNode) {
    const targetNode = mountNode || uiContainer;
    const layout = normalizeLayout(page);
    if (!layout) return false;
    const root = document.createElement("div");
    root.className = "n3-layout-root";
    const overlayItems = [];
    const slots = {};
    LAYOUT_SLOTS.forEach((slot) => {
      const split = splitOverlayItems(layout[slot]);
      slots[slot] = split.items;
      overlayItems.push(...split.overlays);
    });

    let sidebarDrawer = null;
    let sidebarToggle = null;
    const hasSidebar = slots.sidebar_left.length > 0;

    function setSidebarDrawerOpen(open) {
      if (!sidebarDrawer) return;
      sidebarDrawer.classList.toggle("open", open);
      if (sidebarToggle) {
        sidebarToggle.setAttribute("aria-expanded", open ? "true" : "false");
      }
    }

    const header = document.createElement("div");
    header.className = "n3-layout-header";
    if (hasSidebar) {
      sidebarToggle = document.createElement("button");
      sidebarToggle.type = "button";
      sidebarToggle.className = "btn small ghost n3-layout-sidebar-toggle";
      sidebarToggle.textContent = "Sections";
      sidebarToggle.setAttribute("aria-expanded", "false");
      sidebarToggle.onclick = () => {
        const nextOpen = !sidebarDrawer || !sidebarDrawer.classList.contains("open");
        setSidebarDrawerOpen(nextOpen);
      };
      header.appendChild(sidebarToggle);
    }
    appendRenderedItems(header, slots.header, page.name);
    if (header.children.length) {
      root.appendChild(header);
    }

    const body = document.createElement("div");
    body.className = "n3-layout-body";
    body.dataset.hasDrawer = slots.drawer_right.length > 0 ? "true" : "false";

    if (hasSidebar) {
      const sidebar = document.createElement("aside");
      sidebar.className = "n3-layout-sidebar";
      appendRenderedItems(sidebar, slots.sidebar_left, page.name);
      body.appendChild(sidebar);

      sidebarDrawer = document.createElement("div");
      sidebarDrawer.className = "n3-layout-sidebar-drawer";
      const drawerBackdrop = document.createElement("button");
      drawerBackdrop.type = "button";
      drawerBackdrop.className = "n3-layout-sidebar-backdrop";
      drawerBackdrop.setAttribute("aria-label", "Close sidebar");
      drawerBackdrop.onclick = () => setSidebarDrawerOpen(false);
      const drawerPanel = document.createElement("div");
      drawerPanel.className = "n3-layout-sidebar-panel";
      const closeButton = document.createElement("button");
      closeButton.type = "button";
      closeButton.className = "btn small ghost n3-layout-sidebar-close";
      closeButton.textContent = "Close";
      closeButton.onclick = () => setSidebarDrawerOpen(false);
      drawerPanel.appendChild(closeButton);
      appendRenderedItems(drawerPanel, slots.sidebar_left, page.name);
      sidebarDrawer.appendChild(drawerBackdrop);
      sidebarDrawer.appendChild(drawerPanel);
      root.appendChild(sidebarDrawer);
    }

    if (slots.main.length) {
      const main = document.createElement("section");
      main.className = "n3-layout-main";
      appendRenderedItems(main, slots.main, page.name);
      body.appendChild(main);
    }

    if (slots.drawer_right.length) {
      const drawer = document.createElement("aside");
      drawer.className = "n3-layout-drawer";
      appendRenderedItems(drawer, slots.drawer_right, page.name);
      body.appendChild(drawer);
    }

    if (body.children.length) {
      root.appendChild(body);
    }

    if (slots.footer.length) {
      const footer = document.createElement("div");
      footer.className = "n3-layout-footer";
      appendRenderedItems(footer, slots.footer, page.name);
      root.appendChild(footer);
    }

    const diagnosticsSection = buildDiagnosticsSection(page);
    if (diagnosticsSection) {
      root.appendChild(diagnosticsSection);
    }

    if (overlayItems.length) {
      const overlayLayer = document.createElement("div");
      overlayLayer.className = "ui-overlay-layer";
      overlayItems.forEach((el) => {
        const overlayNode = renderOverlay(el, page.name);
        applyThemeClasses(overlayNode, el);
        overlayLayer.appendChild(overlayNode);
      });
      root.appendChild(overlayLayer);
    }
    targetNode.appendChild(root);
    return true;
  }

  function renderPage(pageKey, options = {}) {
    uiContainer.innerHTML = "";
    overlayRegistry.clear();
    const entry = resolvePageEntry(pageKey) || pageEntries[0];
    const page = entry ? entry.page : null;
    if (!page) {
      showEmpty(uiContainer, emptyMessage);
      return;
    }
    const resolvedSlug = entry ? entry.slug : "";
    currentPageSlug = resolvedSlug;
    if (!navigationLocked && !options.skipRouteSync) {
      writeRouteSlug(resolvedSlug, { push: false });
    }
    applyLocaleSettings();
    applyPageTheme(page);
    let pageContainer = uiContainer;
    const sidebar = renderNavigationSidebar(resolvedSlug);
    if (sidebar) {
      const shell = document.createElement("div");
      shell.className = "n3-navigation-shell";
      const content = document.createElement("div");
      content.className = "n3-navigation-content";
      shell.appendChild(sidebar);
      shell.appendChild(content);
      uiContainer.appendChild(shell);
      pageContainer = content;
    }
    if (renderLayoutPage(page, pageContainer)) {
      return;
    }
    const split = splitOverlayItems(page.elements || []);
    split.items.forEach((el) => {
      const node = renderElement(el, page.name);
      applyThemeClasses(node, el);
      pageContainer.appendChild(node);
    });
    if (split.overlays.length) {
      const overlayLayer = document.createElement("div");
      overlayLayer.className = "ui-overlay-layer";
      split.overlays.forEach((el) => {
        const overlayNode = renderOverlay(el, page.name);
        applyThemeClasses(overlayNode, el);
        overlayLayer.appendChild(overlayNode);
      });
      pageContainer.appendChild(overlayLayer);
    }
    const diagnosticsSection = buildDiagnosticsSection(page);
    if (diagnosticsSection) {
      pageContainer.appendChild(diagnosticsSection);
    }
  }
  if (select) {
    select.onchange = (e) => navigateToPage(e.target.value, { push: true });
  }
  if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
    const popKey = "__n3PagePopstateHandler";
    const previous = window[popKey];
    if (typeof previous === "function") {
      window.removeEventListener("popstate", previous);
    }
    const handler = () => {
      if (navigationLocked) return;
      const routeSlug = readRouteSlug();
      const stateSlug = resolvePageSlug(window.history && window.history.state ? window.history.state.n3PageSlug : "");
      const nextSlug = routeSlug || stateSlug || (pageEntries[0] ? pageEntries[0].slug : "");
      if (!nextSlug) return;
      if (select) select.value = nextSlug;
      renderPage(nextSlug, { skipRouteSync: true });
    };
    window[popKey] = handler;
    window.addEventListener("popstate", handler);
  }
  const initialPage = (select && select.value) || (pageEntries[0] ? pageEntries[0].slug : "");
  if (initialPage) {
    renderPage(initialPage, { skipRouteSync: navigationLocked });
  } else {
    showEmpty(uiContainer, emptyMessage);
  }
};

let renderUIError = (detail) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const emptyMessage = "Run your app to see it here.";
  if (!uiContainer) return;
  if (select) select.innerHTML = "";
  if (typeof showError === "function") {
    showError(uiContainer, detail);
  } else if (typeof showEmpty === "function") {
    showEmpty(uiContainer, emptyMessage);
  }
};

window.renderUI = renderUI;
window.renderUIError = renderUIError;
