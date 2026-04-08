"""
Wrapper around gen2.py that writes the schedule HTML directly into
the Zola shortcode files schedule_en.html and schedule_fr.html.

Usage:
    uv run gen_schedule.py ~/Downloads/EGMO\ EdT/Détail-Table\ 1.csv
"""

import sys
from pathlib import Path

# Add parent dir so we can import gen2
sys.path.insert(0, str(Path(__file__).parent))
from gen2 import read_csv, build_days, render_html, MARKER_START, MARKER_END

SHORTCODES = Path(__file__).parent / "zola/templates/shortcodes"

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "schedule.csv"
    rows = read_csv(csv_path)
    days = build_days(rows)

    for lang, fname in [("en", "schedule_en.html"), ("fr", "schedule_fr.html")]:
        html = render_html(days, lang=lang)
        # Strip the marker comments — shortcodes don't need them
        html = html.replace(MARKER_START + "\n", "").replace("\n" + MARKER_END, "")
        out = SHORTCODES / fname
        out.write_text(html + "\n", encoding="utf-8")
        print(f"Written: {out}")

if __name__ == "__main__":
    main()
