#!/usr/bin/env python3
"""HTML visualization for sidm2.audio_tightness's TightnessReport.

Mirrors accuracy_heatmap_exporter.py's structure: HTMLComponents dark-theme
header/footer, a StatCard row, a waveform view (downsampled envelope of
both renders with colored onset markers), and a sortable onset table.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from pyscript.html_components import HTMLComponents, StatCard, StatCardType, NavItem
from sidm2.audio_tightness import (
    TightnessReport,
    count_alignment_crossings,
    offset_and_jitter,
)

try:
    from sidm2 import __version__ as SIDM2_VERSION
except ImportError:
    SIDM2_VERSION = "unknown"


class AudioTightnessHTMLExporter:
    """Builds a self-contained HTML tightness report."""

    def __init__(self, report: TightnessReport, meta: Optional[Dict[str, Any]] = None,
                 orig_env: Optional[Sequence[float]] = None,
                 driver_env: Optional[Sequence[float]] = None,
                 env_hop_s: float = 0.01):
        self.report = report
        self.meta = meta or {}
        self.orig_env = list(orig_env) if orig_env is not None else None
        self.driver_env = list(driver_env) if driver_env is not None else None
        self.env_hop_s = env_hop_s

    # -- stats -----------------------------------------------------------

    def _counts(self):
        n_orig = len(self.report.orig_onsets)
        n_driver = len(self.report.driver_onsets)
        n_matched = len(self.report.matched)
        n_missing = len(self.report.missing)
        n_extra = len(self.report.extra)
        n_loose = sum(1 for m in self.report.matched if m.loose)
        return n_orig, n_driver, n_matched, n_missing, n_extra, n_loose

    def _stat_cards(self) -> List[StatCard]:
        n_orig, n_driver, n_matched, n_missing, n_extra, n_loose = self._counts()

        offset_ms, jitters = offset_and_jitter(self.report.matched)
        thr = float(self.report.params.get('loose_threshold_ms', 40))
        n_loose_jitter = sum(1 for j in jitters if abs(j) > thr)
        loose_pct = 100.0 * n_loose_jitter / n_matched if n_matched else 0.0
        n_cross = count_alignment_crossings(self.report.matched)

        return [
            StatCard("Matched", str(n_matched), StatCardType.SUCCESS),
            StatCard("Missing", str(n_missing), StatCardType.ERROR if n_missing else StatCardType.PRIMARY),
            StatCard("Extra", str(n_extra), StatCardType.WARNING if n_extra else StatCardType.PRIMARY),
            # Offset and jitter are shown as separate cards on purpose: a
            # uniform shift and genuine looseness are different defects, and
            # a single "mean delta" number conflates them.
            StatCard("Offset", f"{offset_ms:+.1f} ms", StatCardType.INFO),
            StatCard("Loose % (jitter)", f"{loose_pct:.1f}%",
                     StatCardType.WARNING if loose_pct > 0 else StatCardType.SUCCESS),
            StatCard("Crossed", str(n_cross),
                     StatCardType.ERROR if n_cross else StatCardType.SUCCESS),
        ]

    # -- sections ----------------------------------------------------------

    def _overview_html(self) -> str:
        n_orig, n_driver, n_matched, n_missing, n_extra, n_loose = self._counts()
        rows = [
            ["Original", self.meta.get('orig_path', '?')],
            ["Driver", self.meta.get('driver_path', '?')],
            ["Orig onsets", str(n_orig)],
            ["Driver onsets", str(n_driver)],
            ["Matched", str(n_matched)],
            ["Missing", str(n_missing)],
            ["Extra", str(n_extra)],
            ["Loose (of matched)", f"{n_loose} / {n_matched}"],
        ]
        for key in sorted(self.report.params.keys()):
            rows.append([key, str(self.report.params[key])])
        return HTMLComponents.create_table(["Metric", "Value"], rows)

    def _waveform_html(self) -> str:
        markers = []
        for m in self.report.matched:
            markers.append({
                'origT': m.orig_t, 'driverT': m.driver_t, 'type': 'loose' if m.loose else 'matched',
                'deltaMs': m.delta_ms, 'riseDeltaMs': m.rise_delta_ms, 'specDist': m.spectral_dist,
            })
        for t in self.report.missing:
            markers.append({'origT': t, 'driverT': None, 'type': 'missing'})
        for t in self.report.extra:
            markers.append({'origT': None, 'driverT': t, 'type': 'extra'})

        data = {
            'origEnv': self.orig_env or [],
            'driverEnv': self.driver_env or [],
            'hopS': self.env_hop_s,
            'markers': markers,
        }
        data_json = json.dumps(data)

        no_env_note = "" if (self.orig_env and self.driver_env) else (
            '<p style="color:#f09819">No waveform envelope data was supplied -- '
            'showing onset markers only.</p>'
        )

        return f"""
        <div id="waveform-tooltip" style="position:fixed; display:none; background:#252526;
             border:1px solid #3e3e42; padding:8px 12px; border-radius:4px; font-size:12px;
             pointer-events:none; z-index:1000;"></div>
        {no_env_note}
        <p style="color:#858585; font-size:0.85em; margin-bottom:10px;">
            Green = matched, Yellow = matched but loose, Red = missing (orig only),
            Purple = extra (driver only). Hover a marker for details.
        </p>
        <canvas id="tightness-waveform-canvas" width="1200" height="260"
                style="width:100%; max-width:1200px; background:#1e1e1e; border:1px solid #3e3e42;"></canvas>
        <script>
        (function() {{
            const DATA = {data_json};
            const canvas = document.getElementById('tightness-waveform-canvas');
            const tooltip = document.getElementById('waveform-tooltip');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const W = canvas.width, H = canvas.height;
            const midOrig = H * 0.28, midDriver = H * 0.72, ampScale = H * 0.22;

            const maxT = Math.max(
                DATA.origEnv.length * DATA.hopS,
                DATA.driverEnv.length * DATA.hopS,
                ...DATA.markers.map(m => Math.max(m.origT || 0, m.driverT || 0)),
                1
            );
            const xOf = t => (t / maxT) * W;

            function drawEnv(env, mid, color) {{
                if (!env.length) return;
                ctx.strokeStyle = color;
                ctx.beginPath();
                for (let i = 0; i < env.length; i++) {{
                    const x = xOf(i * DATA.hopS);
                    const y = mid - env[i] * ampScale;
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                }}
                ctx.stroke();
            }}

            ctx.fillStyle = '#1e1e1e';
            ctx.fillRect(0, 0, W, H);
            ctx.font = '11px monospace';
            ctx.fillStyle = '#858585';
            ctx.fillText('original', 4, midOrig - ampScale - 4);
            ctx.fillText('driver', 4, midDriver - ampScale - 4);
            drawEnv(DATA.origEnv, midOrig, '#569cd6');
            drawEnv(DATA.driverEnv, midDriver, '#c586c0');

            const colors = {{matched: '#56ab2f', loose: '#dcdcaa', missing: '#eb3349', extra: '#c586c0'}};
            const markerXs = [];
            DATA.markers.forEach(m => {{
                const color = colors[m.type] || '#d4d4d4';
                const t = m.origT != null ? m.origT : m.driverT;
                const x = xOf(t);
                markerXs.push({{x: x, m: m}});
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x, H / 2, 4, 0, 2 * Math.PI);
                ctx.fill();
            }});

            canvas.addEventListener('mousemove', function(ev) {{
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const x = (ev.clientX - rect.left) * scaleX;
                let nearest = null, bestD = 12;
                markerXs.forEach(entry => {{
                    const d = Math.abs(entry.x - x);
                    if (d < bestD) {{ bestD = d; nearest = entry.m; }}
                }});
                if (nearest) {{
                    let lines = ['type: ' + nearest.type];
                    if (nearest.origT != null) lines.push('orig_t: ' + nearest.origT.toFixed(3) + 's');
                    if (nearest.driverT != null) lines.push('driver_t: ' + nearest.driverT.toFixed(3) + 's');
                    if (nearest.deltaMs != null) lines.push('delta_ms: ' + nearest.deltaMs.toFixed(1));
                    if (nearest.riseDeltaMs != null) lines.push('rise_delta_ms: ' + nearest.riseDeltaMs.toFixed(1));
                    if (nearest.specDist != null && !isNaN(nearest.specDist)) lines.push('spec_dist: ' + nearest.specDist.toFixed(3));
                    tooltip.innerHTML = lines.join('<br>');
                    tooltip.style.left = (ev.clientX + 12) + 'px';
                    tooltip.style.top = (ev.clientY + 12) + 'px';
                    tooltip.style.display = 'block';
                }} else {{
                    tooltip.style.display = 'none';
                }}
            }});
            canvas.addEventListener('mouseleave', function() {{ tooltip.style.display = 'none'; }});
        }})();
        </script>
