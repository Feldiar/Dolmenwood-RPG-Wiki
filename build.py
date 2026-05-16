#!/usr/bin/env python3
"""
Dolmenwood Campaign Wiki — Static Site Builder
Run this script to regenerate all HTML pages from the data/ folder.

Usage:
    python3 build.py
"""

import json
import os
import re
from pathlib import Path
from urllib.parse import quote

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
DATA   = BASE / "data"
PAGES  = BASE / "pages"
ASSETS = BASE / "assets"


# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_all(folder):
    """Load all .json files in a folder, keyed by stem."""
    result = {}
    p = DATA / folder
    if not p.exists():
        return result
    for f in sorted(p.glob("*.json")):
        result[f.stem] = load_json(f)
    return result


# ─────────────────────────────────────────────────────────────
# AUTO-LINKER
# ─────────────────────────────────────────────────────────────
def build_link_map(entities):
    """
    Build a flat list of (name, url) pairs sorted longest-first.
    Skips the _notes key and the 'party' category (party links all go
    to the same page, so we skip auto-linking party member names to
    avoid cluttering prose — they can be referenced normally).
    """
    skip = {"_notes"}
    pairs = []
    for category, entries in entities.items():
        if category in skip:
            continue
        for name, url in entries.items():
            pairs.append((name, url))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs

def auto_link(text, link_map, current_url=None, link_prefix=""):
    """
    Replace entity names in text with wiki-link anchors.
    Uses placeholder substitution to avoid double-linking.
    Skips replacement when the result would create a self-link.

    link_prefix: prepended to every URL so paths resolve correctly
    relative to the current page's directory. E.g. "../../" for pages
    two levels deep (pages/category/page.html).
    """
    if not text:
        return text

    placeholders = {}
    result = text

    for i, (name, url) in enumerate(link_map):
        # Don't self-link
        if current_url and url == current_url:
            continue
        if name not in result:
            continue
        # Only match whole-word occurrences (handles names with spaces too)
        pattern = re.compile(r'(?<![A-Za-z\-\'])' + re.escape(name) + r'(?![A-Za-z\-\'])')
        if pattern.search(result):
            ph = f"\x00LINK{i:04d}\x00"
            link_html = f'<a class="wiki-link" href="{link_prefix}{url}">{name}</a>'
            placeholders[ph] = link_html
            result = pattern.sub(ph, result)

    for ph, link_html in placeholders.items():
        result = result.replace(ph, link_html)

    return result

def al(text, link_map, current_url=None, link_prefix=""):
    """Shorthand auto_link."""
    return auto_link(text, link_map, current_url, link_prefix)


# ─────────────────────────────────────────────────────────────
# HTML SHELL
# ─────────────────────────────────────────────────────────────
def css_path(depth):
    """Return relative path to style.css from a page at `depth` levels deep."""
    return ("../" * depth) + "assets/css/style.css"

def google_fonts():
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '  <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:'
        'ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400'
        '&display=swap" rel="stylesheet">'
    )

def sidebar_html(active_section=None, depth=1):
    """Generate the left sidebar. active_section matches a key like 'locations'."""
    prefix = "../" * depth

    def item(label, href, section=None, sub=False):
        cls = "sidebar-item"
        if sub:
            cls += " sub"
        if active_section and section == active_section:
            cls += " active"
        return f'  <a class="{cls}" href="{prefix}{href}">{label}</a>'

    def section(label):
        return f'  <div class="sidebar-section">{label}</div>'

    lines = [
        '<nav class="sidebar">',
        '  <div class="sidebar-logo">',
        f'    <a href="{prefix}index.html">Dolmenwood Campaign Wiki</a>',
        '    <span class="campaign-name">Dolmenwood</span>',
        '  </div>',
        section("Party"),
        item("The Party", "pages/party.html", "party"),
        section("World"),
        item("Locations", "pages/locations/index.html", "locations"),
        item("Factions", "pages/factions/index.html", "factions"),
        item("NPCs", "pages/npcs/index.html", "npcs"),
        section("Story"),
        item("Quests", "pages/quests/index.html", "quests"),
        item("Loose Ends, Rumors, and Misc.", "pages/loose-ends.html", "loose-ends"),
        section("Journal"),
        item("Session 1 — The Road East", "pages/sessions/session-1.html", "sessions"),
        item("Session 2 — Below the Knoll", "pages/sessions/session-2.html", "sessions"),
        item("Session 3 — The Prisoner", "pages/sessions/session-3.html", "sessions"),
        item("Session 4 — The Con(stable) Job", "pages/sessions/session-4.html", "sessions"),
        '</nav>',
    ]
    return "\n".join(lines)

