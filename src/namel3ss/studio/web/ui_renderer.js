let renderUI = (manifest) => {
  const select = document.getElementById("pageSelect");
  const uiContainer = document.getElementById("ui");
  const pages = manifest.pages || [];
  const emptyMessage = "Run your app to see it here.";
  const collectionRender = window.N3UIRender || {};
  const renderListElement = collectionRender.renderListElement;
  const renderTableElement = collectionRender.renderTableElement;
  const renderFormElement = collectionRender.renderFormElement;
  const renderChatElement = collectionRender.renderChatElement;
  const renderChartElement = collectionRender.renderChartElement;
  const overlayRegistry = new Map();
  if (!uiContainer) return;
  const currentSelection = select ? select.value : "";
  if (select) {
    select.innerHTML = "";
    pages.forEach((p, idx) => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = p.name;
      if (p.name === currentSelection || (currentSelection === "" && idx === 0)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
  }
  function renderChildren(container, children, pageName) {
    (children || []).forEach((child) => {
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
  function handleAction(action, payload, opener) {
    if (!action || !action.id) return;
    const actionType = action.type || "call_flow";
    if (actionType === "open_modal" || actionType === "open_drawer") {
      openOverlay(action.target, opener);
      return { ok: true };
    }
    if (actionType === "close_modal" || actionType === "close_drawer") {
      closeOverlay(action.target);
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
      const tabs = Array.isArray(el.children) ? el.children : [];
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
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "btn small";
          btn.textContent = action.label || "Run";
          btn.onclick = (e) => {
            e.stopPropagation();
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
      const img = document.createElement("img");
      img.className = "ui-image";
      img.src = el.src || "";
      img.alt = el.alt || "";
      img.loading = "lazy";
      wrapper.appendChild(img);
      return wrapper;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";
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
    } else if (el.type === "button") {
      const actions = document.createElement("div");
      actions.className = "ui-buttons";
      const btn = document.createElement("button");
      btn.className = "btn primary";
      btn.textContent = el.label;
      btn.onclick = (e) => {
        e.stopPropagation();
        handleAction({ id: el.action_id, type: "call_flow", flow: el.action && el.action.flow }, {}, e.currentTarget);
      };
      actions.appendChild(btn);
      wrapper.appendChild(actions);
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
  function renderPage(pageName) {
    uiContainer.innerHTML = "";
    overlayRegistry.clear();
    const page = pages.find((p) => p.name === pageName) || pages[0];
    if (!page) {
      showEmpty(uiContainer, emptyMessage);
      return;
    }
    const overlayItems = [];
    const mainItems = [];
    (page.elements || []).forEach((el) => {
      if (el.type === "modal" || el.type === "drawer") {
        overlayItems.push(el);
      } else {
        mainItems.push(el);
      }
    });
    mainItems.forEach((el) => {
      uiContainer.appendChild(renderElement(el, page.name));
    });
    if (overlayItems.length) {
      const overlayLayer = document.createElement("div");
      overlayLayer.className = "ui-overlay-layer";
      overlayItems.forEach((el) => {
        overlayLayer.appendChild(renderOverlay(el, page.name));
      });
      uiContainer.appendChild(overlayLayer);
    }
  }
  if (select) {
    select.onchange = (e) => renderPage(e.target.value);
  }
  const initialPage = (select && select.value) || (pages[0] ? pages[0].name : "");
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
