"use strict";

(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // Times arrive already in the host's display timezone, do not convert them here

  const refresh = Number(document.body.dataset.refresh || 0);
  if (refresh > 0) {
    setInterval(() => {
      if (document.visibilityState === "visible" && !$("main details[open]")) location.reload();
    }, refresh * 1000);
  }

  async function call(url, options = {}) {
    const headers = { Accept: "application/json" };
    if (options.body) headers["Content-Type"] = "application/json";
    const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
    if (response.status === 401) {
      location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
      throw new Error("signed out");
    }
    let body = null;
    try {
      body = await response.json();
    } catch (_) {
      /* not JSON */
    }
    if (!response.ok) throw new Error(body && body.message ? body.message : `HTTP ${response.status}`);
    return body;
  }

  // Poll a run until it is no longer started, `onTick` sees every record
  async function follow(url, onTick) {
    let failures = 0;
    for (;;) {
      await sleep(1500);
      try {
        const run = await call(url);
        failures = 0;
        onTick(run);
        if (run.status !== "started") return run;
      } catch (error) {
        if (++failures >= 5) throw error;
      }
    }
  }

  // ---- Run a dataset ----
  const panel = $(".run-panel");
  if (panel) {
    const button = $("#run-button");
    const status = $("#run-status");
    const params = $("#run-params");
    const say = (text, cls) => {
      status.textContent = text;
      status.className = "small " + (cls || "");
    };

    button.addEventListener("click", async () => {
      const body = {};
      const text = params.value.trim();
      if (text) {
        try {
          body.params = JSON.parse(text);
        } catch (_) {
          say("params is not valid JSON", "err");
          return;
        }
      }
      if (!confirm(`Run ${button.dataset.name} now?`)) return;

      button.disabled = true;
      try {
        const run = await call(panel.dataset.runUrl, { method: "POST", body: JSON.stringify(body) });
        say(`started ${run.id}`, "warn");
        const done = await follow(`${panel.dataset.runUrl}/${encodeURIComponent(run.id)}`, (r) =>
          say(`${r.id} · ${r.status}`, "warn"),
        );
        if (done.status === "completed") say(`${done.id} completed · ${done.height} × ${done.width}`);
        else say(`${done.id} failed: ${done.error || "unknown error"}`, "err");
        setTimeout(() => location.reload(), 1500);
      } catch (error) {
        say(error.message, "err");
      } finally {
        button.disabled = false;
      }
    });
  }

  // Runs still going when the page loaded
  document.querySelectorAll("tr[data-poll]").forEach((row) => {
    follow(row.dataset.poll, () => {})
      .then(() => location.reload())
      .catch(() => {});
  });

  // ---- Logs of a source, read when opened ----
  document.querySelectorAll("details.logs").forEach((details) => {
    details.addEventListener("toggle", async () => {
      if (!details.open || details.dataset.loaded) return;
      details.dataset.loaded = "1";
      const term = $(".term", details);
      term.textContent = "loading…";
      try {
        const events = await call(details.dataset.url);
        term.textContent = "";
        // The node answers newest first, a terminal reads oldest first
        events.reverse().forEach((event) => {
          const line = document.createElement("span");
          line.className = "lv-" + event.level;
          const ts = document.createElement("span");
          ts.className = "ts";
          ts.textContent = String(event.created_at || "").replace("T", " ") + " ";
          line.append(ts, `${String(event.level).padEnd(7)} ${event.msg}`);
          const meta = event.metadata && Object.keys(event.metadata).length ? " " + JSON.stringify(event.metadata) : "";
          line.append(meta, "\n");
          term.append(line);
        });
        if (!events.length) term.textContent = "no log events\n";
        term.scrollTop = term.scrollHeight;
      } catch (error) {
        term.textContent = error.message;
        details.dataset.loaded = "";
      }
    });
  });

  // ---- Machine charts: a cursor and the readings under it ----
  const machineData = $("#machine-data");
  if (machineData) {
    const data = JSON.parse(machineData.textContent);
    const nearest = (x) => {
      let lo = 0;
      let hi = data.t.length - 1;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (data.t[mid] < x) lo = mid + 1;
        else hi = mid;
      }
      return lo > 0 && x - data.t[lo - 1] < data.t[lo] - x ? lo - 1 : lo;
    };

    document.querySelectorAll(".plot").forEach((plot) => {
      const chart = data.charts[plot.dataset.chart];
      const cursor = $(".cursor", plot);
      const tip = $(".tip", plot);
      if (!chart) return;

      plot.addEventListener("mousemove", (event) => {
        const box = plot.getBoundingClientRect();
        const x = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1);
        const i = nearest(x);
        cursor.hidden = false;
        cursor.style.left = data.t[i] * 100 + "%";

        const head = document.createElement("div");
        head.className = "t";
        head.textContent = data.labels[i];
        const rows = chart.series.map((s) => {
          const row = document.createElement("div");
          row.className = s.cls;
          const v = s.values[i];
          row.textContent = `${s.label} ${v === null ? "-" : v} ${chart.unit}`;
          return row;
        });
        tip.replaceChildren(head, ...rows);
        tip.hidden = false;
        // The tip flips to the left of the cursor near the right edge
        if (data.t[i] > 0.6) {
          tip.style.left = "auto";
          tip.style.right = (1 - data.t[i]) * 100 + "%";
        } else {
          tip.style.right = "auto";
          tip.style.left = data.t[i] * 100 + "%";
        }
      });
      plot.addEventListener("mouseleave", () => {
        cursor.hidden = true;
        tip.hidden = true;
      });
    });
  }

  // ---- Query ----
  const form = $("#query-form");
  if (form) {
    const sql = $("#sql");
    const meta = $("#query-meta");
    const error = $("#query-error");
    const out = $("#query-result");
    const run = $("#query-run");
    const MAX_ROWS_SHOWN = 2000;

    const cell = (value) => {
      const td = document.createElement("td");
      if (value === null || value === undefined) {
        td.className = "null";
        td.textContent = "NULL";
      } else {
        td.textContent = typeof value === "object" ? JSON.stringify(value) : String(value);
      }
      return td;
    };

    const render = (result) => {
      const table = document.createElement("table");
      const head = table.createTHead().insertRow();
      result.columns.forEach((name, i) => {
        const th = document.createElement("th");
        th.append(name);
        const type = document.createElement("small");
        type.textContent = result.types[i] || "";
        th.append(type);
        head.append(th);
      });
      const body = table.createTBody();
      result.rows.slice(0, MAX_ROWS_SHOWN).forEach((row) => {
        const tr = body.insertRow();
        row.forEach((value) => tr.append(cell(value)));
      });
      out.replaceChildren(table);
    };

    const submit = async () => {
      const text = sql.value.trim();
      if (!text) return;
      run.disabled = true;
      error.textContent = "";
      meta.textContent = "running…";
      try {
        const result = await call(form.dataset.url, { method: "POST", body: JSON.stringify({ sql: text }) });
        render(result);
        const parts = [`${result.rows.length} rows`, `${Math.round(result.elapsed_ms)} ms`];
        if (result.truncated) parts.push(`cut by ${result.truncated_by} cap`);
        if (result.rows.length > MAX_ROWS_SHOWN) parts.push(`showing first ${MAX_ROWS_SHOWN}`);
        meta.textContent = parts.join(" · ");
      } catch (e) {
        out.replaceChildren();
        meta.textContent = "";
        error.textContent = e.message;
      } finally {
        run.disabled = false;
      }
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submit();
    });
    sql.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        submit();
      }
    });
    document.querySelectorAll(".table-pick").forEach((button) =>
      button.addEventListener("click", () => {
        sql.value = `SELECT * FROM ${button.dataset.table} LIMIT 100`;
        sql.focus();
      }),
    );

    const filter = $("#table-filter");
    filter.addEventListener("input", () => {
      const needle = filter.value.trim().toLowerCase();
      document.querySelectorAll("[data-group]").forEach((group) => {
        let shown = 0;
        group.querySelectorAll(".table-pick").forEach((button) => {
          const hit = !needle || button.dataset.table.toLowerCase().includes(needle);
          button.hidden = !hit;
          if (hit) shown++;
        });
        group.hidden = shown === 0;
      });
    });
  }
})();
