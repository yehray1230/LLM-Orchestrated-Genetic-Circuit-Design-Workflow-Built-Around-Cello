(() => {
  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const ensureFormMessage = (form) => {
    let message = form.querySelector("[data-form-message]");
    if (!message) {
      message = document.createElement("div");
      message.dataset.formMessage = "true";
      message.setAttribute("role", "alert");
      message.setAttribute("aria-live", "polite");
      form.prepend(message);
    }
    return message;
  };

  const setFormMessage = (form, text, type = "error") => {
    const message = ensureFormMessage(form);
    message.className = type === "error" ? "form-error" : "form-notice";
    message.textContent = text;
  };

  const clearFormMessage = (form) => {
    const message = form.querySelector("[data-form-message]");
    if (message) {
      message.textContent = "";
      message.className = "";
    }
  };

  const setFieldError = (field, text) => {
    field.setAttribute("aria-invalid", text ? "true" : "false");
    let error = field.parentElement?.querySelector("[data-field-error]");
    if (text && !error) {
      error = document.createElement("span");
      error.dataset.fieldError = "true";
      error.className = "field-error";
      field.insertAdjacentElement("afterend", error);
    }
    if (error) {
      error.textContent = text || "";
      if (!text) error.remove();
    }
  };

  const validateJsonField = (field) => {
    const raw = field.value.trim();
    if (!raw) {
      setFieldError(field, "");
      return true;
    }
    try {
      const parsed = JSON.parse(raw);
      const expected = field.dataset.jsonInput;
      if (expected === "array" && !Array.isArray(parsed)) {
        setFieldError(field, "Please provide a valid JSON array.");
        return false;
      }
      if (expected === "object" && (Array.isArray(parsed) || parsed === null || typeof parsed !== "object")) {
        setFieldError(field, "Please provide a valid JSON object.");
        return false;
      }
      setFieldError(field, "");
      return true;
    } catch (error) {
      setFieldError(field, `Invalid JSON: ${error.message}`);
      return false;
    }
  };

  const enhanceForms = () => {
    document.querySelectorAll("[data-json-input]").forEach((field) => {
      field.addEventListener("input", () => validateJsonField(field));
      field.addEventListener("blur", () => validateJsonField(field));
    });

    document.querySelectorAll("form").forEach((form) => {
      form.addEventListener("submit", (event) => {
        clearFormMessage(form);
        const jsonFields = Array.from(form.querySelectorAll("[data-json-input]"));
        const jsonIsValid = jsonFields.every(validateJsonField);
        if (!jsonIsValid) {
          event.preventDefault();
          setFormMessage(form, "Please fix invalid JSON fields before submitting.");
          jsonFields.find((field) => field.getAttribute("aria-invalid") === "true")?.focus();
          return;
        }

        form.setAttribute("aria-busy", "true");
        form.querySelectorAll("button[type='submit']").forEach((button) => {
          if (!button.dataset.originalText) button.dataset.originalText = button.textContent || "";
          button.textContent = button.dataset.loadingText || "Submitting...";
          button.disabled = true;
        });
      });
    });
  };

  const monitor = document.querySelector("[data-run-monitor='true']");
  if (monitor) {
    const statusUrl = monitor.dataset.statusUrl;
    const statusNode = monitor.querySelector("[data-run-status]");
    const stageNode = monitor.querySelector("[data-run-stage]");
    const statusPill = monitor.querySelector("[data-run-status-pill]");
    const stagePill = monitor.querySelector("[data-run-stage-pill]");
    const progressLabel = monitor.querySelector("[data-run-progress-label]");
    const progressBar = monitor.querySelector("[data-run-progress-bar]");
    const errorNode = monitor.querySelector("[data-run-error]");
    const eventsNode = monitor.querySelector("[data-run-events]");
    const eventCountNode = monitor.querySelector("[data-run-event-count]");
    const latestMessageNode = monitor.querySelector("[data-run-latest-message]");
    const resultJsonNode = monitor.querySelector("[data-run-result-json]");
    const initialTerminal = monitor.dataset.terminal === "true";
    let lastEventId = Math.max(
      0,
      ...Array.from(monitor.querySelectorAll("[data-event-id]")).map((node) =>
        Number(node.dataset.eventId || 0)
      )
    );

    const renderEvent = (event) => {
      const item = document.createElement("div");
      item.className = `timeline-item ${event.stage_class || "stage-neutral"} ${event.status_class || "status-neutral"}`;
      item.dataset.eventId = String(event.event_id || "");
      item.innerHTML = `
        <div class="timeline-meta">
          <span>#${escapeHtml(event.event_id ?? "-")}</span>
          <span class="stage-chip ${escapeHtml(event.stage_class || "stage-neutral")}">${escapeHtml(event.stage || "-")}</span>
          <span class="status-badge ${escapeHtml(event.status_class || "status-neutral")}">${escapeHtml(event.status || "-")}</span>
        </div>
        <div class="timeline-message">${escapeHtml(event.message || "No message recorded.")}</div>
      `;
      return item;
    };

    const updateMonitor = async () => {
      if (!statusUrl || initialTerminal) return;
      const separator = statusUrl.includes("?") ? "&" : "?";
      const response = await fetch(`${statusUrl}${separator}after_event_id=${lastEventId}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return;
      const payload = await response.json();
      const run = payload.run || {};
      const monitorPayload = payload.monitor || {};
      const progress = Number(run.progress || 0);
      const percent = Math.max(0, Math.min(100, progress * 100));

      if (statusNode) statusNode.textContent = run.status || "-";
      if (stageNode) stageNode.textContent = run.stage || "-";
      if (statusPill) {
        statusPill.textContent = run.status || "-";
        statusPill.className = `status-badge ${monitorPayload.status_class || "status-neutral"}`;
      }
      if (stagePill) {
        stagePill.textContent = run.stage || "waiting";
        stagePill.className = `stage-chip ${monitorPayload.stage_class || "stage-neutral"}`;
      }
      if (progressLabel) progressLabel.textContent = `${Math.round(percent)}%`;
      if (progressBar) progressBar.style.width = `${percent}%`;
      if (latestMessageNode && monitorPayload.latest_message) {
        latestMessageNode.textContent = monitorPayload.latest_message;
      }
      if (errorNode) {
        errorNode.innerHTML = run.error
          ? `<div class="error-box section-space">${escapeHtml(run.error)}</div>`
          : "";
      }

      const events = monitorPayload.events || payload.events || [];
      if (eventsNode && events.length) {
        const empty = eventsNode.querySelector("[data-empty-events]");
        if (empty) empty.remove();
        for (const event of events) {
          eventsNode.appendChild(renderEvent(event));
          lastEventId = Math.max(lastEventId, Number(event.event_id || 0));
        }
      }
      if (eventCountNode) {
        const count = eventsNode
          ? eventsNode.querySelectorAll("[data-event-id]").length
          : events.length;
        eventCountNode.textContent = `${count} events`;
      }
      if (resultJsonNode) {
        resultJsonNode.textContent = JSON.stringify(payload.result || payload, null, 2);
      }

      if (payload.terminal || run.status === "needs_human_input") {
        window.location.reload();
        return;
      }
      window.setTimeout(updateMonitor, payload.next_poll_ms || 3000);
    };

    window.setTimeout(updateMonitor, 3000);
  }

  const marker = document.querySelector("[data-auto-refresh='true']");
  if (marker) {
    window.setTimeout(() => window.location.reload(), 3000);
  }

  enhanceForms();
})();
