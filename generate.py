#!/usr/bin/env python3
"""Generate a self-contained index.html from data/wvs-synthetic.csv."""

import csv
import json
import random
import os
from collections import Counter

SEED = 42
random.seed(SEED)

COLORS = {
    "China": "#E69F00",
    "Singapore": "#D55E00",
    "Turkey": "#CC79A7",
    "India": "#0072B2",
    "Kazakhstan": "#009E73",
}

MARKERS = {
    "China": "circle",
    "Singapore": "rect",
    "Turkey": "triangle",
    "India": "rectRot",
    "Kazakhstan": "star",
}

NUMERIC_COLS = {
    "age", "life_satisfaction", "freedom_of_choice",
    "emancipative_values", "trust_people_numeric",
    "importance_of_god", "financial_satisfaction", "secular_values",
}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames


def detect_type(col, rows):
    vals = [r[col] for r in rows if r[col].strip()]
    if not vals:
        return "empty"
    try:
        [float(v) for v in vals[:200]]
        if all("." in v for v in vals[:200]):
            return "float"
        return "integer"
    except ValueError:
        return "categorical"


def main():
    src = os.path.join("data", "wvs-synthetic.csv")
    rows, fieldnames = read_csv(src)
    total_rows = len(rows)

    # Column info (exclude respondent_id from display)
    display_cols = [c for c in fieldnames if c != "respondent_id"]
    col_info = []
    for c in display_cols:
        dtype = detect_type(c, rows)
        non_empty = sum(1 for r in rows if r[c].strip())
        col_info.append({"name": c, "type": dtype, "non_empty": non_empty})

    # Duplicate check
    ids = [r["respondent_id"] for r in rows]
    dup_count = len(ids) - len(set(ids))

    # Missing values
    rows_with_missing = sum(
        1 for r in rows if any(r[c].strip() == "" for c in fieldnames)
    )

    # Drop rows with any blank
    clean = [r for r in rows if all(r[c].strip() != "" for c in fieldnames)]
    clean_count = len(clean)

    # Parse numeric fields
    for r in clean:
        r["life_satisfaction"] = float(r["life_satisfaction"])
        r["freedom_of_choice"] = float(r["freedom_of_choice"])
        r["emancipative_values"] = float(r["emancipative_values"])
        r["importance_of_god"] = float(r["importance_of_god"])
        r["financial_satisfaction"] = float(r["financial_satisfaction"])
        r["secular_values"] = float(r["secular_values"])
        r["age"] = float(r["age"])

    countries = ["China", "India", "Kazakhstan", "Singapore", "Turkey"]
    by_country = {c: [r for r in clean if r["country"] == c] for c in countries}

    # --- Analysis 1: Cultural map (country averages) ---
    cultural_map = {}
    for c in countries:
        grp = by_country[c]
        cultural_map[c] = {
            "secular": round(sum(r["secular_values"] for r in grp) / len(grp), 3),
            "emancipative": round(
                sum(r["emancipative_values"] for r in grp) / len(grp), 3
            ),
        }

    # --- Analysis 2: Radar ---
    radar = {}
    for c in countries:
        grp = by_country[c]
        n = len(grp)
        radar[c] = {
            "life_satisfaction": round(
                sum(r["life_satisfaction"] for r in grp) / n / 10, 3
            ),
            "trust_people": round(
                sum(1 for r in grp if r["trust_people"] == "Trusted") / n, 3
            ),
            "importance_of_god": round(
                sum(r["importance_of_god"] for r in grp) / n / 10, 3
            ),
            "emancipative_values": round(
                sum(r["emancipative_values"] for r in grp) / n, 3
            ),
            "secular_values": round(
                sum(r["secular_values"] for r in grp) / n, 3
            ),
            "financial_satisfaction": round(
                sum(r["financial_satisfaction"] for r in grp) / n / 10, 3
            ),
        }

    # --- Analysis 3: China vs India scatter (sampled) ---
    scatter_ci = {}
    for c in ["China", "India"]:
        grp = by_country[c]
        sample = random.sample(grp, min(300, len(grp)))
        scatter_ci[c] = {
            "points": [
                {
                    "x": round(r["secular_values"], 4),
                    "y": round(r["emancipative_values"], 4),
                }
                for r in sample
            ],
            "avg": cultural_map[c],
        }

    # --- Analysis 4: Singapore heatmap ---
    sg = by_country["Singapore"]
    heatmap = [[0] * 10 for _ in range(10)]
    for r in sg:
        ls = int(r["life_satisfaction"])
        fs = int(r["financial_satisfaction"])
        if 1 <= ls <= 10 and 1 <= fs <= 10:
            heatmap[ls - 1][fs - 1] += 1
    heatmap_max = max(max(row) for row in heatmap)

    data_obj = {
        "totalRows": total_rows,
        "colInfo": col_info,
        "dupCount": dup_count,
        "rowsWithMissing": rows_with_missing,
        "cleanCount": clean_count,
        "culturalMap": cultural_map,
        "radar": radar,
        "scatterCI": scatter_ci,
        "heatmap": heatmap,
        "heatmapMax": heatmap_max,
        "colors": COLORS,
        "markers": MARKERS,
        "countries": countries,
    }

    html = build_html(data_obj)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Generated index.html")