"""

    def _timeline_html(self) -> str:
        """Zoomable orig-vs-driver onset timeline with connector lines.

        The point of this view: a pair whose connector line CROSSES its
        neighbour's cannot be a real match (music does not reorder itself),
        so crossings localise greedy-alignment mispairings that would
        otherwise masquerade as timing jitter. The offset-correction toggle
        separates the other confound -- a uniform whole-render shift, which
        makes every pair look late without any of them being loose.
        """
        offset_ms, jitters = offset_and_jitter(self.report.matched)
        thr = float(self.report.params.get('loose_threshold_ms', 40))
        n_cross = count_alignment_crossings(self.report.matched)

        pairs = [
            {'origT': m.orig_t, 'driverT': m.driver_t, 'deltaMs': m.delta_ms, 'jitterMs': j}
            for m, j in zip(self.report.matched, jitters)
        ]
        data_json = json.dumps({
            'pairs': pairs,
            'missing': list(self.report.missing),
            'extra': list(self.report.extra),
            'offsetMs': offset_ms,
            'looseThresholdMs': thr,
        })

        cross_note = (
            f'<p style="color:#eb3349; margin:6px 0;"><strong>{n_cross} crossed pair(s)</strong> '
            f'&mdash; connector lines that run backwards in time. These are alignment '
            f'mispairings, not real timing errors; jitter statistics are an upper bound '
            f'while they persist.</p>'
        ) if n_cross else (
            '<p style="color:#56ab2f; margin:6px 0;">No crossed pairs &mdash; onset '
            'alignment is monotonic, so jitter reflects real timing.</p>'
        )

        return f"""
        <div id="timeline-tooltip" style="position:fixed; display:none; background:#252526;
             border:1px solid #3e3e42; padding:8px 12px; border-radius:4px; font-size:12px;
             pointer-events:none; z-index:1000;"></div>
        <p style="color:#858585; font-size:0.85em; margin-bottom:6px;">
            Top lane = original onsets, bottom lane = driver onsets, joined by a connector
            per matched pair. Connector colour = |jitter| (green tight &rarr; red loose).
            <strong>Crossed connectors mean mispairing, not looseness.</strong>
            Red ticks = missing, purple = extra.
            <br>Scroll to zoom, drag to pan, double-click to reset.
        </p>
        {cross_note}
        <label style="color:#d4d4d4; font-size:0.85em; user-select:none; cursor:pointer;">
            <input type="checkbox" id="timeline-offset-toggle" checked>
            Remove systematic offset ({offset_ms:+.1f} ms) &mdash; uncheck to see raw alignment
        </label>
        <canvas id="tightness-timeline-canvas" width="1200" height="300"
                style="width:100%; max-width:1200px; background:#1e1e1e; border:1px solid #3e3e42;
                       display:block; margin-top:8px; cursor:grab;"></canvas>
        <script>
        (function() {{
            const D = {data_json};
            const canvas = document.getElementById('tightness-timeline-canvas');
            const tooltip = document.getElementById('timeline-tooltip');
            const toggle = document.getElementById('timeline-offset-toggle');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const W = canvas.width, H = canvas.height;
            const yOrig = 70, yDriver = H - 70;

            const allT = []
                .concat(D.pairs.map(p => p.origT), D.pairs.map(p => p.driverT),
                        D.missing, D.extra);
            const tMin = 0;
            const tMax = allT.length ? Math.max.apply(null, allT) * 1.02 : 1;
            let viewA = tMin, viewB = tMax;

            const xOf = t => ((t - viewA) / (viewB - viewA)) * W;
            const tOf = x => viewA + (x / W) * (viewB - viewA);

            // Offset correction shifts the DRIVER lane back by the median
            // delta, so a uniformly-late render lines up and only genuine
            // jitter stays visible.
            const corr = () => (toggle && toggle.checked) ? D.offsetMs / 1000.0 : 0;

            function jitterColor(j) {{
                const a = Math.abs(j), thr = D.looseThresholdMs;
                if (a <= thr * 0.5) return '#56ab2f';
                if (a <= thr) return '#dcdcaa';
                if (a <= thr * 2) return '#f09819';
                return '#eb3349';
            }}

            let hot = [];

            function draw() {{
                ctx.fillStyle = '#1e1e1e';
                ctx.fillRect(0, 0, W, H);

                // lanes
                ctx.strokeStyle = '#3e3e42';
                ctx.lineWidth = 1;
                [yOrig, yDriver].forEach(y => {{
                    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
                }});
                ctx.font = '11px monospace';
                ctx.fillStyle = '#858585';
                ctx.fillText('original', 6, yOrig - 12);
                ctx.fillText('driver' + (corr() ? ' (offset removed)' : ''), 6, yDriver + 22);

                // time ruler
                const span = viewB - viewA;
                const step = Math.pow(10, Math.floor(Math.log10(span / 6)));
                const nice = span / step > 30 ? step * 5 : step;
                ctx.fillStyle = '#6a6a6a';
                for (let t = Math.ceil(viewA / nice) * nice; t < viewB; t += nice) {{
                    const x = xOf(t);
                    ctx.fillRect(x, H / 2 - 4, 1, 8);
                    ctx.fillText(t.toFixed(2) + 's', x + 3, H / 2 + 14);
                }}

                hot = [];
                const c = corr();

                // detect backwards-running pairs for emphasis
                const ordered = D.pairs.slice().sort((a, b) => a.origT - b.origT);
                const crossed = new Set();
                for (let i = 1; i < ordered.length; i++) {{
                    if (ordered[i].driverT < ordered[i - 1].driverT) {{
                        crossed.add(ordered[i]); crossed.add(ordered[i - 1]);
                    }}
                }}

                D.pairs.forEach(p => {{
                    const x1 = xOf(p.origT), x2 = xOf(p.driverT - c);
                    if ((x1 < -50 && x2 < -50) || (x1 > W + 50 && x2 > W + 50)) return;
                    const isCross = crossed.has(p);
                    ctx.strokeStyle = isCross ? '#eb3349' : jitterColor(p.jitterMs);
                    ctx.lineWidth = isCross ? 2.5 : 1;
                    ctx.globalAlpha = isCross ? 1.0 : 0.65;
                    ctx.beginPath(); ctx.moveTo(x1, yOrig); ctx.lineTo(x2, yDriver); ctx.stroke();
                    ctx.globalAlpha = 1.0;

                    ctx.fillStyle = '#569cd6';
                    ctx.fillRect(x1 - 1, yOrig - 7, 2, 14);
                    ctx.fillStyle = '#c586c0';
                    ctx.fillRect(x2 - 1, yDriver - 7, 2, 14);
                    hot.push({{x: x1, y: yOrig, p: p, cross: isCross}});
                    hot.push({{x: x2, y: yDriver, p: p, cross: isCross}});
                }});

                ctx.fillStyle = '#eb3349';
                D.missing.forEach(t => {{
                    const x = xOf(t);
                    if (x < -10 || x > W + 10) return;
                    ctx.fillRect(x - 1.5, yOrig - 11, 3, 22);
                    hot.push({{x: x, y: yOrig, missing: t}});
                }});
                ctx.fillStyle = '#c586c0';
                D.extra.forEach(t => {{
                    const x = xOf(t - c);
                    if (x < -10 || x > W + 10) return;
                    ctx.fillRect(x - 1.5, yDriver - 11, 3, 22);
                    hot.push({{x: x, y: yDriver, extra: t}});
                }});
            }}

            canvas.addEventListener('wheel', function(ev) {{
                ev.preventDefault();
                const rect = canvas.getBoundingClientRect();
                const x = (ev.clientX - rect.left) * (canvas.width / rect.width);
                const tAt = tOf(x);
                const factor = ev.deltaY < 0 ? 0.8 : 1.25;
                let a = tAt - (tAt - viewA) * factor;
                let b = tAt + (viewB - tAt) * factor;
                if (b - a < 0.02) return;           // zoom floor
                viewA = Math.max(tMin, a); viewB = Math.min(tMax, b);
                if (viewB <= viewA) {{ viewA = tMin; viewB = tMax; }}
                draw();
            }}, {{passive: false}});

            let dragging = false, dragX = 0;
            canvas.addEventListener('mousedown', function(ev) {{
                dragging = true; dragX = ev.clientX; canvas.style.cursor = 'grabbing';
            }});
            window.addEventListener('mouseup', function() {{
                dragging = false; canvas.style.cursor = 'grab';
            }});
            canvas.addEventListener('dblclick', function() {{
                viewA = tMin; viewB = tMax; draw();
            }});

            canvas.addEventListener('mousemove', function(ev) {{
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                if (dragging) {{
                    const dt = ((ev.clientX - dragX) * scaleX / W) * (viewB - viewA);
                    dragX = ev.clientX;
                    let a = viewA - dt, b = viewB - dt;
                    if (a >= tMin && b <= tMax) {{ viewA = a; viewB = b; draw(); }}
                    return;
                }}
                const x = (ev.clientX - rect.left) * scaleX;
                const y = (ev.clientY - rect.top) * (canvas.height / rect.height);
                let best = null, bestD = 14;
                hot.forEach(h => {{
                    const d = Math.hypot(h.x - x, h.y - y);
                    if (d < bestD) {{ bestD = d; best = h; }}
                }});
                if (best) {{
                    let L = [];
                    if (best.missing != null) {{
                        L = ['MISSING onset', 'orig_t: ' + best.missing.toFixed(3) + 's',
                             'no driver onset within tolerance'];
                    }} else if (best.extra != null) {{
                        L = ['EXTRA onset', 'driver_t: ' + best.extra.toFixed(3) + 's',
                             'no original onset within tolerance'];
                    }} else {{
                        L = ['orig_t: ' + best.p.origT.toFixed(3) + 's',
                             'driver_t: ' + best.p.driverT.toFixed(3) + 's',
                             'delta: ' + best.p.deltaMs.toFixed(1) + ' ms',
                             'jitter: ' + best.p.jitterMs.toFixed(1) + ' ms'];
                        if (best.cross) L.push('<span style="color:#eb3349">CROSSED &mdash; likely mispaired</span>');
                    }}
                    tooltip.innerHTML = L.join('<br>');
                    tooltip.style.left = (ev.clientX + 12) + 'px';
                    tooltip.style.top = (ev.clientY + 12) + 'px';
                    tooltip.style.display = 'block';
                }} else {{
                    tooltip.style.display = 'none';
                }}
            }});
            canvas.addEventListener('mouseleave', function() {{
                tooltip.style.display = 'none'; dragging = false;
            }});
            if (toggle) toggle.addEventListener('change', draw);
            draw();
        }})();
        </script>
