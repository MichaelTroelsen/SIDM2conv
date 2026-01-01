#!/usr/bin/env python3
"""
SIDwinder HTML Trace Exporter

Generates interactive HTML visualizations from SIDwinder trace data.
Provides frame-by-frame register write analysis with timeline navigation.

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
from sidtracer import SIDTracer, TraceData
from sidm2.cpu6502_emulator import SIDRegisterWrite


class SIDwinderHTMLExporter:
    """Export SIDwinder trace data to interactive HTML"""

    # SID register names and descriptions
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
        0x19: ("Paddle X (Unused)", "other"),
        0x1A: ("Paddle Y (Unused)", "other"),
        0x1B: ("Voice 3: Oscillator Output", "other"),
        0x1C: ("Voice 3: Envelope Output", "other"),
    }

    def __init__(self, trace_data: TraceData, sid_name: str = "SID Trace"):
        """
        Initialize exporter with trace data

        Args:
            trace_data: Trace data from SIDTracer
            sid_name: Name of SID file (for display)
        """
        self.trace_data = trace_data
        self.sid_name = sid_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def export(self, output_path: str) -> bool:
        """
        Export trace to HTML file

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
            print(f"[ERROR] Failed to export trace HTML: {e}")
            return False

    def _generate_html(self) -> str:
        """Generate complete HTML document"""
        html = HTMLComponents.get_document_header(
            title=f"SIDwinder Trace - {self.sid_name}",
            include_chartjs=False
        )

        html += '<div class="container">'

        # Sidebar
        html += self._create_sidebar()

        # Main content
        html += '<div class="main-content">'
        html += self._create_header()
        html += self._create_stats_grid()
        html += self._create_timeline_section()
        html += self._create_frame_viewer()
        html += self._create_register_state_section()
        html += HTMLComponents.create_footer("3.0.1", self.timestamp)
        html += '</div>'  # main-content

        html += '</div>'  # container

        html += self._add_custom_css()
        html += self._add_custom_javascript()
        html += HTMLComponents.get_document_footer()

        return html

    def _create_sidebar(self) -> str:
        """Create navigation sidebar"""
        nav_items = [
            NavItem("Overview", "overview"),
            NavItem("Timeline", "timeline"),
            NavItem("Frame Viewer", "frames", count=self.trace_data.frames),
            NavItem("Register States", "registers")
        ]

        # Sidebar stats
        total_writes = len(self.trace_data.init_writes) + sum(len(f) for f in self.trace_data.frame_writes)
        avg_writes = sum(len(f) for f in self.trace_data.frame_writes) / max(1, len(self.trace_data.frame_writes))

        sidebar_stats = [
            StatCard("Total Frames", str(self.trace_data.frames), StatCardType.PRIMARY),
            StatCard("Avg Writes/Frame", f"{avg_writes:.1f}", StatCardType.INFO)
        ]

        return HTMLComponents.create_sidebar(
            "Trace",
            nav_items,
            sidebar_stats
        )

    def _create_header(self) -> str:
        """Create trace header"""
        return f'''
        <div id="overview" class="header">
            <h1>SIDwinder Trace Visualization</h1>
            <div class="subtitle">{self.sid_name}</div>
        </div>

        <div class="trace-info-section">
            <h3>Trace Information</h3>
            <table class="info-table">
                <tr>
                    <td><strong>SID Name:</strong></td>
                    <td>{self.trace_data.header.name if self.trace_data.header else 'N/A'}</td>
                </tr>
                <tr>
                    <td><strong>Author:</strong></td>
                    <td>{self.trace_data.header.author if self.trace_data.header else 'N/A'}</td>
                </tr>
                <tr>
                    <td><strong>Total Frames:</strong></td>
                    <td>{self.trace_data.frames}</td>
                </tr>
                <tr>
                    <td><strong>Total Cycles:</strong></td>
                    <td>{self.trace_data.cycles:,}</td>
                </tr>
            </table>
        </div>
        '''

    def _create_stats_grid(self) -> str:
        """Create statistics grid"""
        total_writes = len(self.trace_data.init_writes) + sum(len(f) for f in self.trace_data.frame_writes)
        avg_writes = sum(len(f) for f in self.trace_data.frame_writes) / max(1, len(self.trace_data.frame_writes))
        max_writes = max((len(f) for f in self.trace_data.frame_writes), default=0)
        min_writes = min((len(f) for f in self.trace_data.frame_writes), default=0) if self.trace_data.frame_writes else 0

        cards = [
            StatCard("Total Writes", str(total_writes), StatCardType.PRIMARY),
            StatCard("Init Writes", str(len(self.trace_data.init_writes)), StatCardType.INFO),
            StatCard("Avg/Frame", f"{avg_writes:.1f}", StatCardType.SUCCESS),
            StatCard("Max/Frame", str(max_writes), StatCardType.WARNING),
            StatCard("Min/Frame", str(min_writes), StatCardType.INFO),
            StatCard("Total Cycles", f"{self.trace_data.cycles:,}", StatCardType.PRIMARY)
        ]

        return HTMLComponents.create_stat_grid(cards)

    def _create_timeline_section(self) -> str:
        """Create interactive timeline section"""
        # Calculate write counts per frame for visualization
        write_counts = [len(f) for f in self.trace_data.frame_writes]
        max_count = max(write_counts) if write_counts else 1

        return f'''
        <div id="timeline" class="section">
            <h2>Frame Timeline</h2>
            <p>Use the slider to navigate through frames. Bar height shows register write activity.</p>

            <div class="timeline-container">
                <input type="range" id="frameSlider" min="0" max="{self.trace_data.frames - 1}" value="0" class="frame-slider">
                <div class="frame-indicator">
                    Frame: <span id="currentFrame">0</span> / {self.trace_data.frames - 1}
                </div>
            </div>

            <div class="timeline-bars">
                {self._create_timeline_bars(write_counts, max_count)}
            </div>
        </div>
        '''

    def _create_timeline_bars(self, write_counts: List[int], max_count: int) -> str:
        """Create visual timeline bars"""
        bars_html = ""
        step = max(1, len(write_counts) // 500)  # Limit to ~500 bars for performance

        for i in range(0, len(write_counts), step):
            count = write_counts[i]
            height_pct = (count / max_count * 100) if max_count > 0 else 0
            color = ColorScheme.ACCENT_TEAL if count > 0 else ColorScheme.BG_TERTIARY

            bars_html += f'''
            <div class="timeline-bar" data-frame="{i}" style="height: {height_pct}%; background: {color};"
                 title="Frame {i}: {count} writes"></div>
            '''

        return bars_html

    def _create_frame_viewer(self) -> str:
        """Create frame-by-frame viewer section"""
        return f'''
        <div id="frames" class="section">
            <h2>Frame Viewer</h2>
            <p>Current frame's register writes (navigate using timeline above)</p>

            <div id="frameContent">
                <!-- Frame content will be loaded by JavaScript -->
                <p class="loading">Loading frame data...</p>
            </div>
        </div>
        '''

    def _create_register_state_section(self) -> str:
        """Create register state visualization section"""
        return f'''
        <div id="registers" class="section">
            <h2>Register States</h2>
            <p>Current SID register values</p>

            <div class="register-groups">
                {self._create_register_group("Voice 1", range(0x00, 0x07))}
                {self._create_register_group("Voice 2", range(0x07, 0x0E))}
                {self._create_register_group("Voice 3", range(0x0E, 0x15))}
                {self._create_register_group("Filter", range(0x15, 0x19))}
            </div>

            <div id="registerValues">
                <!-- Register values will be updated by JavaScript -->
            </div>
        </div>
        '''

    def _create_register_group(self, title: str, registers: range) -> str:
        """Create a register group section"""
        rows_html = ""
        for reg in registers:
            name, _ = self.REGISTER_INFO.get(reg, (f"D4{reg:02X}", "other"))
            rows_html += f'''
            <tr id="reg-{reg:02X}">
                <td class="reg-addr">$D4{reg:02X}</td>
                <td class="reg-name">{name}</td>
                <td class="reg-value" id="reg-val-{reg:02X}">$00</td>
            </tr>
            '''

        return f'''
        <div class="register-group">
            <h3>{title}</h3>
            <table class="register-table">
                <thead>
                    <tr>
                        <th>Address</th>
                        <th>Register</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        '''

    def _add_custom_css(self) -> str:
        """Add custom CSS for trace visualization"""
        return f'''
        <style>
            .timeline-container {{
                margin: 20px 0;
                padding: 20px;
                background: {ColorScheme.BG_SECONDARY};
                border-radius: 8px;
            }}

            .frame-slider {{
                width: 100%;
                height: 6px;
                border-radius: 3px;
                background: {ColorScheme.BG_TERTIARY};
                outline: none;
                -webkit-appearance: none;
                appearance: none;
            }}

            .frame-slider::-webkit-slider-thumb {{
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: {ColorScheme.ACCENT_TEAL};
                cursor: pointer;
            }}

            .frame-slider::-moz-range-thumb {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: {ColorScheme.ACCENT_TEAL};
                cursor: pointer;
                border: none;
            }}

            .frame-indicator {{
                margin-top: 10px;
                font-size: 1.2em;
                text-align: center;
                color: {ColorScheme.TEXT_PRIMARY};
            }}

            #currentFrame {{
                color: {ColorScheme.ACCENT_TEAL};
                font-weight: bold;
            }}

            .timeline-bars {{
                display: flex;
                align-items: flex-end;
                height: 100px;
                margin-top: 20px;
                gap: 1px;
                background: {ColorScheme.BG_TERTIARY};
                padding: 5px;
                border-radius: 4px;
            }}

            .timeline-bar {{
                flex: 1;
                min-width: 1px;
                transition: background 0.2s;
                cursor: pointer;
            }}

            .timeline-bar:hover {{
                background: {ColorScheme.ACCENT_BLUE} !important;
            }}

            .register-groups {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}

            .register-group {{
                background: {ColorScheme.BG_SECONDARY};
                padding: 15px;
                border-radius: 8px;
            }}

            .register-group h3 {{
                margin: 0 0 10px 0;
                color: {ColorScheme.ACCENT_TEAL};
            }}

            .register-table {{
                width: 100%;
                border-collapse: collapse;
                font-family: monospace;
            }}

            .register-table th {{
                text-align: left;
                padding: 8px;
                background: {ColorScheme.BG_TERTIARY};
                color: {ColorScheme.TEXT_PRIMARY};
            }}

            .register-table td {{
                padding: 6px 8px;
                border-bottom: 1px solid {ColorScheme.BG_TERTIARY};
            }}

            .reg-addr {{
                color: {ColorScheme.ACCENT_BLUE};
                font-weight: bold;
            }}

            .reg-name {{
                color: {ColorScheme.TEXT_PRIMARY};
            }}

            .reg-value {{
                color: {ColorScheme.ACCENT_TEAL};
                font-weight: bold;
                text-align: right;
            }}

            .reg-changed {{
                background: {ColorScheme.WARNING}44 !important;
                transition: background 0.5s;
            }}

            .frame-writes {{
                margin: 20px 0;
            }}

            .write-item {{
                display: inline-block;
                margin: 4px;
                padding: 6px 12px;
                background: {ColorScheme.BG_SECONDARY};
                border-radius: 4px;
                font-family: monospace;
                transition: transform 0.2s;
            }}

            .write-item:hover {{
                transform: scale(1.05);
                background: {ColorScheme.BG_TERTIARY};
            }}

            .write-voice1 {{ border-left: 3px solid #e74c3c; }}
            .write-voice2 {{ border-left: 3px solid #3498db; }}
            .write-voice3 {{ border-left: 3px solid #2ecc71; }}
            .write-filter {{ border-left: 3px solid #f39c12; }}
            .write-other {{ border-left: 3px solid {ColorScheme.TEXT_SECONDARY}; }}

            .loading {{
                text-align: center;
                padding: 40px;
                color: {ColorScheme.TEXT_SECONDARY};
            }}
        </style>
        '''

    def _add_custom_javascript(self) -> str:
        """Add custom JavaScript for interactivity"""
        # Serialize frame data to JavaScript
        frame_data_js = "const frameData = " + self._serialize_frames_to_js() + ";"

        return f'''
        <script>
            // Frame data
            {frame_data_js}

            // Current register state
            const registerState = new Array(29).fill(0);

            // Initialize on load
            document.addEventListener('DOMContentLoaded', function() {{
                // Frame slider
                const slider = document.getElementById('frameSlider');
                const frameIndicator = document.getElementById('currentFrame');

                slider.addEventListener('input', function() {{
                    const frame = parseInt(this.value);
                    frameIndicator.textContent = frame;
                    loadFrame(frame);
                }});

                // Timeline bar click
                const bars = document.querySelectorAll('.timeline-bar');
                bars.forEach(bar => {{
                    bar.addEventListener('click', function() {{
                        const frame = parseInt(this.dataset.frame);
                        slider.value = frame;
                        frameIndicator.textContent = frame;
                        loadFrame(frame);
                    }});
                }});

                // Load initial frame
                loadFrame(0);
            }});

            function loadFrame(frameNum) {{
                const frameContent = document.getElementById('frameContent');
                const writes = frameData[frameNum] || [];

                if (writes.length === 0) {{
                    frameContent.innerHTML = '<p class="warning">No register writes in this frame</p>';
                    return;
                }}

                // Display frame writes
                let html = '<div class="frame-writes"><h3>Register Writes (' + writes.length + ')</h3>';
                writes.forEach(write => {{
                    const regInfo = getRegisterInfo(write.reg);
                    html += '<div class="write-item write-' + regInfo.type + '" title="' + regInfo.name + '">';
                    html += '$D4' + write.reg.toString(16).toUpperCase().padStart(2, '0');
                    html += ' = $' + write.value.toString(16).toUpperCase().padStart(2, '0');
                    html += '</div>';

                    // Update register state
                    updateRegister(write.reg, write.value);
                }});
                html += '</div>';

                frameContent.innerHTML = html;
            }}

            function updateRegister(reg, value) {{
                registerState[reg] = value;

                // Update display
                const regCell = document.getElementById('reg-val-' + reg.toString(16).toUpperCase().padStart(2, '0'));
                if (regCell) {{
                    regCell.textContent = '$' + value.toString(16).toUpperCase().padStart(2, '0');

                    // Highlight changed register
                    const row = regCell.closest('tr');
                    row.classList.add('reg-changed');
                    setTimeout(() => row.classList.remove('reg-changed'), 500);
                }}
            }}

            function getRegisterInfo(reg) {{
                const registerInfo = {self._get_register_info_js()};
                return registerInfo[reg] || {{ name: 'Unknown', type: 'other' }};
            }}
        </script>
        '''

    def _serialize_frames_to_js(self) -> str:
        """Serialize frame data to JavaScript array"""
        frames_js = "["
        for frame_writes in self.trace_data.frame_writes:
            writes_js = "["
            for write in frame_writes:
                reg_offset = write.address - 0xD400
                writes_js += f'{{"reg":{reg_offset},"value":{write.value}}},'
            writes_js += "],"
            frames_js += writes_js
        frames_js += "]"
        return frames_js

    def _get_register_info_js(self) -> str:
        """Get register info as JavaScript object"""
        info_js = "{"
        for reg, (name, reg_type) in self.REGISTER_INFO.items():
            info_js += f'{reg}:{{"name":"{name}","type":"{reg_type}"}},'
        info_js += "}"
        return info_js


def export_trace_to_html(trace_data: TraceData, output_path: str, sid_name: str = "SID Trace") -> bool:
    """
    Export trace data to interactive HTML (convenience function)

    Args:
        trace_data: Trace data from SIDTracer
        output_path: Path to save HTML file
        sid_name: Name of SID file

    Returns:
        True if successful
    """
    exporter = SIDwinderHTMLExporter(trace_data, sid_name)
    return exporter.export(output_path)


# Demo usage
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Export SIDwinder trace to interactive HTML")
    parser.add_argument('sid_file', help="Input SID file")
    parser.add_argument('-o', '--output', default=None, help="Output HTML file (default: <input>.html)")
    parser.add_argument('-f', '--frames', type=int, default=300, help="Number of frames to trace (default: 300)")
    args = parser.parse_args()

    sid_path = Path(args.sid_file)
    if not sid_path.exists():
        print(f"[ERROR] SID file not found: {sid_path}")
        sys.exit(1)

    output_path = args.output or str(sid_path.with_suffix('.html'))

    print(f"Generating SIDwinder HTML trace...")
    print(f"Input:  {sid_path}")
    print(f"Output: {output_path}")
    print(f"Frames: {args.frames}")
    print()

    # Create tracer
    tracer = SIDTracer(sid_path, verbose=0)
    print(f"SID: {tracer.header.name}")
    print()

    # Generate trace
    print(f"Tracing {args.frames} frames...")
    trace_data = tracer.trace(frames=args.frames)

    # Export to HTML
    print(f"Exporting to HTML...")
    success = export_trace_to_html(trace_data, output_path, tracer.header.name)

    if success:
        file_size = Path(output_path).stat().st_size
        print()
        print(f"[OK] HTML trace generated: {output_path}")
        print(f"     Size: {file_size:,} bytes")
        print()
        print("Open in browser to view interactive trace!")
    else:
        print()
        print("[ERROR] Failed to export HTML trace")
        sys.exit(1)
