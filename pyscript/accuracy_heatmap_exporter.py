#!/usr/bin/env python3
"""
Accuracy Heatmap HTML Exporter - Generate interactive Canvas-based heatmap

Exports heatmap data to standalone HTML with Canvas-based visualization.
Supports 4 visualization modes, interactive tooltips, zoom, and pan.

Usage:
    from accuracy_heatmap_exporter import AccuracyHeatmapExporter

    exporter = AccuracyHeatmapExporter(heatmap_data)
    exporter.export("heatmap.html")

Version: 1.0.0
Date: 2026-01-01
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.accuracy_heatmap_generator import HeatmapData, REGISTER_NAMES
from pyscript.html_components import HTMLComponents, ColorScheme, StatCard, StatCardType


class AccuracyHeatmapExporter:
    """Export heatmap data to interactive Canvas-based HTML."""

    def __init__(self, heatmap_data: HeatmapData):
        """
        Initialize exporter with heatmap data.

        Args:
            heatmap_data: Complete heatmap data structure
        """
        self.data = heatmap_data

    def export(self, output_path: str) -> bool:
        """
        Generate and save HTML file.

        Args:
            output_path: Path to save HTML file

        Returns:
            True if successful, False otherwise
        """
        try:
            html = self._generate_html()

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            return True

        except Exception as e:
            print(f"[ERROR] Failed to export HTML: {e}")
            return False

    def _generate_html(self) -> str:
        """
        Build complete HTML document.

        Returns:
            Complete HTML string
        """
        html_parts = []

        # Header
        html_parts.append(HTMLComponents.get_document_header(
            title=f"Accuracy Heatmap - {self.data.filename_a} vs {self.data.filename_b}",
            include_chartjs=False
        ))

        # Add custom CSS for heatmap
        html_parts.append(self._create_custom_css())

        # Container with sidebar + heatmap
        html_parts.append('<div class="container">')

        # Sidebar with stats and controls
        html_parts.append(self._create_sidebar())

        # Main heatmap area
        html_parts.append(self._create_canvas_section())

        html_parts.append('</div>')  # End container

        # Embed heatmap data as JavaScript
        html_parts.append('<script>')
        html_parts.append(self._serialize_heatmap_data_to_js())
        html_parts.append(self._add_canvas_rendering_js())
        html_parts.append('</script>')

        # Footer
        html_parts.append(HTMLComponents.get_document_footer())

        return ''.join(html_parts)

    def _create_custom_css(self) -> str:
        """Create custom CSS for heatmap layout."""
        return f"""
<style>
/* Heatmap Layout */
.container {{
    display: flex;
    height: 100vh;
    overflow: hidden;
}}

.sidebar {{
    width: 320px;
    background: {ColorScheme.BG_SECONDARY};
    border-right: 1px solid {ColorScheme.BORDER_PRIMARY};
    padding: 20px;
    overflow-y: auto;
    flex-shrink: 0;
}}

.heatmap-main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}

.heatmap-header {{
    background: {ColorScheme.BG_SECONDARY};
    border-bottom: 1px solid {ColorScheme.BORDER_PRIMARY};
    padding: 15px 20px;
    flex-shrink: 0;
}}

.heatmap-header h2 {{
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 500;
    margin: 0;
}}

.heatmap-canvas-wrapper {{
    flex: 1;
    overflow: auto;
    position: relative;
    background: {ColorScheme.BG_PRIMARY};
}}

.heatmap-canvas {{
    display: block;
    cursor: crosshair;
}}

/* Tooltip */
.heatmap-tooltip {{
    position: fixed;
    background: {ColorScheme.BG_TERTIARY};
    border: 1px solid {ColorScheme.BORDER_PRIMARY};
    border-radius: 4px;
    padding: 10px;
    font-size: 12px;
    color: {ColorScheme.TEXT_PRIMARY};
    pointer-events: none;
    z-index: 1000;
    display: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    max-width: 300px;
}}

.heatmap-tooltip strong {{
    display: block;
    margin-bottom: 5px;
    color: {ColorScheme.ACCENT_TEAL};
}}

/* Controls */
.control-group {{
    margin-bottom: 25px;
}}

.control-group h3 {{
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 10px;
}}

.mode-selector {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}

.mode-option {{
    display: flex;
    align-items: center;
    padding: 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
}}

.mode-option:hover {{
    background: {ColorScheme.BG_HOVER};
}}