"""

    def _onset_table_html(self) -> str:
        _off, jitters = offset_and_jitter(self.report.matched)
        thr = float(self.report.params.get('loose_threshold_ms', 40))
        rows_html = []
        for m, j in zip(self.report.matched, jitters):
            # Status reflects JITTER, not raw delta: with a systematic offset
            # present, raw delta would mark every row loose and the table
            # would be useless for finding the genuinely mistimed onsets.
            is_loose = abs(j) > thr
            badge = HTMLComponents.create_badge(
                "LOOSE" if is_loose else "OK",
                StatCardType.WARNING if is_loose else StatCardType.SUCCESS
            )
            spec = f"{m.spectral_dist:.3f}" if m.spectral_dist == m.spectral_dist else "n/a"
            rows_html.append(
                f"<tr><td>{m.orig_t:.3f}</td><td>{m.driver_t:.3f}</td>"
                f"<td>{m.delta_ms:+.1f}</td><td>{j:+.1f}</td><td>{m.rise_delta_ms:+.1f}</td>"
                f"<td>{spec}</td><td>{badge}</td></tr>"
            )
        for t in self.report.missing:
            badge = HTMLComponents.create_badge("MISSING", StatCardType.ERROR)
            rows_html.append(f"<tr><td>{t:.3f}</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>{badge}</td></tr>")
        for t in self.report.extra:
            badge = HTMLComponents.create_badge("EXTRA", StatCardType.INFO)
            rows_html.append(f"<tr><td>-</td><td>{t:.3f}</td><td>-</td><td>-</td><td>-</td><td>-</td><td>{badge}</td></tr>")

        headers = ["orig_t (s)", "driver_t (s)", "delta_ms", "jitter_ms", "rise_delta_ms",
                   "spec_dist", "status"]
        header_cells = ''.join(
            f'<th style="cursor:pointer" onclick="sortOnsetTable({i})">{h} ⇅</th>'
            for i, h in enumerate(headers)
        )

        return f"""
        {HTMLComponents.create_search_box("Search onsets...", ".onset-row")}
        <table id="onset-table">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{''.join(rows_html)}</tbody>
        </table>
        <script>
        function sortOnsetTable(colIndex) {{
            const table = document.getElementById('onset-table');
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            const prevCol = table.getAttribute('data-sort-col');
            const asc = !(prevCol == colIndex && table.getAttribute('data-sort-dir') === 'asc');
            rows.sort((a, b) => {{
                let x = a.cells[colIndex].textContent.trim();
                let y = b.cells[colIndex].textContent.trim();
                const nx = parseFloat(x), ny = parseFloat(y);
                if (!isNaN(nx) && !isNaN(ny)) {{ x = nx; y = ny; }}
                if (x < y) return asc ? -1 : 1;
                if (x > y) return asc ? 1 : -1;
                return 0;
            }});
            rows.forEach(r => tbody.appendChild(r));
            table.setAttribute('data-sort-col', colIndex);
            table.setAttribute('data-sort-dir', asc ? 'asc' : 'desc');
        }}
        </script>
