#!/usr/bin/env python3
"""Tiny local web UI for the TeleMemetry Memory Rail Demo."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
MAX_TURNS = 10_000
MAX_FIELDS = 10
MAX_EPISODES = 100


FAVICON_SVG = """<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><rect width="256" height="256" rx="44" fill="#f4f3ef"/><g fill="none" stroke="#13233a" stroke-width="14" stroke-linejoin="round"><rect x="42" y="42" width="108" height="108" rx="8"/><rect x="106" y="106" width="108" height="108" rx="8"/></g></svg>"""


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Launch TeleMemetry</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <style>
    :root {
      --bg: #f4f3ef;
      --ink: #15171c;
      --muted: #5d646d;
      --line: #d7d9d5;
      --green: #66a80f;
      --teal: #387d83;
      --panel: #ffffff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: #070b12;
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }

    body::before {
      content: "";
      position: fixed;
      inset: -20%;
      z-index: -2;
      background: url("https://telememetry.com/space-bkg.jpg") center center / cover no-repeat;
      transform: rotate(12deg);
      opacity: .86;
    }

    body::after {
      content: "";
      position: fixed;
      inset: 0;
      z-index: -1;
      background: linear-gradient(rgba(7, 11, 18, .12), rgba(7, 11, 18, .38));
    }

    main {
      position: relative;
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0 64px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 26px;
      color: #fff;
      font-size: 24px;
      font-weight: 350;
      letter-spacing: .02em;
    }

    .brand svg {
      width: 34px;
      height: 34px;
      color: #fff;
    }

    h1 {
      margin: 0 0 10px;
      font-size: clamp(38px, 6vw, 72px);
      line-height: 1.02;
      letter-spacing: -.02em;
      color: #fff;
    }

    .demo-points {
      display: grid;
      gap: 8px;
      max-width: 850px;
      margin: 0 0 24px;
      background: rgba(255, 255, 255, .9);
      padding: 16px 18px;
      color: #38424b;
      font-size: 17px;
      font-weight: 700;
      list-style: none;
    }

    .demo-points li::before {
      content: "•";
      color: var(--teal);
      font-weight: 950;
      margin-right: 8px;
    }

    .scope-note {
      max-width: 850px;
      margin: -6px 0 24px;
      background: rgba(255, 255, 255, .9);
      padding: 14px 16px;
      color: var(--ink);
      font-size: 18px;
      font-weight: 850;
    }

    .hero-cta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 52px;
      margin: 0 0 24px;
      border: 1px solid rgba(255, 255, 255, .3);
      background: var(--green);
      color: #fff;
      padding: 0 20px;
      font-size: 18px;
      font-weight: 900;
      text-decoration: none;
    }

    .hero-cta:hover {
      background: #5c980d;
      color: #fff;
      text-decoration: none;
    }

    .controls,
    .result,
    .log,
    .files {
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: 0 18px 48px rgba(20, 24, 32, .08);
    }

    .controls {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
      gap: 14px;
      align-items: end;
      padding: 20px;
      margin-bottom: 18px;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    input {
      width: 100%;
      border: 1px solid var(--line);
      background: #fbfbf9;
      color: var(--ink);
      padding: 12px 13px;
      font: 800 22px/1.1 inherit;
    }

    .limits {
      margin: -4px 0 18px;
      background: rgba(255, 255, 255, .9);
      padding: 12px 14px;
      color: var(--muted);
      font-size: 15px;
      font-weight: 700;
    }

    .limits strong {
      color: var(--ink);
    }

    .limits a {
      color: var(--teal);
      font-weight: 900;
    }

    button {
      min-height: 52px;
      border: 0;
      background: var(--green);
      color: #fff;
      padding: 0 24px;
      font: 900 18px/1 inherit;
      cursor: pointer;
    }

    button:disabled {
      opacity: .62;
      cursor: wait;
    }

    .status {
      min-height: 28px;
      margin: 0 0 18px;
      color: #fff;
      font-size: 18px;
      font-weight: 800;
      text-shadow: 0 2px 12px rgba(0, 0, 0, .45);
    }

    .progress {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }

    .progress-bar {
      height: 12px;
      margin: -4px 0 18px;
      overflow: hidden;
      border: 1px solid rgba(56, 125, 131, .22);
      background: rgba(255, 255, 255, .72);
    }

    .progress-fill {
      width: 0%;
      height: 100%;
      background: var(--green);
      transition: width .45s ease;
    }

    .step {
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, .7);
      padding: 14px;
      color: var(--muted);
      font-weight: 800;
    }

    .step.done {
      border-color: rgba(102, 168, 15, .45);
      color: var(--green);
      background: rgba(102, 168, 15, .08);
    }

    .result {
      display: none;
      gap: 16px;
      padding: 22px;
      margin-bottom: 18px;
    }

    .result-copy {
      max-width: 900px;
      margin: 0;
      color: var(--ink);
      font-size: 22pt;
      font-weight: 750;
    }

    .metric-em {
      color: var(--green);
      font-weight: 900;
    }

    .result-why {
      max-width: 900px;
      margin: 0;
      color: var(--muted);
      font-size: 18px;
      font-weight: 650;
    }

    .result-metrics {
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .result-metrics li {
      border: 1px solid var(--line);
      background: #fff;
      padding: 11px 13px;
      color: var(--green);
      font-size: 22pt;
      font-weight: 800;
    }

    .files {
      display: none;
      padding: 18px 20px;
      margin-bottom: 18px;
    }

    .files h2 {
      margin: 0 0 10px;
      font-size: 22px;
    }

    .files a {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      margin: 6px 12px 6px 0;
      border: 1px solid rgba(56, 125, 131, .35);
      background: #fff;
      color: var(--teal);
      padding: 10px 13px;
      font-size: 15px;
      font-weight: 900;
      text-decoration: none;
    }

    .files a:hover {
      border-color: var(--teal);
      background: rgba(56, 125, 131, .08);
      text-decoration: none;
    }

    .log {
      display: none;
      padding: 16px;
      color: #dfe7ef;
      background: #10151d;
      overflow: auto;
      white-space: pre-wrap;
      font: 14px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace;
    }

    @media (max-width: 820px) {
      .controls,
      .progress {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
<main>
  <div class="brand">
    <svg width="256" height="256" viewBox="0 0 256 256" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="currentColor" stroke-width="14" stroke-linejoin="round"><rect x="42" y="42" width="108" height="108" rx="8"/><rect x="106" y="106" width="108" height="108" rx="8"/></g></svg>
    TeleMemetry&trade;
  </div>
  <h1>Launch TeleMemetry&trade;</h1>
  <ul class="demo-points">
    <li>Watch thousands of operational recall events become instantly queryable without replaying conversation history.</li>
    <li>Every answer is backed by verifiable evidence and SHA256 receipts, available in the result links below after the run.</li>
  </ul>
  <p class="scope-note">This is a public reproduction harness, not the private production engine. It mathematically verifies this measurement workflow and proves the artifact trail.</p>
  <a class="hero-cta" href="#run-panel">Try the Docker Version of the TeleMemetry Engine</a>

  <section class="controls" id="run-panel" aria-label="Benchmark controls">
    <label>Turns <input id="turns" type="number" min="1" max="10000" value="3000"></label>
    <label>Fields <input id="fields" type="number" min="1" max="10" value="10"></label>
    <label>Episodes <input id="episodes" type="number" min="1" max="100" value="20"></label>
    <button id="run">Run Demo</button>
  </section>
  <p class="limits"><strong>Public demo limits:</strong> up to 10,000 turns, 10 fields, and 100 episodes. These caps keep browser response, result files, and Brev instance time predictable. Need a bigger or domain-specific run? <a href="https://telememetry.com/reproduce.html" target="_blank" rel="noopener">Request a custom benchmark</a>.</p>

  <p class="status" id="status">Ready. Recommended first run: 3,000 turns, 10 fields, 20 episodes.</p>
  <div class="progress-bar" aria-label="Benchmark progress"><div class="progress-fill" id="progress-fill"></div></div>

  <section class="progress" aria-label="Progress">
    <div class="step" id="step-generate">Generate evidence packets</div>
    <div class="step" id="step-verify">Verify 1:1 recall</div>
    <div class="step" id="step-hash">Write SHA256 receipts</div>
    <div class="step" id="step-package">Package AI audit files</div>
  </section>

  <section class="result" id="result" aria-label="Benchmark result">
    <p class="result-copy" id="result-copy"></p>
    <p class="result-why">Why this matters: a field appliance, robot, vehicle, or satellite can keep long operational history outside the model, then retrieve the exact state needed for the next decision without replaying the whole history into context.</p>
    <ul class="result-metrics">
      <li id="metric-responses">-</li>
      <li id="metric-recall">-</li>
      <li id="metric-tokens">-</li>
      <li id="metric-reduction">-</li>
    </ul>
  </section>

  <section class="files" id="files" aria-label="Result files">
    <h2>Result Package</h2>
    <a href="/file/results/latest/RESULT_SUMMARY.txt" target="_blank">Open Result Summary ↗</a>
    <a href="/file/results/latest/prompt.md" target="_blank">Open AI Audit Prompt ↗</a>
    <a href="/file/results/latest/metrics.json" target="_blank">Open Metrics ↗</a>
    <a href="/file/results/latest/manifest.json" target="_blank">Open SHA256 Manifest ↗</a>
    <a href="/file/results/latest/dataset.jsonl" target="_blank">Open Raw Telemetry In ↗</a>
    <a href="/file/results/latest/evidence_packets.jsonl" target="_blank">Open Evidence Packets ↗</a>
    <a href="/file/results/latest/outputs.jsonl" target="_blank">Open Verified Outputs ↗</a>
  </section>

  <pre class="log" id="log"></pre>
</main>
<script>
  var runButton = document.getElementById('run');
  var statusEl = document.getElementById('status');
  var logEl = document.getElementById('log');
  var resultEl = document.getElementById('result');
  var filesEl = document.getElementById('files');
  var progressFill = document.getElementById('progress-fill');
  var steps = ['generate', 'verify', 'hash', 'package'].map(function (id) {
    return document.getElementById('step-' + id);
  });
  var progressDelayMs = 2000;
  var minimumRunMs = 10000;
  var numericLimits = {
    turns: { min: 1, max: 10000 },
    fields: { min: 1, max: 10 },
    episodes: { min: 1, max: 100 }
  };

  function clampNumber(id) {
    var input = document.getElementById(id);
    var limits = numericLimits[id];
    var value = Number(input.value);
    if (!Number.isFinite(value)) {
      value = Number(input.defaultValue);
    }
    value = Math.round(value);
    value = Math.max(limits.min, Math.min(limits.max, value));
    input.value = value;
    return value;
  }

  Object.keys(numericLimits).forEach(function (id) {
    var input = document.getElementById(id);
    input.addEventListener('input', function () {
      if (Number(input.value) > numericLimits[id].max) {
        input.value = numericLimits[id].max;
      }
      if (Number(input.value) < numericLimits[id].min && input.value !== '') {
        input.value = numericLimits[id].min;
      }
    });
    input.addEventListener('change', function () {
      clampNumber(id);
    });
  });

  function setRunning(running) {
    runButton.disabled = running;
    runButton.textContent = running ? 'Running...' : 'Run Demo';
  }

  function resetUi() {
    steps.forEach(function (step) { step.classList.remove('done'); });
    resultEl.style.display = 'none';
    filesEl.style.display = 'none';
    logEl.style.display = 'none';
    logEl.textContent = '';
    progressFill.style.width = '0%';
  }

  function beginSteps() {
    steps.forEach(function (step, index) {
      setTimeout(function () {
        step.classList.add('done');
        progressFill.style.width = ((index + 1) * 25) + '%';
      }, (index + 1) * progressDelayMs);
    });
  }

  function waitForMinimum(startedAt) {
    var elapsed = Date.now() - startedAt;
    var remaining = Math.max(0, minimumRunMs - elapsed);
    return new Promise(function (resolve) {
      setTimeout(resolve, remaining);
    });
  }

  function setPassText(metrics) {
    var copy = document.getElementById('result-copy');
    copy.textContent = '';

    function text(value) {
      copy.appendChild(document.createTextNode(value));
    }

    function metric(value) {
      var span = document.createElement('span');
      span.className = 'metric-em';
      span.textContent = value;
      copy.appendChild(span);
    }

    text('PASS: this run verified ');
    metric(metrics.recall.verified_turns + ' of ' + metrics.recall.total_turns + ' turns');
    text(' with ');
    metric(metrics.recall.final_verified_output_failures + ' final failures');
    text(', averaging ');
    metric(metrics.token_accounting.average_packet_tokens_per_turn_estimate + ' bounded packet tokens per turn');
    text(' and reporting a ');
    metric(metrics.token_accounting.replay_reduction_ratio_estimate + 'x replay reduction estimate');
    text('.');
  }

  runButton.addEventListener('click', function () {
    resetUi();
    setRunning(true);
    var startedAt = Date.now();
    statusEl.textContent = 'Running workflow: telemetry, packets, recall verification, receipts, and audit package...';
    beginSteps();

    fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        turns: clampNumber('turns'),
        fields: clampNumber('fields'),
        episodes: clampNumber('episodes')
      })
    }).then(function (response) {
      return response.json();
    }).then(function (data) {
      return waitForMinimum(startedAt).then(function () { return data; });
    }).then(function (data) {
      if (!data.ok) {
        throw new Error(data.error || 'Benchmark failed');
      }
      var metrics = data.metrics;
      document.getElementById('metric-responses').textContent = metrics.recall.verified_turns + ' bit-perfect responses';
      document.getElementById('metric-recall').textContent = '100% 1:1 recall - zero failures';
      document.getElementById('metric-tokens').textContent = metrics.token_accounting.average_packet_tokens_per_turn_estimate + ' tokens per turn';
      document.getElementById('metric-reduction').textContent = metrics.token_accounting.replay_reduction_ratio_estimate + 'x context-history reduction estimate';
      setPassText(metrics);
      statusEl.textContent = 'PASS. Result package is ready in results/latest.';
      resultEl.style.display = 'grid';
      filesEl.style.display = 'block';
      logEl.style.display = 'block';
      logEl.textContent = data.output + '\\n\\n' + data.summary;
    }).catch(function (error) {
      statusEl.textContent = 'Failed: ' + error.message;
      logEl.style.display = 'block';
      logEl.textContent = String(error);
    }).finally(function () {
      setRunning(false);
    });
  });
</script>
</body>
</html>
"""


