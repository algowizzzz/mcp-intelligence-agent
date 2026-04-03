"""
Visualisation Toolkit — generate_chart MCP Tool
Produces interactive Plotly HTML for canvas + optional PNG export.
"""
import os, json
from datetime import datetime, timezone
from pathlib import Path
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator

# ── Theme definitions ─────────────────────────────────────────────────────────
_THEMES = {
    'riskgpt': {
        'colors': ['#2E75B6','#1F5C99','#5B9BD5','#7B9EC8','#0D5F5F','#D4A017',
                   '#4472C4','#ED7D31','#A9D18E','#FF6B6B'],
        'bg':       '#FFFFFF',
        'plot_bg':  '#F8FAFC',
        'grid':     '#EEEEEE',
        'axis':     '#CCCCCC',
        'font':     '#595959',
        'title':    '#1F3864',
        'hoverbg':  '#1F3864',
        'hoverfont':'#FFFFFF',
    },
    'minimal': {
        'colors': ['#2E75B6','#5B9BD5','#7B9EC8','#1F5C99','#0D5F5F','#D4A017'],
        'bg':       '#FFFFFF',
        'plot_bg':  '#FFFFFF',
        'grid':     'rgba(0,0,0,0)',
        'axis':     '#CCCCCC',
        'font':     '#595959',
        'title':    '#1F3864',
        'hoverbg':  '#333333',
        'hoverfont':'#FFFFFF',
    },
    'dark': {
        'colors': ['#5B9BD5','#2E75B6','#D4A017','#0D5F5F','#A9D18E','#FF6B6B'],
        'bg':       '#1A1A2E',
        'plot_bg':  '#16213E',
        'grid':     '#2A2A4A',
        'axis':     '#555577',
        'font':     '#CCCCDD',
        'title':    '#FFFFFF',
        'hoverbg':  '#0F3460',
        'hoverfont':'#FFFFFF',
    },
}

SUPPORTED_TYPES = ['bar','bar_horizontal','line','area','scatter','histogram',
                   'pie','donut','heatmap','box','treemap','waterfall']

PLOTLY_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.26.0/plotly.min.js'


def _resolve_my_data():
    v = PropertiesConfigurator().get('data.my_data.dir', './data/uploads')
    p = Path(v)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _make_layout(title, x_label, y_label, theme_key, width, height):
    t = _THEMES.get(theme_key, _THEMES['riskgpt'])
    return {
        'title': {'text': title, 'font': {'family': 'Arial', 'size': 14,
                                           'color': t['title']}, 'x': 0.02},
        'paper_bgcolor': t['bg'],
        'plot_bgcolor':  t['plot_bg'],
        'font': {'family': 'Arial', 'size': 11, 'color': t['font']},
        'width': width, 'height': height,
        'margin': {'l': 60, 'r': 30, 't': 60, 'b': 60},
        'xaxis': {'title': x_label, 'gridcolor': t['grid'],
                  'linecolor': t['axis'], 'tickfont': {'color': t['font']}},
        'yaxis': {'title': y_label, 'gridcolor': t['grid'],
                  'linecolor': t['axis'], 'tickfont': {'color': t['font']}},
        'hoverlabel': {'bgcolor': t['hoverbg'], 'font': {'color': t['hoverfont']}},
        'colorway': t['colors'],
        'legend': {'bgcolor': 'rgba(0,0,0,0)'},
    }


def _extract_rows(data):
    """Accept data_transform output dict, plain list of row dicts, or JSON string."""
    if isinstance(data, str):
        try:
            import json as _json
            data = _json.loads(data)
        except Exception:
            return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get('data', [])
    return []


def _col(rows, col):
    return [r.get(col) for r in rows]