.mode-option input[type="radio"] {{
    margin-right: 8px;
    cursor: pointer;
}}

.mode-option label {{
    cursor: pointer;
    flex: 1;
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 13px;
}}

.mode-option.active {{
    background: {ColorScheme.BG_TERTIARY};
    border-left: 3px solid {ColorScheme.ACCENT_TEAL};
}}

/* Legend */
.legend {{
    margin-top: 20px;
    padding: 15px;
    background: {ColorScheme.BG_TERTIARY};
    border-radius: 4px;
}}

.legend h4 {{
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 13px;
    margin-bottom: 10px;
}}

.legend-items {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: {ColorScheme.TEXT_SECONDARY};
}}

.legend-color {{
    width: 20px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid {ColorScheme.BORDER_PRIMARY};
}}

/* Zoom Controls */
.zoom-controls {{
    display: flex;
    gap: 8px;
    margin-top: 15px;
}}

.zoom-btn {{
    padding: 6px 12px;
    background: {ColorScheme.BG_TERTIARY};
    border: 1px solid {ColorScheme.BORDER_PRIMARY};
    border-radius: 4px;
    color: {ColorScheme.TEXT_PRIMARY};
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
}}

.zoom-btn:hover {{
    background: {ColorScheme.BG_HOVER};
    border-color: {ColorScheme.ACCENT_TEAL};
}}

/* Stats Section */
.stats-section {{
    margin-bottom: 25px;
}}

.stat-card {{
    background: {ColorScheme.BG_TERTIARY};
    border-radius: 4px;
    padding: 12px;
    margin-bottom: 10px;
}}