def page_shell(title, content, css_depth=1, active_section=None, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Dolmenwood Campaign Wiki</title>
  {google_fonts()}
  <link rel="stylesheet" href="{css_path(css_depth)}">
  <style>
    #lightbox-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.88);
      z-index: 9999;
      cursor: zoom-out;
      align-items: center;
      justify-content: center;
    }}
    #lightbox-overlay.active {{ display: flex; }}
    #lightbox-overlay img {{
      max-width: 92vw;
      max-height: 92vh;
      border-radius: 4px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.7);
    }}
  </style>
  {extra_head}
</head>
<body>
<div class="layout">

{sidebar_html(active_section, depth=css_depth)}

<main class="main">
  <div class="main-inner">
{content}
  </div>
</main>

</div>

<div id="lightbox-overlay">
  <img id="lightbox-img" src="" alt="Enlarged map view">
</div>
<script>
  (function() {{
    var overlay = document.getElementById('lightbox-overlay');
    var img     = document.getElementById('lightbox-img');
    window.openLightbox = function(src) {{
      img.src = src;
      overlay.classList.add('active');
    }};
    overlay.addEventListener('click', function() {{
      overlay.classList.remove('active');
      img.src = '';
    }});
    document.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape') {{
        overlay.classList.remove('active');
        img.src = '';
      }}
    }});
  }})();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# TAG HELPERS
# ─────────────────────────────────────────────────────────────
def status_tag(status):
    status = status.lower()
    cls_map = {
        "active":   "tag-active",
        "inactive": "tag-inactive",
        "closed":   "tag-inactive",
        "missing":  "tag-suspected",
        "suspected":"tag-suspected",
        "rumored":  "tag-suspected",
    }
    cls = cls_map.get(status, "tag-inactive")
    return f'<span class="tag {cls}">{status.capitalize()}</span>'

def session_tag(session_id):
    label = session_id.replace("session-", "S")
    return f'<span class="tag tag-session">{label}</span>'

def eyebrow(parts, prefix="../../"):
    """Breadcrumb eyebrow. parts = list of (label, href) or just label strings."""
    items = []
    for i, p in enumerate(parts):
        if isinstance(p, tuple):
            label, href = p
            items.append(f'<a href="{prefix}{href}">{label}</a>')
        else:
            items.append(p)
        if i < len(parts) - 1:
            items.append('<span class="separator">›</span>')
    return '<div class="page-eyebrow">' + " ".join(items) + "</div>"


# ─────────────────────────────────────────────────────────────
# PAGE GENERATORS
# ─────────────────────────────────────────────────────────────

