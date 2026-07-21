#!/usr/bin/env python3
"""Tiny local web UI for the TeleMemetry Memory Rail Demo."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import zipfile
from io import BytesIO
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
  <title>TeleMemetry Launchable on NVIDIA Brev</title>
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
      background: #f7f6f2;
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }

    body::before {
      content: none;
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
      background:
        radial-gradient(circle at 72% 12%, rgba(140, 193, 193, .34), transparent 24%),
        radial-gradient(circle at 56% 52%, rgba(140, 193, 193, .20), transparent 28%),
        linear-gradient(90deg, rgba(247, 246, 242, 1), rgba(247, 246, 242, .88));
    }

    main {
      position: relative;
      width: min(940px, calc(100% - 32px));
      margin: 0 auto;
      padding: 42px 0 64px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 26px;
      color: #3d4652;
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
      margin: 0 0 8px;
      font-size: clamp(44px, 5.2vw, 64px);
      line-height: .98;
      letter-spacing: -.02em;
      color: var(--ink);
    }

    .demo-points {
      display: grid;
      gap: 8px;
      max-width: 850px;
      margin: 0 0 24px;
      background: rgba(255, 255, 255, .9);
      padding: 16px 18px;
      color: #173046;
      font-size: 17px;
      font-weight: 700;
      list-style: none;
    }

    .hero-subhead {
      display: none;
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
      display: none;
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
      font: 800 14px/1.1 inherit;
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
      color: var(--teal);
      font-size: 18px;
      font-weight: 800;
      text-shadow: none;
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
      background: rgba(255, 255, 255, .62);
      padding: 14px;
      color: var(--muted);
      font-weight: 800;
      cursor: default;
    }

    .step::before {
      content: "";
      display: inline-block;
      width: 9px;
      height: 9px;
      margin-right: 9px;
      border: 2px solid currentColor;
      border-radius: 999px;
      vertical-align: 1px;
    }

    .step.done {
      border-color: rgba(102, 168, 15, .45);
      color: var(--green);
      background: rgba(102, 168, 15, .08);
    }

    .step.done::before {
      background: currentColor;
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
      color: var(--green);
      font-size: 29px;
      line-height: 1.35;
      font-weight: 900;
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
      font-weight: 800;
    }

    .result-metrics {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .result-metrics li {
      border: 1px solid var(--line);
      background: #fff;
      min-height: 92px;
      padding: 14px 15px;
      color: var(--green);
      font-size: 27px;
      line-height: 1.12;
      font-weight: 900;
      display: flex;
      align-items: center;
    }

    .claim-boundaries {
      display: none;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .claim-box {
      border: 1px solid var(--line);
      background: #fff;
      padding: 14px 16px;
    }

    .claim-box h3 {
      margin: 0 0 8px;
      color: var(--ink);
      font-size: 17px;
    }

    .claim-box ul {
      margin: 0;
      padding-left: 19px;
      color: var(--muted);
      font-weight: 700;
    }

    .claim-box li {
      margin: 4px 0;
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

    /* Benchmark Library visual language */
    :root {
      --border: rgba(184, 184, 184, .5);
      --border-teal: rgba(140, 193, 193, .65);
      --body-c: rgb(109, 110, 112);
      --name-c: rgb(28, 30, 35);
      --teal: rgb(140, 193, 193);
      --teal-dark: rgb(100, 155, 155);
      --orange: #f47d21;
      --green: #76b900;
      --font: "Segoe UI", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    }

    body {
      background: #080c14;
      color: #fff;
      font-family: var(--font);
    }

    body::before {
      content: "";
      position: fixed;
      inset: -50%;
      width: 200%;
      height: 200%;
      background: url("https://telememetry.com/space-bkg.jpg") center center / cover no-repeat;
      transform: rotate(22deg);
      transform-origin: center center;
      z-index: -2;
      pointer-events: none;
      opacity: .92;
    }

    body::after {
      content: "";
      position: fixed;
      inset: 0;
      background:
        linear-gradient(rgba(7, 11, 18, .16), rgba(7, 11, 18, .16)),
        radial-gradient(ellipse at 60% 30%, transparent 40%, rgba(10, 12, 20, .35) 100%);
      z-index: -1;
      pointer-events: none;
    }

    main {
      max-width: 80%;
      width: auto;
      padding: 36px 0 64px;
    }

    .brand {
      justify-content: center;
      margin-bottom: 18px;
      color: rgba(255, 255, 255, .88);
      font-size: 18pt;
      font-family: var(--font);
      font-weight: 400;
    }

    .brand svg {
      color: rgba(255, 255, 255, .88);
    }

    h1 {
      max-width: 1180px;
      margin: 0 auto 12px;
      color: #fff;
      text-align: left;
      font-family: var(--font);
      font-size: 21.6pt;
      font-weight: 400;
      line-height: 1.25;
      letter-spacing: .02em;
    }

    h1 .brand-mark {
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }

    h1 svg {
      width: 41px;
      height: 41px;
      color: rgba(255, 255, 255, .88);
      flex: 0 0 auto;
    }

    .launch-link {
      position: fixed;
      top: 22px;
      right: 28px;
      z-index: 10;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 9px;
      min-height: 36px;
      padding: 0 12px;
      border: 1px solid rgba(140, 193, 193, .5);
      border-radius: 6px;
      color: rgba(255, 255, 255, .88);
      background: rgba(255, 255, 255, .08);
      font-family: var(--font);
      font-size: 14pt;
      font-weight: 400;
      letter-spacing: .02em;
      text-decoration: none;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      transition: background .16s ease, border-color .16s ease, color .16s ease;
    }

    .launch-link:hover {
      color: #fff;
      background: rgba(140, 193, 193, .18);
      border-color: rgba(140, 193, 193, .78);
      text-decoration: none;
    }

    .launch-link svg {
      width: 20px;
      height: 20px;
      color: currentColor;
    }

    .hero-subhead {
      display: block;
      max-width: 1180px;
      margin: 0 auto 24px;
      padding: 18px 20px;
      border: 1px solid rgba(140, 193, 193, .34);
      border-radius: 6px;
      background: rgba(4, 12, 22, .42);
      color: rgba(255, 255, 255, .76);
      font-size: 18pt;
      font-weight: 600;
      line-height: 1.5;
      text-align: left;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    }

    .demo-points,
    .scope-note,
    .controls,
    .result,
    .files {
      max-width: 1180px;
      margin-left: auto;
      margin-right: auto;
      background: #fff;
      border: .64px solid var(--border);
      border-radius: 6px;
      box-shadow: none;
      font-family: var(--font);
    }

    .demo-points {
      display: grid;
      gap: 0;
      padding: 0;
      overflow: hidden;
      color: var(--body-c);
    }

    .demo-points li {
      min-height: 78px;
      display: flex;
      align-items: center;
      padding: 13px 16px 11px;
      border-bottom: .64px solid var(--border);
      color: var(--name-c);
      font-size: 14pt;
      font-weight: 500;
      line-height: 1.35;
    }

    .demo-points li:last-child {
      border-bottom: 0;
    }

    .demo-points li::before {
      content: "";
      width: 8px;
      height: 8px;
      margin-right: 12px;
      background: var(--teal-dark);
      flex: 0 0 auto;
    }

    .scope-note {
      margin-top: 12px;
      margin-bottom: 12px;
      padding: 16px 20px 14px;
      color: var(--name-c);
      font-size: 14pt;
      font-weight: 500;
      line-height: 1.45;
    }

    .controls {
      grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(138px, auto);
      gap: 18px;
      padding: 22px 24px;
      margin-bottom: 12px;
    }

    .controls .runtime-note {
      grid-column: 1 / -1;
      margin: 0;
      padding: 0 0 2px;
      color: var(--name-c);
      background: transparent;
      font-size: 14pt;
      font-weight: 500;
      line-height: 1.45;
    }

    .controls .runtime-note strong {
      font-weight: 600;
    }

    label {
      color: var(--body-c);
      font-size: 14pt;
      font-weight: 500;
      letter-spacing: 0;
      text-transform: none;
    }

    input {
      min-height: 60px;
      border: 2px solid rgba(140, 193, 193, .82);
      border-radius: 8px;
      background: rgb(250, 253, 253);
      padding: 12px 16px;
      color: var(--name-c);
      font-size: 20pt;
      font-weight: 500;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, .88),
        0 8px 18px rgba(20, 24, 32, .06);
    }

    button {
      min-height: 60px;
      border-radius: 8px;
      background: var(--green);
      color: #fff;
      font-size: 15pt;
      font-weight: 650;
      box-shadow: 0 10px 22px rgba(76, 121, 0, .18);
    }

    .limits,
    .status,
    .progress-bar,
    .progress {
      max-width: 1180px;
      margin-left: auto;
      margin-right: auto;
    }

    .limits {
      margin-bottom: 14px;
      padding: 0;
      background: transparent;
      color: rgba(255, 255, 255, .72);
      font-size: 12pt;
      line-height: 1.45;
    }

    .limits strong {
      color: #fff;
    }

    .limits a {
      color: var(--teal);
    }

    .status {
      color: var(--teal);
      font-size: 14pt;
      font-weight: 700;
    }

    .progress-bar {
      border: .64px solid rgba(255, 255, 255, .3);
      background: rgba(255, 255, 255, .22);
    }

    .progress {
      gap: 8px;
    }

    .step {
      border: 1px solid rgba(118, 185, 0, .28);
      background: rgba(244, 250, 232, .9);
      color: var(--green);
      font-size: 12pt;
      font-weight: 800;
    }

    .result {
      padding: 22px;
      margin-bottom: 12px;
    }

    .result-copy {
      color: var(--green);
      font-size: 22pt;
      line-height: 1.35;
    }

    .result-why {
      color: var(--body-c);
      font-size: 13pt;
      line-height: 1.45;
    }

    .result-metrics li {
      min-height: 58px;
      border: .64px solid var(--border);
      color: var(--green);
      font-size: 20pt;
      font-weight: 800;
    }

    .files {
      padding: 18px 20px;
    }

    .files h2 {
      color: var(--name-c);
      font-size: 17pt;
      font-weight: 700;
    }

    .files a {
      border: 1px solid rgba(140, 193, 193, .65);
      color: var(--teal-dark);
      font-size: 11pt;
      font-weight: 800;
    }

    .log {
      max-width: 1180px;
      margin: 0 auto;
    }

    .brand {
      display: none;
    }

    .launch-panel {
      max-width: 1180px;
      margin: 0 auto;
      background: #fff;
      border: .64px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      color: var(--name-c);
      font-family: var(--font);
    }

    .launch-panel .demo-points,
    .launch-panel .scope-note,
    .launch-panel .controls,
    .launch-panel .result,
    .launch-panel .files,
    .launch-panel .log {
      max-width: none;
      margin: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
    }

    .launch-panel .demo-points,
    .launch-panel .scope-note,
    .launch-panel .controls,
    .launch-panel .limits,
    .launch-panel .status,
    .launch-panel .progress-bar,
    .launch-panel .progress,
    .launch-panel .result,
    .launch-panel .files {
      border-bottom: .64px solid var(--border);
    }

    .launch-panel .limits,
    .launch-panel .status,
    .launch-panel .progress-bar,
    .launch-panel .progress {
      max-width: none;
      margin: 0;
    }

    .launch-panel .limits {
      padding: 18px 20px;
      color: var(--body-c);
      background: transparent;
      font-size: 13pt;
      font-weight: 500;
      line-height: 1.5;
    }

    .launch-panel .limits strong {
      color: var(--name-c);
    }

    .launch-panel .limits a {
      font-weight: 500;
    }

    .launch-panel .status {
      padding: 18px 20px;
      color: var(--teal-dark);
      font-size: 14pt;
      font-weight: 500;
    }

    .launch-panel .progress-bar {
      height: 14px;
      border-width: 0;
      background: rgb(238, 241, 241);
    }

    .launch-panel .progress {
      padding: 20px;
      background: #fff;
    }

    .launch-panel .result {
      padding: 24px 20px;
    }

    .launch-panel .files {
      padding: 24px 20px;
    }

    .launch-panel .log-wrap {
      border-bottom: 0;
      background: #10151d;
    }

    .metric-em {
      color: var(--name-c);
      font-weight: 600;
    }

    .step {
      min-height: 60px;
      display: flex;
      align-items: center;
      border: 1px solid rgba(140, 193, 193, .64);
      border-radius: 8px;
      background: rgb(250, 253, 253);
      color: var(--name-c);
      padding: 14px 16px;
      font-size: 14pt;
      font-weight: 500;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, .88),
        0 8px 18px rgba(20, 24, 32, .04);
    }

    .step::before {
      width: 11px;
      height: 11px;
      margin-right: 12px;
      border-color: var(--teal-dark);
    }

    .step.done {
      border-color: rgba(118, 185, 0, .44);
      color: var(--green);
      background: rgba(244, 250, 232, .9);
    }

    .result-copy {
      color: var(--name-c);
      font-size: 20pt;
      font-weight: 500;
      line-height: 1.42;
    }

    .copy-evidence {
      justify-self: center;
      min-height: 52px;
      margin: 0 auto 4px;
      border: 1px solid rgba(140, 193, 193, .72);
      border-radius: 8px;
      background: rgb(250, 253, 253);
      color: var(--teal-dark);
      padding: 0 18px;
      font-size: 13.5pt;
      font-weight: 500;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, .88),
        0 8px 18px rgba(20, 24, 32, .04);
      transition: transform .16s ease, background .16s ease, border-color .16s ease;
    }

    .copy-evidence:hover {
      background: rgba(140, 193, 193, .12);
      border-color: var(--teal-dark);
      transform: scale(1.035);
    }

    .pass-lead {
      color: var(--green);
      font-size: 23pt;
      font-weight: 650;
    }

    .result-why {
      margin-top: 14px;
      color: var(--body-c);
      font-size: 14pt;
      font-weight: 500;
      line-height: 1.5;
    }

    .result-metrics {
      gap: 12px;
      margin-top: 18px;
    }

    .result-metrics li {
      position: relative;
      min-height: 66px;
      border: 1px solid rgba(140, 193, 193, .64);
      border-radius: 8px;
      background: rgb(250, 253, 253);
      color: var(--name-c);
      font-size: 20pt;
      font-weight: 500;
      padding: 14px 16px;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, .88),
        0 8px 18px rgba(20, 24, 32, .04);
    }

    .result-metrics li::after {
      content: attr(data-tooltip);
      position: absolute;
      left: 18px;
      right: 18px;
      bottom: calc(100% + 10px);
      z-index: 5;
      display: none;
      padding: 16px 18px;
      border: 1px solid rgba(140, 193, 193, .72);
      border-radius: 8px;
      background: #fff;
      color: var(--name-c);
      box-shadow: 0 16px 36px rgba(20, 24, 32, .18);
      font-size: 20pt;
      font-weight: 500;
      line-height: 1.35;
    }

    .result-metrics li:hover::after,
    .result-metrics li:focus::after {
      display: block;
    }

    .metric-number {
      color: var(--green);
      margin-right: 8px;
      font-size: 22pt;
      font-weight: 600;
    }

    .metric-label {
      color: var(--name-c);
      font-weight: 500;
    }

    .files h2 {
      margin-bottom: 16px;
      color: var(--name-c);
      font-size: 18pt;
      font-weight: 500;
    }

    .files a {
      min-height: 48px;
      border: 1px solid rgba(140, 193, 193, .72);
      border-radius: 8px;
      background: rgb(250, 253, 253);
      color: var(--teal-dark);
      padding: 0 14px;
      font-size: 12.5pt;
      font-weight: 500;
      transform: scale(1);
      transform-origin: center;
      transition: transform .16s ease, background .16s ease, border-color .16s ease, box-shadow .16s ease;
    }

    .files a:hover {
      background: rgba(140, 193, 193, .12);
      border-color: var(--teal-dark);
      box-shadow: 0 10px 24px rgba(20, 24, 32, .10);
      transform: scale(1.045);
    }

    .log-wrap {
      position: relative;
      display: none;
      max-width: 1180px;
      margin: 0 auto;
      background: #10151d;
    }

    .copy-log {
      position: absolute;
      top: 14px;
      right: 14px;
      z-index: 2;
      min-height: 38px;
      border: 1px solid rgba(140, 193, 193, .52);
      border-radius: 7px;
      background: rgba(255, 255, 255, .08);
      color: #dfe7ef;
      padding: 0 12px;
      font-size: 11pt;
      font-weight: 500;
      box-shadow: none;
    }

    .copy-log:hover {
      background: rgba(140, 193, 193, .18);
    }

    .log {
      min-height: 260px;
      padding: 64px 22px 22px;
      font-size: 12pt;
      line-height: 1.55;
    }

    @media (max-width: 820px) {
      main {
        max-width: 96%;
        padding: 20px 12px 40px;
      }

      .controls,
      .progress,
      .result-metrics,
      .claim-boundaries {
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
  <a class="launch-link" href="https://brev.nvidia.com/launchable/deploy?launchableID=env-3Gl3frrN9xLqxFk47kk8TMGE3kD" target="_blank" rel="noopener" aria-label="Open TeleMemetry Launchable on NVIDIA Brev">Share Launchable<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 17 17 7M9 7h8v8" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 4h6v6M20 4 10 14" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" opacity=".45"/></svg></a>
  <h1><span class="brand-mark"><svg width="256" height="256" viewBox="0 0 256 256" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg"><g fill="none" stroke="currentColor" stroke-width="14" stroke-linejoin="round"><rect x="42" y="42" width="108" height="108" rx="8"/><rect x="106" y="106" width="108" height="108" rx="8"/></g></svg>TeleMemetry&trade; Launchable on NVIDIA Brev</span></h1>
  <p class="hero-subhead">This benchmark demonstrates how AI can respond with bit-perfect operational recall, even over long-running telemetry, without replaying historical context.</p>
  <section class="launch-panel" aria-label="Launchable benchmark">
    <ul class="demo-points">
      <li>Watch thousands of operational recall events become instantly queryable without replaying conversation history.</li>
      <li>Every answer is backed by verifiable evidence and SHA256 receipts, available in the result links below after the run.</li>
    </ul>
    <p class="scope-note">This is a public reproduction harness, not the private production engine. It mathematically verifies this measurement workflow and proves the artifact trail.</p>
    <a class="hero-cta" href="#run-panel">Try the Docker Version of the TeleMemetry Engine</a>

    <section class="controls" id="run-panel" aria-label="Benchmark controls">
      <p class="runtime-note"><strong>Typical runtime:</strong> 20&ndash;60 seconds depending on workload.</p>
      <label>Turns <input id="turns" type="number" min="1" max="10000" value="3000"></label>
      <label>Fields per Record <input id="fields" type="number" min="1" max="10" value="10"></label>
      <label>Episodes <input id="episodes" type="number" min="1" max="100" value="20"></label>
      <button id="run">Run TeleMemetry</button>
    </section>
    <p class="limits"><strong>Public demo limits:</strong> up to 10,000 turns, 10 fields, and 100 episodes. These caps keep browser response, result files, and Brev instance time predictable. Need a bigger or domain-specific run? <a href="https://telememetry.com/reproduce.html" target="_blank" rel="noopener">Request a custom benchmark</a>.</p>

    <p class="status" id="status">Ready. Recommended first run: 3,000 turns, 10 fields, 20 episodes.</p>
    <div class="progress-bar" aria-label="Benchmark progress"><div class="progress-fill" id="progress-fill"></div></div>

    <section class="progress" aria-label="Progress">
      <div class="step" id="step-generate">Generating evidence</div>
      <div class="step" id="step-verify">Verify 1:1 recall</div>
      <div class="step" id="step-hash">Write SHA256 receipts</div>
      <div class="step" id="step-package">Package AI audit files</div>
    </section>

    <section class="result" id="result" aria-label="Benchmark result">
      <button class="copy-evidence" id="copy-evidence" type="button">Copy Benchmark Evidence for AI</button>
      <p class="result-copy" id="result-copy"></p>
      <p class="result-why">Why this matters: a field appliance, robot, vehicle, or satellite can keep long operational history outside the model, then retrieve the exact state needed for the next decision without replaying the whole history into context.</p>
      <ul class="result-metrics">
        <li id="metric-responses" tabindex="0" data-tooltip="Bit-perfect responses are exact matches against stored telemetry state. Legacy context replay has to drag history forward; TeleMemetry retrieves the bounded proof needed for each answer.">-</li>
        <li id="metric-recall" tabindex="0" data-tooltip="1:1 recall means every checked answer matched the reference value. Compared with legacy long-context replay, this turns memory verification into a measurable pass or fail result.">-</li>
        <li id="metric-tokens" tabindex="0" data-tooltip="Tokens per turn estimates how small each bounded evidence packet is. Lower packet size matters because legacy replay grows with history, while this stays compact.">-</li>
        <li id="metric-reduction" tabindex="0" data-tooltip="Context-history reduction estimates how much less history is replayed. This is the legacy comparison: instead of pushing old telemetry back into context, the system retrieves the exact evidence needed.">-</li>
      </ul>
      <div class="claim-boundaries" aria-label="Benchmark claim boundaries">
        <div class="claim-box">
          <h3>What this proves</h3>
          <ul>
            <li>Exact operational-state recall inside this public benchmark scope.</li>
            <li>Bounded evidence packets instead of full-history replay.</li>
            <li>SHA256 receipts for artifact-change detection.</li>
          </ul>
        </div>
        <div class="claim-box">
          <h3>What this does not prove</h3>
          <ul>
            <li>Universal semantic memory or chatbot reasoning quality.</li>
            <li>Robotics, AV, or production safety certification.</li>
            <li>Private TeleMemetry production engine internals.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="files" id="files" aria-label="Result files">
      <h2>TeleMemetry&trade; Result Packages</h2>
      <a href="/file/results/latest/RESULT_SUMMARY.txt" target="_blank">View Result Summary ↗</a>
      <a href="/file/results/latest/prompt.md" target="_blank">View AI Audit Prompt ↗</a>
      <a href="/file/results/latest/metrics.json" target="_blank">View Metrics ↗</a>
      <a href="/file/results/latest/manifest.json" target="_blank">View SHA256 Manifest ↗</a>
      <a href="/file/results/latest/dataset.jsonl" target="_blank">View Raw Telemetry In ↗</a>
      <a href="/file/results/latest/evidence_packets.jsonl" target="_blank">View Evidence Packets ↗</a>
      <a href="/file/results/latest/outputs.jsonl" target="_blank">View Verified Outputs ↗</a>
      <a href="/bundle/latest.tar.gz" download>Download Evidence Bundle (.tar.gz) ↗</a>
      <a href="/bundle/latest.zip" download>Download Evidence Bundle (.zip) ↗</a>
    </section>

    <section class="log-wrap" id="log-wrap" aria-label="Output terminal">
      <button class="copy-log" id="copy-log" type="button">Copy output</button>
      <pre class="log" id="log"></pre>
    </section>
  </section>
</main>
<script>
  var runButton = document.getElementById('run');
  var statusEl = document.getElementById('status');
  var logEl = document.getElementById('log');
  var logWrapEl = document.getElementById('log-wrap');
  var copyLogButton = document.getElementById('copy-log');
  var copyEvidenceButton = document.getElementById('copy-evidence');
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
  var numberFormatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

  function formatNumber(value) {
    return numberFormatter.format(Number(value));
  }

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
    runButton.textContent = running ? 'Running...' : 'Run TeleMemetry';
  }

  function resetUi() {
    steps.forEach(function (step) { step.classList.remove('done'); });
    resultEl.style.display = 'none';
    filesEl.style.display = 'none';
    logWrapEl.style.display = 'none';
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

    function passLead(value) {
      var span = document.createElement('span');
      span.className = 'pass-lead';
      span.textContent = value;
      copy.appendChild(span);
    }

    function metric(value) {
      var span = document.createElement('span');
      span.className = 'metric-em';
      span.textContent = value;
      copy.appendChild(span);
    }

    passLead('PASS: ');
    text('this run verified ');
    metric(formatNumber(metrics.recall.verified_turns) + ' of ' + formatNumber(metrics.recall.total_turns) + ' turns');
    text(' with ');
    metric(formatNumber(metrics.recall.final_verified_output_failures) + ' final failures');
    text(', averaging ');
    metric(formatNumber(metrics.token_accounting.average_packet_tokens_per_turn_estimate) + ' bounded packet tokens per turn');
    text(' and reporting a ');
    metric(formatNumber(metrics.token_accounting.replay_reduction_ratio_estimate) + 'x replay reduction estimate');
    text('.');
  }

  function showResult(data, statusText) {
    var metrics = data.metrics;
    var exactRecallPercent = Math.round(metrics.recall.exact_match_rate * 10000) / 100;

    function setMetric(id, numberText, labelText) {
      var item = document.getElementById(id);
      item.textContent = '';

      var number = document.createElement('span');
      number.className = 'metric-number';
      number.textContent = numberText;

      var label = document.createElement('span');
      label.className = 'metric-label';
      label.textContent = labelText;

      item.appendChild(number);
      item.appendChild(label);
    }

    setMetric('metric-responses', formatNumber(metrics.recall.verified_turns), 'bit-perfect responses');
    setMetric('metric-recall', exactRecallPercent + '%', '1:1 recall - zero failures');
    setMetric('metric-tokens', formatNumber(metrics.token_accounting.average_packet_tokens_per_turn_estimate), 'tokens per turn');
    setMetric('metric-reduction', formatNumber(metrics.token_accounting.replay_reduction_ratio_estimate) + 'x', 'context-history reduction estimate');
    setPassText(metrics);
    statusEl.textContent = statusText || 'PASS. Result package is ready in results/latest.';
    progressFill.style.width = '100%';
    steps.forEach(function (step) { step.classList.add('done'); });
    resultEl.style.display = 'grid';
    filesEl.style.display = 'block';
    logWrapEl.style.display = 'block';
    logEl.style.display = 'block';
    logEl.textContent = (data.output || '') + (data.output ? '\\n\\n' : '') + (data.summary || '');
  }

  function loadLatestPreview() {
    fetch('/latest').then(function (response) {
      if (!response.ok) return null;
      return response.json();
    }).then(function (data) {
      if (!data || !data.ok) return;
      showResult(data, 'Previewing results/latest so the after-run page can be reviewed.');
    }).catch(function () {});
  }

  function copyTextWithFeedback(button, output, successText, defaultText) {
    if (!output) return;

    navigator.clipboard.writeText(output).then(function () {
      button.textContent = successText;
      setTimeout(function () {
        button.textContent = defaultText;
      }, 1400);
    }).catch(function () {
      button.textContent = 'Copy failed';
      setTimeout(function () {
        button.textContent = defaultText;
      }, 1400);
    });
  }

  copyEvidenceButton.addEventListener('click', function () {
    copyTextWithFeedback(copyEvidenceButton, logEl.textContent || '', 'Evidence copied', 'Copy Benchmark Evidence for AI');
  });

  copyLogButton.addEventListener('click', function () {
    copyTextWithFeedback(copyLogButton, logEl.textContent || '', 'Copied', 'Copy output');
  });

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
      showResult(data, 'PASS. Result package is ready in results/latest.');
    }).catch(function (error) {
      statusEl.textContent = 'Failed: ' + error.message;
      logWrapEl.style.display = 'block';
      logEl.style.display = 'block';
      logEl.textContent = String(error);
    }).finally(function () {
      setRunning(false);
    });
  });

  loadLatestPreview();
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

    def send_download(self, body: bytes, content_type: str, filename: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
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
        if parsed.path == "/latest":
            metrics_path = ROOT / "results/latest/metrics.json"
            summary_path = ROOT / "results/latest/RESULT_SUMMARY.txt"
            verify_path = ROOT / "results/latest/VERIFY.txt"
            if not metrics_path.exists() or not summary_path.exists():
                self.send_json(404, {"ok": False, "error": "latest result package not found"})
                return
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            summary = summary_path.read_text(encoding="utf-8")
            output = verify_path.read_text(encoding="utf-8") if verify_path.exists() else ""
            self.send_json(200, {
                "ok": True,
                "metrics": metrics,
                "summary": summary,
                "output": output,
            })
            return
        if parsed.path == "/bundle/latest.tar.gz":
            bundle_dir = (ROOT / "results/latest").resolve()
            if not str(bundle_dir).startswith(str(ROOT)) or not bundle_dir.exists() or not bundle_dir.is_dir():
                self.send_json(404, {"ok": False, "error": "latest result package not found"})
                return
            buffer = BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
                for path in sorted(bundle_dir.rglob("*")):
                    if path.is_file():
                        tar.add(path, arcname=str(Path("telememetry-evidence-bundle") / path.relative_to(bundle_dir)))
            self.send_download(
                buffer.getvalue(),
                "application/gzip",
                "telememetry-evidence-bundle-latest.tar.gz",
            )
            return
        if parsed.path == "/bundle/latest.zip":
            bundle_dir = (ROOT / "results/latest").resolve()
            if not str(bundle_dir).startswith(str(ROOT)) or not bundle_dir.exists() or not bundle_dir.is_dir():
                self.send_json(404, {"ok": False, "error": "latest result package not found"})
                return
            buffer = BytesIO()
            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                for path in sorted(bundle_dir.rglob("*")):
                    if path.is_file():
                        zip_file.write(path, arcname=str(Path("telememetry-evidence-bundle") / path.relative_to(bundle_dir)))
            self.send_download(
                buffer.getvalue(),
                "application/zip",
                "telememetry-evidence-bundle-latest.zip",
            )
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