.stat-label {{
    font-size: 11px;
    color: {ColorScheme.TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}}

.stat-value {{
    font-size: 24px;
    font-weight: 600;
    color: {ColorScheme.TEXT_PRIMARY};
}}

.stat-value.success {{
    color: {ColorScheme.SUCCESS};
}}

.stat-value.warning {{
    color: {ColorScheme.WARNING};
}}

.stat-value.error {{
    color: {ColorScheme.ERROR};
}}
</style>
"""

    def _create_sidebar(self) -> str:
        """Create sidebar with stats and controls."""

        # Determine accuracy color class
        accuracy = self.data.overall_accuracy
        if accuracy >= 95.0:
            accuracy_class = "success"
        elif accuracy >= 70.0:
            accuracy_class = "warning"
        else:
            accuracy_class = "error"

        return f"""
<div class="sidebar">
    <!-- Stats Section -->
    <div class="stats-section">
        <div class="stat-card">
            <div class="stat-label">Overall Accuracy</div>
            <div class="stat-value {accuracy_class}">{accuracy:.2f}%</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Matches / Total</div>
            <div class="stat-value">{self.data.total_matches:,} / {self.data.total_comparisons:,}</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Dimensions</div>
            <div class="stat-value">{self.data.frames} × {self.data.registers}</div>
        </div>
    </div>

    <!-- Mode Selector -->
    <div class="control-group">
        <h3>Visualization Mode</h3>
        <div class="mode-selector">
            <div class="mode-option active" onclick="switchMode(1)" id="mode-option-1">
                <input type="radio" name="mode" id="mode-1" value="1" checked>
                <label for="mode-1">Binary Match/Mismatch</label>
            </div>
            <div class="mode-option" onclick="switchMode(2)" id="mode-option-2">
                <input type="radio" name="mode" id="mode-2" value="2">
                <label for="mode-2">Value Delta Magnitude</label>
            </div>
            <div class="mode-option" onclick="switchMode(3)" id="mode-option-3">
                <input type="radio" name="mode" id="mode-3" value="3">
                <label for="mode-3">Register Group Highlighting</label>
            </div>
            <div class="mode-option" onclick="switchMode(4)" id="mode-option-4">
                <input type="radio" name="mode" id="mode-4" value="4">
                <label for="mode-4">Frame Accuracy Summary</label>
            </div>
        </div>
    </div>

    <!-- Zoom Controls -->
    <div class="control-group">
        <h3>Zoom</h3>
        <div class="zoom-controls">
            <button class="zoom-btn" onclick="zoomIn()">Zoom In (+)</button>
            <button class="zoom-btn" onclick="zoomOut()">Zoom Out (-)</button>
            <button class="zoom-btn" onclick="resetZoom()">Reset</button>
        </div>
    </div>

    <!-- Legend -->
    <div class="legend" id="legend">
        <h4>Legend</h4>
        <div class="legend-items" id="legend-items">
            <!-- Dynamic legend content based on mode -->
        </div>
    </div>

    <!-- File Info -->
    <div class="control-group" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid {ColorScheme.BORDER_PRIMARY};">
        <h3>Files</h3>
        <div style="font-size: 12px; color: {ColorScheme.TEXT_SECONDARY}; line-height: 1.6;">
            <div style="margin-bottom: 8px;">
                <strong style="color: {ColorScheme.ACCENT_TEAL};">File A:</strong><br>
                {self.data.filename_a}
            </div>
            <div>
                <strong style="color: {ColorScheme.ACCENT_BLUE};">File B:</strong><br>
                {self.data.filename_b}
            </div>
        </div>
    </div>
</div>
"""

    def _create_canvas_section(self) -> str:
        """Create main canvas area."""
        return f"""
<div class="heatmap-main">
    <div class="heatmap-header">
        <h2>Accuracy Heatmap - Frame-by-Frame Register Comparison</h2>
    </div>

    <div class="heatmap-canvas-wrapper" id="canvas-wrapper">
        <canvas id="heatmap-canvas" class="heatmap-canvas"></canvas>
    </div>

    <div class="heatmap-tooltip" id="tooltip"></div>
</div>
"""

    def _serialize_heatmap_data_to_js(self) -> str:
        """Serialize heatmap data to JavaScript."""

        # Convert Python lists to JSON
        match_grid_json = json.dumps(self.data.match_grid)
        value_grid_a_json = json.dumps(self.data.value_grid_a)
        value_grid_b_json = json.dumps(self.data.value_grid_b)
        delta_grid_json = json.dumps(self.data.delta_grid)
        frame_accuracy_json = json.dumps(self.data.frame_accuracy)
        register_accuracy_json = json.dumps(self.data.register_accuracy)
        register_names_json = json.dumps(REGISTER_NAMES)

        return f"""
// Heatmap data
const heatmapData = {{
    frames: {self.data.frames},
    registers: {self.data.registers},
    matchGrid: {match_grid_json},
    valueGridA: {value_grid_a_json},
    valueGridB: {value_grid_b_json},
    deltaGrid: {delta_grid_json},
    frameAccuracy: {frame_accuracy_json},
    registerAccuracy: {register_accuracy_json},
    filenameA: "{self.data.filename_a}",
    filenameB: "{self.data.filename_b}",
    totalComparisons: {self.data.total_comparisons},
    totalMatches: {self.data.total_matches},
    overallAccuracy: {self.data.overall_accuracy:.2f}
}};

const REGISTER_NAMES = {register_names_json};
"""

    def _add_canvas_rendering_js(self) -> str:
        """Add JavaScript for Canvas rendering and interactivity."""
        return f"""
// Heatmap configuration
const config = {{
    cellWidth: 4,           // pixels per frame
    cellHeight: 20,         // pixels per register
    margin: {{ top: 50, right: 20, bottom: 50, left: 150 }},
    colors: {{
        match: '{ColorScheme.SUCCESS}',
        mismatch: '{ColorScheme.ERROR}',
        deltaMin: '{ColorScheme.SUCCESS_LIGHT}',
        deltaMax: '{ColorScheme.ERROR}',
        voice1: '{ColorScheme.ERROR}',
        voice2: '{ColorScheme.ACCENT_BLUE}',
        voice3: '{ColorScheme.SUCCESS}',
        filter: '{ColorScheme.WARNING}',
        bgPrimary: '{ColorScheme.BG_PRIMARY}',
        textPrimary: '{ColorScheme.TEXT_PRIMARY}',
        textSecondary: '{ColorScheme.TEXT_SECONDARY}',
        border: '{ColorScheme.BORDER_PRIMARY}'
    }},
    minCellWidth: 1,
    maxCellWidth: 20,
    minCellHeight: 10,
    maxCellHeight: 40
}};

// State
let currentMode = 1;
let zoomLevel = 1.0;

// Canvas reference
let canvas = null;
let ctx = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {{
    canvas = document.getElementById('heatmap-canvas');
    ctx = canvas.getContext('2d');

    // Initial render
    drawHeatmap(currentMode);
    updateLegend(currentMode);

    // Set up event listeners
    setupEventListeners();
}});