def build_html(data):
    d = json.dumps(data)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WVS Synthetic Data — Exploratory Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
:root {{
  --bg: #ffffff; --fg: #1a1a2e; --card: #f8f9fa; --border: #dee2e6;
  --muted: #6c757d; --accent: #0072B2;
}}
*, *::before, *::after {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 16px; font-family: system-ui, -apple-system, sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.6;
  max-width: 960px; margin: 0 auto;
}}
h1 {{ font-size: 1.6rem; margin: 0 0 0.25rem; }}
h2 {{ font-size: 1.25rem; margin: 2rem 0 0.75rem; border-bottom: 2px solid var(--border); padding-bottom: 0.25rem; }}
h3 {{ font-size: 1.05rem; margin: 1.5rem 0 0.5rem; }}
p, .takeaway {{ font-size: 0.95rem; }}
.takeaway {{ background: var(--card); border-left: 3px solid var(--accent); padding: 0.6rem 0.8rem; margin: 0.5rem 0 1.5rem; border-radius: 4px; }}
.intro {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }}
table {{
  width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 0.5rem 0;
}}
th, td {{ padding: 6px 10px; border: 1px solid var(--border); text-align: left; }}
th {{ background: var(--card); font-weight: 600; }}
.chart-wrap {{ position: relative; width: 100%; max-width: 700px; margin: 0 auto; }}
.chart-wrap canvas {{ width: 100% !important; }}
.info-box {{ background: var(--card); padding: 0.5rem 0.8rem; border-radius: 4px; font-size: 0.9rem; margin: 0.5rem 0; }}
.heatmap-grid {{
  display: grid; grid-template-columns: 30px 28px repeat(10, 1fr);
  gap: 2px; max-width: 620px; margin: 0.5rem auto; font-size: 0.75rem; text-align: center;
}}
.heatmap-grid .cell {{
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  border-radius: 3px; font-weight: 600; min-height: 28px;
}}
.heatmap-grid .label {{
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; color: var(--muted); font-size: 0.7rem;
}}
.axis-label {{ text-align: center; color: var(--muted); font-size: 0.8rem; margin-top: 4px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 0.75rem 0; font-size: 0.85rem; align-items: center; }}
.legend-item {{ display: flex; align-items: center; gap: 4px; }}
.legend-swatch {{ width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }}
@media (max-width: 600px) {{
  body {{ padding: 12px; }}
  h1 {{ font-size: 1.3rem; }}
  .heatmap-grid {{ font-size: 0.65rem; }}
  .heatmap-grid .cell {{ min-height: 22px; }}
}}
</style>
</head>
<body>
<h1>Exploring Simulated World Values Survey Data</h1>
<p class="intro">
  This page analyses a <strong>synthetic (fabricated) dataset</strong> designed to resemble the
  <a href="https://www.worldvaluessurvey.org/" target="_blank" rel="noopener">World Values Survey, Wave 7</a>
  (Haerpfer, C., et al., 2022, <em>World Values Survey Wave 7</em>, JD Systems Institute &amp; WVSA Secretariat).
  All rows are simulated &mdash; no real respondent data is used &mdash; so any patterns are
  <strong>illustrative only</strong>, not real-world findings.<br>
  The five countries represented are: <strong>China</strong>, <strong>India</strong>,
  <strong>Kazakhstan</strong>, <strong>Singapore</strong>, and <strong>Turkey</strong>.
</p>

<h2>Dataset Overview</h2>
<div id="overview"></div>

<h2>1&ensp;Cultural Map &mdash; Emancipative vs Secular Values</h2>
<p>Each point is one country&rsquo;s average on secular (x) and emancipative (y) values, in the style of the Inglehart&ndash;Welzel cultural map.</p>
<div class="chart-wrap"><canvas id="chartCulturalMap"></canvas></div>
<div class="takeaway" id="takeawayCM"></div>

