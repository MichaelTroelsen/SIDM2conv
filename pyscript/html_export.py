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
    lines: List[str]
) -> str:
    """Generate interactive HTML output with embedded CSS and JavaScript"""

    # Build HTML
    html_parts = []

    # Add HTML header and CSS
    html_parts.append(_get_html_header(input_path.name))

    # Add content
    html_parts.append(_get_html_body_start(input_path, file_info, subroutines, symbols, patterns, loops, dead_code))

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


def _get_html_body_start(input_path: Path, file_info: dict, subroutines: Dict, symbols: Dict, patterns: List, loops: List, dead_code: List) -> str:
    """Generate HTML body start with sidebar and header"""

    author = file_info.get('author', 'Unknown')
    player = file_info.get('player', 'Unknown')

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

            <h2>🔍 Quick Search</h2>
            <input type="text" id="search" placeholder="Search addresses, names...">

            <h2>📑 Navigation</h2>
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
                <div class="page-title">{input_path.name}</div>
                <div class="page-meta">Author: {author} | Player: {player}</div>
            </div>

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

        // Search
        document.getElementById('search').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            const navItems = document.querySelectorAll('.nav-item');

            navItems.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? 'flex' : 'none';
            });
        });

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
