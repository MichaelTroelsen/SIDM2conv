"""
HTML Export Module for ASM Annotation System
Generates interactive HTML with collapsible sections, search, and syntax highlighting
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional


def generate_html_export(
    input_path: Path,
    file_info: dict,
    subroutines: Dict[int, any],
    sections: List[any],
    symbols: Dict[int, any],
    xrefs: Dict[int, List[any]],
    patterns: List[any],
    loops: List[any],
    branches: List[any],
    cycle_counts: Dict[int, any],
    call_graph: Dict[int, any],
    lifecycles: Dict[str, List[any]],
    dependencies: Dict[int, any],
    dead_code: List[Tuple[int, str, str]],
    optimizations: List[str],
    lines: List[str],
    table_candidates: List[any] = None
) -> str:
    """Generate interactive HTML output with embedded CSS and JavaScript"""

    # Create generation info with version and tools
    from datetime import datetime
    generation_info = {
        'version': '3.0.1',  # SIDM2 version
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tools': [
            'SIDwinder 0.2.6',
            'Python SID Parser',
            'Enhanced Player Detector',
            'Python Assembly Annotator',
            '6502 Register Tracker',
            'Label Name Generator'
        ]
    }

    # Build HTML
    html_parts = []

    # Add HTML header and CSS
    html_parts.append(_get_html_header(input_path.name))

    # Add content
    html_parts.append(_get_html_body_start(input_path, file_info, subroutines, symbols, patterns, loops, dead_code, generation_info))

    # Add Player Structure section (NEW)
    html_parts.append(_get_player_structure_section(file_info, symbols, sections))

    # Add AI-Detected Tables section (NEW)
    if table_candidates:
        html_parts.append(_get_ai_tables_section(table_candidates))

    # Add Architectural Insights section (NEW)
    html_parts.append(_get_architectural_insights_section(file_info, subroutines, patterns, loops))

    # Add Code Organization section (NEW)
    html_parts.append(_get_code_organization_section(file_info, sections, symbols))

    # Add subroutines section
    html_parts.append(_get_subroutines_section(subroutines, cycle_counts))

    # Add loops section
    html_parts.append(_get_loops_section(loops))

    # Add dead code section
    if dead_code:
        html_parts.append(_get_dead_code_section(dead_code))

    # Add optimizations section
    if optimizations:
        html_parts.append(_get_optimizations_section(optimizations))

    # Add symbols section
    html_parts.append(_get_symbols_section(symbols))

    # Add Code Patterns section (NEW)
    html_parts.append(_get_code_patterns_section(patterns))

    # Add Raw Data section (NEW)
    html_parts.append(_get_raw_data_section(sections, symbols))

    # Add Full Assembly Code section (NEW)
    html_parts.append(_get_full_assembly_section(lines, symbols, xrefs, cycle_counts, sections))

    # Add JavaScript and closing tags
    html_parts.append(_get_html_footer())

    return "".join(html_parts)


def _get_html_header(title: str) -> str:
    """Generate HTML header with embedded CSS"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Assembly Analysis</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/vs2015.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
            background: #1e1e1e;
            color: #d4d4d4;
        }}
        .container {{ display: flex; height: 100vh; }}

        /* Sidebar */
        .sidebar {{
            width: 320px;
            background: #252526;
            border-right: 1px solid #3e3e42;
            overflow-y: auto;
            padding: 20px;
        }}
        .sidebar h2 {{
            color: #4ec9b0;
            font-size: 16px;
            margin-bottom: 15px;
            border-bottom: 1px solid #3e3e42;
            padding-bottom: 8px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .stat-item {{
            background: #1e1e1e;
            padding: 12px;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-value {{
            color: #4ec9b0;
            font-size: 24px;
            font-weight: bold;
        }}
        .stat-label {{
            color: #858585;
            font-size: 11px;
            text-transform: uppercase;
        }}
        #search {{
            width: 100%;
            padding: 10px;
            background: #3c3c3c;
            border: 1px solid #3e3e42;
            color: #d4d4d4;
            border-radius: 4px;
            margin: 15px 0;
        }}
        #search:focus {{
            outline: none;
            border-color: #007acc;
        }}
        .nav-item {{
            padding: 8px 12px;
            cursor: pointer;
            border-radius: 4px;
            margin: 3px 0;
            display: flex;
            justify-content: space-between;
            transition: all 0.2s;
        }}
        .nav-item:hover {{
            background: #2a2d2e;
            transform: translateX(4px);
        }}
        .nav-item.active {{
            background: #37373d;
            border-left: 3px solid #007acc;
        }}
        .nav-address {{
            color: #4ec9b0;
            font-weight: bold;
        }}
        .nav-name {{
            color: #dcdcaa;
            margin-left: 10px;
        }}

        /* Main content */
        .main-content {{
            flex-grow: 1;
            overflow-y: auto;
            padding: 30px;
        }}
        .page-header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #1e1e1e 100%);
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 5px solid #4ec9b0;
        }}
        .page-title {{
            color: #4ec9b0;
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        .page-meta {{
            color: #9cdcfe;
            font-size: 14px;
        }}

        /* Section */
        .section {{
            background: #252526;
            border-radius: 8px;
            margin-bottom: 25px;
            border: 1px solid #3e3e42;
            overflow: hidden;
        }}
        .section-header {{
            padding: 18px 24px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #2d2d30;
            transition: background 0.2s;
        }}
        .section-header:hover {{
            background: #383838;
        }}
        .section-title {{
            color: #569cd6;
            font-weight: bold;
            font-size: 18px;
        }}
        .section-toggle {{
            color: #858585;
            font-size: 14px;
            transition: transform 0.3s;
        }}
        .section-toggle.collapsed {{
            transform: rotate(-90deg);
        }}
        .section-content {{
            padding: 24px;
            max-height: 10000px;
            overflow: hidden;
            transition: max-height 0.3s ease-out, padding 0.3s;
        }}
        .section-content.collapsed {{
            max-height: 0;
            padding: 0 24px;
        }}

        /* Card */
        .card {{
            background: #1e1e1e;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 4px solid #dcdcaa;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        .card-title {{
            color: #dcdcaa;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .card-subtitle {{
            color: #4ec9b0;
            font-size: 13px;
            margin-bottom: 12px;
        }}
        .card-content {{
            color: #9cdcfe;
            font-size: 14px;
            line-height: 1.8;
        }}
        .card-meta {{
            display: flex;
            gap: 20px;
            margin-top: 12px;
            font-size: 13px;
            flex-wrap: wrap;
        }}
        .meta-badge {{
            background: #2d2d30;
            padding: 6px 12px;
            border-radius: 4px;
            color: #9cdcfe;
        }}
        .meta-badge strong {{
            color: #ce9178;
        }}

        /* Table */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th {{
            background: #2d2d30;
            color: #569cd6;
            padding: 12px;
            text-align: left;
            font-weight: bold;
            border-bottom: 2px solid #3e3e42;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #3e3e42;
        }}
        tr:hover {{
            background: #2a2d2e;
        }}

        /* Warning/Info boxes */
        .warning-box {{
            background: linear-gradient(135deg, #4a1c00 0%, #2d2d30 100%);
            border-left: 4px solid #ce9178;
            padding: 18px;
            border-radius: 6px;
            margin-bottom: 12px;
        }}
        .warning-title {{
            color: #ce9178;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 15px;
        }}
        .warning-text {{
            color: #cccccc;
        }}
        .info-box {{
            background: linear-gradient(135deg, #0a3a2a 0%, #2d2d30 100%);
            border-left: 4px solid #4ec9b0;
            padding: 18px;
            border-radius: 6px;
            margin-bottom: 12px;
        }}
        .info-text {{
            color: #cccccc;
        }}

        /* Highlight effect */
        .highlight {{
            animation: highlight-flash 1.5s;
        }}
        @keyframes highlight-flash {{
            0%, 100% {{ background: transparent; }}
            50% {{ background: #264f78; }}
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 12px;
            height: 12px;
        }}
        ::-webkit-scrollbar-track {{
            background: #1e1e1e;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #424242;
            border-radius: 6px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #4e4e4e;
        }}
    </style>
</head>
"""


def _get_html_body_start(input_path: Path, file_info: dict, subroutines: Dict, symbols: Dict, patterns: List, loops: List, dead_code: List, generation_info: dict = None) -> str:
    """Generate HTML body start with sidebar and header"""

    author = file_info.get('author', 'Unknown')
    player = file_info.get('player', 'Unknown')
    song_name = file_info.get('name', input_path.name)  # Use song name from PSID header, fallback to filename
    song_copyright = file_info.get('copyright', '')

    html = f"""<body>
    <div class="container">
        <!-- Sidebar -->
        <div class="sidebar">
            <h2>📊 Analysis Stats</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-value">{len(subroutines)}</div>
                    <div class="stat-label">Subroutines</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(symbols)}</div>
                    <div class="stat-label">Symbols</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(patterns)}</div>
                    <div class="stat-label">Patterns</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(loops)}</div>
                    <div class="stat-label">Loops</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(dead_code)}</div>
                    <div class="stat-label">Dead Code</div>
                </div>
            </div>

            <h2>📑 Quick Jump</h2>
            <div style="margin-bottom: 20px;">
                <button onclick="document.getElementById('player-structure').scrollIntoView({{behavior: 'smooth'}}); toggleSection('player-structure');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    🏗️ Player Structure
                </button>
                <button onclick="document.getElementById('ai-tables').scrollIntoView({{behavior: 'smooth'}}); toggleSection('ai-tables');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #4ec9b0; cursor: pointer; border-radius: 4px; text-align: left; font-weight: bold;">
                    🤖 AI-Detected Tables
                </button>
                <button onclick="document.getElementById('architectural-insights').scrollIntoView({{behavior: 'smooth'}}); toggleSection('architectural-insights');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    💡 Architectural Insights
                </button>
                <button onclick="document.getElementById('code-org').scrollIntoView({{behavior: 'smooth'}}); toggleSection('code-org');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    🗂️ Code Organization
                </button>
                <button onclick="document.getElementById('subroutines').scrollIntoView({{behavior: 'smooth'}}); toggleSection('subroutines');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    🔧 Subroutines
                </button>
                <button onclick="document.getElementById('loops').scrollIntoView({{behavior: 'smooth'}}); toggleSection('loops');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    🔄 Loops
                </button>
                <button onclick="document.getElementById('patterns').scrollIntoView({{behavior: 'smooth'}}); toggleSection('patterns');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    🔍 Code Patterns
                </button>
                <button onclick="document.getElementById('symbols').scrollIntoView({{behavior: 'smooth'}}); toggleSection('symbols');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    📝 Symbols
                </button>
                <button onclick="document.getElementById('raw-data').scrollIntoView({{behavior: 'smooth'}}); toggleSection('raw-data');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    💾 Raw Data
                </button>
                <button onclick="document.getElementById('full-asm').scrollIntoView({{behavior: 'smooth'}}); toggleSection('full-asm');"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; cursor: pointer; border-radius: 4px; text-align: left;">
                    📜 Assembly Code
                </button>
                <button onclick="scrollToEOF();"
                        style="width: 100%; padding: 10px; margin: 5px 0; background: #3e2d2d; border: 1px solid #5e3e3e; color: #ff9999; cursor: pointer; border-radius: 4px; text-align: left; font-weight: bold;">
                    🏁 Jump to EOF
                </button>
            </div>

            <h2>🔗 Subroutine Links</h2>
            <div id="nav-list">
"""

    # Add navigation items
    for addr, info in sorted(subroutines.items()):
        name = info.name or f"sub_{addr:04x}"
        html += f"""                <div class="nav-item" onclick="scrollTo('sub-{addr:04x}')">
                    <span class="nav-address">${addr:04X}</span>
                    <span class="nav-name">{name}</span>
                </div>
"""

    html += f"""            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <div class="page-header">
                <div class="page-title">{song_name}</div>
                <div class="page-meta">Author: {author} | Player: {player}{' | ' + song_copyright if song_copyright else ''}</div>
"""

    # Add version and tool information if provided
    if generation_info:
        version = generation_info.get('version', 'Unknown')
        timestamp = generation_info.get('timestamp', 'Unknown')
        tools = generation_info.get('tools', [])
        tools_str = ' + '.join(tools) if tools else 'Unknown'

        html += f"""                <div style="margin-top: 10px; padding: 10px; background: #2d2d30; border-radius: 4px; font-size: 12px; color: #858585;">
                    <strong style="color: #569cd6;">SIDM2 v{version}</strong> | Generated: {timestamp}<br>
                    Tools: {tools_str}
                </div>
"""

    html += """            </div>

"""
    return html


def _get_subroutines_section(subroutines: Dict, cycle_counts: Dict) -> str:
    """Generate subroutines section"""
    html = f"""            <!-- Subroutines -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('subroutines')">
                    <span class="section-title">🔧 Subroutines ({len(subroutines)})</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="subroutines">
"""

    for addr, info in sorted(subroutines.items()):
        name = info.name or f"sub_{addr:04x}"
        purpose = info.purpose or "No description"

        # Build metadata
        meta_items = []

        # Inputs/Outputs
        inputs = []
        outputs = []
        if info.register_usage.a_input:
            inputs.append("A")
        if info.register_usage.x_input:
            inputs.append("X")
        if info.register_usage.y_input:
            inputs.append("Y")
        if info.register_usage.a_output:
            outputs.append("A")
        if info.register_usage.x_output:
            outputs.append("X")
        if info.register_usage.y_output:
            outputs.append("Y")

        if inputs:
            meta_items.append(f'<div class="meta-badge"><strong>In:</strong> {", ".join(inputs)}</div>')
        if outputs:
            meta_items.append(f'<div class="meta-badge"><strong>Out:</strong> {", ".join(outputs)}</div>')

        # Cycles
        if addr in cycle_counts:
            cycles = cycle_counts[addr]
            meta_items.append(f'<div class="meta-badge"><strong>Cycles:</strong> {cycles.typical_cycles}</div>')

        html += f"""                    <div class="card" id="sub-{addr:04x}">
                        <div class="card-title">{name}</div>
                        <div class="card-subtitle">${addr:04X}</div>
                        <div class="card-content">{purpose}</div>
                        <div class="card-meta">
                            {''.join(meta_items)}
                        </div>
                    </div>
"""

    html += """                </div>
            </div>

"""
    return html


def _get_loops_section(loops: List) -> str:
    """Generate loops section"""
    html = f"""            <!-- Loops -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('loops')">
                    <span class="section-title">🔄 Loops ({len(loops)})</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="loops">
"""

    for i, loop in enumerate(loops[:25], 1):
        html += f"""                    <div class="card">
                        <div class="card-title">Loop #{i}</div>
                        <div class="card-subtitle">${loop.start_address:04X} - ${loop.end_address:04X}</div>
                        <div class="card-meta">
                            <div class="meta-badge"><strong>Type:</strong> {loop.loop_type}</div>
"""
        if loop.counter_register:
            html += f"""                            <div class="meta-badge"><strong>Counter:</strong> Reg {loop.counter_register}</div>
"""
        html += f"""                            <div class="meta-badge"><strong>Iterations:</strong> {loop.iterations_min}-{loop.iterations_max}</div>
                            <div class="meta-badge"><strong>Cycles/iter:</strong> {loop.cycles_per_iteration}</div>
                        </div>
                    </div>
"""

    if len(loops) > 25:
        html += f"""                    <div style="text-align: center; color: #858585; padding: 15px;">
                        ({len(loops) - 25} more loops not shown)
                    </div>
"""

    html += """                </div>
            </div>

"""
    return html


def _get_dead_code_section(dead_code: List) -> str:
    """Generate dead code section"""
    html = f"""            <!-- Dead Code -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('deadcode')">
                    <span class="section-title">⚠️ Dead Code ({len(dead_code)})</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="deadcode">
"""

    for addr, reg, reason in dead_code:
        html += f"""                    <div class="warning-box">
                        <div class="warning-title">${addr:04X} - Register {reg}</div>
                        <div class="warning-text">{reason}</div>
                    </div>
"""

    html += """                </div>
            </div>

"""
    return html


def _get_optimizations_section(optimizations: List) -> str:
    """Generate optimizations section"""
    html = f"""            <!-- Optimizations -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('optimizations')">
                    <span class="section-title">💡 Optimizations ({len(optimizations)})</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="optimizations">
"""

    for i, opt in enumerate(optimizations, 1):
        html += f"""                    <div class="info-box">
                        <div class="info-text">{i}. {opt}</div>
                    </div>
"""

    html += """                </div>
            </div>

"""
    return html


def _get_symbols_section(symbols: Dict) -> str:
    """Generate symbols table section"""
    html = f"""            <!-- Symbol Table -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('symbols')">
                    <span class="section-title">📋 Symbol Table ({len(symbols)})</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content collapsed" id="symbols">
                    <table>
                        <thead>
                            <tr>
                                <th>Address</th>
                                <th>Type</th>
                                <th>Name</th>
                                <th>Refs</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
"""

    for addr, sym in sorted(symbols.items())[:100]:
        # Format refs
        refs_parts = []
        if sym.call_count > 0:
            refs_parts.append(f"{sym.call_count}c")
        if sym.read_count > 0:
            refs_parts.append(f"{sym.read_count}r")
        if sym.write_count > 0:
            refs_parts.append(f"{sym.write_count}w")
        refs_str = ",".join(refs_parts) if refs_parts else "-"

        html += f"""                            <tr>
                                <td style="color: #4ec9b0; font-weight: bold;">${addr:04X}</td>
                                <td style="color: #569cd6;">{sym.symbol_type.value}</td>
                                <td style="color: #dcdcaa;">{sym.name or '-'}</td>
                                <td style="color: #ce9178;">{refs_str}</td>
                                <td>{sym.description[:50] if sym.description else '-'}</td>
                            </tr>
"""

    if len(symbols) > 100:
        html += f"""                        </tbody>
                    </table>
                    <div style="text-align: center; color: #858585; padding: 15px;">
                        ({len(symbols) - 100} more symbols not shown)
                    </div>
"""
    else:
        html += """                        </tbody>
                    </table>
"""

    html += """                </div>
            </div>
"""
    return html


def _get_player_structure_section(file_info: dict, symbols: Dict, sections: List) -> str:
    """Generate Player Structure section with detected addresses and tables"""

    # Detect key addresses from file_info and symbols
    init_addr = file_info.get('init_address', 0)
    play_addr = file_info.get('play_address', 0)
    load_addr = file_info.get('load_address', 0)

    # Find table addresses from symbols
    wave_table = None
    instrument_table = None
    pulse_table = None
    filter_table = None
    sequence_data = None

    for addr, sym in symbols.items():
        name_lower = (sym.name or "").lower()
        desc_lower = (sym.description or "").lower()
        if 'wave' in name_lower or 'wave' in desc_lower:
            wave_table = addr
        elif 'instrument' in name_lower or 'instrument' in desc_lower:
            instrument_table = addr
        elif 'pulse' in name_lower or 'pulse' in desc_lower:
            pulse_table = addr
        elif 'filter' in name_lower or 'filter' in desc_lower:
            filter_table = addr
        elif 'sequence' in name_lower or 'sequence' in desc_lower:
            sequence_data = addr

    html = f"""            <!-- Player Structure -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('player-structure')">
                    <span class="section-title">🎵 Player Structure</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="player-structure">
                    <div class="card">
                        <div class="card-title">Entry Points</div>
                        <div class="card-content">
                            <table>
                                <tr>
                                    <td style="color: #dcdcaa; font-weight: bold;">Load Address:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${load_addr:04X}</td>
                                    <td style="color: #858585;">Code/data load point</td>
                                </tr>
                                <tr>
                                    <td style="color: #dcdcaa; font-weight: bold;">Init Routine:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${init_addr:04X}</td>
                                    <td style="color: #858585;">Player initialization</td>
                                </tr>
                                <tr>
                                    <td style="color: #dcdcaa; font-weight: bold;">Play Routine:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${play_addr:04X}</td>
                                    <td style="color: #858585;">Called every frame (50Hz PAL / 60Hz NTSC)</td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Data Tables</div>
                        <div class="card-content">
                            <table>
"""

    if wave_table:
        html += f"""                                <tr>
                                    <td style="color: #dcdcaa;">Wave Table:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${wave_table:04X}</td>
                                    <td style="color: #858585;">Waveform definitions</td>
                                </tr>
"""

    if instrument_table:
        html += f"""                                <tr>
                                    <td style="color: #dcdcaa;">Instruments:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${instrument_table:04X}</td>
                                    <td style="color: #858585;">Instrument parameters</td>
                                </tr>
"""

    if pulse_table:
        html += f"""                                <tr>
                                    <td style="color: #dcdcaa;">Pulse Table:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${pulse_table:04X}</td>
                                    <td style="color: #858585;">Pulse width modulation</td>
                                </tr>
"""

    if filter_table:
        html += f"""                                <tr>
                                    <td style="color: #dcdcaa;">Filter Table:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${filter_table:04X}</td>
                                    <td style="color: #858585;">Filter parameters</td>
                                </tr>
"""

    if sequence_data:
        html += f"""                                <tr>
                                    <td style="color: #dcdcaa;">Sequence Data:</td>
                                    <td style="color: #4ec9b0; font-family: monospace;">${sequence_data:04X}</td>
                                    <td style="color: #858585;">Music sequence commands</td>
                                </tr>
"""

    if not any([wave_table, instrument_table, pulse_table, filter_table, sequence_data]):
        html += """                                <tr>
                                    <td colspan="3" style="color: #858585; text-align: center;">No data tables detected</td>
                                </tr>
"""

    html += """                            </table>
                        </div>
                    </div>
                </div>
            </div>
"""
    return html


def _get_ai_tables_section(table_candidates: List) -> str:
    """Generate AI-Detected Music Tables section"""

    if not table_candidates:
        return ""

    # Group by type
    by_type = {}
    for candidate in table_candidates:
        table_type = candidate.table_type
        if table_type not in by_type:
            by_type[table_type] = []
        by_type[table_type].append(candidate)

    # Sort each group by confidence
    for table_type in by_type:
        by_type[table_type].sort(key=lambda c: c.confidence, reverse=True)

    # Build table type summary
    type_summary = []
    type_order = ['note_freq', 'instrument', 'arpeggio', 'wave', 'pulse', 'filter']
    for table_type in type_order:
        if table_type in by_type:
            count = len(by_type[table_type])
            max_conf = max(c.confidence for c in by_type[table_type])
            type_summary.append(f"{table_type.replace('_', ' ').title()}: {count} (max {max_conf:.0%})")

    html = f"""            <!-- AI-Detected Music Tables -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('ai-tables')">
                    <span class="section-title">🤖 AI-Detected Music Tables</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="ai-tables">
                    <p style="color: #cccccc; line-height: 1.6; margin-bottom: 20px;">
                        AI analysis of the disassembled code identified <strong>{len(table_candidates)} potential music data structures</strong>.
                        These tables were detected using pattern recognition, heuristics, and SID register analysis.
                    </p>

                    <div style="background: #2d2d30; padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #569cd6;">
                        <h3 style="color: #569cd6; margin: 0 0 10px 0; font-size: 16px;">Detection Summary</h3>
                        <div style="color: #cccccc; font-size: 13px; line-height: 1.8;">
                            {' • '.join(type_summary)}
                        </div>
                    </div>
"""

    # Add tabs for each table type
    for idx, table_type in enumerate(type_order):
        if table_type not in by_type:
            continue

        candidates = by_type[table_type][:10]  # Show top 10
        type_name = table_type.replace('_', ' ').title()
        type_id = f"ai-table-{table_type}"

        html += f"""
                    <div style="margin-bottom: 25px;">
                        <div class="section-header" onclick="toggleSection('{type_id}')" style="background: #1e1e1e; padding: 12px 18px;">
                            <span style="color: #4ec9b0; font-weight: bold; font-size: 15px;">📊 {type_name} Tables ({len(by_type[table_type])})</span>
                            <span class="section-toggle">▼</span>
                        </div>
                        <div class="section-content" id="{type_id}" style="background: #252526; padding: 15px; border-radius: 0 0 6px 6px;">
"""

        for candidate in candidates:
            # Build confidence badge color
            if candidate.confidence >= 0.8:
                conf_color = "#4ec9b0"  # Green
            elif candidate.confidence >= 0.6:
                conf_color = "#dcdcaa"  # Yellow
            else:
                conf_color = "#858585"  # Gray

            # Build data preview
            if candidate.size <= 32:
                hex_bytes = ' '.join(f'${b:02X}' for b in candidate.data[:16])
                if len(candidate.data) > 16:
                    hex_bytes += '...'
            else:
                hex_bytes = ' '.join(f'${b:02X}' for b in candidate.data[:16]) + f'... ({candidate.size} bytes total)'

            html += f"""
                            <div style="background: #1e1e1e; padding: 15px; margin-bottom: 12px; border-radius: 6px; border-left: 3px solid {conf_color};">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <span style="color: #569cd6; font-family: 'Consolas', monospace; font-size: 14px; font-weight: bold;">
                                        ${candidate.address:04X} - {candidate.size} bytes
                                    </span>
                                    <span style="background: {conf_color}; color: #1e1e1e; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                                        {candidate.confidence:.0%}
                                    </span>
                                </div>
                                <div style="color: #858585; font-size: 12px; margin-bottom: 8px;">
"""

            for reason in candidate.reasons:
                html += f"""                                    <div style="margin: 3px 0;">• {reason}</div>
"""

            html += f"""
                                </div>
                                <div style="background: #252526; padding: 10px; border-radius: 4px; margin-top: 8px;">
                                    <div style="color: #6a9955; font-size: 11px; margin-bottom: 4px;">Data:</div>
                                    <code style="color: #ce9178; font-family: 'Consolas', monospace; font-size: 12px;">{hex_bytes}</code>
                                </div>
                            </div>
"""

        html += """
                        </div>
                    </div>
"""

    html += """
                </div>
            </div>
"""

    return html


def _get_architectural_insights_section(file_info: dict, subroutines: Dict, patterns: List, loops: List) -> str:
    """Generate Architectural Insights section analyzing player design"""

    # Analyze architecture based on what we found
    insights = []

    # Check for initialization patterns
    if subroutines:
        init_count = sum(1 for info in subroutines.values() if 'init' in (info.purpose or "").lower())
        if init_count >= 2:
            insights.append(("Dual Initialization",
                           f"Found {init_count} initialization routines - suggests separate setup for player and music data"))

    # Check for state machine patterns
    bit_test_patterns = [p for p in patterns if hasattr(p, 'pattern_type') and 'BIT test' in str(p.pattern_type)]
    if len(bit_test_patterns) >= 3:
        insights.append(("State Machine",
                        f"Detected {len(bit_test_patterns)} BIT test patterns - player uses flag-based state control"))

    # Check for sequencer architecture
    indirect_patterns = [p for p in patterns if hasattr(p, 'pattern_type') and 'indirect' in str(p.pattern_type).lower()]
    if len(indirect_patterns) >= 5:
        insights.append(("Tracker-Style Sequencer",
                        f"Found {len(indirect_patterns)} indirect addressing patterns - suggests orderlist/sequence architecture"))

    # Check for loop-based processing
    if len(loops) >= 10:
        insights.append(("Loop-Heavy Design",
                        f"{len(loops)} loops detected - efficient iterative processing of voices/channels"))

    # Check for voice processing
    if len(loops) >= 3:
        voice_loops = [l for l in loops if hasattr(l, 'iterations') and str(l.iterations).startswith('3')]
        if voice_loops:
            insights.append(("3-Voice Processing",
                           "Loop patterns suggest separate processing for 3 SID voices"))

    # Default insights if none detected
    if not insights:
        insights.append(("Standard Player", "Classic SID player architecture with init and play routines"))

    html = f"""            <!-- Architectural Insights -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('arch-insights')">
                    <span class="section-title">🏗️ Architectural Insights</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="arch-insights">
"""

    for title, description in insights:
        html += f"""                    <div class="card">
                        <div class="card-title">{title}</div>
                        <div class="card-content">{description}</div>
                    </div>
"""

    html += """                </div>
            </div>
"""
    return html


def _get_code_organization_section(file_info: dict, sections: List, symbols: Dict) -> str:
    """Generate Code Organization section with memory map"""

    # Build memory map from sections
    load_addr = file_info.get('load_address', 0)
    init_addr = file_info.get('init_address', 0)
    play_addr = file_info.get('play_address', 0)

    # Build map of data section addresses for clickable links
    data_addresses = {}  # address -> section for creating links
    for section in sections:
        if hasattr(section, 'section_type') and hasattr(section, 'start_address') and section.start_address:
            if hasattr(section, 'data') and section.data:
                data_addresses[section.start_address] = section

    # Group sections by type
    code_sections = []
    data_sections = []

    for section in sections:
        if hasattr(section, 'section_type'):
            if 'code' in str(section.section_type).lower():
                code_sections.append(section)
            else:
                data_sections.append(section)

    # Helper function to format addresses as clickable links to raw data
    def format_address(addr: int, color: str = '#4ec9b0') -> str:
        """Format an address, making it clickable if it's a data section"""
        if addr in data_addresses:
            return f'<a href="#data-{addr:04x}" style="color: {color}; text-decoration: none; border-bottom: 1px dotted {color};" title="View raw data">${addr:04X}</a>'
        return f'<span style="color: {color};">${addr:04X}</span>'

    html = f"""            <!-- Code Organization -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('code-org')">
                    <span class="section-title">📐 Code Organization</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content" id="code-org">
                    <div class="card">
                        <div class="card-title">Memory Layout - Complete Map ({len(data_sections)} data sections)</div>
                        <div class="card-content">
                            <div style="font-family: monospace; line-height: 1.6; font-size: 13px;">
                                <div style="color: #4ec9b0; font-weight: bold;">• {format_address(load_addr)} - Load Address</div>
                                <div style="color: #569cd6; margin-left: 20px;">├─ {format_address(init_addr)} Init | {format_address(play_addr)} Play</div>
"""

    # Sort sections by address for display
    sorted_sections = sorted(data_sections, key=lambda s: s.start_address if hasattr(s, 'start_address') else 0)

    # Display each section individually
    for idx, section in enumerate(sorted_sections):
        if not hasattr(section, 'start_address') or not section.start_address:
            continue

        symbol = "├─" if idx < len(sorted_sections) - 1 else "└─"

        # Get section name (prefer custom name over type)
        if hasattr(section, 'name') and section.name:
            section_name = section.name
        else:
            section_type = str(section.section_type).replace('SectionType.', '') if hasattr(section, 'section_type') else 'Data'
            section_name = section_type.replace('_', ' ').title()

        # Format address range with clickable link
        addr_range = format_address(section.start_address, '#dcdcaa')
        if hasattr(section, 'end_address') and section.end_address:
            end_addr_str = f'<span style="color: #dcdcaa;">${section.end_address:04X}</span>'
            addr_range += f"-{end_addr_str}"

        # Add size information
        size_info = ""
        if hasattr(section, 'size') and section.size:
            size_info = f" ({section.size} bytes)"
        elif hasattr(section, 'start_address') and hasattr(section, 'end_address') and section.end_address:
            size = section.end_address - section.start_address + 1
            size_info = f" ({size} bytes)"

        html += f"""                                <div style="color: #dcdcaa; margin-left: 20px;">{symbol} {addr_range} - {section_name}{size_info}</div>
"""

    html += """                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">Structure Summary</div>
                        <div class="card-content">
                            <table>
                                <tr>
                                    <td style="color: #dcdcaa; font-weight: bold;">Code Sections:</td>
                                    <td style="color: #4ec9b0;">{}</td>
                                </tr>
                                <tr>
                                    <td style="color: #dcdcaa; font-weight: bold;">Data Sections:</td>
                                    <td style="color: #4ec9b0;">{}</td>
                                </tr>
                                <tr>
                                    <td style="color: #dcdcaa; font-weight: bold;">Total Symbols:</td>
                                    <td style="color: #4ec9b0;">{}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
""".format(len(code_sections), len(data_sections), len(symbols))

    return html


def _get_code_patterns_section(patterns: List) -> str:
    """Generate Code Patterns section"""

    if not patterns:
        return ""

    html = f"""            <!-- Code Patterns -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('patterns')">
                    <span class="section-title">🔍 Code Patterns ({len(patterns)})</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content collapsed" id="patterns">
"""

    for i, pattern in enumerate(patterns[:20]):
        if hasattr(pattern, 'pattern_type') and hasattr(pattern, 'description'):
            pattern_type = str(pattern.pattern_type).replace('PatternType.', '')
            html += f"""                    <div class="card">
                        <div class="card-title">Pattern #{i+1}: {pattern_type}</div>
                        <div class="card-content">{pattern.description}</div>
"""

            if hasattr(pattern, 'address'):
                html += f"""                        <div class="card-subtitle">${pattern.address:04X}</div>
"""

            html += """                    </div>
"""

    if len(patterns) > 20:
        html += f"""                    <div style="text-align: center; color: #858585; padding: 15px;">
                        ({len(patterns) - 20} more patterns not shown)
                    </div>
"""

    html += """                </div>
            </div>
"""
    return html


def _get_raw_data_section(sections: List, symbols: Dict) -> str:
    """Generate Raw Data section with hex dumps of all data sections"""

    # Filter to only data sections
    data_sections = [s for s in sections if hasattr(s, 'section_type') and hasattr(s, 'data') and s.data]

    if not data_sections:
        return ""

    html = f"""            <!-- Raw Data -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('raw-data')">
                    <span class="section-title">💾 Raw Data ({len(data_sections)} sections)</span>
                    <span class="section-toggle">▼</span>
                </div>
                <div class="section-content collapsed" id="raw-data">
                    <div style="color: #858585; margin-bottom: 15px; padding: 10px; background: #2d2d30; border-radius: 4px;">
                        This section shows the raw hexadecimal data for all data tables in the player.
                        Click on data addresses in the assembly code or memory map to jump here.
                    </div>
"""

    # Sort sections by address for display
    sorted_data_sections = sorted(data_sections, key=lambda s: s.start_address if hasattr(s, 'start_address') else 0)

    # Display each section individually
    for section in sorted_data_sections:
            if not hasattr(section, 'start_address') or not section.start_address:
                continue

            start_addr = section.start_address
            end_addr = section.end_address if hasattr(section, 'end_address') and section.end_address else start_addr + len(section.data) - 1
            size = len(section.data)

            # Get section name
            if hasattr(section, 'name') and section.name:
                section_name = section.name
            else:
                section_type = str(section.section_type).replace('SectionType.', '') if hasattr(section, 'section_type') else 'Data'
                section_name = section_type.replace('_', ' ').title()

            # Create anchor ID for linking
            anchor_id = f"data-{start_addr:04x}"

            html += f"""                        <div id="{anchor_id}" style="background: #1e1e1e; padding: 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #4ec9b0;">
                            <div style="margin-bottom: 10px;">
                                <div style="color: #dcdcaa; font-size: 14px; font-weight: bold; margin-bottom: 5px;">📊 {section_name}</div>
                                <div style="display: flex; justify-content: space-between;">
                                    <div style="color: #4ec9b0; font-family: monospace; font-weight: bold;">${start_addr:04X} - ${end_addr:04X}</div>
                                    <div style="color: #858585;">{size} bytes</div>
                                </div>
                            </div>
                            <div style="font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.8;">
"""

            # Format data as hex dump (16 bytes per line) with annotations
            for offset in range(0, len(section.data), 16):
                addr = start_addr + offset
                chunk = section.data[offset:offset+16]

                # Hex bytes
                hex_bytes = ' '.join(f'{b:02X}' for b in chunk)
                # Pad to align ASCII
                hex_bytes = hex_bytes.ljust(47)

                # ASCII representation
                ascii_chars = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)

                html += f"""                                <div style="color: #d4d4d4;">
                                    <span style="color: #858585;">${addr:04X}:</span>
                                    <span style="color: #ce9178;">{hex_bytes}</span>
                                    <span style="color: #6a9955;">; {ascii_chars}</span>
                                </div>
"""

                # Add annotations if available
                if hasattr(section, 'annotations') and section.annotations:
                    anno_chunk = section.annotations[offset:offset+16]
                    anno_text = ', '.join(anno_chunk)
                    html += f"""                                <div style="color: #4fc1ff; margin-left: 50px; font-size: 11px; margin-bottom: 5px;">
                                    {anno_text}
                                </div>
"""

            html += """                            </div>
                        </div>
"""

    html += """                </div>
            </div>
"""
    return html


def _get_full_assembly_section(lines: List[str], symbols: Dict, xrefs: Dict, cycle_counts: Dict, sections: List = None) -> str:
    """Generate Full Assembly Code section with comprehensive inline annotations"""
    import re

    # Build map of data section addresses for clickable links to raw data
    data_addresses = set()
    if sections:
        for section in sections:
            if hasattr(section, 'section_type') and hasattr(section, 'start_address') and section.start_address:
                if hasattr(section, 'data') and section.data:
                    data_addresses.add(section.start_address)

    # Parse all lines to extract addresses and create annotation map
    annotations = {}

    # Common instruction annotations
    instr_comments = {
        'JMP': 'Jump to',
        'JSR': 'Call subroutine at',
        'RTS': 'Return from subroutine',
        'BNE': 'Branch if not equal to',
        'BEQ': 'Branch if equal to',
        'BMI': 'Branch if negative to',
        'BPL': 'Branch if positive to',
        'BCC': 'Branch if carry clear to',
        'BCS': 'Branch if carry set to',
        'BVC': 'Branch if overflow clear to',
        'BVS': 'Branch if overflow set to',
        'LDA': 'Load A with',
        'LDX': 'Load X with',
        'LDY': 'Load Y with',
        'STA': 'Store A to',
        'STX': 'Store X to',
        'STY': 'Store Y to',
        'INC': 'Increment',
        'DEC': 'Decrement',
        'INX': 'Increment X',
        'DEX': 'Decrement X',
        'INY': 'Increment Y',
        'DEY': 'Decrement Y',
        'CMP': 'Compare A with',
        'CPX': 'Compare X with',
        'CPY': 'Compare Y with',
        'AND': 'AND A with',
        'ORA': 'OR A with',
        'EOR': 'XOR A with',
        'BIT': 'Test bits in',
        'ASL': 'Shift left',
        'LSR': 'Shift right',
        'ROL': 'Rotate left',
        'ROR': 'Rotate right',
        'CLC': 'Clear carry flag',
        'SEC': 'Set carry flag',
        'CLI': 'Enable interrupts',
        'SEI': 'Disable interrupts',
        'TAX': 'Transfer A to X',
        'TAY': 'Transfer A to Y',
        'TXA': 'Transfer X to A',
        'TYA': 'Transfer Y to A',
        'TSX': 'Transfer SP to X',
        'TXS': 'Transfer X to SP',
        'PHA': 'Push A to stack',
        'PLA': 'Pull A from stack',
        'PHP': 'Push status to stack',
        'PLP': 'Pull status from stack'
    }

    # SID register annotations
    sid_regs = {
        'D400': 'Voice 1 Frequency Lo',
        'D401': 'Voice 1 Frequency Hi',
        'D402': 'Voice 1 Pulse Width Lo',
        'D403': 'Voice 1 Pulse Width Hi',
        'D404': 'Voice 1 Control Register',
        'D405': 'Voice 1 Attack/Decay',
        'D406': 'Voice 1 Sustain/Release',
        'D407': 'Voice 2 Frequency Lo',
        'D408': 'Voice 2 Frequency Hi',
        'D409': 'Voice 2 Pulse Width Lo',
        'D40A': 'Voice 2 Pulse Width Hi',
        'D40B': 'Voice 2 Control Register',
        'D40C': 'Voice 2 Attack/Decay',
        'D40D': 'Voice 2 Sustain/Release',
        'D40E': 'Voice 3 Frequency Lo',
        'D40F': 'Voice 3 Frequency Hi',
        'D410': 'Voice 3 Pulse Width Lo',
        'D411': 'Voice 3 Pulse Width Hi',
        'D412': 'Voice 3 Control Register',
        'D413': 'Voice 3 Attack/Decay',
        'D414': 'Voice 3 Sustain/Release',
        'D415': 'Filter Cutoff Lo',
        'D416': 'Filter Cutoff Hi',
        'D417': 'Filter Resonance/Routing',
        'D418': 'Filter Mode/Volume'
    }

    html = f"""            <!-- Full Assembly Code -->
            <div class="section">
                <div class="section-header" onclick="toggleSection('full-asm')">
                    <span class="section-title">📜 Fully Annotated Assembly ({len(lines)} lines)</span>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="position: relative; display: flex; align-items: center; gap: 8px;" onclick="event.stopPropagation();">
                            <input type="text" id="asm-search" placeholder="Search code, data, addresses..."
                                   style="padding: 8px 12px; background: #1e1e1e; border: 1px solid #3e3e42; border-radius: 4px; color: #cccccc; font-size: 13px; width: 500px; outline: none;">
                            <button id="search-prev" style="padding: 6px 12px; background: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px; color: #cccccc; cursor: pointer; font-size: 12px; transition: background 0.2s;" title="Previous match (Shift+Enter)" onmouseover="this.style.background='#383838'" onmouseout="this.style.background='#2d2d30'">◀</button>
                            <button id="search-next" style="padding: 6px 12px; background: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px; color: #cccccc; cursor: pointer; font-size: 12px; transition: background 0.2s;" title="Next match (Enter)" onmouseover="this.style.background='#383838'" onmouseout="this.style.background='#2d2d30'">▶</button>
                            <span style="color: #858585; font-size: 12px; margin-left: 8px;">│</span>
                            <button id="zoom-out" style="padding: 6px 12px; background: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px; color: #cccccc; cursor: pointer; font-size: 12px; font-weight: bold; transition: background 0.2s;" title="Zoom out" onmouseover="this.style.background='#383838'" onmouseout="this.style.background='#2d2d30'">−</button>
                            <span id="zoom-level" style="color: #858585; font-size: 11px; min-width: 40px; text-align: center;">100%</span>
                            <button id="zoom-in" style="padding: 6px 12px; background: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px; color: #cccccc; cursor: pointer; font-size: 12px; font-weight: bold; transition: background 0.2s;" title="Zoom in" onmouseover="this.style.background='#383838'" onmouseout="this.style.background='#2d2d30'">+</button>
                            <button id="zoom-reset" style="padding: 6px 10px; background: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px; color: #858585; cursor: pointer; font-size: 11px; transition: background 0.2s;" title="Reset zoom (100%)" onmouseover="this.style.background='#383838'" onmouseout="this.style.background='#2d2d30'">Reset</button>
                            <div id="asm-search-count" style="position: absolute; top: 100%; left: 0; margin-top: 5px; font-size: 11px; color: #858585; white-space: nowrap; display: none;"></div>
                        </div>
                        <span class="section-toggle">▼</span>
                    </div>
                </div>
                <div class="section-content" id="full-asm">
                    <div style="background: #1e1e1e; padding: 20px; border-radius: 6px; max-height: calc(100vh - 300px); overflow-y: scroll; overflow-x: auto; border: 1px solid #3e3e42;">
                        <pre id="asm-code-pre" style="color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.8; margin: 0;">"""

    prev_was_blank = False
    section_started = False

    # Add assembly lines with smart annotations (show all lines, no limit)
    for i, line in enumerate(lines):  # Show ALL lines including EOF marker
        # Skip all blank lines completely
        if not line.strip():
            continue
        prev_was_blank = False

        # Strip trailing newlines from the line (we'll add exactly one back at the end)
        line = line.rstrip('\r\n')

        # Escape HTML
        line_escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Convert label markers to actual HTML links (after escaping)
        import re
        # Convert label definitions: [[LABELDEF:Loop_Countdown]] -> <a id="Loop_Countdown">Loop_Countdown:</a>
        line_escaped = re.sub(
            r'\[\[LABELDEF:([^\]]+)\]\]',
            r'<a id="\1" style="text-decoration: none;"><span style="color: #dcdcaa;">\1:</span></a>',
            line_escaped
        )
        # Convert label references: [[LABELREF:DataBlock_6]] -> <a href="#DataBlock_6">DataBlock_6</a>
        line_escaped = re.sub(
            r'\[\[LABELREF:([^\]]+)\]\]',
            r'<a href="#\1" style="color: #dcdcaa; text-decoration: underline; text-decoration-style: dotted;" title="Jump to \1">\1</a>',
            line_escaped
        )

        # Convert anchor markers: [[ANCHOR:PulseTable]] -> <a id="PulseTable"></a>
        line_escaped = re.sub(
            r'\[\[ANCHOR:([^\]]+)\]\]',
            r'<a id="\1" style="text-decoration: none;"></a>',
            line_escaped
        )

        # Convert table link markers: [[TABLELINK:VoiceControl]] -> <a href="#VoiceControl">VoiceControl</a>
        line_escaped = re.sub(
            r'\[\[TABLELINK:([^\]]+)\]\]',
            r'<a href="#\1" style="color: #4ec9b0; text-decoration: underline; text-decoration-style: dotted;" title="Jump to \1 section">\1</a>',
            line_escaped
        )

        # Check if line already has a comment
        has_comment = ';' in line_escaped

        # Extract address and instruction
        addr_match = re.search(r'\$([0-9A-Fa-f]{4}):', line)
        addr = int(addr_match.group(1), 16) if addr_match else None

        # Add section headers based on address or labels
        if addr:
            if addr == 0x1000 or 'init' in line.lower():
                if not section_started:
                    html += '<span style="color: #6a9955;">; ========================================\n'
                    html += '; Init Routine - Player Initialization\n'
                    html += '; ========================================</span>\n'
                    section_started = True
            elif addr == 0x1006 or 'play' in line.lower():
                html += '\n<span style="color: #6a9955;">; ========================================\n'
                html += '; Play Routine - Called Every Frame\n'
                html += '; ========================================</span>\n'

        # Add smart inline comments
        if not has_comment and addr:
            # Parse instruction
            instr_match = re.search(r':\s+[0-9a-f ]+\s+(\w+)\s*(.*)', line, re.IGNORECASE)
            if instr_match:
                instr = instr_match.group(1).upper()
                operand = instr_match.group(2).strip()

                comment = None

                # Check for SID register access
                sid_match = re.search(r'\$d4([0-9a-f]{2})', operand, re.IGNORECASE)
                if sid_match:
                    reg = 'D4' + sid_match.group(1).upper()
                    if reg in sid_regs:
                        if 'STA' in instr or 'STX' in instr or 'STY' in instr:
                            comment = f'Set {sid_regs[reg]}'
                        else:
                            comment = f'Read {sid_regs[reg]}'

                # Check for zero-page pointer setup
                elif re.search(r'\$fc|\$fd', operand, re.IGNORECASE):
                    if 'STA' in instr:
                        if '$FC' in operand.upper():
                            comment = 'Set pointer lo-byte'
                        else:
                            comment = 'Set pointer hi-byte'
                    elif 'LDA' in instr:
                        comment = 'Read via pointer'

                # Indirect indexed addressing
                elif re.search(r'\(\$fc\),y', operand, re.IGNORECASE):
                    comment = 'Read data via pointer + Y offset'

                # Generic instruction comment
                elif not comment and instr in instr_comments:
                    comment = instr_comments[instr]
                    if operand:
                        # Add operand to comment
                        if instr in ['BNE', 'BEQ', 'BMI', 'BPL', 'BCC', 'BCS', 'BVC', 'BVS']:
                            comment += f' {operand}'
                        elif '#$' in operand:
                            val = re.search(r'#\$([0-9A-Fa-f]+)', operand)
                            if val:
                                comment += f' ${val.group(1)}'

                # Add comment to line
                if comment:
                    # Pad line to column 40 for alignment
                    padding = max(1, 45 - len(line))
                    line_escaped += ' ' * padding + f'<span style="color: #6a9955;">; {comment}</span>'

        # Color code the line (but don't split semicolons inside HTML tags)
        # Use a more sophisticated approach that preserves anchor tags
        if ';' in line_escaped:
            # Find the first semicolon that's NOT inside an HTML tag
            in_tag = False
            semicolon_pos = -1
            for i, char in enumerate(line_escaped):
                if char == '<':
                    in_tag = True
                elif char == '>':
                    in_tag = False
                elif char == ';' and not in_tag:
                    semicolon_pos = i
                    break

            if semicolon_pos > 0:
                parts = [line_escaped[:semicolon_pos], line_escaped[semicolon_pos+1:]]
                line_escaped = parts[0] + '<span style="color: #6a9955;">; ' + parts[1] + '</span>'

        # Addresses in cyan - make data addresses clickable
        def make_addr_clickable(match):
            addr_str = match.group(1)
            addr = int(addr_str, 16)
            if addr in data_addresses:
                # Make it a clickable link to the raw data section
                return f'<a href="#data-{addr_str.lower()}" style="color: #4ec9b0; text-decoration: none; border-bottom: 1px dotted #4ec9b0;" title="View raw data at ${addr_str}">${addr_str}</a>'
            return f'<span style="color: #4ec9b0;">${addr_str}</span>'

        line_escaped = re.sub(r'\$([0-9A-Fa-f]{4})', make_addr_clickable, line_escaped)

        # Immediate values in orange
        line_escaped = re.sub(r'#\<span style="color: #4ec9b0;">\$([0-9A-Fa-f]{2})', r'#<span style="color: #ce9178;">$\1', line_escaped)

        # Labels in yellow
        if line and not line.startswith(' ') and not line.startswith(';') and ':' in line:
            line_escaped = f'<span style="color: #dcdcaa;">{line_escaped}</span>'

        html += line_escaped + '\n'

    # All lines are now shown, no truncation message needed

    html += """</pre>
                    </div>
                </div>
            </div>
"""
    return html


def _get_html_footer() -> str:
    """Generate HTML footer with JavaScript"""
    return """
        </div>
    </div>

    <script>
        // Toggle section
        function toggleSection(id) {
            const content = document.getElementById(id);
            const header = content.previousElementSibling;
            const toggle = header.querySelector('.section-toggle');

            content.classList.toggle('collapsed');
            toggle.classList.toggle('collapsed');
        }

        // Scroll to element
        function scrollTo(id) {
            const element = document.getElementById(id);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                element.classList.add('highlight');
                setTimeout(() => element.classList.remove('highlight'), 1500);
            }
        }

        // Scroll to EOF marker
        function scrollToEOF() {
            // Expand the full-asm section if collapsed
            const asmSection = document.getElementById('full-asm');
            if (asmSection && asmSection.classList.contains('collapsed')) {
                toggleSection('full-asm');
            }

            // Wait for expansion animation, then scroll to bottom
            setTimeout(() => {
                const asmContent = document.getElementById('full-asm');
                if (asmContent) {
                    // Scroll the assembly section to the very bottom
                    const pre = asmContent.querySelector('pre');
                    if (pre) {
                        pre.scrollTop = pre.scrollHeight;
                    }
                    // Also scroll the main content to show the assembly section
                    asmContent.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }
            }, 300);
        }

        // Enhanced Search with highlighting in assembly code and raw data
        let currentMatches = [];
        let currentMatchIndex = -1;
        const searchInput = document.getElementById('asm-search');

        function clearHighlights() {
            document.querySelectorAll('.search-highlight').forEach(el => {
                el.outerHTML = el.textContent;
            });
            currentMatches = [];
            currentMatchIndex = -1;
        }

        function highlightMatches(query) {
            clearHighlights();
            if (!query || query.length < 2) return;

            // Search in assembly code section
            const asmSection = document.querySelector('#full-asm pre');
            if (asmSection) {
                highlightInElement(asmSection, query);
            }

            // Search in raw data sections
            document.querySelectorAll('[id^="data-"] pre').forEach(section => {
                highlightInElement(section, query);
            });

            // Update match count
            updateMatchCount();

            // Jump to first match
            if (currentMatches.length > 0) {
                jumpToMatch(0);
            }
        }

        function highlightInElement(element, query) {
            const walker = document.createTreeWalker(
                element,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            const textNodes = [];
            while (walker.nextNode()) {
                textNodes.push(walker.currentNode);
            }

            textNodes.forEach(node => {
                const text = node.textContent;
                const lowerText = text.toLowerCase();
                const lowerQuery = query.toLowerCase();
                let index = 0;
                let lastIndex = 0;
                const fragments = [];

                while ((index = lowerText.indexOf(lowerQuery, lastIndex)) !== -1) {
                    // Add text before match
                    if (index > lastIndex) {
                        fragments.push(document.createTextNode(text.substring(lastIndex, index)));
                    }

                    // Add highlighted match
                    const mark = document.createElement('span');
                    mark.className = 'search-highlight';
                    mark.textContent = text.substring(index, index + query.length);
                    mark.style.backgroundColor = '#ffd700';
                    mark.style.color = '#000';
                    mark.style.padding = '2px 4px';
                    mark.style.borderRadius = '3px';
                    fragments.push(mark);
                    currentMatches.push(mark);

                    lastIndex = index + query.length;
                }

                // Add remaining text
                if (lastIndex < text.length) {
                    fragments.push(document.createTextNode(text.substring(lastIndex)));
                }

                // Replace node if we found matches
                if (fragments.length > 0) {
                    const parent = node.parentNode;
                    fragments.forEach(frag => parent.insertBefore(frag, node));
                    parent.removeChild(node);
                }
            });
        }

        function updateMatchCount() {
            const countDisplay = document.getElementById('asm-search-count');
            if (countDisplay) {
                if (currentMatches.length > 0) {
                    countDisplay.textContent = `${currentMatchIndex + 1} of ${currentMatches.length} matches`;
                    countDisplay.style.display = 'block';
                } else {
                    countDisplay.textContent = searchInput.value.length >= 2 ? 'No matches' : '';
                    countDisplay.style.display = searchInput.value.length >= 2 ? 'block' : 'none';
                }
            }
        }

        function jumpToMatch(index) {
            if (currentMatches.length === 0) return;

            // Remove active class from current match
            if (currentMatchIndex >= 0 && currentMatchIndex < currentMatches.length) {
                currentMatches[currentMatchIndex].style.backgroundColor = '#ffd700';
            }

            // Set new index
            currentMatchIndex = index;
            if (currentMatchIndex < 0) currentMatchIndex = currentMatches.length - 1;
            if (currentMatchIndex >= currentMatches.length) currentMatchIndex = 0;

            // Highlight current match
            const match = currentMatches[currentMatchIndex];
            match.style.backgroundColor = '#ff6b35';
            match.scrollIntoView({ behavior: 'smooth', block: 'center' });

            updateMatchCount();
        }

        // Search input handler
        let searchTimeout;
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value;

            // Debounce content search
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                highlightMatches(query);
            }, 300);
        });

        // Keyboard navigation (Enter for next, Shift+Enter for previous)
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (currentMatches.length > 0) {
                    jumpToMatch(e.shiftKey ? currentMatchIndex - 1 : currentMatchIndex + 1);
                }
            } else if (e.key === 'Escape') {
                searchInput.value = '';
                clearHighlights();
                updateMatchCount();
            }
        });

        // Button navigation
        const searchPrevBtn = document.getElementById('search-prev');
        const searchNextBtn = document.getElementById('search-next');

        if (searchPrevBtn) {
            searchPrevBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (currentMatches.length > 0) {
                    jumpToMatch(currentMatchIndex - 1);
                }
            });
        }

        if (searchNextBtn) {
            searchNextBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (currentMatches.length > 0) {
                    jumpToMatch(currentMatchIndex + 1);
                }
            });
        }

        // Zoom functionality
        const asmCodePre = document.getElementById('asm-code-pre');
        const zoomInBtn = document.getElementById('zoom-in');
        const zoomOutBtn = document.getElementById('zoom-out');
        const zoomResetBtn = document.getElementById('zoom-reset');
        const zoomLevelSpan = document.getElementById('zoom-level');

        let currentZoom = 100; // percentage
        const baseFontSize = 13; // pixels
        const minZoom = 50;
        const maxZoom = 200;
        const zoomStep = 10;

        function updateZoom(newZoom) {
            currentZoom = Math.max(minZoom, Math.min(maxZoom, newZoom));
            const newFontSize = (baseFontSize * currentZoom) / 100;
            if (asmCodePre) {
                asmCodePre.style.fontSize = newFontSize + 'px';
            }
            if (zoomLevelSpan) {
                zoomLevelSpan.textContent = currentZoom + '%';
            }
        }

        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                updateZoom(currentZoom + zoomStep);
            });
        }

        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                updateZoom(currentZoom - zoomStep);
            });
        }

        if (zoomResetBtn) {
            zoomResetBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                updateZoom(100);
            });
        }

        // Active navigation on scroll
        const mainContent = document.querySelector('.main-content');
        const navItems = document.querySelectorAll('.nav-item');

        mainContent.addEventListener('scroll', function() {
            const cards = document.querySelectorAll('.card[id^="sub-"]');
            let currentId = null;

            cards.forEach(card => {
                const rect = card.getBoundingClientRect();
                if (rect.top >= 0 && rect.top <= window.innerHeight / 2) {
                    currentId = card.id;
                }
            });

            if (currentId) {
                navItems.forEach(item => {
                    const onclick = item.getAttribute('onclick');
                    if (onclick && onclick.includes(currentId)) {
                        item.classList.add('active');
                    } else {
                        item.classList.remove('active');
                    }
                });
            }
        });
    </script>
</body>
</html>
"""
