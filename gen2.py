import csv
import sys
import re
from collections import defaultdict
from pathlib import Path

DAY_ORDER = ["jeudi", "vendredi", "samedi", "dimanche", "lundi", "mardi", "mercredi"]
DAY_NAMES_EN = {
    "jeudi": "Thursday", "vendredi": "Friday", "samedi": "Saturday",
    "dimanche": "Sunday", "lundi": "Monday", "mardi": "Tuesday", "mercredi": "Wednesday",
}
DAY_NAMES_FR = {
    "jeudi": "Jeudi", "vendredi": "Vendredi", "samedi": "Samedi",
    "dimanche": "Dimanche", "lundi": "Lundi", "mardi": "Mardi", "mercredi": "Mercredi",
}

GROUPS = {
    "Equipes":        ("nav-teams",        "Équipes"),
    "Deputy leaders": ("nav-deputyleader", "Deputy leaders"),
    "Leaders":        ("nav-leaders",      "Leaders"),
    "Guides":         ("nav-guides",       "Guides"),
    "Coordinateurs":  ("nav-coordinators", "Coordinateurs"),
}

GROUP_NAMES_EN = {
    "Équipes": "Contestants",
    "Deputy leaders": "Deputy leaders", 
    "Leaders": "Leaders", 
    "Guides": "Guides", 
    "Coordinateurs": "Coordinators", 
}

GROUP_NAMES_FR = {
    "Équipes": "Équipes",
    "Deputy leaders": "Chefs d'équipe adjoints", 
    "Leaders": "Chefs d'équipe", 
    "Guides": "Guides", 
    "Coordinateurs": "Coordinateurs", 
}

MARKER_START = "<!-- ======= Calendar Section ======= -->"
MARKER_END   = "<!-- End Calendar Section -->"


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows


def build_days(rows):
    days = defaultdict(list)
    for row in rows:
        # Only include rows that have a faketime value
        if not row.get("faketime", "").strip():
            continue
        day = row.get("Jour", "").lower().strip()
        if day in DAY_ORDER:
            days[day].append(row)
    return days


def render_event(row, grp, lang):
    time = row.get("faketime", "").strip() or "—"
    val = row.get(grp, "").strip().lower()
    if val not in ["oui", "opt"]:
        return ""
    optional = val == "opt"

    if lang == "en":
        activity = escape(row.get("name_en", "").strip())
        location = escape(row.get("place_en", "").strip())
        opt_label = "Optional"
    else:
        activity = escape(row.get("name_fr", "").strip())
        location = escape(row.get("place_fr", "").strip())
        opt_label = "Optionnel"

    opt_class = " optional" if optional else ""
    opt_badge = f' <span class="opt-badge">{opt_label}</span>' if optional else ""
    loc_html = f'\n            <div class="location">{location}</div>' if location else ""

    return (
        f'          <div class="event{opt_class}">'
        f'<div class="time">{time}</div>'
        f'<div class="info">'
        f'<div class="activity">{activity}{opt_badge}</div>'
        f'{loc_html}'
        f'</div></div>'
    )


def render_day_block(i, day_key, day_rows, grp, lang):
    day_names = DAY_NAMES_EN if lang == "en" else DAY_NAMES_FR
    day_name = day_names[day_key]
    events = [render_event(row, grp, lang) for row in day_rows]
    events = [e for e in events if e]
    if not events:
        return ""
    lines = [
        f'        <div class="day-block">',
        f'          <div class="day-label">Day {i}</div>',
        f'          <div class="day-title">{day_name}</div>',
        *events,
        f'        </div>',
    ]
    return "\n".join(lines)


def render_tab_pane(grp, tab_id, days, lang, first=False):
    active = "show active" if first else ""
    lines = [
        f'          <div class="tab-pane fade {active}" id="{tab_id}" role="tabpanel" tabindex="0">',
        f'            <div class="schedule-wrap">',
    ]
    for i, day_key in enumerate(DAY_ORDER, 1):
        if day_key not in days:
            continue
        block = render_day_block(i, day_key, days[day_key], grp, lang)
        if block:
            lines.append(block)
    lines.append(f'            </div>')
    lines.append(f'          </div>')
    return "\n".join(lines)


def render_html(days, lang):
    grp_items = list(GROUPS.items())
    title = "Programme détaillé" if lang == "fr" else "Detailed schedule"

    tab_buttons = []
    for idx, (grp, (tab_id, label)) in enumerate(grp_items):
        l = GROUP_NAMES_FR[label] if lang == "fr" else GROUP_NAMES_EN[label]
        active = "active" if idx == 0 else ""
        selected = "true" if idx == 0 else "false"
        tab_buttons.append(
            f'            <button class="nav-link {active}" id="{tab_id}-tab"'
            f' data-bs-toggle="tab" data-bs-target="#{tab_id}"'
            f' type="button" role="tab" aria-selected="{selected}">'
            f'<h5>{l}</h5></button>'
        )

    tab_panes = []
    for idx, (grp, (tab_id, _)) in enumerate(grp_items):
        tab_panes.append(render_tab_pane(grp, tab_id, days, lang, first=(idx == 0)))

    lines = [
        MARKER_START,
        '<section id="calendar" class="calendar section light-background">',
        '  <div class="container section-title" data-aos="fade-up">',
        f'    <h2>{title}</h2>',
        '  </div>',
        '  <div class="container">',
        '    <nav>',
        '      <div class="nav nav-tabs" id="nav-tab" role="tablist">',
        *tab_buttons,
        '      </div>',
        '    </nav>',
        '    <div class="tab-content" id="nav-tabContent">',
        *tab_panes,
        '    </div>',
        '  </div>',
        '</section>',
        MARKER_END,
    ]
    return "\n".join(lines)


def inject_into_file(html_path, new_block):
    content = Path(html_path).read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL
    )
    if not pattern.search(content):
        raise ValueError(f"Markers not found in {html_path}")
    updated = pattern.sub(new_block, content)
    Path(html_path).write_text(updated, encoding="utf-8")
    print(f"Updated: {html_path}")


def main():
    base = Path(__file__).parent
    csv_path = sys.argv[1] if len(sys.argv) > 1 else base / "schedule.csv"

    rows = read_csv(csv_path)
    days = build_days(rows)

    inject_into_file(base / "agenda.html",    render_html(days, lang="en"))
    inject_into_file(base / "agenda_fr.html", render_html(days, lang="fr"))


if __name__ == "__main__":
    main()