// Draw complete heatmap
function drawHeatmap(mode) {{
    if (!canvas || !ctx) return;

    const cellW = config.cellWidth * zoomLevel;
    const cellH = config.cellHeight * zoomLevel;

    // Calculate canvas size
    const canvasWidth = config.margin.left + (heatmapData.frames * cellW) + config.margin.right;
    const canvasHeight = config.margin.top + (heatmapData.registers * cellH) + config.margin.bottom;

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    // Clear canvas
    ctx.fillStyle = config.colors.bgPrimary;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw cells
    for (let frame = 0; frame < heatmapData.frames; frame++) {{
        for (let reg = 0; reg < heatmapData.registers; reg++) {{
            const x = config.margin.left + (frame * cellW);
            const y = config.margin.top + (reg * cellH);

            const color = getCellColor(frame, reg, mode);

            ctx.fillStyle = color;
            ctx.fillRect(x, y, cellW, cellH);
        }}
    }}

    // Draw axis labels
    drawAxisLabels(cellW, cellH);
}}

// Get cell color based on mode
function getCellColor(frame, reg, mode) {{
    switch(mode) {{
        case 1:  // Binary match/mismatch
            return heatmapData.matchGrid[frame][reg] ? config.colors.match : config.colors.mismatch;

        case 2:  // Value delta magnitude
            const delta = heatmapData.deltaGrid[frame][reg];
            return interpolateColor(config.colors.deltaMin, config.colors.deltaMax, delta / 255);

        case 3:  // Register group highlighting
            const group = getRegisterGroup(reg);
            const isMatch = heatmapData.matchGrid[frame][reg];
            const baseColor = config.colors[group];
            return isMatch ? baseColor : darkenColor(baseColor, 0.4);

        case 4:  // Frame accuracy
            const accuracy = heatmapData.frameAccuracy[frame];
            return interpolateColor(config.colors.mismatch, config.colors.match, accuracy / 100);
    }}
}}

// Get register group (voice1, voice2, voice3, filter)
function getRegisterGroup(reg) {{
    if (reg >= 0 && reg <= 6) return 'voice1';
    if (reg >= 7 && reg <= 13) return 'voice2';
    if (reg >= 14 && reg <= 20) return 'voice3';
    return 'filter';
}}

// Interpolate between two colors
function interpolateColor(color1, color2, factor) {{
    const c1 = hexToRgb(color1);
    const c2 = hexToRgb(color2);

    const r = Math.round(c1.r + factor * (c2.r - c1.r));
    const g = Math.round(c1.g + factor * (c2.g - c1.g));
    const b = Math.round(c1.b + factor * (c2.b - c1.b));

    return `rgb(${{r}}, ${{g}}, ${{b}})`;
}}

// Darken color
function darkenColor(color, factor) {{
    const rgb = hexToRgb(color);
    const r = Math.round(rgb.r * (1 - factor));
    const g = Math.round(rgb.g * (1 - factor));
    const b = Math.round(rgb.b * (1 - factor));
    return `rgb(${{r}}, ${{g}}, ${{b}})`;
}}

// Convert hex to RGB
function hexToRgb(hex) {{
    const result = /^#?([a-f\\d]{{2}})([a-f\\d]{{2}})([a-f\\d]{{2}})$/i.exec(hex);
    return result ? {{
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    }} : {{ r: 0, g: 0, b: 0 }};
}}

// Draw axis labels
function drawAxisLabels(cellW, cellH) {{
    ctx.font = '11px monospace';
    ctx.fillStyle = config.colors.textSecondary;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    // Y-axis (register names)
    for (let reg = 0; reg < heatmapData.registers; reg++) {{
        const y = config.margin.top + (reg * cellH) + (cellH / 2);
        ctx.fillText(REGISTER_NAMES[reg], config.margin.left - 10, y);
    }}

    // X-axis (frame numbers) - only show every 50 frames
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    for (let frame = 0; frame < heatmapData.frames; frame += 50) {{
        const x = config.margin.left + (frame * cellW) + (cellW / 2);
        ctx.fillText(frame.toString(), x, config.margin.top - 30);
    }}

    // Title
    ctx.font = '14px sans-serif';
    ctx.fillStyle = config.colors.textPrimary;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(`Frames (0-${{heatmapData.frames-1}})`, config.margin.left, 10);
}}

// Set up event listeners
function setupEventListeners() {{
    // Mouse move for tooltip
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseleave', hideTooltip);

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {{
        if (e.key === '+' || e.key === '=') {{
            zoomIn();
        }} else if (e.key === '-') {{
            zoomOut();
        }} else if (e.key === '0') {{
            resetZoom();
        }}
    }});
}}