def _build_traces(chart_type, rows, x, y, color, params, theme_key):
    import plotly.graph_objects as go
    t = _THEMES.get(theme_key, _THEMES['riskgpt'])
    colors = t['colors']
    traces = []
    bar_mode = params.get('bar_mode', 'group')
    show_values = params.get('show_values', False)

    if chart_type in ('bar', 'bar_horizontal'):
        orient = 'h' if chart_type == 'bar_horizontal' else 'v'
        y_cols = [y] if isinstance(y, str) else y
        if color:
            groups = sorted(set(_col(rows, color)))
            for i, g in enumerate(groups):
                sub = [r for r in rows if r.get(color) == g]
                kw = {'x': _col(sub, x), 'y': _col(sub, y_cols[0]),
                      'name': str(g), 'orientation': orient,
                      'marker_color': colors[i % len(colors)]}
                if show_values:
                    kw['text'] = _col(sub, y_cols[0]); kw['textposition'] = 'auto'
                traces.append(go.Bar(**kw))
        else:
            for i, yc in enumerate(y_cols):
                kw = {'x': _col(rows, x) if orient == 'v' else _col(rows, yc),
                      'y': _col(rows, yc) if orient == 'v' else _col(rows, x),
                      'name': yc, 'orientation': orient,
                      'marker_color': colors[i % len(colors)]}
                if show_values:
                    kw['text'] = _col(rows, yc); kw['textposition'] = 'auto'
                traces.append(go.Bar(**kw))

    elif chart_type == 'line':
        y_cols = [y] if isinstance(y, str) else y
        line_shape = params.get('line_shape', 'linear')
        for i, yc in enumerate(y_cols):
            traces.append(go.Scatter(
                x=_col(rows, x), y=_col(rows, yc), name=yc,
                mode='lines+markers',
                line={'color': colors[i % len(colors)], 'shape': line_shape},
                marker={'size': 5},
            ))

    elif chart_type == 'area':
        y_cols = [y] if isinstance(y, str) else y
        line_shape = params.get('line_shape', 'linear')
        for i, yc in enumerate(y_cols):
            fill = 'tonexty' if i > 0 else 'tozeroy'
            traces.append(go.Scatter(
                x=_col(rows, x), y=_col(rows, yc), name=yc,
                mode='lines', fill=fill,
                line={'color': colors[i % len(colors)], 'shape': line_shape},
                fillcolor=colors[i % len(colors)].replace(')', ',0.2)').replace('rgb','rgba') if colors[i%len(colors)].startswith('rgb') else colors[i%len(colors)] + '33',
            ))

    elif chart_type == 'scatter':
        marker_size = params.get('marker_size', 8)
        y_cols = [y] if isinstance(y, str) else y
        yc = y_cols[0]
        if color:
            groups = sorted(set(_col(rows, color)))
            for i, g in enumerate(groups):
                sub = [r for r in rows if r.get(color) == g]
                traces.append(go.Scatter(
                    x=_col(sub, x), y=_col(sub, yc), name=str(g),
                    mode='markers', marker={'size': marker_size, 'color': colors[i % len(colors)]}
                ))
        else:
            traces.append(go.Scatter(
                x=_col(rows, x), y=_col(rows, yc), name=yc,
                mode='markers', marker={'size': marker_size, 'color': colors[0]}
            ))
        if params.get('show_trendline') and len(rows) >= 2:
            try:
                import numpy as np
                xs = [r.get(x) for r in rows if r.get(x) is not None and r.get(yc) is not None]
                ys = [r.get(yc) for r in rows if r.get(x) is not None and r.get(yc) is not None]
                coeffs = np.polyfit(xs, ys, 1)
                x_range = [min(xs), max(xs)]
                y_fit = [coeffs[0] * xi + coeffs[1] for xi in x_range]
                traces.append(go.Scatter(x=x_range, y=y_fit, name='Trend',
                                         mode='lines', line={'dash': 'dash', 'color': '#999999'}))
            except Exception:
                pass

    elif chart_type == 'histogram':
        nbins = params.get('nbins')
        kw = {'x': _col(rows, x), 'name': x, 'marker_color': colors[0]}
        if nbins:
            kw['nbinsx'] = nbins
        traces.append(go.Histogram(**kw))

    elif chart_type in ('pie', 'donut'):
        hole = params.get('hole', 0.4) if chart_type == 'donut' else 0
        y_cols = [y] if isinstance(y, str) else y
        traces.append(go.Pie(
            labels=_col(rows, x), values=_col(rows, y_cols[0]),
            hole=hole, marker={'colors': colors},
            textinfo='label+percent' if params.get('show_values', True) else 'none',
        ))

    elif chart_type == 'heatmap':
        colorscale = params.get('colorscale', 'Blues')
        y_cols = [y] if isinstance(y, str) else y
        traces.append(go.Heatmap(
            x=_col(rows, x), y=_col(rows, y_cols[0]),
            z=_col(rows, y_cols[0]) if len(y_cols) == 1 else None,
            colorscale=colorscale,
        ))

    elif chart_type == 'box':
        y_cols = [y] if isinstance(y, str) else y
        if color:
            groups = sorted(set(_col(rows, color)))
            for i, g in enumerate(groups):
                sub = [r for r in rows if r.get(color) == g]
                traces.append(go.Box(y=_col(sub, y_cols[0]), name=str(g),
                                      marker_color=colors[i % len(colors)]))
        else:
            for i, yc in enumerate(y_cols):
                traces.append(go.Box(y=_col(rows, yc), name=yc,
                                      marker_color=colors[i % len(colors)]))

    elif chart_type == 'treemap':
        y_cols = [y] if isinstance(y, str) else y
        text_col = params.get('text_column', x)
        traces.append(go.Treemap(
            labels=_col(rows, text_col), values=_col(rows, y_cols[0]),
            parents=['' for _ in rows],
            marker={'colors': _col(rows, y_cols[0]),
                    'colorscale': [[0, colors[0]], [1, colors[2]]]},
        ))

    elif chart_type == 'waterfall':
        y_cols = [y] if isinstance(y, str) else y
        measure_col = params.get('measure_column')
        measures = _col(rows, measure_col) if measure_col else ['relative'] * len(rows)
        traces.append(go.Waterfall(
            x=_col(rows, x), y=_col(rows, y_cols[0]),
            measure=measures, name=y_cols[0],
            connector={'line': {'color': colors[0]}},
            increasing={'marker': {'color': colors[0]}},
            decreasing={'marker': {'color': '#ef4444'}},
            totals={'marker': {'color': colors[4]}},
        ))

    return traces