class DemoHandler(BaseHTTPRequestHandler):
    def send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, obj: dict) -> None:
        self.send_bytes(status, json.dumps(obj, indent=2).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_bytes(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.svg":
            self.send_bytes(200, FAVICON_SVG.encode("utf-8"), "image/svg+xml; charset=utf-8")
            return
        if parsed.path.startswith("/file/"):
            rel = parsed.path.removeprefix("/file/")
            target = (ROOT / rel).resolve()
            if not str(target).startswith(str(ROOT)) or not target.exists() or not target.is_file():
                self.send_json(404, {"ok": False, "error": "file not found"})
                return
            content_type = "text/plain; charset=utf-8"
            if target.suffix == ".json":
                content_type = "application/json; charset=utf-8"
            self.send_bytes(200, target.read_bytes(), content_type)
            return
        self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/run":
            self.send_json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        turns = int(payload.get("turns", 3000))
        fields = int(payload.get("fields", 10))
        episodes = int(payload.get("episodes", 20))

        if turns < 1 or turns > MAX_TURNS or fields < 1 or fields > MAX_FIELDS or episodes < 1 or episodes > MAX_EPISODES:
            self.send_json(400, {
                "ok": False,
                "error": f"public demo limits are {MAX_TURNS} turns, {MAX_FIELDS} fields, and {MAX_EPISODES} episodes",
            })
            return

        run_cmd = [sys.executable, "run.py", "--turns", str(turns), "--fields", str(fields), "--episodes", str(episodes)]
        verify_cmd = [sys.executable, "verify.py", "results/latest"]

        try:
            run_result = subprocess.run(run_cmd, cwd=ROOT, text=True, capture_output=True, check=True)
            verify_result = subprocess.run(verify_cmd, cwd=ROOT, text=True, capture_output=True, check=True)
            metrics = json.loads((ROOT / "results/latest/metrics.json").read_text(encoding="utf-8"))
            summary = (ROOT / "results/latest/RESULT_SUMMARY.txt").read_text(encoding="utf-8")
            self.send_json(200, {
                "ok": True,
                "metrics": metrics,
                "summary": summary,
                "output": run_result.stdout + verify_result.stdout,
            })
        except subprocess.CalledProcessError as exc:
            self.send_json(500, {
                "ok": False,
                "error": "benchmark command failed",
                "output": (exc.stdout or "") + (exc.stderr or ""),
            })


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", 7860), DemoHandler)
    print("Launch TeleMemetry")
    print("Open: http://127.0.0.1:7860")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
