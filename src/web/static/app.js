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

    const updateElapsedTimer = () => {
      const elapsedEl = document.getElementById("elapsed-time");
      if (!elapsedEl) return;
      const createdAtStr = elapsedEl.dataset.createdAt;
      if (!createdAtStr) return;

      const createdAt = new Date(createdAtStr);
      const update = () => {
        const now = new Date();
        let diffMs = now - createdAt;
        if (diffMs < 0) diffMs = 0;

        const diffSecs = Math.floor(diffMs / 1000);
        const mins = Math.floor(diffSecs / 60);
        const secs = diffSecs % 60;

        const pad = (num) => String(num).padStart(2, "0");
        elapsedEl.textContent = `${pad(mins)}:${pad(secs)}`;
      };

      update();
      if (!initialTerminal) {
        window.setInterval(update, 1000);
      }
    };
    updateElapsedTimer();

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

  const checkAIStatus = async () => {
    const card = document.getElementById("ai-status-card");
    if (!card) return;
    const detailNode = document.getElementById("ai-status-detail");
    const badgeContainer = document.getElementById("ai-status-badge-container");

    try {
      const response = await fetch("/api/v1/settings/status", {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("API response error");
      const payload = await response.json();
      const status = payload.data || {};

      if (status.available) {
        if (status.mode === "byok") {
          card.style.borderLeft = "5px solid var(--success)";
          if (detailNode) detailNode.textContent = `供應商: ${status.provider} · 模型: ${status.model_name} (連線成功)`;
          if (badgeContainer) {
            badgeContainer.innerHTML = '<span class="status-badge status-ready">已啟用自備金鑰</span>';
          }
        } else {
          card.style.borderLeft = "5px solid var(--warning)";
          if (detailNode) detailNode.textContent = `使用系統環境變數 · 模型: ${status.model_name} (連線成功)`;
          if (badgeContainer) {
            badgeContainer.innerHTML = '<span class="status-badge status-warning">使用系統預設</span>';
          }
        }
      } else {
        card.style.borderLeft = "5px solid #d92d20";
        if (detailNode) detailNode.textContent = `錯誤: ${status.message || "無法連線至模型 API"}`;
        if (badgeContainer) {
          badgeContainer.innerHTML = '<span class="status-badge status-error">連線失敗 / 未設定</span>';
        }
      }
    } catch (err) {
      card.style.borderLeft = "5px solid #d92d20";
      if (detailNode) detailNode.textContent = `無法獲取連線狀態: ${err.message}`;
      if (badgeContainer) {
        badgeContainer.innerHTML = '<span class="status-badge status-error">檢查失敗</span>';
      }
    }
  };

  const setupSettingsTest = () => {
    const btn = document.getElementById("test-connection-btn");
    if (!btn) return;
    const resultNode = document.getElementById("test-result");

    btn.addEventListener("click", async () => {
      const provider = document.getElementById("setting-provider").value;
      const modelName = document.getElementById("setting-model-name").value;
      const apiKey = document.getElementById("setting-api-key").value;
      const apiBase = document.getElementById("setting-api-base").value;

      btn.disabled = true;
      const originalText = btn.textContent;
      btn.textContent = "測試中...";
      if (resultNode) {
        resultNode.style.display = "block";
        resultNode.className = "warning-box";
        resultNode.style.background = "#f2f4f7";
        resultNode.style.color = "var(--muted)";
        resultNode.style.border = "1px solid var(--line)";
        resultNode.textContent = "正在發送測試請求，請稍候...";
      }

      try {
        const response = await fetch("/api/v1/settings/test", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            provider: provider,
            model_name: modelName,
            api_key: apiKey,
            api_base: apiBase,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`);
        }

        const payload = await response.json();
        const status = payload.data || {};

        if (resultNode) {
          if (status.available) {
            resultNode.className = "warning-box";
            resultNode.style.background = "#ecfdf3";
            resultNode.style.color = "#027a48";
            resultNode.style.border = "1px solid #d0f5e3";
            resultNode.textContent = "連線測試成功！" + (status.message || "");
          } else {
            resultNode.className = "error-box";
            resultNode.style.background = "#fef3f2";
            resultNode.style.color = "#b42318";
            resultNode.style.border = "1px solid #fee4e2";
            resultNode.textContent = "連線測試失敗: " + (status.message || "原因未知");
          }
        }
      } catch (err) {
        if (resultNode) {
          resultNode.className = "error-box";
          resultNode.style.background = "#fef3f2";
          resultNode.style.color = "#b42318";
          resultNode.style.border = "1px solid #fee4e2";
          resultNode.textContent = `請求失敗: ${err.message}`;
        }
      } finally {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });
  };

  const setupDesignWizard = () => {
    const form = document.getElementById("wizard-form");
    if (!form) return;

    let currentStep = 1;
    const maxStep = 4;

    const btnPrev = document.getElementById("btn-wizard-prev");
    const btnNext = document.getElementById("btn-wizard-next");
    const btnSubmit = document.getElementById("btn-wizard-submit");
    const autosaveIndicator = document.getElementById("draft-autosave-indicator");
    const recoveryBanner = document.getElementById("draft-recovery-banner");
    const savedTimeSpan = document.getElementById("draft-saved-time");
    const btnRestore = document.getElementById("btn-restore-draft");
    const btnDiscard = document.getElementById("btn-discard-draft");

    // Inputs mapping
    const fields = {
      user_intent: document.getElementById("wizard-user-intent"),
      host_organism: document.getElementById("wizard-host-organism"),
      compute_budget: document.getElementById("wizard-compute-budget"),
      enable_rag: document.getElementById("wizard-enable-rag"),
      enable_ode: document.getElementById("wizard-enable-ode"),
      enable_skill_extraction: document.getElementById("wizard-enable-skill"),
      model_name: document.getElementById("wizard-model-name"),
      api_base: document.getElementById("wizard-api-base"),
    };

    // Previews mapping
    const previews = {
      user_intent: document.getElementById("preview-user-intent"),
      host_organism: document.getElementById("preview-host-organism"),
      compute_budget: document.getElementById("preview-compute-budget"),
      model_config: document.getElementById("preview-model-config"),
      tools: document.getElementById("preview-tools"),
    };

    const updateWizardUI = () => {
      // Hide all steps, show current step
      for (let i = 1; i <= maxStep; i++) {
        const stepContent = document.getElementById(`step-content-${i}`);
        const stepIndicator = document.getElementById(`step-indicator-${i}`);
        if (stepContent) stepContent.style.display = i === currentStep ? "block" : "none";
        if (stepIndicator) {
          if (i === currentStep) {
            stepIndicator.className = "active";
            stepIndicator.style.background = "var(--brand)";
            stepIndicator.style.color = "white";
          } else if (i < currentStep) {
            stepIndicator.className = "completed";
            stepIndicator.style.background = "var(--brand-soft)";
            stepIndicator.style.color = "var(--brand)";
          } else {
            stepIndicator.className = "";
            stepIndicator.style.background = "#eaecf0";
            stepIndicator.style.color = "var(--muted)";
          }
        }
      }

      // Previews setup for Step 4
      if (currentStep === 4) {
        if (previews.user_intent) previews.user_intent.textContent = fields.user_intent.value || "未填寫";
        if (previews.host_organism) previews.host_organism.textContent = fields.host_organism.value || "未填寫";
        if (previews.compute_budget) previews.compute_budget.textContent = fields.compute_budget.value || "6";

        let modelText = fields.model_name.value ? `自定義模型: ${fields.model_name.value}` : "使用伺服器預設模型";
        if (fields.api_base.value) modelText += ` (${fields.api_base.value})`;
        if (previews.model_config) previews.model_config.textContent = modelText;

        const activeTools = [];
        if (fields.enable_rag.checked) activeTools.push("RAG 知識增強");
        if (fields.enable_ode.checked) activeTools.push("ODE 模擬");
        if (fields.enable_skill_extraction.checked) activeTools.push("技能提取");
        if (previews.tools) previews.tools.textContent = activeTools.join(", ") || "無";
      }

      // Buttons visibility
      if (btnPrev) btnPrev.style.display = currentStep > 1 ? "inline-block" : "none";
      if (btnNext) btnNext.style.display = currentStep < maxStep ? "inline-block" : "none";
      if (btnSubmit) btnSubmit.style.display = currentStep === maxStep ? "inline-block" : "none";

      if (currentStep === 2) {
        if (btnNext) btnNext.style.display = "none";
        loadElicitationState();
      }
    };

    const validateStep = (step) => {
      if (step === 1) {
        if (!fields.user_intent.value.trim()) {
          fields.user_intent.focus();
          return false;
        }
      }
      if (step === 2) {
        if (!fields.host_organism.value.trim()) {
          return false;
        }
      }
      return true;
    };

    // PM Elicitation state cache
    let elicitationLoaded = false;

    const escapeHtml = (str) => {
      if (typeof str !== "string") return str;
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };

    const loadElicitationState = async () => {
      const messagesContainer = document.getElementById("elicitation-chat-messages");
      const proposalContainer = document.getElementById("elicitation-proposal-card");
      if (!messagesContainer || !proposalContainer) return;

      if (!elicitationLoaded) {
        messagesContainer.innerHTML = `
          <div style="align-self: flex-start; max-width: 80%; background: #e9ecef; color: var(--text-dark); padding: 10px 14px; border-radius: 12px 12px 12px 0; margin-bottom: 8px;">
            🤖 PM Agent 正在分析設計意圖並生成規格提案，請稍候...
          </div>
        `;
        proposalContainer.innerHTML = `
          <div style="text-align: center; color: var(--muted); font-size: 13px; padding: 12px;">
            正在載入推薦設定...
          </div>
        `;
      }

      try {
        const response = await fetch("/api/v1/designs/drafts/elicitation/next", {
          method: "POST",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error("Failed to load elicitation state");
        const payload = await response.json();
        elicitationLoaded = true;
        renderElicitation(payload.data);
      } catch (err) {
        console.error("Failed to load elicitation:", err);
        messagesContainer.innerHTML += `
          <div style="align-self: flex-start; max-width: 80%; background: #fff5f5; color: var(--error); padding: 10px 14px; border-radius: 12px 12px 12px 0; margin-bottom: 8px;">
            ⚠️ 載入引導對話失敗，請檢查設定與網路連線。
          </div>
        `;
      }
    };

    const renderElicitation = (draft) => {
      const messagesContainer = document.getElementById("elicitation-chat-messages");
      const proposalContainer = document.getElementById("elicitation-proposal-card");
      const specsPreview = document.getElementById("elicitation-specs-preview");
      if (!messagesContainer || !proposalContainer || !specsPreview) return;

      // 1. Render Chat Messages
      const history = draft.pm_chat_history || [];
      if (history.length === 0) {
        messagesContainer.innerHTML = `
          <div style="align-self: flex-start; max-width: 80%; background: #e9ecef; color: var(--text-dark); padding: 10px 14px; border-radius: 12px 12px 12px 0; margin-bottom: 8px;">
            👋 您好！我是您的 PM 規格助理。我會協助您確認基因電路的各項關鍵規格。
          </div>
        `;
      } else {
        messagesContainer.innerHTML = history.map((msg) => {
          if (msg.role === "user") {
            return `
              <div style="align-self: flex-end; max-width: 80%; background: var(--brand); color: white; padding: 10px 14px; border-radius: 12px 12px 0 12px; margin-bottom: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                ${escapeHtml(msg.content)}
              </div>
            `;
          } else {
            return `
              <div style="align-self: flex-start; max-width: 80%; background: #e9ecef; color: var(--text-dark); padding: 10px 14px; border-radius: 12px 12px 12px 0; margin-bottom: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                ${escapeHtml(msg.content)}
              </div>
            `;
          }
        }).join("");
      }
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      // 2. Render Proposal Card
      const proposal = draft.pending_proposal;
      const pmStage = draft.pm_stage;

      if (pmStage === "completed" || !proposal || Object.keys(proposal).length === 0) {
        proposalContainer.innerHTML = `
          <div style="text-align: center; padding: 12px; color: var(--success); font-weight: 500;">
            🎉 PM 引導規格優化已完成！<br>
            <span style="font-size: 12.5px; font-weight: normal; color: var(--text-light); display: inline-block; margin-top: 4px;">請點擊下方「下一步」按鈕繼續設定進階選項。</span>
          </div>
        `;
        if (btnNext) btnNext.style.display = "inline-block";

        // Sync structured spec back to hidden form inputs
        if (draft.structured_spec) {
          if (draft.structured_spec.chassis) {
            fields.host_organism.value = draft.structured_spec.chassis;
          }
          if (draft.structured_spec.copy_number) {
            fields.compute_budget.value = draft.structured_spec.copy_number;
          }
        }
      } else {
        if (btnNext) btnNext.style.display = "none";

        proposalContainer.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: bold; color: var(--text-dark);">
              <span>💡</span> AI 推薦設定：${escapeHtml(proposal.missing_field)}
            </div>
            <div style="font-size: 13px; color: var(--text-light); line-height: 1.4;">
              ${escapeHtml(proposal.description || "")}
            </div>
            <div style="background: #f8fafc; border: 1px solid var(--line); border-radius: 6px; padding: 10px; font-size: 12.5px; font-family: monospace; word-break: break-all;">
              <strong>推薦值：</strong> ${escapeHtml(JSON.stringify(proposal.proposed_value))}
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;">
              <button type="button" class="button" id="elicitation-agree-btn" style="padding: 8px 12px; font-size: 12.5px; background: var(--brand); color: white; border: none; cursor: pointer;">👍 同意並繼續</button>
              <button type="button" class="button secondary" id="elicitation-custom-toggle-btn" style="padding: 8px 12px; font-size: 12.5px; cursor: pointer;">✏️ 自訂修改</button>
            </div>

            <!-- Custom Input Area -->
            <div id="elicitation-custom-area" style="display: none; flex-direction: column; gap: 8px; border-top: 1px solid var(--line); padding-top: 12px; margin-top: 6px;">
              <label style="font-size: 12.5px; color: var(--text-dark);">自訂值 (請輸入文字或 JSON):
                <input type="text" id="wizard-custom-input" style="width: 100%; font-size: 12.5px; padding: 6px 10px; margin-top: 4px;" value='${escapeHtml(typeof proposal.proposed_value === "string" ? proposal.proposed_value : JSON.stringify(proposal.proposed_value))}'>
              </label>
              <button type="button" class="button" id="elicitation-custom-apply-btn" style="width: 100%; padding: 8px; font-size: 12.5px; background: var(--brand); color: white; border: none; cursor: pointer;">確認套用</button>
            </div>
          </div>
        `;

        // Bind events
        document.getElementById("elicitation-agree-btn").addEventListener("click", () => {
          submitElicitationResponse("agree");
        });
        const toggleBtn = document.getElementById("elicitation-custom-toggle-btn");
        const customArea = document.getElementById("elicitation-custom-area");
        toggleBtn.addEventListener("click", () => {
          customArea.style.display = customArea.style.display === "none" ? "flex" : "none";
        });
        document.getElementById("elicitation-custom-apply-btn").addEventListener("click", () => {
          const val = document.getElementById("wizard-custom-input").value;
          submitElicitationResponse("override", val);
        });
      }

      // 3. Render Specs Preview
      const spec = draft.structured_spec || {};
      let specHtml = '<div style="display: flex; flex-direction: column; gap: 8px;">';
      specHtml += `<div><strong>宿主生物 (Chassis):</strong> <span class="badge" style="background:#ecfdf3; color:#027a48; font-weight:bold; font-size:11.5px; padding:2px 6px; border-radius:4px;">${escapeHtml(spec.chassis || '未填寫')}</span></div>`;

      if (spec.inputs && spec.inputs.length > 0) {
        const inputNames = spec.inputs.map(ip => `${ip.name}${ip.sensor_promoter ? ` (${ip.sensor_promoter})` : ''}`).join(', ');
        specHtml += `<div><strong>輸入信號 (Inputs):</strong> <span class="badge" style="background:#eff8ff; color:#175cd3; font-size:11.5px; padding:2px 6px; border-radius:4px;">${escapeHtml(inputNames)}</span></div>`;
      } else {
        specHtml += `<div><strong>輸入信號 (Inputs):</strong> <span class="muted">未填寫</span></div>`;
      }

      if (spec.outputs && spec.outputs.length > 0) {
        const outputNames = spec.outputs.map(op => op.name).join(', ');
        specHtml += `<div><strong>輸出基因 (Outputs):</strong> <span class="badge" style="background:#fffaf0; color:#b54708; font-size:11.5px; padding:2px 6px; border-radius:4px;">${escapeHtml(outputNames)}</span></div>`;
      } else {
        specHtml += `<div><strong>輸出基因 (Outputs):</strong> <span class="muted">未填寫</span></div>`;
      }

      specHtml += `<div><strong>邏輯關係 (Logic):</strong> <code>${escapeHtml(spec.logic_relation || '未填寫')}</code></div>`;
      specHtml += `<div><strong>質體拷貝數 (Copy):</strong> <code>${escapeHtml(spec.copy_number || '未填寫')}</code></div>`;
      specHtml += '</div>';
      specsPreview.innerHTML = specHtml;
    };

    const submitElicitationResponse = async (choice, value = null) => {
      const proposalContainer = document.getElementById("elicitation-proposal-card");
      if (proposalContainer) {
        proposalContainer.innerHTML = `
          <div style="text-align: center; color: var(--muted); font-size: 13px; padding: 12px;">
            PM Agent 正在評估規格設定，請稍候...
          </div>
        `;
      }

      try {
        const response = await fetch("/api/v1/designs/drafts/elicitation/propose", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ choice: choice, value: value }),
        });
        if (!response.ok) throw new Error("Failed to submit elicitation response");
        const payload = await response.json();
        renderElicitation(payload.data);
        triggerAutoSave();
      } catch (err) {
        console.error("Failed to submit response:", err);
        alert("設定提交失敗，請檢查設定後重試。");
      }
    };

    const skipElicitation = async () => {
      const proposalContainer = document.getElementById("elicitation-proposal-card");
      if (proposalContainer) {
        proposalContainer.innerHTML = `
          <div style="text-align: center; color: var(--muted); font-size: 13px; padding: 12px;">
            正在略過對話並套用預設值...
          </div>
        `;
      }

      try {
        const response = await fetch("/api/v1/designs/drafts/elicitation/skip", {
          method: "POST",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error("Failed to skip elicitation");
        const payload = await response.json();
        renderElicitation(payload.data);
        triggerAutoSave();
      } catch (err) {
        console.error("Failed to skip elicitation:", err);
        alert("略過引導對話失敗。");
      }
    };

    // Bind skip button
    const skipBtn = document.getElementById("elicitation-skip-btn");
    if (skipBtn) {
      skipBtn.addEventListener("click", skipElicitation);
    }

    // Wizard navigation
    if (btnNext) {
      btnNext.addEventListener("click", () => {
        if (validateStep(currentStep)) {
          currentStep++;
          updateWizardUI();
          triggerAutoSave();
        }
      });
    }

    if (btnPrev) {
      btnPrev.addEventListener("click", () => {
        if (currentStep > 1) {
          currentStep--;
          updateWizardUI();
          triggerAutoSave();
        }
      });
    }

    // Auto-save logic
    let saveTimeout = null;
    const triggerAutoSave = () => {
      if (saveTimeout) clearTimeout(saveTimeout);
      saveTimeout = setTimeout(saveDraft, 500); // 500ms debounce
    };

    const saveDraft = async () => {
      if (!autosaveIndicator) return;
      autosaveIndicator.textContent = "正在自動儲存草稿...";

      const payload = {
        current_step: currentStep,
        user_intent: fields.user_intent.value,
        host_organism: fields.host_organism.value,
        compute_budget: parseInt(fields.compute_budget.value) || 6,
        enable_rag: fields.enable_rag.checked,
        enable_ode: fields.enable_ode.checked,
        enable_skill_extraction: fields.enable_skill_extraction.checked,
        model_name: fields.model_name.value,
        api_base: fields.api_base.value,
      };

      try {
        const response = await fetch("/api/v1/designs/drafts", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error("Auto-save failed");

        const now = new Date();
        const timeString = now.toLocaleTimeString();
        autosaveIndicator.textContent = `草稿已自動儲存於 ${timeString}`;
      } catch (err) {
        autosaveIndicator.textContent = "草稿自動儲存失敗";
      }
    };

    // Bind inputs to auto-save
    Object.values(fields).forEach((el) => {
      if (!el) return;
      const eventType = el.tagName === "INPUT" && el.type !== "checkbox" ? "input" : "change";
      el.addEventListener(eventType, triggerAutoSave);
    });

    // Check for existing draft on load
    const checkActiveDraft = async () => {
      try {
        const response = await fetch("/api/v1/designs/drafts/active", {
          headers: { Accept: "application/json" },
        });
        if (!response.ok) return;
        const payload = await response.json();
        const draft = payload.data;

        if (draft && draft.user_intent) {
          if (recoveryBanner) {
            recoveryBanner.style.display = "flex";
            if (savedTimeSpan) {
              const date = new Date(draft.last_saved);
              savedTimeSpan.textContent = date.toLocaleString();
            }
          }

          // Restore action
          if (btnRestore) {
            btnRestore.onclick = () => {
              fields.user_intent.value = draft.user_intent || "";
              fields.host_organism.value = draft.host_organism || "Escherichia coli";
              fields.compute_budget.value = draft.compute_budget || 6;
              fields.enable_rag.checked = draft.enable_rag !== false;
              fields.enable_ode.checked = draft.enable_ode !== false;
              fields.enable_skill_extraction.checked = draft.enable_skill_extraction !== false;
              fields.model_name.value = draft.model_name || "";
              fields.api_base.value = draft.api_base || "";
              currentStep = draft.current_step || 1;

              recoveryBanner.style.display = "none";
              updateWizardUI();
              if (autosaveIndicator) autosaveIndicator.textContent = "草稿已恢復";
            };
          }

          // Discard action
          if (btnDiscard) {
            btnDiscard.onclick = async () => {
              if (confirm("您確定要捨棄此草稿並重新開始嗎？")) {
                await fetch("/api/v1/designs/drafts/active", { method: "DELETE" });
                recoveryBanner.style.display = "none";
                form.reset();
                currentStep = 1;
                updateWizardUI();
                if (autosaveIndicator) autosaveIndicator.textContent = "草稿已清空";
              }
            };
          }
        }
      } catch (err) {
        console.error("Failed to check active draft:", err);
      }
    };

    checkActiveDraft();
    updateWizardUI();
  };

  const setupClipboardCopy = () => {
    document.querySelectorAll("[data-copy-text]").forEach((button) => {
      button.addEventListener("click", async () => {
        const text = button.dataset.copyText;
        if (!text) return;
        try {
          await navigator.clipboard.writeText(text);
          const originalText = button.innerHTML;
          button.innerHTML = "✨ 已複製！";
          button.classList.add("success");
          setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove("success");
          }, 1500);
        } catch (err) {
          console.error("Failed to copy text:", err);
          alert("複製失敗，請手動選取複製");
        }
      });
    });
  };

  const setupRevisionTimeline = () => {
    const compareBtn = document.getElementById("btn-compare-revisions");
    if (!compareBtn) return;

    compareBtn.addEventListener("click", async () => {
      const baseRadio = document.querySelector(".diff-radio-base:checked");
      const compareRadio = document.querySelector(".diff-radio-compare:checked");

      if (!baseRadio || !compareRadio) {
        alert("請選擇基準版本 (Base) 與比對版本 (Compare)！");
        return;
      }

      const leftRev = baseRadio.value;
      const rightRev = compareRadio.value;

      const pathParts = window.location.pathname.split("/");
      const designId = pathParts[pathParts.length - 1];

      const placeholder = document.getElementById("diff-placeholder");
      const loading = document.getElementById("diff-loading");
      const content = document.getElementById("diff-content");

      placeholder.style.display = "none";
      loading.style.display = "flex";
      content.style.display = "none";

      try {
        const response = await fetch(`/api/v1/designs/${designId}/revisions/compare?left=${leftRev}&right=${rightRev}`);
        if (!response.ok) {
          throw new Error("Failed to fetch diff");
        }

        const res = await response.json();
        const diff = res.data;

        let html = "";

        if (diff.summary || diff.recommendation) {
          html += `
            <div style="background: #f8fafc; border: 1px solid var(--line); border-radius: 8px; padding: 14px; margin-bottom: 16px;">
              ${diff.summary ? `<p style="margin: 0 0 8px 0; font-size: 13.5px; line-height: 1.5;"><strong>變更摘要：</strong>${escapeHtml(diff.summary)}</p>` : ""}
              ${diff.recommendation ? `<p style="margin: 0; font-size: 13.5px; line-height: 1.5; color: var(--brand);"><strong>最佳化建議：</strong>${escapeHtml(diff.recommendation)}</p>` : ""}
            </div>
          `;
        }

        html += `<h3 style="font-size: 14px; margin: 18px 0 8px 0; border-bottom: 1px solid var(--line); padding-bottom: 6px;">🧬 零件變更 (Part Changes)</h3>`;
        if (diff.part_changes && diff.part_changes.length > 0) {
          html += `<div style="display:flex; flex-direction:column; gap:8px;">`;
          diff.part_changes.forEach(change => {
            let badgeColor = "#98a2b3";
            let bg = "#f2f4f7";
            let actionText = change.change_type;

            if (change.change_type === "added") {
              badgeColor = "#027a48";
              bg = "#ecfdf3";
              actionText = "新增零件";
            } else if (change.change_type === "removed") {
              badgeColor = "#b42318";
              bg = "#fef3f2";
              actionText = "移除零件";
            } else if (change.change_type === "modified") {
              badgeColor = "#b54708";
              bg = "#fffbeb";
              actionText = "修改零件";
            }

            html += `
              <div style="background: ${bg}; border: 1px solid ${badgeColor}40; border-radius: 6px; padding: 8px 12px; font-size: 13px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <span class="status-badge" style="background: ${badgeColor}20; color: ${badgeColor}; font-size: 11px; padding: 1px 6px; margin-right: 8px; font-weight:bold;">${escapeHtml(actionText)}</span>
                  <strong style="color: #101828;">${escapeHtml(change.part_id)}</strong>
                </div>
                <div class="muted" style="font-size: 11.5px;">
                  ${change.change_type === "modified" ? "序列或屬性已變更" : ""}
                </div>
              </div>
            `;
          });
          html += `</div>`;
        } else {
          html += `<p class="muted" style="font-size: 13px; margin: 0;">零件無任何異動。</p>`;
        }

        const hasValidation = diff.validation_changes && diff.validation_changes.length > 0;
        const hasMetrics = diff.metric_changes && diff.metric_changes.length > 0;

        if (hasValidation || hasMetrics) {
          html += `<h3 style="font-size: 14px; margin: 20px 0 8px 0; border-bottom: 1px solid var(--line); padding-bottom: 6px;">📈 指移與度量變更 (Metrics & Validation)</h3>`;
          html += `
            <table style="width:100%; border-collapse: collapse; font-size: 13px; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid var(--line); color: var(--muted);">
                  <th style="padding: 6px 4px;">指標項目</th>
                  <th style="padding: 6px 4px; text-align:right;">Rev ${escapeHtml(leftRev)} (Base)</th>
                  <th style="padding: 6px 4px; text-align:right;">Rev ${escapeHtml(rightRev)} (Compare)</th>
                </tr>
              </thead>
              <tbody>
          `;

          if (hasValidation) {
            diff.validation_changes.forEach(change => {
              html += `
                <tr style="border-bottom: 1px dashed var(--line);">
                  <td style="padding: 8px 4px; font-weight:500;">${escapeHtml(change.metric)}</td>
                  <td style="padding: 8px 4px; text-align:right;">${escapeHtml(change.left !== null ? change.left : "-")}</td>
                  <td style="padding: 8px 4px; text-align:right;">${escapeHtml(change.right !== null ? change.right : "-")}</td>
                </tr>
              `;
            });
          }

          if (hasMetrics) {
            diff.metric_changes.forEach(change => {
              const deltaText = change.delta !== null ? ` (${change.delta >= 0 ? "+" : ""}${change.delta.toFixed(2)})` : "";
              html += `
                <tr style="border-bottom: 1px dashed var(--line);">
                  <td style="padding: 8px 4px; font-weight:500;">${escapeHtml(change.metric)}</td>
                  <td style="padding: 8px 4px; text-align:right;">${escapeHtml(change.left !== null ? change.left : "-")}</td>
                  <td style="padding: 8px 4px; text-align:right;">${escapeHtml(change.left !== null && change.right !== null ? change.right + deltaText : (change.right !== null ? change.right : "-"))}</td>
                </tr>
              `;
            });
          }

          html += `
              </tbody>
            </table>
          `;
        }

        content.innerHTML = html;
        content.style.display = "block";

      } catch (err) {
        console.error("Failed to compare design revisions:", err);
        placeholder.innerHTML = `<span style="color:#b42318;">❌ 比對失敗：請確認所選版本有效並重試。</span>`;
        placeholder.style.display = "flex";
      } finally {
        loading.style.display = "none";
      }
    });
  };

  const setupNotifications = () => {
    const readAllBtn = document.getElementById("btn-read-all-notifs");
    const readBtns = document.querySelectorAll(".btn-mark-notif-read");
    const globalBadge = document.getElementById("global-unread-badge");
    const notifsSection = document.getElementById("notifications-section");

    const updateBadgeCount = (count) => {
      if (globalBadge) {
        if (count > 0) {
          globalBadge.textContent = count;
          globalBadge.style.display = "inline-block";
        } else {
          globalBadge.style.display = "none";
        }
      }
    };

    if (readAllBtn) {
      readAllBtn.addEventListener("click", async () => {
        try {
          const response = await fetch("/api/v1/notifications/read-all", {
            method: "POST",
            headers: { Accept: "application/json" },
          });
          if (response.ok) {
            if (notifsSection) {
              notifsSection.style.opacity = "0";
              setTimeout(() => {
                notifsSection.style.display = "none";
              }, 300);
            }
            updateBadgeCount(0);
          }
        } catch (err) {
          console.error("Failed to mark all as read:", err);
        }
      });
    }

    readBtns.forEach((btn) => {
      btn.addEventListener("click", async () => {
        const notifId = btn.dataset.notifId;
        if (!notifId) return;

        try {
          const response = await fetch(`/api/v1/notifications/${notifId}/read`, {
            method: "POST",
            headers: { Accept: "application/json" },
          });
          if (response.ok) {
            const item = document.querySelector(`.notice-item[data-notif-id="${notifId}"]`);
            if (item) {
              item.style.opacity = "0";
              item.style.transform = "translateX(20px)";
              setTimeout(() => {
                item.remove();
                const remaining = document.querySelectorAll(".notice-item");
                if (remaining.length === 0 && notifsSection) {
                  notifsSection.style.display = "none";
                }
                if (globalBadge) {
                  const current = parseInt(globalBadge.textContent) || 0;
                  updateBadgeCount(current - 1);
                }
              }, 300);
            }
          }
        } catch (err) {
          console.error("Failed to mark notification as read:", err);
        }
      });
    });
  };

  const setupViewModeToggle = () => {
    const toggle = document.getElementById("global-mode-toggle");
    if (!toggle) return;

    const isAdvanced = localStorage.getItem("view_mode") === "advanced";
    toggle.checked = isAdvanced;
    updateViewMode(isAdvanced);

    toggle.addEventListener("change", (e) => {
      const active = e.target.checked;
      localStorage.setItem("view_mode", active ? "advanced" : "general");
      updateViewMode(active);
    });

    function updateViewMode(active) {
      if (active) {
        document.body.classList.add("view-mode-advanced");
      } else {
        document.body.classList.remove("view-mode-advanced");
      }
    }
  };

  checkAIStatus();
  setupSettingsTest();
  setupDesignWizard();
  setupClipboardCopy();
  enhanceForms();
  setupNotifications();
  setupRevisionTimeline();
  setupViewModeToggle();
})();