def _build_html(traces, layout, bar_mode, width, height, title):
    import plotly.graph_objects as go
    import plotly.io as pio

    fig = go.Figure(data=traces, layout=layout)
    if bar_mode and any(isinstance(t, go.Bar) for t in fig.data):
        fig.update_layout(barmode=bar_mode)

    # Get div-only (no full page), then wrap in our template
    div_html = pio.to_html(fig, full_html=False, include_plotlyjs=False,
                           config={'displayModeBar': True,
                                   'modeBarButtonsToRemove': ['select2d','lasso2d','autoScale2d'],
                                   'displaylogo': False, 'responsive': True})

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 12px; font-family: Arial, sans-serif;
       background: {layout.get('paper_bgcolor','#fff')}; }}
</style>
<script src="{PLOTLY_CDN}"></script>
</head><body>
{div_html}
</body></html>"""


class GenerateChartTool(BaseMCPTool):
    def __init__(self, config=None):
        cfg = {
            'name': 'generate_chart',
            'description': (
                'Generate an interactive chart from data_transform output or any row-dict list. '
                'Supports 12 chart types (bar, line, area, scatter, histogram, pie, donut, '
                'heatmap, box, treemap, waterfall, bar_horizontal). '
                'Returns self-contained HTML for canvas rendering and optionally saves a PNG. '
                'Always call parquet_read or data_transform first to confirm column names.'
            ),
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            cfg.update(config)
        super().__init__(cfg)

    def get_output_schema(self):
        return {'type': 'object', 'properties': {
            'html': {'type': 'string'}, 'png_path': {'type': 'string'},
            'chart_type': {'type': 'string'}, 'data_rows_plotted': {'type': 'integer'}
        }}

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'data':         {'description': 'Row dicts or data_transform output dict with .data key'},
                'chart_type':   {'type': 'string', 'enum': SUPPORTED_TYPES},
                'x':            {'type': 'string', 'description': 'Column for x-axis / labels'},
                'y':            {'description': 'Column name or list of column names for y-axis / values'},
                'color':        {'type': 'string', 'description': 'Column for colour grouping (one trace per value)'},
                'title':        {'type': 'string'},
                'x_label':      {'type': 'string'},
                'y_label':      {'type': 'string'},
                'theme':        {'type': 'string', 'enum': ['riskgpt','minimal','dark'], 'default': 'riskgpt'},
                'output_format':{'type': 'string', 'enum': ['html','png','both'], 'default': 'html'},
                'filename':     {'type': 'string', 'description': 'PNG filename. Default: chart_{type}_{ts}.png'},
                'width':        {'type': 'integer', 'default': 900},
                'height':       {'type': 'integer', 'default': 500},
                # chart-specific
                'bar_mode':     {'type': 'string', 'enum': ['group','stack','relative']},
                'nbins':        {'type': 'integer'},
                'hole':         {'type': 'number'},
                'colorscale':   {'type': 'string'},
                'show_values':  {'type': 'boolean'},
                'line_shape':   {'type': 'string', 'enum': ['linear','spline','hv']},
                'show_trendline':{'type': 'boolean'},
                'marker_size':  {'type': 'integer'},
                'text_column':  {'type': 'string'},
                'measure_column':{'type': 'string'},
            },
            'required': ['data', 'chart_type', 'x', 'y'],
        }

    def execute(self, arguments):
        import plotly.graph_objects as go

        chart_type = arguments.get('chart_type', '')
        if chart_type not in SUPPORTED_TYPES:
            return {'error': f"Unsupported chart_type '{chart_type}'. Supported: {SUPPORTED_TYPES}"}

        raw_data = arguments.get('data')
        rows = _extract_rows(raw_data)
        if not rows:
            return {'error': "Cannot generate chart from empty dataset. data has 0 rows."}

        x = arguments.get('x', '')
        y = arguments.get('y', '')
        color = arguments.get('color')
        theme_key = arguments.get('theme', 'riskgpt')
        # Support both output_format enum and save_png/save_html boolean flags
        save_png = arguments.get('save_png', False)
        save_html = arguments.get('save_html', False)
        output_format = arguments.get('output_format', None)
        if output_format is None:
            if save_png and save_html:
                output_format = 'both'
            elif save_png:
                output_format = 'both'   # always produce html too; png additionally
            elif save_html:
                output_format = 'html'
            else:
                output_format = 'html'
        # When save_png=True ensure PNG is generated
        if save_png and output_format == 'html':
            output_format = 'both'
        width = int(arguments.get('width', 900))
        height = int(arguments.get('height', 500))

        # Validate columns
        sample = rows[0]
        available = list(sample.keys())
        y_cols = [y] if isinstance(y, str) else list(y)
        for col in ([x] + y_cols + ([color] if color else [])):
            if col and col not in available:
                return {'error': f"Column '{col}' not found. Available: {available}"}

        title = arguments.get('title') or f"{chart_type.replace('_',' ').title()} — {'/'.join(y_cols)} by {x}"
        x_label = arguments.get('x_label', x)
        y_label = arguments.get('y_label', y_cols[0] if y_cols else '')

        # Build
        try:
            traces = _build_traces(chart_type, rows, x, y, color, arguments, theme_key)
        except Exception as e:
            return {'error': f"Chart build error: {e}"}

        layout = _make_layout(title, x_label, y_label, theme_key, width, height)
        # Pie/donut don't need x/y axis
        if chart_type in ('pie', 'donut', 'treemap'):
            layout.pop('xaxis', None); layout.pop('yaxis', None)

        bar_mode = arguments.get('bar_mode', 'group')
        html_content = None
        png_path = None
        png_size = None
        warnings = []

        # Color cardinality warning
        if color and len(set(_col(rows, color))) > 20:
            warnings.append(f"Column '{color}' has >20 unique values — chart may be crowded.")

        # HTML output
        if output_format in ('html', 'both'):
            try:
                html_content = _build_html(traces, layout, bar_mode, width, height, title)
            except Exception as e:
                return {'error': f"HTML generation failed: {e}"}

        # PNG output
        if output_format in ('png', 'both'):
            try:
                import plotly.graph_objects as go
                import plotly.io as pio
                fig = go.Figure(data=traces, layout=layout)
                if bar_mode and any(isinstance(tr, go.Bar) for tr in fig.data):
                    fig.update_layout(barmode=bar_mode)

                ts = datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
                fname = arguments.get('filename') or f"chart_{chart_type}_{ts}.png"
                if not fname.endswith('.png'):
                    fname += '.png'
                charts_dir = _resolve_my_data() / 'charts'
                charts_dir.mkdir(parents=True, exist_ok=True)
                out_path = charts_dir / fname
                img_bytes = pio.to_image(fig, format='png', width=width, height=height, scale=2)
                out_path.write_bytes(img_bytes)
                png_path = str(out_path)
                png_size = len(img_bytes)
            except ImportError:
                warnings.append('Kaleido not installed — PNG export skipped. Install with: pip install kaleido')
                if output_format == 'png':
                    return {'error': 'PNG export requires kaleido. Install: pip install kaleido'}
            except Exception as e:
                warnings.append(f'PNG export failed: {e}')
                if output_format == 'png':
                    return {'error': f'PNG export failed: {e}'}

        # Save HTML to my_data/charts/ for file-tree access
        html_file_path = None
        if html_content:
            try:
                ts = datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
                charts_dir = _resolve_my_data() / 'charts'
                charts_dir.mkdir(parents=True, exist_ok=True)
                html_fname = f"chart_{chart_type}_{ts}.html"
                html_out = charts_dir / html_fname
                html_out.write_text(html_content, encoding='utf-8')
                html_file_path = str(html_out)
            except Exception:
                pass

        result = {
            'chart_type': chart_type,
            'title': title,
            'output_format': output_format,
            'theme': theme_key,
            'width': width,
            'height': height,
            'data_rows_plotted': len(rows),
            'html': html_content,
            'html_file': html_file_path,
            'png_path': png_path,
            'png_size_bytes': png_size,
        }
        if warnings:
            result['warnings'] = warnings
        return result