// Handle mouse move (show tooltip)
function handleMouseMove(event) {{
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const cellW = config.cellWidth * zoomLevel;
    const cellH = config.cellHeight * zoomLevel;

    const frame = Math.floor((x - config.margin.left) / cellW);
    const reg = Math.floor((y - config.margin.top) / cellH);

    if (frame >= 0 && frame < heatmapData.frames && reg >= 0 && reg < heatmapData.registers) {{
        showTooltip(event.clientX, event.clientY, frame, reg);
    }} else {{
        hideTooltip();
    }}
}}

// Show tooltip
function showTooltip(x, y, frame, reg) {{
    const tooltip = document.getElementById('tooltip');
    const regName = REGISTER_NAMES[reg];
    const valueA = heatmapData.valueGridA[frame][reg];
    const valueB = heatmapData.valueGridB[frame][reg];
    const match = heatmapData.matchGrid[frame][reg];
    const delta = heatmapData.deltaGrid[frame][reg];
    const matchIcon = match ? '[MATCH]' : '[DIFF]';

    tooltip.innerHTML = `
        <strong>Frame ${{frame}}, ${{regName}}</strong><br>
        File A: $$${{valueA.toString(16).toUpperCase().padStart(2, '0')}} (${{valueA}})<br>
        File B: $$${{valueB.toString(16).toUpperCase().padStart(2, '0')}} (${{valueB}})<br>
        Delta: ${{delta}} ${{matchIcon}}
    `;

    tooltip.style.left = (x + 10) + 'px';
    tooltip.style.top = (y + 10) + 'px';
    tooltip.style.display = 'block';
}}

// Hide tooltip
function hideTooltip() {{
    const tooltip = document.getElementById('tooltip');
    tooltip.style.display = 'none';
}}

// Switch visualization mode
function switchMode(mode) {{
    currentMode = mode;

    // Update radio button
    document.getElementById('mode-' + mode).checked = true;

    // Update active class
    for (let i = 1; i <= 4; i++) {{
        const option = document.getElementById('mode-option-' + i);
        if (i === mode) {{
            option.classList.add('active');
        }} else {{
            option.classList.remove('active');
        }}
    }}

    // Redraw heatmap
    drawHeatmap(mode);

    // Update legend
    updateLegend(mode);
}}

// Update legend based on mode
function updateLegend(mode) {{
    const legendItems = document.getElementById('legend-items');

    let html = '';

    switch(mode) {{
        case 1:
            html = `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.match}};"></div>
                    <span>Match</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.mismatch}};"></div>
                    <span>Mismatch</span>
                </div>
            `;
            break;
        case 2:
            html = `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.deltaMin}};"></div>
                    <span>0 difference</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.deltaMax}};"></div>
                    <span>255 difference</span>
                </div>
            `;
            break;
        case 3:
            html = `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.voice1}};"></div>
                    <span>Voice 1 (Bright=Match)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.voice2}};"></div>
                    <span>Voice 2 (Bright=Match)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.voice3}};"></div>
                    <span>Voice 3 (Bright=Match)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.filter}};"></div>
                    <span>Filter (Bright=Match)</span>
                </div>
            `;
            break;
        case 4:
            html = `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.match}};"></div>
                    <span>100% accuracy</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{config.colors.mismatch}};"></div>
                    <span>0% accuracy</span>
                </div>
            `;
            break;
    }}

    legendItems.innerHTML = html;
}}

// Zoom functions
function zoomIn() {{
    zoomLevel = Math.min(zoomLevel * 1.5, 5.0);
    drawHeatmap(currentMode);
}}

function zoomOut() {{
    zoomLevel = Math.max(zoomLevel / 1.5, 0.25);
    drawHeatmap(currentMode);
}}

function resetZoom() {{
    zoomLevel = 1.0;
    drawHeatmap(currentMode);
}}
"""


def main():
    """Test heatmap exporter."""
    print("Accuracy Heatmap HTML Exporter - Test Mode")
    print("This module is meant to be imported, not run directly.")
    print()
    print("Usage:")
    print("  from accuracy_heatmap_exporter import AccuracyHeatmapExporter")
    print("  exporter = AccuracyHeatmapExporter(heatmap_data)")
    print("  exporter.export('heatmap.html')")
    print()
    print("See accuracy_heatmap_tool.py for complete CLI usage.")


if __name__ == '__main__':
    main()
