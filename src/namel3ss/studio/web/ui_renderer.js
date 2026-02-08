let renderUI = (manifest) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const pages = manifest.pages || [];
  const navigation = manifest.navigation || {};
  const activePage = navigation.active_page || null;
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

  function readRouteSlug() {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search || "");
    return resolvePageSlug(params.get("page"));
  }

  function writeRouteSlug(slug) {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (slug) {
      url.searchParams.set("page", slug);
    } else {
      url.searchParams.delete("page");
    }
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", url.toString());
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
  function renderChildren(container, children, pageName) {
    (children || []).forEach((child) => {
      if (child && child.visible === false) return;
      const node = renderElement(child, pageName);
      container.appendChild(node);
    });
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
    if (entry.type === "modal") {
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
  function navigateToPage(value) {
    if (navigationLocked) return;
    const slug = resolvePageSlug(value);
    if (!slug) return;
    if (select) {
      select.value = slug;
    }
    writeRouteSlug(slug);
    renderPage(slug);
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
    if (actionType === "open_page") {
      if (navigationLocked) return { ok: false };
      navigateToPage(action.target);
      return { ok: true };
    }
    return executeAction(action.id, payload);
  }
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
      container.appendChild(renderElement(el, pageName));
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

  function renderLayoutPage(page) {
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
        overlayLayer.appendChild(renderOverlay(el, page.name));
      });
      root.appendChild(overlayLayer);
    }
    uiContainer.appendChild(root);
    return true;
  }

  function renderPage(pageKey) {
    uiContainer.innerHTML = "";
    overlayRegistry.clear();
    const entry = resolvePageEntry(pageKey) || pageEntries[0];
    const page = entry ? entry.page : null;
    if (!page) {
      showEmpty(uiContainer, emptyMessage);
      return;
    }
    if (renderLayoutPage(page)) {
      return;
    }
    const split = splitOverlayItems(page.elements || []);
    split.items.forEach((el) => {
      uiContainer.appendChild(renderElement(el, page.name));
    });
    if (split.overlays.length) {
      const overlayLayer = document.createElement("div");
      overlayLayer.className = "ui-overlay-layer";
      split.overlays.forEach((el) => {
        overlayLayer.appendChild(renderOverlay(el, page.name));
      });
      uiContainer.appendChild(overlayLayer);
    }
    const diagnosticsSection = buildDiagnosticsSection(page);
    if (diagnosticsSection) {
      uiContainer.appendChild(diagnosticsSection);
    }
  }
  if (select) {
    select.onchange = (e) => navigateToPage(e.target.value);
  }
  const initialPage = (select && select.value) || (pageEntries[0] ? pageEntries[0].slug : "");
  if (initialPage) {
    renderPage(initialPage);
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
