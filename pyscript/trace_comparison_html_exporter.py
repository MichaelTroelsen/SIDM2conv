#!/usr/bin/env python3
"""
Trace Comparison HTML Exporter

Generates interactive tabbed HTML comparison of two SID execution traces.
Shows File A, File B, and Differences in separate tabs with metrics sidebar.

Version: 1.0.0
Date: 2026-01-01
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import sys

# Add pyscript to path
sys.path.insert(0, str(Path(__file__).parent))

from html_components import (
    HTMLComponents, StatCard, NavItem, StatCardType, ColorScheme
)
from sidtracer import TraceData, SIDRegisterWrite
from trace_comparator import TraceComparisonMetrics


class TraceComparisonHTMLExporter:
    """Export trace comparison to interactive tabbed HTML"""

    # SID register info (reuse from SIDwinder)
    REGISTER_INFO = {
        0x00: ("Voice 1: Frequency Lo", "voice1"),
        0x01: ("Voice 1: Frequency Hi", "voice1"),
        0x02: ("Voice 1: Pulse Width Lo", "voice1"),
        0x03: ("Voice 1: Pulse Width Hi", "voice1"),
        0x04: ("Voice 1: Control Register", "voice1"),
        0x05: ("Voice 1: Attack/Decay", "voice1"),
        0x06: ("Voice 1: Sustain/Release", "voice1"),
        0x07: ("Voice 2: Frequency Lo", "voice2"),
        0x08: ("Voice 2: Frequency Hi", "voice2"),
        0x09: ("Voice 2: Pulse Width Lo", "voice2"),
        0x0A: ("Voice 2: Pulse Width Hi", "voice2"),
        0x0B: ("Voice 2: Control Register", "voice2"),
        0x0C: ("Voice 2: Attack/Decay", "voice2"),
        0x0D: ("Voice 2: Sustain/Release", "voice2"),
        0x0E: ("Voice 3: Frequency Lo", "voice3"),
        0x0F: ("Voice 3: Frequency Hi", "voice3"),
        0x10: ("Voice 3: Pulse Width Lo", "voice3"),
        0x11: ("Voice 3: Pulse Width Hi", "voice3"),
        0x12: ("Voice 3: Control Register", "voice3"),
        0x13: ("Voice 3: Attack/Decay", "voice3"),
        0x14: ("Voice 3: Sustain/Release", "voice3"),
        0x15: ("Filter: Cutoff Frequency Lo", "filter"),
        0x16: ("Filter: Cutoff Frequency Hi", "filter"),
        0x17: ("Filter: Resonance/Routing", "filter"),
        0x18: ("Filter: Mode/Volume", "filter"),
    }

    def __init__(self,
                 trace_a: TraceData,
                 trace_b: TraceData,
                 comparison: TraceComparisonMetrics,
                 filename_a: str,
                 filename_b: str):
        """
        Initialize exporter with comparison data.

        Args:
            trace_a: First trace data
            trace_b: Second trace data
            comparison: Comparison metrics
            filename_a: Name of first SID file
            filename_b: Name of second SID file
        """
        self.trace_a = trace_a
        self.trace_b = trace_b
        self.comparison = comparison
        self.filename_a = filename_a
        self.filename_b = filename_b
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def export(self, output_path: str) -> bool:
        """
        Export comparison to HTML file.

        Args:
            output_path: Path to save HTML file

        Returns:
            True if successful
        """
        try:
            html = self._generate_html()
            Path(output_path).write_text(html, encoding='utf-8')
            return True
        except Exception as e:
            print(f"[ERROR] Failed to export comparison HTML: {e}")
            return False

    def _generate_html(self) -> str:
        """Generate complete HTML document"""
        html = HTMLComponents.get_document_header(
            title=f"Trace Comparison - {self.filename_a} vs {self.filename_b}",
            include_chartjs=False
        )

        html += '<div class="container">'

        # Sidebar with metrics (visible in all tabs)
        html += self._create_sidebar()

        # Main content
        html += '<div class="main-content">'
        html += self._create_header()
        html += self._create_tabbed_interface()
        html += HTMLComponents.create_footer("3.0.2", self.timestamp)
        html += '</div>'  # main-content

        html += '</div>'  # container

        html += self._add_custom_css()
        html += self._add_custom_javascript()
        html += HTMLComponents.get_document_footer()

        return html

    def _create_sidebar(self) -> str:
        """Create sidebar with comparison metrics"""
        # Create stat cards for 4 key metrics
        stats = [
            StatCard(
                "Frame Match",
                f"{self.comparison.frame_match_percent:.1f}%",
                StatCardType.SUCCESS if self.comparison.frame_match_percent >= 90 else StatCardType.WARNING
            ),
            StatCard(
                "Register Acc.",
                f"{self.comparison.register_accuracy_overall:.1f}%",
                StatCardType.SUCCESS if self.comparison.register_accuracy_overall >= 90 else StatCardType.INFO
            ),
            StatCard(
                "Voice 1/2/3",
                f"{self.comparison.voice_accuracy[1]['overall']:.0f}/"
                f"{self.comparison.voice_accuracy[2]['overall']:.0f}/"
                f"{self.comparison.voice_accuracy[3]['overall']:.0f}%",
                StatCardType.INFO
            ),
            StatCard(
                "Total Diffs",
                str(self.comparison.total_diff_count),
                StatCardType.ERROR if self.comparison.total_diff_count > 100 else StatCardType.WARNING
            )
        ]

        # Navigation items (tabs)
        nav_items = [
            NavItem("File A", "file-a"),
            NavItem("File B", "file-b"),
            NavItem("Differences", "diffs", count=self.comparison.total_diff_count)
        ]

        return HTMLComponents.create_sidebar(
            "Comparison",
            nav_items,
            stats
        )

    def _create_header(self) -> str:
        """Create comparison header"""
        return f'''
        <div class="header">
            <h1>SID Trace Comparison</h1>
            <div class="comparison-files">
                <div class="file-label">
                    <span class="file-tag file-a-tag">A</span>
                    <span class="file-name">{self.filename_a}</span>
                </div>
                <div class="vs">vs</div>
                <div class="file-label">
                    <span class="file-tag file-b-tag">B</span>
                    <span class="file-name">{self.filename_b}</span>
                </div>
            </div>
            <div class="trace-info">
                <span>Frames: A={self.trace_a.frames}, B={self.trace_b.frames}</span>
                <span class="separator">|</span>
                <span>Cycles: A={self.trace_a.cycles:,}, B={self.trace_b.cycles:,}</span>
            </div>
        </div>
        '''

    def _create_tabbed_interface(self) -> str:
        """Create tabbed interface with File A, File B, Differences"""
        html = '<div class="tabs-container">'

        # Tab buttons
        html += '''
        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('file-a')" data-tab="file-a">
                <span class="tab-icon">📄</span> File A
            </button>
            <button class="tab-btn" onclick="switchTab('file-b')" data-tab="file-b">
                <span class="tab-icon">📄</span> File B
            </button>
            <button class="tab-btn" onclick="switchTab('diffs')" data-tab="diffs">
                <span class="tab-icon">⚡</span> Differences
            </button>
        </div>
        '''

        # Tab content sections
        html += self._create_file_a_tab()
        html += self._create_file_b_tab()
        html += self._create_differences_tab()

        html += '</div>'  # tabs-container
        return html

    def _create_file_a_tab(self) -> str:
        """Create File A tab content"""
        return f'''
        <div id="file-a" class="tab-content active">
            <h2><span class="file-tag file-a-tag">A</span> {self.filename_a}</h2>
            {self._create_trace_sections(self.trace_a, 'a')}
        </div>
        '''

    def _create_file_b_tab(self) -> str:
        """Create File B tab content"""
        return f'''
        <div id="file-b" class="tab-content">
            <h2><span class="file-tag file-b-tag">B</span> {self.filename_b}</h2>
            {self._create_trace_sections(self.trace_b, 'b')}
        </div>
        '''

    def _create_differences_tab(self) -> str:
        """Create Differences tab content"""
        html = '''
        <div id="diffs" class="tab-content">
            <h2><span class="file-tag diff-tag">Δ</span> Differences</h2>
        '''

        # Init differences
        init_diffs = [d for d in self.comparison.register_diffs if d.frame == -1]
        html += f'''
        <div class="section">
            <h3>Initialization Phase</h3>
            <p class="diff-summary">
                {len(init_diffs)} difference(s) found during init
            </p>
        '''

        if init_diffs:
            html += '<table class="diff-table"><thead><tr>'
            html += '<th>Register</th><th>File A</th><th>File B</th><th>Delta</th>'
            html += '</tr></thead><tbody>'

            for diff in init_diffs[:50]:  # Limit to 50 for performance
                delta = diff.exported_value - diff.original_value
                html += f'''
                <tr class="diff-row">
                    <td>${diff.register:02X} - {diff.register_name}</td>
                    <td class="file-a-value">${diff.original_value:02X}</td>
                    <td class="file-b-value">${diff.exported_value:02X}</td>
                    <td class="delta">{delta:+d}</td>
                </tr>
                '''

            html += '</tbody></table>'

        html += '</div>'  # section

        # Frame differences with timeline
        html += self._create_diff_timeline()

        html += '</div>'  # tab-content
        return html

    def _create_trace_sections(self, trace: TraceData, file_id: str) -> str:
        """
        Create timeline and register sections for a trace.

        Args:
            trace: TraceData object
            file_id: 'a' or 'b' (for element IDs)

        Returns:
            HTML string
        """
        html = ''

        # Init section (collapsible)
        html += f'''
        <div class="section">
            <h3>Initialization ({len(trace.init_writes)} writes)</h3>
            <details>
                <summary>Show init writes</summary>
                <div class="init-writes">
        '''

        for write in trace.init_writes[:100]:  # Limit display
            reg_offset = write.address - 0xD400
            reg_info = self.REGISTER_INFO.get(reg_offset, (f"Reg ${reg_offset:02X}", "other"))
            html += f'<div class="write-item">${write.address:04X}: ${write.value:02X} ({reg_info[0]})</div>'

        html += '''
                </div>
            </details>
        </div>
        '''

        # Frame timeline
        html += f'''
        <div class="section" id="timeline-{file_id}">
            <h3>Frame Timeline</h3>
            <div class="timeline-controls">
                <label>Frame <span id="current-frame-{file_id}">0</span> / {trace.frames - 1}</label>
                <input type="range" id="frame-slider-{file_id}"
                       class="frame-slider" min="0" max="{max(0, trace.frames - 1)}" value="0"
                       oninput="updateFrame('{file_id}', this.value)">
            </div>
            <div class="timeline-bars" id="timeline-bars-{file_id}">
        '''

        # Create timeline bars
        for frame_idx, frame_writes in enumerate(trace.frame_writes[:500]):  # Limit to 500 bars
            write_count = len(frame_writes)
            height = min(100, (write_count / 10) * 100) if write_count > 0 else 5
            color = ColorScheme.ACCENT_TEAL if write_count > 0 else ColorScheme.BG_TERTIARY

            html += f'''
            <div class="timeline-bar" data-frame="{frame_idx}"
                 style="height: {height}%; background: {color};"
                 onclick="jumpToFrame('{file_id}', {frame_idx})"
                 title="Frame {frame_idx}: {write_count} writes">
            </div>
            '''

        html += '''
            </div>
        </div>
        '''

        # Frame viewer
        html += f'''
        <div class="section" id="frame-viewer-{file_id}">
            <h3>Frame Viewer</h3>
            <div id="frame-data-{file_id}" class="frame-data">
                <p class="hint">Use slider above to navigate frames</p>
            </div>
        </div>
        '''

        # Register states
        html += f'''
        <div class="section" id="register-states-{file_id}">
            <h3>Register States</h3>
            <div id="register-table-{file_id}" class="register-table-container">
                {self._create_register_state_table(file_id)}
            </div>
        </div>
        '''

        return html

    def _create_diff_timeline(self) -> str:
        """Create timeline showing frame match accuracy"""
        max_frames = min(len(self.comparison.per_frame_accuracy), 500)

        html = '''
        <div class="section">
            <h3>Frame Match Timeline</h3>
            <div class="timeline-controls">
                <label>Frame <span id="current-frame-diff">0</span> / ''' + str(max_frames - 1) + '''</label>
                <input type="range" id="frame-slider-diff"
                       class="frame-slider" min="0" max="''' + str(max(0, max_frames - 1)) + '''" value="0"
                       oninput="updateDiffFrame(this.value)">
            </div>
            <div class="timeline-bars" id="timeline-bars-diff">
        '''

        for frame_idx, accuracy in enumerate(self.comparison.per_frame_accuracy[:max_frames]):
            # Color by accuracy
            if accuracy == 100.0:
                color = ColorScheme.SUCCESS  # Green: Perfect
            elif accuracy >= 90.0:
                color = ColorScheme.SUCCESS_LIGHT  # Light green
            elif accuracy >= 50.0:
                color = ColorScheme.WARNING  # Orange
            else:
                color = ColorScheme.ERROR  # Red

            html += f'''
            <div class="timeline-bar" data-frame="{frame_idx}"
                 style="height: 100%; background: {color};"
                 onclick="jumpToDiffFrame({frame_idx})"
                 title="Frame {frame_idx}: {accuracy:.1f}% match">
            </div>
            '''

        html += '''
            </div>
            <div class="legend">
                <span class="legend-item"><span class="legend-box" style="background:''' + ColorScheme.SUCCESS + '''"></span> 100% Match</span>
                <span class="legend-item"><span class="legend-box" style="background:''' + ColorScheme.SUCCESS_LIGHT + '''"></span> 90-99%</span>
                <span class="legend-item"><span class="legend-box" style="background:''' + ColorScheme.WARNING + '''"></span> 50-89%</span>
                <span class="legend-item"><span class="legend-box" style="background:''' + ColorScheme.ERROR + '''"></span> &lt;50%</span>
            </div>
        </div>
        '''

        # Diff frame viewer
        html += '''
        <div class="section">
            <h3>Frame Diff Viewer</h3>
            <div id="diff-frame-data" class="diff-frame-data">
                <p class="hint">Use slider above to navigate frames</p>
            </div>
        </div>
        '''

        return html

    def _create_register_state_table(self, file_id: str) -> str:
        """Create register state display table"""
        html = '<div class="register-states">'

        # Voice 1
        html += '<div class="register-group voice1"><h4>Voice 1</h4>'
        for reg in range(0x00, 0x07):
            reg_info = self.REGISTER_INFO.get(reg, (f"Reg ${reg:02X}", ""))
            html += f'<div class="register-row" id="reg-{file_id}-{reg:02x}"><span class="reg-addr">${0xD400+reg:04X}</span> <span class="reg-name">{reg_info[0]}</span> <span class="reg-value">--</span></div>'
        html += '</div>'

        # Voice 2
        html += '<div class="register-group voice2"><h4>Voice 2</h4>'
        for reg in range(0x07, 0x0E):
            reg_info = self.REGISTER_INFO.get(reg, (f"Reg ${reg:02X}", ""))
            html += f'<div class="register-row" id="reg-{file_id}-{reg:02x}"><span class="reg-addr">${0xD400+reg:04X}</span> <span class="reg-name">{reg_info[0]}</span> <span class="reg-value">--</span></div>'
        html += '</div>'

        # Voice 3
        html += '<div class="register-group voice3"><h4>Voice 3</h4>'
        for reg in range(0x0E, 0x15):
            reg_info = self.REGISTER_INFO.get(reg, (f"Reg ${reg:02X}", ""))
            html += f'<div class="register-row" id="reg-{file_id}-{reg:02x}"><span class="reg-addr">${0xD400+reg:04X}</span> <span class="reg-name">{reg_info[0]}</span> <span class="reg-value">--</span></div>'
        html += '</div>'

        # Filter
        html += '<div class="register-group filter"><h4>Filter</h4>'
        for reg in range(0x15, 0x19):
            reg_info = self.REGISTER_INFO.get(reg, (f"Reg ${reg:02X}", ""))
            html += f'<div class="register-row" id="reg-{file_id}-{reg:02x}"><span class="reg-addr">${0xD400+reg:04X}</span> <span class="reg-name">{reg_info[0]}</span> <span class="reg-value">--</span></div>'
        html += '</div>'

        html += '</div>'  # register-states
        return html

    def _serialize_traces_to_js(self) -> str:
        """Serialize both traces to JavaScript for client-side interaction"""
        def serialize_trace(trace: TraceData) -> str:
            js = "{"
            js += "init: ["
            for write in trace.init_writes:
                reg_offset = write.address - 0xD400
                js += f'{{"reg":{reg_offset},"value":{write.value}}},'
            js += "],"

            js += "frames: ["
            for frame_writes in trace.frame_writes:
                js += "["
                for write in frame_writes:
                    reg_offset = write.address - 0xD400
                    js += f'{{"reg":{reg_offset},"value":{write.value}}},'
                js += "],"
            js += "]"
            js += "}"
            return js

        trace_a_js = serialize_trace(self.trace_a)
        trace_b_js = serialize_trace(self.trace_b)

        # Per-frame accuracy for diff visualization
        accuracy_js = "[" + ",".join(str(acc) for acc in self.comparison.per_frame_accuracy) + "]"

        return f'''
        const traceA = {trace_a_js};
        const traceB = {trace_b_js};
        const frameAccuracy = {accuracy_js};
        '''

    def _add_custom_css(self) -> str:
        """Add custom CSS for tabbed interface"""
        return f'''
        <style>
        /* Tab system */
        .tabs-container {{
            width: 100%;
        }}

        .tab-buttons {{
            display: flex;
            gap: 5px;
            border-bottom: 2px solid {ColorScheme.BORDER_PRIMARY};
            margin-bottom: 20px;
        }}

        .tab-btn {{
            padding: 12px 24px;
            background: {ColorScheme.BG_TERTIARY};
            border: none;
            border-radius: 5px 5px 0 0;
            color: {ColorScheme.TEXT_PRIMARY};
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .tab-btn:hover {{
            background: {ColorScheme.BG_HOVER};
        }}

        .tab-btn.active {{
            background: {ColorScheme.BG_PRIMARY};
            border-bottom: 3px solid {ColorScheme.ACCENT_TEAL};
            font-weight: 600;
        }}

        .tab-icon {{
            font-size: 16px;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        /* File labels */
        .comparison-files {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
        }}

        .file-label {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .file-tag {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 12px;
        }}

        .file-a-tag {{
            background: {ColorScheme.ACCENT_BLUE};
            color: white;
        }}

        .file-b-tag {{
            background: {ColorScheme.ACCENT_PURPLE};
            color: white;
        }}

        .diff-tag {{
            background: {ColorScheme.WARNING};
            color: {ColorScheme.BG_PRIMARY};
        }}

        .file-name {{
            font-family: monospace;
            color: {ColorScheme.TEXT_PRIMARY};
        }}

        .vs {{
            color: {ColorScheme.TEXT_SECONDARY};
            font-weight: 300;
        }}

        .trace-info {{
            color: {ColorScheme.TEXT_SECONDARY};
            font-size: 13px;
        }}

        .separator {{
            margin: 0 10px;
        }}

        /* Diff highlighting */
        .diff-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .diff-table th {{
            background: {ColorScheme.BG_TERTIARY};
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid {ColorScheme.BORDER_PRIMARY};
        }}

        .diff-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid {ColorScheme.BORDER_SECONDARY};
        }}

        .diff-row {{
            background: rgba(235, 51, 73, 0.15);
        }}

        .file-a-value {{
            color: {ColorScheme.ACCENT_BLUE};
            font-weight: 600;
        }}

        .file-b-value {{
            color: {ColorScheme.ACCENT_PURPLE};
            font-weight: 600;
        }}

        .delta {{
            font-family: monospace;
            color: {ColorScheme.WARNING};
        }}

        .diff-summary {{
            padding: 10px;
            background: {ColorScheme.BG_TERTIARY};
            border-left: 4px solid {ColorScheme.WARNING};
            margin-bottom: 15px;
        }}

        /* Timeline */
        .timeline-bars {{
            display: flex;
            gap: 1px;
            height: 100px;
            align-items: flex-end;
            background: {ColorScheme.BG_TERTIARY};
            padding: 5px;
            border-radius: 4px;
            overflow-x: auto;
        }}

        .timeline-bar {{
            flex: 1;
            min-width: 2px;
            cursor: pointer;
            transition: opacity 0.2s;
        }}

        .timeline-bar:hover {{
            opacity: 0.7;
        }}

        .timeline-controls {{
            margin-bottom: 10px;
        }}

        .frame-slider {{
            width: 100%;
            margin-top: 5px;
        }}

        /* Legend */
        .legend {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
            font-size: 12px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .legend-box {{
            width: 20px;
            height: 15px;
            border-radius: 2px;
        }}

        /* Register states */
        .register-states {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}

        .register-group {{
            padding: 10px;
            background: {ColorScheme.BG_TERTIARY};
            border-radius: 4px;
        }}

        .register-group h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: {ColorScheme.TEXT_SECONDARY};
        }}

        .register-group.voice1 h4 {{ color: {ColorScheme.ERROR}; }}
        .register-group.voice2 h4 {{ color: {ColorScheme.ACCENT_BLUE}; }}
        .register-group.voice3 h4 {{ color: {ColorScheme.SUCCESS}; }}
        .register-group.filter h4 {{ color: {ColorScheme.WARNING}; }}

        .register-row {{
            display: flex;
            justify-content: space-between;
            padding: 5px;
            font-size: 12px;
            font-family: monospace;
        }}

        .reg-addr {{
            color: {ColorScheme.TEXT_SECONDARY};
        }}

        .reg-name {{
            flex: 1;
            margin: 0 10px;
        }}

        .reg-value {{
            color: {ColorScheme.ACCENT_TEAL};
            font-weight: 600;
        }}

        /* Init writes */
        .init-writes {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 5px;
            margin-top: 10px;
            max-height: 300px;
            overflow-y: auto;
        }}

        .write-item {{
            padding: 5px;
            background: {ColorScheme.BG_TERTIARY};
            font-family: monospace;
            font-size: 12px;
        }}

        details summary {{
            cursor: pointer;
            padding: 10px;
            background: {ColorScheme.BG_TERTIARY};
            border-radius: 4px;
            margin-bottom: 10px;
        }}

        details summary:hover {{
            background: {ColorScheme.BG_HOVER};
        }}

        .hint {{
            color: {ColorScheme.TEXT_SECONDARY};
            font-style: italic;
        }}

        .frame-data {{
            padding: 15px;
            background: {ColorScheme.BG_TERTIARY};
            border-radius: 4px;
            min-height: 100px;
        }}

        .diff-frame-data {{
            padding: 15px;
            background: {ColorScheme.BG_TERTIARY};
            border-radius: 4px;
            min-height: 150px;
        }}

        .section {{
            margin-bottom: 30px;
        }}

        .section h3 {{
            margin-bottom: 15px;
            color: {ColorScheme.ACCENT_TEAL};
        }}
        </style>
        '''

    def _add_custom_javascript(self) -> str:
        """Add custom JavaScript for tab switching and frame navigation"""
        return f'''
        <script>
        {self._serialize_traces_to_js()}

        // Tab switching
        function switchTab(tabId) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});

            // Show selected tab
            document.getElementById(tabId).classList.add('active');

            // Update button states
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});

            document.querySelector(`[data-tab="${{tabId}}"]`).classList.add('active');
        }}

        // Update frame for File A or B
        function updateFrame(fileId, frameNum) {{
            frameNum = parseInt(frameNum);
            document.getElementById(`current-frame-${{fileId}}`).textContent = frameNum;

            const trace = fileId === 'a' ? traceA : traceB;

            if (frameNum >= 0 && frameNum < trace.frames.length) {{
                const frameWrites = trace.frames[frameNum];

                // Update frame data display
                const frameDataEl = document.getElementById(`frame-data-${{fileId}}`);
                if (frameWrites.length === 0) {{
                    frameDataEl.innerHTML = '<p class="hint">No writes in this frame</p>';
                }} else {{
                    let html = `<p><strong>${{frameWrites.length}} register writes:</strong></p>`;
                    html += '<div class="init-writes">';
                    frameWrites.forEach(write => {{
                        const addr = 0xD400 + write.reg;
                        html += `<div class="write-item">$${{addr.toString(16).toUpperCase().padStart(4, '0')}}: $${{write.value.toString(16).toUpperCase().padStart(2, '0')}}</div>`;
                    }});
                    html += '</div>';
                    frameDataEl.innerHTML = html;
                }}

                // Update register states
                updateRegisterStates(fileId, frameWrites);
            }}
        }}

        // Update diff frame
        function updateDiffFrame(frameNum) {{
            frameNum = parseInt(frameNum);
            document.getElementById('current-frame-diff').textContent = frameNum;

            if (frameNum >= 0 && frameNum < traceA.frames.length && frameNum < traceB.frames.length) {{
                const writesA = traceA.frames[frameNum];
                const writesB = traceB.frames[frameNum];

                // Build register maps
                const regsA = {{}};
                writesA.forEach(w => regsA[w.reg] = w.value);

                const regsB = {{}};
                writesB.forEach(w => regsB[w.reg] = w.value);

                // Find all registers
                const allRegs = new Set([...Object.keys(regsA).map(Number), ...Object.keys(regsB).map(Number)]);

                // Build diff display
                const diffEl = document.getElementById('diff-frame-data');
                const accuracy = frameAccuracy[frameNum] || 0;

                let html = `<p><strong>Frame ${{frameNum}} Match: ${{accuracy.toFixed(1)}}%</strong></p>`;

                const diffs = [];
                allRegs.forEach(reg => {{
                    const valA = regsA[reg] !== undefined ? regsA[reg] : null;
                    const valB = regsB[reg] !== undefined ? regsB[reg] : null;

                    if (valA !== valB) {{
                        diffs.push({{reg, valA, valB}});
                    }}
                }});

                if (diffs.length === 0) {{
                    html += '<p class="hint">Perfect match - no differences</p>';
                }} else {{
                    html += `<p>${{diffs.length}} difference(s):</p>`;
                    html += '<table class="diff-table"><thead><tr><th>Register</th><th>File A</th><th>File B</th></tr></thead><tbody>';

                    diffs.forEach(diff => {{
                        const addr = 0xD400 + diff.reg;
                        const valAStr = diff.valA !== null ? `$${{diff.valA.toString(16).toUpperCase().padStart(2, '0')}}` : '--';
                        const valBStr = diff.valB !== null ? `$${{diff.valB.toString(16).toUpperCase().padStart(2, '0')}}` : '--';

                        html += `<tr class="diff-row">`;
                        html += `<td>$${{addr.toString(16).toUpperCase().padStart(4, '0')}}</td>`;
                        html += `<td class="file-a-value">${{valAStr}}</td>`;
                        html += `<td class="file-b-value">${{valBStr}}</td>`;
                        html += `</tr>`;
                    }});

                    html += '</tbody></table>';
                }}

                diffEl.innerHTML = html;
            }}
        }}

        // Update register states table
        function updateRegisterStates(fileId, frameWrites) {{
            // Reset all to --
            for (let reg = 0; reg < 0x19; reg++) {{
                const el = document.getElementById(`reg-${{fileId}}-${{reg.toString(16).padStart(2, '0')}}`);
                if (el) {{
                    const valueEl = el.querySelector('.reg-value');
                    if (valueEl) valueEl.textContent = '--';
                }}
            }}

            // Update with frame values
            frameWrites.forEach(write => {{
                const el = document.getElementById(`reg-${{fileId}}-${{write.reg.toString(16).padStart(2, '0')}}`);
                if (el) {{
                    const valueEl = el.querySelector('.reg-value');
                    if (valueEl) {{
                        valueEl.textContent = `$${{write.value.toString(16).toUpperCase().padStart(2, '0')}}`;
                    }}
                }}
            }});
        }}

        // Jump to frame by clicking timeline bar
        function jumpToFrame(fileId, frameNum) {{
            document.getElementById(`frame-slider-${{fileId}}`).value = frameNum;
            updateFrame(fileId, frameNum);
        }}

        // Jump to diff frame
        function jumpToDiffFrame(frameNum) {{
            document.getElementById('frame-slider-diff').value = frameNum;
            updateDiffFrame(frameNum);
        }}

        // Initialize first frame
        window.addEventListener('DOMContentLoaded', () => {{
            updateFrame('a', 0);
            updateFrame('b', 0);
            updateDiffFrame(0);
        }});
        </script>
        '''


def export_comparison_to_html(trace_a: TraceData,
                               trace_b: TraceData,
                               comparison: TraceComparisonMetrics,
                               filename_a: str,
                               filename_b: str,
                               output_path: str) -> bool:
    """
    Convenience function to export trace comparison to HTML.

    Args:
        trace_a: First trace
        trace_b: Second trace
        comparison: Comparison metrics
        filename_a: Name of first SID file
        filename_b: Name of second SID file
        output_path: Output HTML path

    Returns:
        True if successful
    """
    exporter = TraceComparisonHTMLExporter(trace_a, trace_b, comparison, filename_a, filename_b)
    return exporter.export(output_path)


def main():
    """Test the exporter"""
    print("TraceComparisonHTMLExporter module loaded successfully")


if __name__ == '__main__':
    main()
