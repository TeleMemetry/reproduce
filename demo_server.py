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


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleMemetry Memory Rail Demo</title>
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
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }

    main {
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0 64px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 26px;
      color: #32363d;
      font-size: 24px;
      font-weight: 350;
      letter-spacing: .02em;
    }

    .brand svg {
      width: 34px;
      height: 34px;
      color: #13233a;
    }

    h1 {
      margin: 0 0 10px;
      font-size: clamp(38px, 6vw, 72px);
      line-height: 1.02;
      letter-spacing: -.02em;
    }

    .lede {
      max-width: 850px;
      margin: 0 0 28px;
      color: var(--muted);
      font-size: 23px;
      font-weight: 600;
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
      color: var(--teal);
      font-size: 18px;
      font-weight: 800;
    }

    .progress {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 18px;
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
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 18px;
    }

    .metric {
      min-height: 126px;
      padding: 22px;
      border-right: 1px solid var(--line);
    }

    .metric:last-child { border-right: 0; }

    .value {
      display: block;
      color: var(--green);
      font-size: clamp(30px, 4vw, 48px);
      font-weight: 950;
      line-height: 1;
      margin-bottom: 9px;
    }

    .label {
      display: block;
      color: var(--ink);
      font-size: 18px;
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
      margin: 6px 12px 6px 0;
      color: var(--teal);
      font-weight: 850;
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
      .progress,
      .result {
        grid-template-columns: 1fr;
      }

      .metric {
        border-right: 0;
        border-bottom: 1px solid var(--line);
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
  <h1>Memory Rail Demo</h1>
  <p class="lede">Run a public verified-recall benchmark, generate bounded evidence packets, write SHA256 receipts, and produce an AI-auditable result package.</p>

  <section class="controls" aria-label="Benchmark controls">
    <label>Turns <input id="turns" type="number" min="1" max="100000" value="3000"></label>
    <label>Fields <input id="fields" type="number" min="1" max="10" value="10"></label>
    <label>Episodes <input id="episodes" type="number" min="1" max="1000" value="20"></label>
    <button id="run">Run Demo</button>
  </section>

  <p class="status" id="status">Ready. Recommended first run: 3,000 turns, 10 fields, 20 episodes.</p>

  <section class="progress" aria-label="Progress">
    <div class="step" id="step-generate">Generate evidence packets</div>
    <div class="step" id="step-verify">Verify 1:1 recall</div>
    <div class="step" id="step-hash">Write SHA256 receipts</div>
    <div class="step" id="step-package">Package AI audit files</div>
  </section>

  <section class="result" id="result" aria-label="Benchmark result">
    <div class="metric"><span class="value" id="verified">-</span><span class="label">Verified Recall</span></div>
    <div class="metric"><span class="value" id="failures">-</span><span class="label">Final Failures</span></div>
    <div class="metric"><span class="value" id="tokens">-</span><span class="label">Tokens / Turn</span></div>
    <div class="metric"><span class="value" id="reduction">-</span><span class="label">Replay Reduction</span></div>
  </section>

  <section class="files" id="files" aria-label="Result files">
    <h2>Result Package</h2>
    <a href="/file/results/latest/RESULT_SUMMARY.txt" target="_blank">Open Result Summary</a>
    <a href="/file/results/latest/prompt.md" target="_blank">Open AI Audit Prompt</a>
    <a href="/file/results/latest/metrics.json" target="_blank">Open Metrics</a>
    <a href="/file/results/latest/manifest.json" target="_blank">Open SHA256 Manifest</a>
  </section>

  <pre class="log" id="log"></pre>
</main>
<script>
  var runButton = document.getElementById('run');
  var statusEl = document.getElementById('status');
  var logEl = document.getElementById('log');
  var resultEl = document.getElementById('result');
  var filesEl = document.getElementById('files');
  var steps = ['generate', 'verify', 'hash', 'package'].map(function (id) {
    return document.getElementById('step-' + id);
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
  }

  function completeSteps() {
    steps.forEach(function (step, index) {
      setTimeout(function () { step.classList.add('done'); }, index * 260);
    });
  }

  runButton.addEventListener('click', function () {
    resetUi();
    setRunning(true);
    statusEl.textContent = 'Running benchmark and verification...';
    completeSteps();

    fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        turns: Number(document.getElementById('turns').value),
        fields: Number(document.getElementById('fields').value),
        episodes: Number(document.getElementById('episodes').value)
      })
    }).then(function (response) {
      return response.json();
    }).then(function (data) {
      if (!data.ok) {
        throw new Error(data.error || 'Benchmark failed');
      }
      var metrics = data.metrics;
      document.getElementById('verified').textContent = metrics.recall.verified_turns + ' / ' + metrics.recall.total_turns;
      document.getElementById('failures').textContent = metrics.recall.final_verified_output_failures;
      document.getElementById('tokens').textContent = metrics.token_accounting.average_packet_tokens_per_turn_estimate;
      document.getElementById('reduction').textContent = metrics.token_accounting.replay_reduction_ratio_estimate + 'x';
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

        if turns < 1 or fields < 1 or fields > 10 or episodes < 1:
            self.send_json(400, {"ok": False, "error": "invalid benchmark parameters"})
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
    print("TeleMemetry Memory Rail Demo")
    print("Open: http://127.0.0.1:7860")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