"""

    # -- top-level -----------------------------------------------------

    def build_html(self) -> str:
        orig_name = self.meta.get('orig_path', 'original')
        driver_name = self.meta.get('driver_path', 'driver')
        title = f"Audio Tightness: {orig_name} vs {driver_name}"

        nav_items = [
            NavItem("Overview", "overview"),
            NavItem("Timeline", "timeline"),
            NavItem("Waveform", "waveform"),
            NavItem("Onset Table", "onset-table-section",
                    count=len(self.report.matched) + len(self.report.missing) + len(self.report.extra)),
        ]

        html = HTMLComponents.get_document_header(title)
        html += '<div class="container">'
        html += HTMLComponents.create_sidebar("Audio Tightness", nav_items, stats=self._stat_cards())

        html += '<div class="main-content">'
        html += (
            f'<div class="header"><h1>Audio Tightness Report</h1>'
            f'<div class="subtitle">{orig_name} vs {driver_name}</div></div>'
        )
        html += HTMLComponents.create_stat_grid(self._stat_cards())

        html += '<div class="section" id="overview"><h2>Overview</h2>' + self._overview_html() + '</div>'
        html += ('<div class="section" id="timeline"><h2>Alignment Timeline</h2>'
                 + self._timeline_html() + '</div>')
        html += '<div class="section" id="waveform"><h2>Waveform</h2>' + self._waveform_html() + '</div>'
        html += (
            '<div class="section" id="onset-table-section"><h2>Onset Table</h2>'
            + self._onset_table_html() + '</div>'
        )

        html += HTMLComponents.create_footer(SIDM2_VERSION, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html += '</div>'  # main-content
        html += '</div>'  # container
        html += HTMLComponents.get_document_footer()
        return html

    def export(self, output_path) -> bool:
        html = self.build_html()
        Path(output_path).write_text(html, encoding='utf-8')
        return True