<h2>2&ensp;Value Fingerprints &mdash; Radar Chart</h2>
<p>Six normalised (0&ndash;1) measures per country, overlaid for comparison.</p>
<div class="chart-wrap" style="max-width:560px;"><canvas id="chartRadar"></canvas></div>
<div class="takeaway" id="takeawayRadar"></div>

<h2>3&ensp;Individual Values &mdash; China vs India</h2>
<p>~300 sampled respondents per country on secular (x) vs emancipative (y) values. Larger outlined points mark each country&rsquo;s average.</p>
<div class="chart-wrap"><canvas id="chartScatter"></canvas></div>
<div class="takeaway" id="takeawayScatter"></div>

<h2>4&ensp;Life vs Financial Satisfaction &mdash; Singapore Heatmap</h2>
<p>Each cell shows the count of Singapore respondents at that combination. Darker = more respondents.</p>
<div id="heatmapContainer"></div>
<div class="axis-label">Financial Satisfaction &rarr;</div>
<div class="takeaway" id="takeawayHeatmap"></div>

<script>
const D = {d};

// ── Overview ──
(function() {{
  let h = '<div class="info-box">Total rows (before cleaning): <strong>' + D.totalRows + '</strong></div>';
  h += '<table><thead><tr><th>Column</th><th>Type</th><th>Non-empty</th></tr></thead><tbody>';
  D.colInfo.forEach(c => {{
    h += '<tr><td>' + c.name + '</td><td>' + c.type + '</td><td>' + c.non_empty.toLocaleString() + '</td></tr>';
  }});
  h += '</tbody></table>';
  h += '<div class="info-box">' + (D.dupCount === 0
    ? 'Duplicate check: <strong>No duplicate respondent IDs found.</strong>'
    : 'Duplicate check: <strong>' + D.dupCount + ' duplicate respondent IDs found.</strong>') + '</div>';
  h += '<div class="info-box">Rows with at least one missing value: <strong>' + D.rowsWithMissing + '</strong>. '
     + 'These rows were removed, leaving <strong>' + D.cleanCount.toLocaleString() + '</strong> complete rows for analysis.</div>';
  document.getElementById('overview').innerHTML = h;
}})();

// ── Helpers ──
const pointStyles = D.markers;
const markerForCtx = (country) => pointStyles[country] || 'circle';

// ── Chart 1: Cultural Map ──
(function() {{
  const pts = D.countries.map(c => ({{
    x: D.culturalMap[c].secular, y: D.culturalMap[c].emancipative, label: c
  }}));
  new Chart(document.getElementById('chartCulturalMap'), {{
    type: 'scatter',
    data: {{
      datasets: D.countries.map(c => ({{
        label: c,
        data: [{{ x: D.culturalMap[c].secular, y: D.culturalMap[c].emancipative }}],
        backgroundColor: D.colors[c],
        borderColor: D.colors[c],
        pointRadius: 9,
        pointStyle: markerForCtx(c),
        pointBorderWidth: 2,
      }}))
    }},
    options: {{
      responsive: true,
      plugins: {{
        datalabels: {{
          align: 'top', anchor: 'end', offset: 6,
          color: (ctx) => D.colors[D.countries[ctx.datasetIndex]],
          font: {{ weight: 'bold', size: 12 }},
          formatter: (v, ctx) => D.countries[ctx.datasetIndex]
        }},
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => ctx.dataset.label + ': secular=' + ctx.parsed.x.toFixed(2) + ', emancipative=' + ctx.parsed.y.toFixed(2)
          }}
        }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Secular Values (mean)' }} }},
        y: {{ title: {{ display: true, text: 'Emancipative Values (mean)' }} }}
      }}
    }},
    plugins: [ChartDataLabels]
  }});
  // takeaway
  const sorted = D.countries.slice().sort((a, b) => D.culturalMap[b].secular - D.culturalMap[a].secular);
  document.getElementById('takeawayCM').innerHTML =
    sorted[0] + ' scores highest on secular values while ' + sorted[sorted.length-1] +
    ' scores lowest. The spread across both axes shows meaningful cultural variation among these five Asian countries.';
}})();