# ── HOME PAGE ────────────────────────────────────────────────
def build_home(data):
    quests_html = ""
    for q in data["quests"].values():
        if q.get("status") == "active":
            quests_html += (
                f'<li><a href="pages/quests/{q["id"]}.html">{q["name"]}</a>'
                f' {status_tag(q["status"])}</li>\n'
            )

    sessions_html = ""
    for s in data["sessions"].values():
        sessions_html += (
            f'<li><a href="pages/sessions/{s["id"]}.html">'
            f'{s["name"]} — <em>{s["subtitle"]}</em></a></li>\n'
        )

    content = f"""
    <div class="landing-hero">
      <div class="landing-subtitle">Tabletop RPG · Campaign Wiki</div>
      <h1 class="landing-title">Dolmenwood</h1>
    </div>

    <div class="landing-grid">
      <div class="landing-panel">
        <h3>Active Quests</h3>
        <ul class="quest-list">
          {quests_html}
        </ul>
      </div>
      <div class="landing-panel">
        <h3>Session Journal</h3>
        <ul class="quest-list">
          {sessions_html}
        </ul>
      </div>
    </div>

    <div class="landing-grid" style="margin-top: var(--space-lg);">
      <div class="landing-panel">
        <h3>World</h3>
        <ul class="quest-list">
          <li><a href="pages/locations/index.html">Locations</a>
            <span style="font-family:var(--font-mono,monospace);font-size:11px;color:var(--text-muted)">{len(data["locations"])}</span></li>
          <li><a href="pages/factions/index.html">Factions</a>
            <span style="font-family:var(--font-mono,monospace);font-size:11px;color:var(--text-muted)">{len(data["factions"])}</span></li>
        </ul>
      </div>
      <div class="landing-panel">
        <h3>People</h3>
        <ul class="quest-list">
          <li><a href="pages/party.html">The Party</a>
            <span style="font-family:var(--font-mono,monospace);font-size:11px;color:var(--text-muted)">{len(data["party"]["members"])}</span></li>
          <li><a href="pages/npcs/index.html">NPCs</a>
            <span style="font-family:var(--font-mono,monospace);font-size:11px;color:var(--text-muted)">{len(data["npcs"])}</span></li>
        </ul>
      </div>
    </div>

    <div class="wiki-map-block" style="margin-top: var(--space-xl);">
      <img src="assets/img/Dolmenwood%20Overworld%20Map%201.png"
           alt="Dolmenwood Overworld Map"
           onclick="openLightbox(this.src)"
           style="width:100%;border-radius:4px;border:1px solid var(--border);display:block;cursor:zoom-in;">
      <p style="font-size:12px;color:var(--text-muted);margin-top:var(--space-sm);text-align:center;">
        Overworld Map · click to enlarge
      </p>
    </div>
"""
    html = page_shell("Home", content, css_depth=0, active_section=None)
    write_file(BASE / "index.html", html)


# ── PARTY PAGE ───────────────────────────────────────────────
def build_party(data, link_map):
    LP = "../"   # link prefix: 1 level deep
    rows = ""
    for m in data["party"]["members"]:
        level = m.get("level", "")
        level_html = f'<span class="font-mono" style="font-size:13px;">{level}</span>' if level != "" else ""
        rows += f"""
      <tr>
        <td><strong>{m["name"]}</strong></td>
        <td><span class="tag tag-kindred">{m["kindred"]}</span></td>
        <td>{m["class"]}</td>
        <td>{level_html}</td>
        <td>{m["player"]}</td>
      </tr>"""

    warden = data["party"].get("warden", "")
    warden_html = (
        f'<p class="font-mono text-muted" style="margin-bottom:var(--space-lg);">'
        f'Warden &nbsp;·&nbsp; {warden}</p>'
    ) if warden else ""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../index.html">Home</a>
        <span class="separator">›</span>
        The Party
      </div>
      <h1 class="page-title">The Party</h1>
    </div>

    {warden_html}

    <table>
      <thead>
        <tr>
          <th>Character</th>
          <th>Kindred</th>
          <th>Class</th>
          <th>Level</th>
          <th>Player</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
"""
    html = page_shell("The Party", content, css_depth=1, active_section="party")
    write_file(PAGES / "party.html", html)


# ── NPC INDEX ────────────────────────────────────────────────
def build_npc_index(data, link_map):
    items = ""
    for npc in data["npcs"].values():
        items += f"""
      <li>
        <a href="{npc['id']}.html">
          <span>{npc['name']}</span>
        </a>
      </li>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        NPCs
      </div>
      <h1 class="page-title">NPCs</h1>
    </div>

    <ul class="index-list">
      {items}
    </ul>