// ── Chart 2: Radar ──
(function() {{
  const labels = ['Life Satisfaction', 'Trust (share)', 'Importance of God', 'Emancipative', 'Secular', 'Financial Satisfaction'];
  const keys = ['life_satisfaction', 'trust_people', 'importance_of_god', 'emancipative_values', 'secular_values', 'financial_satisfaction'];
  const dashes = {{ China: [], Singapore: [6,3], Turkey: [2,2], India: [10,5], Kazakhstan: [4,8] }};
  new Chart(document.getElementById('chartRadar'), {{
    type: 'radar',
    data: {{
      labels: labels,
      datasets: D.countries.map(c => ({{
        label: c,
        data: keys.map(k => D.radar[c][k]),
        borderColor: D.colors[c],
        backgroundColor: D.colors[c] + '18',
        borderWidth: 2,
        borderDash: dashes[c],
        pointStyle: markerForCtx(c),
        pointRadius: 5,
        pointBackgroundColor: D.colors[c],
      }}))
    }},
    options: {{
      responsive: true,
      scales: {{
        r: {{ min: 0, max: 1, ticks: {{ stepSize: 0.2, backdropColor: 'transparent' }} }}
      }},
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ usePointStyle: true, pointStyle: (ctx) => markerForCtx(D.countries[ctx.datasetIndex]), padding: 14 }} }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.r.toFixed(2)
          }}
        }}
      }}
    }}
  }});
  document.getElementById('takeawayRadar').innerHTML =
    'The radar profiles reveal distinct value fingerprints: countries that rank high on importance of god tend to score lower on secular values, while life and financial satisfaction vary more independently.';
}})();

// ── Chart 3: China vs India scatter ──
(function() {{
  const datasets = [];
  ['China', 'India'].forEach(c => {{
    datasets.push({{
      label: c + ' (sample)',
      data: D.scatterCI[c].points,
      backgroundColor: D.colors[c] + '80',
      borderColor: D.colors[c],
      pointRadius: 3,
      pointStyle: markerForCtx(c),
      pointBorderWidth: 0,
    }});
    datasets.push({{
      label: c + ' (avg)',
      data: [{{ x: D.scatterCI[c].avg.secular, y: D.scatterCI[c].avg.emancipative }}],
      backgroundColor: '#ffffff',
      borderColor: D.colors[c],
      pointRadius: 10,
      pointStyle: markerForCtx(c),
      pointBorderWidth: 3,
    }});
  }});
  new Chart(document.getElementById('chartScatter'), {{
    type: 'scatter',
    data: {{ datasets }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ usePointStyle: true, padding: 14 }} }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => ctx.dataset.label + ': secular=' + ctx.parsed.x.toFixed(2) + ', emancipative=' + ctx.parsed.y.toFixed(2)
          }}
        }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Secular Values' }} }},
        y: {{ title: {{ display: true, text: 'Emancipative Values' }} }}
      }}
    }}
  }});
  document.getElementById('takeawayScatter').innerHTML =
    'Although China and India have different averages, the individual clouds overlap substantially &mdash; many respondents from both countries share similar positions on both value dimensions.';
}})();

// ── Chart 4: Heatmap ──
(function() {{
  const grid = document.getElementById('heatmapContainer');
  let h = '<div class="heatmap-grid">';
  // Y-axis label spanning all data rows
  h += '<div class="label" style="writing-mode:vertical-lr;transform:rotate(180deg);grid-row:1/span 10;grid-column:1;">Life Satisfaction &uarr;</div>';
  // Data rows: row 10 at top
  for (let ls = 9; ls >= 0; ls--) {{
    // Row number label
    h += '<div class="label">' + (ls+1) + '</div>';
    for (let fs = 0; fs < 10; fs++) {{
      const v = D.heatmap[ls][fs];
      const intensity = D.heatmapMax > 0 ? v / D.heatmapMax : 0;
      const bg = 'rgba(213, 94, 0, ' + (0.08 + intensity * 0.88).toFixed(2) + ')';
      const fg = intensity > 0.55 ? '#fff' : 'var(--fg)';
      h += '<div class="cell" style="background:' + bg + ';color:' + fg + ';" title="Life=' + (ls+1) + ', Financial=' + (fs+1) + ': ' + v + ' respondents">' + (v || '') + '</div>';
    }}
  }}
  // Column number labels at the bottom
  h += '<div></div><div></div>';
  for (let fs = 1; fs <= 10; fs++) h += '<div class="label">' + fs + '</div>';
  h += '</div>';
  grid.innerHTML = h;
  // find mode
  let modeLS = 1, modeFS = 1, modeV = 0;
  for (let ls = 0; ls < 10; ls++)
    for (let fs = 0; fs < 10; fs++)
      if (D.heatmap[ls][fs] > modeV) {{ modeV = D.heatmap[ls][fs]; modeLS = ls + 1; modeFS = fs + 1; }}
  document.getElementById('takeawayHeatmap').innerHTML =
    'The densest cell is Life Satisfaction=' + modeLS + ', Financial Satisfaction=' + modeFS +
    ' (' + modeV + ' respondents). Most Singapore respondents cluster in the upper-middle range of both scales, suggesting a positive-but-not-extreme satisfaction pattern.';
}})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