"""
    html = page_shell("NPCs", content, css_depth=2, active_section="npcs")
    write_file(PAGES / "npcs" / "index.html", html)


# ── NPC PAGE ─────────────────────────────────────────────────
def build_npc_page(npc, link_map):
    LP = "../../"   # link prefix: 2 levels deep
    current_url = f"pages/npcs/{npc['id']}.html"
    location = npc.get("location", "")
    kindred = npc.get("kindred", "")

    sess_html = session_tag(npc["first_seen"]) if npc.get("first_seen") else ""
    meta = f'<div class="page-meta">{sess_html}</div>'

    desc = al(npc.get("description", ""), link_map, current_url, LP)
    desc_html = f"<p>{desc}</p>" if desc else ""

    notes_html = ""
    if npc.get("notes"):
        notes_html = "<ul>\n"
        for note in npc["notes"]:
            notes_html += f"  <li>{al(note, link_map, current_url, LP)}</li>\n"
        notes_html += "</ul>"

    # Sidebar connections
    conn = npc.get("connections", {})
    sidebar_blocks = ""

    if location:
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Location</h4>
      <p style="font-size:14px;">{al(location, link_map, current_url, LP)}</p>
    </div>"""

    if kindred:
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Kindred</h4>
      <p style="font-size:14px;">{kindred}</p>
    </div>"""

    if conn.get("locations"):
        locs = "".join(f"<li>{al(l, link_map, current_url, LP)}</li>" for l in conn["locations"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Associated Locations</h4>
      <ul>{locs}</ul>
    </div>"""

    if conn.get("npcs"):
        npcs = "".join(f"<li>{al(n, link_map, current_url, LP)}</li>" for n in conn["npcs"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Connected NPCs</h4>
      <ul>{npcs}</ul>
    </div>"""

    if conn.get("quests"):
        qs = "".join(f"<li>{al(q, link_map, current_url, LP)}</li>" for q in conn["quests"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Quests</h4>
      <ul>{qs}</ul>
    </div>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        <a href="index.html">NPCs</a>
        <span class="separator">›</span>
        {npc['name']}
      </div>
      <h1 class="page-title">{npc['name']}</h1>
      {meta}
    </div>

    <div class="entity-layout">
      <div class="entity-content">
        {desc_html}
        {notes_html}
      </div>
      <div class="entity-sidebar">
        {sidebar_blocks}
      </div>
    </div>
"""
    html = page_shell(npc["name"], content, css_depth=2, active_section="npcs")
    write_file(PAGES / "npcs" / f"{npc['id']}.html", html)


# ── LOCATION INDEX ───────────────────────────────────────────
def build_location_tree(locations):
    """
    Build a parent→children map using each location's 'sublocations' list.
    Returns (children_map, root_ids) where root_ids are locations not
    claimed as a sublocation of any other location.
    """
    name_to_id = {loc["name"]: loc_id for loc_id, loc in locations.items()}
    children = {loc_id: [] for loc_id in locations}
    claimed = set()

    for loc_id, loc in locations.items():
        for subloc_name in loc.get("sublocations", []):
            child_id = name_to_id.get(subloc_name)
            if child_id and child_id in locations:
                children[loc_id].append(child_id)
                claimed.add(child_id)

    roots = [loc_id for loc_id in locations if loc_id not in claimed]
    return children, roots

def render_location_node(loc_id, locations, children, depth=0):
    """Recursively render a location and all its nested children."""
    loc = locations[loc_id]
    has_children = bool(children.get(loc_id))

    depth_class = f"loc-depth-{min(depth, 3)}"
    node_html = f'<div class="loc-node {depth_class}">'
    node_html += (
        f'<a href="{loc_id}.html" class="loc-node-link">'
        f'<span class="loc-node-name">{loc["name"]}</span>'
        f'</a>'
    )
    if has_children:
        node_html += '<div class="loc-children">'
        for child_id in children[loc_id]:
            node_html += render_location_node(child_id, locations, children, depth + 1)
        node_html += '</div>'
    node_html += '</div>'
    return node_html

def build_location_index(data, link_map):
    locations = data["locations"]
    children, roots = build_location_tree(locations)

    tree_html = '<div class="loc-tree">'
    for root_id in roots:
        tree_html += render_location_node(root_id, locations, children, depth=0)
    tree_html += '</div>'

    tree_css = """
    <style>
      .loc-tree { margin-top: var(--space-md); }

      .loc-node { position: relative; }

      .loc-node-link {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: var(--space-sm);
        padding: var(--space-sm) 0;
        border-bottom: 1px solid var(--border);
        color: var(--text);
        text-decoration: none;
        border-right: none;
      }
      .loc-node-link:hover { color: var(--accent-dark); border-bottom-color: var(--border); }
      .loc-node-link:hover .loc-node-name { color: var(--accent-dark); }

      .loc-node-name { font-size: 15px; }
      .loc-depth-0 > .loc-node-link .loc-node-name { font-size: 17px; font-weight: 600; color: var(--text); }
      .loc-depth-1 > .loc-node-link .loc-node-name { font-size: 15px; }
      .loc-depth-2 > .loc-node-link .loc-node-name { font-size: 14px; color: var(--text-light); }
      .loc-depth-3 > .loc-node-link .loc-node-name { font-size: 13px; color: var(--text-muted); }

      .loc-children {
        margin-left: var(--space-lg);
        border-left: 2px solid var(--border);
        padding-left: var(--space-md);
        margin-top: 0;
      }

      .loc-depth-0 > .loc-children { margin-top: 0; }
      .loc-node:last-child > .loc-node-link { border-bottom: none; }
    </style>
    """

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        Locations
      </div>
      <h1 class="page-title">Locations</h1>
    </div>

    {tree_html}
"""
    html = page_shell("Locations", content, css_depth=2,
                      active_section="locations", extra_head=tree_css)
    write_file(PAGES / "locations" / "index.html", html)


# ── LOCATION PAGE ────────────────────────────────────────────
def build_location_page(loc, link_map):
    LP = "../../"   # link prefix: 2 levels deep
    current_url = f"pages/locations/{loc['id']}.html"
    region = loc.get("region", "")

    sess_html = session_tag(loc["first_seen"]) if loc.get("first_seen") else ""
    meta = f'<div class="page-meta">{sess_html}</div>' if sess_html else ""

    desc = al(loc.get("description", ""), link_map, current_url, LP)
    desc_html = f"<p>{desc}</p>" if desc else ""

    notes_html = ""
    if loc.get("notes"):
        notes_html = "<ul>\n"
        for note in loc["notes"]:
            notes_html += f"  <li>{al(note, link_map, current_url, LP)}</li>\n"
        notes_html += "</ul>"

    # Map image (optional)
    map_html = ""
    if loc.get("map_image"):
        encoded = quote(loc["map_image"], safe="")
        map_html = f"""
<h2>Map</h2>
<img src="{LP}assets/img/{encoded}" alt="{loc['name']} map"
     onclick="openLightbox(this.src)"
     style="max-width:100%;border-radius:4px;border:1px solid var(--border);display:block;cursor:zoom-in;">
<p style="font-size:12px;color:var(--text-muted);margin-top:var(--space-sm);">Click to enlarge</p>"""

    # Underground passages (optional section for dungeon locations)
    passages_html = ""
    if loc.get("underground_passages"):
        passages_html = "<h2>Underground Passages</h2><ul>\n"
        for note in loc["underground_passages"].get("notes", []):
            passages_html += f"  <li>{al(note, link_map, current_url, LP)}</li>\n"
        passages_html += "</ul>"

    # Sublocations
    sub_html = ""
    if loc.get("sublocations"):
        sub_html = "<h2>Notable Places</h2><ul>\n"
        for s in loc["sublocations"]:
            sub_html += f"  <li>{al(s, link_map, current_url, LP)}</li>\n"
        sub_html += "</ul>"

    # NPCs at this location
    npc_html = ""
    if loc.get("npcs"):
        npc_html = "<h2>People Here</h2><ul>\n"
        for n in loc["npcs"]:
            npc_html += f"  <li>{al(n, link_map, current_url, LP)}</li>\n"
        npc_html += "</ul>"

    # Sidebar
    conn = loc.get("connections", {})
    sidebar_blocks = ""



    if region:
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Region</h4>
      <p style="font-size:14px;">{al(region, link_map, current_url, LP)}</p>
    </div>"""

    if conn.get("factions"):
        facs = "".join(f"<li>{al(f, link_map, current_url, LP)}</li>" for f in conn["factions"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Factions</h4>
      <ul>{facs}</ul>
    </div>"""

    if conn.get("quests"):
        qs = "".join(f"<li>{al(q, link_map, current_url, LP)}</li>" for q in conn["quests"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Quests</h4>
      <ul>{qs}</ul>
    </div>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        <a href="index.html">Locations</a>
        <span class="separator">›</span>
        {loc['name']}
      </div>
      <h1 class="page-title">{loc['name']}</h1>
      {meta}
    </div>

    <div class="entity-layout">
      <div class="entity-content">
        {desc_html}
        {notes_html}
        {map_html}
        {passages_html}
        {sub_html}
        {npc_html}
      </div>
      <div class="entity-sidebar">
        {sidebar_blocks}
      </div>
    </div>
"""
    html = page_shell(loc["name"], content, css_depth=2, active_section="locations")
    write_file(PAGES / "locations" / f"{loc['id']}.html", html)


# ── FACTION INDEX ────────────────────────────────────────────
def build_faction_index(data, link_map):
    items = ""
    for fac in data["factions"].values():
        items += f"""
      <li>
        <a href="{fac['id']}.html">
          <span>{fac['name']}</span>
        </a>
      </li>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        Factions
      </div>
      <h1 class="page-title">Factions</h1>
    </div>

    <ul class="index-list">
      {items}
    </ul>
"""
    html = page_shell("Factions", content, css_depth=2, active_section="factions")
    write_file(PAGES / "factions" / "index.html", html)


# ── FACTION PAGE ─────────────────────────────────────────────
def build_faction_page(fac, link_map):
    LP = "../../"   # link prefix: 2 levels deep
    current_url = f"pages/factions/{fac['id']}.html"
    sess_html = session_tag(fac["first_seen"]) if fac.get("first_seen") else ""
    meta = f'<div class="page-meta">{sess_html}</div>'

    desc = al(fac.get("description", ""), link_map, current_url, LP)
    desc_html = f"<p>{desc}</p>" if desc else ""

    notes_html = ""
    if fac.get("notes"):
        notes_html = "<ul>\n"
        for note in fac["notes"]:
            notes_html += f"  <li>{al(note, link_map, current_url, LP)}</li>\n"
        notes_html += "</ul>"

    members_html = ""
    if fac.get("known_members"):
        members_html = "<h2>Known Members</h2><ul>\n"
        for m in fac["known_members"]:
            members_html += f"  <li>{al(m, link_map, current_url, LP)}</li>\n"
        members_html += "</ul>"

    agents_html = ""
    if fac.get("known_agents"):
        agents_html = "<h2>Known Agents</h2><ul>\n"
        for a in fac["known_agents"]:
            agents_html += f"  <li>{al(a, link_map, current_url, LP)}</li>\n"
        agents_html += "</ul>"

    conn = fac.get("connections", {})
    sidebar_blocks = ""
    if conn.get("locations"):
        locs = "".join(f"<li>{al(l, link_map, current_url, LP)}</li>" for l in conn["locations"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Associated Locations</h4>
      <ul>{locs}</ul>
    </div>"""

    if conn.get("quests"):
        qs = "".join(f"<li>{al(q, link_map, current_url, LP)}</li>" for q in conn["quests"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Quests</h4>
      <ul>{qs}</ul>
    </div>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        <a href="index.html">Factions</a>
        <span class="separator">›</span>
        {fac['name']}
      </div>
      <h1 class="page-title">{fac['name']}</h1>
      {meta}
    </div>

    <div class="entity-layout">
      <div class="entity-content">
        {desc_html}
        {notes_html}
        {members_html}
        {agents_html}
      </div>
      <div class="entity-sidebar">
        {sidebar_blocks}
      </div>
    </div>
"""
    html = page_shell(fac["name"], content, css_depth=2, active_section="factions")
    write_file(PAGES / "factions" / f"{fac['id']}.html", html)


# ── QUEST INDEX ──────────────────────────────────────────────
def build_quest_index(data, link_map):
    items = ""
    for q in data["quests"].values():
        status = q.get("status", "")
        items += f"""
      <li>
        <a href="{q['id']}.html">
          <span>{q['name']}</span>
          <span class="index-meta">{status.capitalize()}</span>
        </a>
      </li>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        Quests
      </div>
      <h1 class="page-title">Quests &amp; Rumors</h1>
    </div>

    <ul class="index-list">
      {items}
    </ul>
"""
    html = page_shell("Quests", content, css_depth=2, active_section="quests")
    write_file(PAGES / "quests" / "index.html", html)


# ── QUEST PAGE ───────────────────────────────────────────────
def build_quest_page(q, link_map):
    LP = "../../"   # link prefix: 2 levels deep
    current_url = f"pages/quests/{q['id']}.html"
    status = q.get("status", "")
    tags = status_tag(status) + " " + (session_tag(q["first_seen"]) if q.get("first_seen") else "")
    meta = f'<div class="page-meta">{tags}</div>'

    desc = al(q.get("description", ""), link_map, current_url, LP)
    desc_html = f"<p>{desc}</p>" if desc else ""

    obj_html = ""
    if q.get("objectives"):
        obj_html = "<h2>Objectives</h2><ol>\n"
        for obj in q["objectives"]:
            obj_html += f"  <li>{al(obj, link_map, current_url, LP)}</li>\n"
        obj_html += "</ol>"

    leads_html = ""
    if q.get("leads"):
        leads_html = "<h2>Leads &amp; Clues</h2><ul>\n"
        for lead in q["leads"]:
            leads_html += f"  <li>{al(lead, link_map, current_url, LP)}</li>\n"
        leads_html += "</ul>"

    conn = q.get("connections", {})
    sidebar_blocks = ""

    if conn.get("npcs"):
        npcs = "".join(f"<li>{al(n, link_map, current_url, LP)}</li>" for n in conn["npcs"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>People Involved</h4>
      <ul>{npcs}</ul>
    </div>"""

    if conn.get("locations"):
        locs = "".join(f"<li>{al(l, link_map, current_url, LP)}</li>" for l in conn["locations"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Locations</h4>
      <ul>{locs}</ul>
    </div>"""

    if conn.get("factions"):
        facs = "".join(f"<li>{al(f, link_map, current_url, LP)}</li>" for f in conn["factions"])
        sidebar_blocks += f"""
    <div class="entity-sidebar-block">
      <h4>Factions</h4>
      <ul>{facs}</ul>
    </div>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        <a href="index.html">Quests</a>
        <span class="separator">›</span>
        {q['name']}
      </div>
      <h1 class="page-title">{q['name']}</h1>
      {meta}
    </div>

    <div class="entity-layout">
      <div class="entity-content">
        {desc_html}
        {obj_html}
        {leads_html}
      </div>
      <div class="entity-sidebar">
        {sidebar_blocks}
      </div>
    </div>
"""
    html = page_shell(q["name"], content, css_depth=2, active_section="quests")
    write_file(PAGES / "quests" / f"{q['id']}.html", html)


# ── SESSION PAGE ─────────────────────────────────────────────
def build_session_page(s, link_map):
    LP = "../../"   # link prefix: 2 levels deep
    current_url = f"pages/sessions/{s['id']}.html"

    paras = ""
    for p in s.get("paragraphs", []):
        paras += f"  <p>{al(p, link_map, current_url, LP)}</p>\n"

    mysteries_html = ""
    if s.get("mysteries_introduced"):
        mysteries_html = '<ul class="mystery-list">\n'
        for m in s["mysteries_introduced"]:
            mysteries_html += f"  <li><span>{al(m, link_map, current_url, LP)}</span></li>\n"
        mysteries_html += "</ul>"

    # Sidebar
    introduced_html = ""
    if s.get("npcs_introduced"):
        npcs = "".join(f"<li>{al(n, link_map, current_url, LP)}</li>" for n in s["npcs_introduced"])
        introduced_html = f"""
    <div class="entity-sidebar-block">
      <h4>NPCs Introduced</h4>
      <ul>{npcs}</ul>
    </div>"""

    locations_html = ""
    if s.get("locations_visited"):
        locs = "".join(f"<li>{al(l, link_map, current_url, LP)}</li>" for l in s["locations_visited"])
        locations_html = f"""
    <div class="entity-sidebar-block">
      <h4>Locations Visited</h4>
      <ul>{locs}</ul>
    </div>"""

    quests_html = ""
    if s.get("quests_updated"):
        qs = "".join(f"<li>{al(q, link_map, current_url, LP)}</li>" for q in s["quests_updated"])
        quests_html = f"""
    <div class="entity-sidebar-block">
      <h4>Quests Active</h4>
      <ul>{qs}</ul>
    </div>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../../index.html">Home</a>
        <span class="separator">›</span>
        Journal
        <span class="separator">›</span>
        {s['name']}
      </div>
      <h1 class="page-title">{s['name']} — <em>{s['subtitle']}</em></h1>
      <div class="page-meta">
        <span class="tag tag-session">{s.get('date','')}</span>
        <span class="tag tag-session">{s.get('weather','')}</span>
      </div>
    </div>

    <div class="entity-layout">
      <div class="entity-content">
        <div class="session-body">
{paras}
        </div>

        {"<h2>Open Threads</h2>" + mysteries_html if mysteries_html else ""}

        <div class="session-end">— End of {s['name']} —</div>
      </div>
      <div class="entity-sidebar">
        {introduced_html}
        {locations_html}
        {quests_html}
      </div>
    </div>
"""
    html = page_shell(f"{s['name']} — {s['subtitle']}", content, css_depth=2, active_section="sessions")
    write_file(PAGES / "sessions" / f"{s['id']}.html", html)


# ── LOOSE ENDS & RUMORS ──────────────────────────────────────
def build_loose_ends(data, link_map):
    LP = "../"
    items = data.get("loose_ends", {}).get("items", [])

    blocks = ""
    for item in items:
        source = item.get("source", "")
        sess_html = session_tag(source) if source else ""
        content_html = al(item["content"], link_map, "pages/loose-ends.html", LP)
        blocks += f"""
    <div class="quest-block">
      <div class="quest-block-title">
        {item['title']}
        {sess_html}
      </div>
      <p>{content_html}</p>
    </div>"""

    content = f"""
    <div class="page-header">
      <div class="page-eyebrow">
        <a href="../index.html">Home</a>
        <span class="separator">›</span>
        Story
        <span class="separator">›</span>
        Loose Ends, Rumors, and Miscellaneous Information
      </div>
      <h1 class="page-title">Loose Ends, Rumors, and Miscellaneous Information</h1>
      <p style="color:var(--text-muted);font-size:15px;margin-top:var(--space-md);">
        Things the party has heard or noticed that don't yet tie to an active quest.
      </p>
    </div>

    {blocks}
"""
    html = page_shell("Loose Ends, Rumors, and Miscellaneous Information", content, css_depth=1, active_section="loose-ends")
    write_file(PAGES / "loose-ends.html", html)


# ─────────────────────────────────────────────────────────────
# FILE WRITER
# ─────────────────────────────────────────────────────────────
def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {path.relative_to(BASE)}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("Loading data...")
    data = {
        "npcs":        load_all("npcs"),
        "locations":   load_all("locations"),
        "factions":    load_all("factions"),
        "quests":      load_all("quests"),
        "sessions":    load_all("sessions"),
        "party":       load_json(DATA / "party.json"),
        "entities":    load_json(DATA / "entities.json"),
        "loose_ends":  load_json(DATA / "loose-ends.json"),
    }

    link_map = build_link_map(data["entities"])
    print(f"  Loaded {len(link_map)} entity links")

    print("\nBuilding pages...")

    build_home(data)
    build_party(data, link_map)

    build_npc_index(data, link_map)
    for npc in data["npcs"].values():
        build_npc_page(npc, link_map)

    build_location_index(data, link_map)
    for loc in data["locations"].values():
        build_location_page(loc, link_map)

    build_faction_index(data, link_map)
    for fac in data["factions"].values():
        build_faction_page(fac, link_map)

    build_quest_index(data, link_map)
    for q in data["quests"].values():
        build_quest_page(q, link_map)

    for s in data["sessions"].values():
        build_session_page(s, link_map)

    build_loose_ends(data, link_map)

    print("\nDone! Open index.html to view the wiki.")

if __name__ == "__main__":
    main()
