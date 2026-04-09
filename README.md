# EGMO 2026 Website — Developer Guide

This website is built with [Zola](https://www.getzola.org/), a static site generator. This guide explains how to modify the site, assuming you are familiar with what a static site generator does but have not used Zola before.

---

## Prerequisites & Installation

### Zola

Zola is a single binary — no dependencies. Install it from [getzola.org](https://www.getzola.org/documentation/getting-started/installation/).

On macOS with Homebrew:
```bash
brew install zola
```

The site was built with **Zola 0.22.x**. Check your version with `zola --version`.

### uv (for the schedule script only)

The schedule generation script (`gen_schedule.py`) uses Python. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to run it without managing a virtualenv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Local development

```bash
zola serve
```

Opens a live-reloading dev server at `http://127.0.0.1:1111`. Edit any file and the browser refreshes automatically.

### Building the site

```bash
zola build
```

Output goes to `public/`. This directory is gitignored — never edit files there directly. Always edit source files and rebuild.

---

## Directory Structure

```
config.toml              Zola configuration (base URL, languages, nav labels)
gen_schedule.py          Python script to regenerate the schedule from a CSV
.gitignore               Ignores public/, .claude/, __pycache__/

content/                 All page content (Markdown files)
  _index.md              Homepage (English)
  _index.fr.md           Homepage (French)
  competition/           Regulations, participation, problems, deadlines, code of conduct
  information/           Venue & accommodation, travel
  news/                  News articles
  organization/          Team, sponsors
  programme/             Agenda, activities, excursions

templates/               HTML templates (Tera templating language)
  base.html              Master layout: header, nav, footer, lang switcher
  index.html             Homepage template
  news.html              News listing template
  page.html              Generic page template (used by almost all pages)
  shortcodes/            Reusable components called from content files

static/                  Static assets — copied as-is to public/
  assets/
    css/main.css         Main stylesheet (Bootstrap + custom)
    js/main.js           Main JavaScript
    img/                 Photos, logos, icons
    vendor/              Bootstrap, AOS, GLightbox, Swiper, etc.

public/                  GENERATED — do not edit (gitignored)
```

---

## Zola & Tera Syntax Primer

Zola uses the **Tera** templating language. There are two kinds of syntax:

### `{{ expression }}` — Output a value

Renders a variable or expression into the HTML. Tera **auto-escapes** all output, so special characters like `<`, `>`, `&`, `/` are turned into HTML entities. This is safe for text content but breaks URLs (see the [URL escaping gotcha](#gotcha-url-auto-escaping) below).

```html
{{ page.title }}           outputs the page title
{{ trans(key="home") }}    outputs the translated navigation label
{{ post.date | date(format="%B %e, %Y") }}   formats a date
```

### `{% statement %}` — Control flow

Does not output anything directly. Used for logic, variable assignment, inheritance, and shortcode definitions.

```html
{% if lang == "fr" %} ... {% endif %}
{% for post in section.pages %} ... {% endfor %}
{% set pfx = "/fr" %}
{% extends "base.html" %}
{% block content %} ... {% endblock content %}
```

### `{{ value | filter }}` — Filters

Transform a value before outputting it. Filters can be chained with `|`.

```html
{{ body | markdown | safe }}    convert markdown to HTML, then mark as safe
{{ url | safe }}                mark URL as trusted (don't escape slashes)
{{ post.date | date(format="%e %B %Y", locale="fr_FR") }}
{{ path | replace(from='/fr/', to='/') | safe }}
```

### Shortcodes

Shortcodes are reusable components defined in `templates/shortcodes/`. They are called from **content files** (not from templates).

**Without body** (inline shortcode):
```
{{ youtube(id="NzezrXjpmKI") }}
{{ team_member(name="Jane Doe", role="Organizer", photo="assets/img/team/jane.jpg") }}
```

**With body** (block shortcode):
```
{% content_section(title="My Section") %}
This is **markdown** content inside the section.
{% end %}
```

Inside the shortcode template, parameters are accessed as variables (`{{ title }}`), and the body content (if any) is accessed as `{{ body | safe }}` or `{{ body | markdown | safe }}`.

---

## Template Inheritance

All pages share a common layout defined in `templates/base.html`. Other templates inherit from it:

```html
{% extends "base.html" %}

{% block content %}
  <!-- Page-specific HTML here -->
{% endblock content %}
```

`base.html` defines several named blocks that child templates can override:

- `{% block content %}` — the main page content
- `{% block title %}` — the `<title>` tag
- `{% block nav_home %}`, `{% block nav_news %}`, `{% block nav_competition %}`, etc. — used to add `class="active"` to the current nav item

For example, the news listing template does:
```html
{% block nav_news %}class="active"{% endblock nav_news %}
```

**How a page gets rendered:**
1. Zola processes the Markdown file and expands all shortcodes in it
2. The resulting HTML is stored in `page.content`
3. The template (usually `page.html`) renders `{{ page.content | safe }}`
4. That gets inserted into `base.html`'s `{% block content %}`

---

## Multilingual System

The site has two languages: **English** (default) and **French**.

### File naming

| Content file | URL |
|---|---|
| `content/foo/bar.md` | `/foo/bar/` |
| `content/foo/bar.fr.md` | `/fr/foo/bar/` |
| `content/foo/_index.md` | `/foo/` (section index) |
| `content/foo/_index.fr.md` | `/fr/foo/` |

If a `.fr.md` file does not exist for a page, that page simply won't be generated in French.

### Translation strings

Navigation labels and other UI strings are defined in `config.toml`:

```toml
[translations]
home = "Home"
news = "News"

[languages.fr.translations]
home = "Accueil"
news = "Nouvelles"
```

Used in templates as `{{ trans(key="home") }}`. Zola automatically picks the right language.

### The `pfx` variable

In `base.html`, a `pfx` variable is set at the top of every page:

```html
{% if lang == "fr" %}{% set pfx = "/fr" %}{% else %}{% set pfx = "" %}{% endif %}
```

All navigation links use `pfx`:
```html
<a href="{{ pfx }}/news/">{{ trans(key="news") }}</a>
<a href="{{ pfx }}/competition/regulations/">{{ trans(key="regulations") }}</a>
```

This ensures English pages link to `/news/` and French pages link to `/fr/news/` without duplicating the nav markup.

**Why not use `config.base_url`?** Because `config.base_url` is `https://egmo2026.fr` and Tera auto-escapes the `://` to `https:&#x2F;&#x2F;` when output in an `href`. Root-relative paths avoid this problem entirely.

### Language switcher

The EN/FR toggle in the header extracts the current page's path from its permalink, then produces the equivalent path in the other language:

```html
{% set current_permalink = page.permalink | default(value=section.permalink | default(value=config.base_url)) %}
{% set current_path = current_permalink | replace(from=config.base_url, to='') %}
{% if lang == "fr" %}
  <a href="{{ current_path | replace(from='/fr/', to='/') | safe }}">EN</a>
{% else %}
  <a href="/fr/{{ current_path | trim_start_matches(pat='/') | safe }}">FR</a>
{% endif %}
```

The `| safe` filter is required here because paths contain `/` which Tera would otherwise escape to `&#x2F;`.

---

## Content Files

Every page is a Markdown file with a **TOML front matter** block delimited by `+++`:

```toml
+++
title = "Regulations"
template = "page.html"
+++
```

After the front matter, write the page body. The body is Markdown, and you can freely mix in shortcode calls.

### `[extra]` fields

Custom metadata goes in `[extra]`:

```toml
+++
title = "My News Article"
date = 2025-12-14
description = "A brief summary shown in the news listing."

[extra]
author = "Jane Doe"
image = "assets/img/photo.jpg"
read_more = false
+++
```

These are accessed in templates as `page.extra.author`, `post.extra.image`, etc.

### Section index files

`_index.md` files control section-level behavior. They can optionally redirect to a subpage:

```toml
+++
redirect_to = "organization/team"
+++
```

---

## Shortcode Reference

All shortcodes live in `templates/shortcodes/`. They are called from content Markdown files.

### Content & Layout

#### `content_section`
General-purpose text section with optional heading.

```
{% content_section(title="Section Title", subtitle="Optional subtitle") %}
Body is **Markdown**. Can include links, lists, headings.
{% end %}
```

Body processed with `body | markdown | safe`.

---

#### `about_section`
Two-column layout: image on the left, text on the right.

```
{% about_section(img_src="assets/img/photo.jpg", img_alt="Description", img_width="600", title="About Us") %}
Body is **Markdown**.
{% end %}
```

| Parameter | Required | Description |
|---|---|---|
| `img_src` | yes | Path to image |
| `img_alt` | no | Alt text |
| `img_width` | no | Image width in px |
| `title` | no | Section heading |

Body processed with `body | markdown | safe`.

---

#### `contact_section`
Contact info block with map embed, address, and email.

```
{% contact_section(heading="Contact Us", address_label="Address", email_label="Email") %}
Optional extra text in **Markdown**.
{% end %}
```

Address and email are hardcoded in the template. Body processed with `body | markdown | safe`.

---

#### `centered_images`
Wraps content in a centered container. Use for image galleries or logos.

```
{% centered_images() %}
<img src="..." alt="...">
{% end %}
```

Body passed with `body | safe` (raw HTML).

---

#### `image_row`
Horizontal row of up to 7 images.

```
{% image_row(i1="assets/img/a.jpg", a1="Alt A", i2="assets/img/b.jpg", a2="Alt B", height=250) %}
```

| Parameter | Description |
|---|---|
| `i1`–`i7` | Image paths |
| `a1`–`a7` | Alt texts |
| `height` | Row height in px (default: 300) |

---

#### `youtube`
Embeds a YouTube video.

```
{{ youtube(id="NzezrXjpmKI") }}
```

---

#### `section_title`
Simple heading block (used for standalone titles without body content).

```
{% section_title(title="My Title", subtitle="Optional") %}
```

---

### Team

#### `team_grid`
Wrapper for a grid of team members (standard layout).

```
{% team_grid() %}
{{ team_member(...) }}
{{ team_member(...) }}
{% end %}
```

Body passed with `body | safe`.

---

#### `team_grid_centered`
Same as `team_grid` but horizontally centered (used for top-row leadership).

```
{% team_grid_centered() %}
{{ team_member(...) }}
{% end %}
```

---

#### `team_member`
Individual team member card.

```
{{ team_member(
  name="Jane Doe",
  role="Chief Coordinator",
  photo="assets/img/team/jane.jpg",
  linkedin="https://linkedin.com/in/jane",
  email="jane@example.com"
) }}
```

| Parameter | Required | Description |
|---|---|---|
| `name` | yes | Full name |
| `role` | yes | Job title / role |
| `photo` | yes | Path to photo |
| `linkedin` | no | LinkedIn profile URL |
| `email` | no | Email address |

**Note:** `linkedin` and `email` use `| safe` in the template — external URLs must not be escaped.

---

### Sponsors

#### `sponsors_section`
Outer wrapper for the entire sponsors page section.

```
{% sponsors_section() %}
  {% sponsor_group(title="Gold Sponsors") %}...{% end %}
{% end %}
```

Body passed with `body | safe`.

---

#### `sponsor_group`
A titled group of sponsor logos.

```
{% sponsor_group(title="Institutional Partners") %}
{{ sponsor_logo(...) }}
{% end %}
```

Body passed with `body | safe`.

---

#### `sponsor_logo`
A single sponsor logo linking to their website.

```
{{ sponsor_logo(img="assets/img/clients/logo.png", url="https://example.com", alt="Company Name") }}
```

| Parameter | Required | Description |
|---|---|---|
| `img` | yes | Path to logo image |
| `url` | yes | Sponsor website URL |
| `alt` | no | Alt text |

**Note:** `url` uses `| safe` — required for any external URL parameter.

---

### Schedule

#### `schedule_en` / `schedule_fr`
These shortcodes are **auto-generated** by `gen_schedule.py`. Do not edit them by hand. Call them in content files like any other shortcode:

```
{% schedule_en() %}{% end %}
{% schedule_fr() %}{% end %}
```

---

## News Articles

News articles live in `content/news/`. Each article is a Markdown file with date-based sorting.

### Front matter

```toml
+++
title = "Article Title"
date = 2025-12-14
description = "Summary shown in the news listing."

[extra]
author = "Author Name"
image = "assets/img/photo.jpg"
read_more = false
+++
```

### `read_more` behavior

| Value | Effect |
|---|---|
| `read_more = false` | Full article body shown inline in the news listing. No "Read more" link. Use for short articles. |
| `read_more = true` or omitted | Only the `description` is shown in the listing, with a "Read more" link to the full article page. |

### Multilingual news

Create both `article.md` and `article.fr.md`. If only one language exists, that article only appears in that language's news listing.

---

## Common Tasks

### Add a new page

1. Create `content/section/page.md` with front matter including `template = "page.html"`
2. Create `content/section/page.fr.md` for the French version
3. Write body using `{% content_section() %}` shortcodes
4. If the page should appear in the nav, edit `templates/base.html`

### Add a news article

1. Create `content/news/my-article.md` (and `my-article.fr.md` for French)
2. Set `date`, `description`, and `[extra]` fields
3. For short articles: set `read_more = false` and write full content in the file
4. For long articles: omit `read_more` and write content normally — it gets its own page

### Add a team member

Edit `content/organization/team.md` and `content/organization/team.fr.md`. Add inside a `{% team_grid() %}` block:

```
{{ team_member(name="Jane Doe", role="My Role", photo="assets/img/team/jane.jpg") }}
```

Put the photo in `static/assets/img/team/`.

### Add a sponsor

Edit `content/organization/sponsors.md` and `sponsors.fr.md`. Inside the appropriate `{% sponsor_group(title="...") %}` block, add:

```
{{ sponsor_logo(img="assets/img/clients/logo.png", url="https://sponsor.com", alt="Sponsor Name") }}
```

Put the logo in `static/assets/img/clients/`.

### Regenerate the schedule

When the timetable CSV changes:

```bash
uv run gen_schedule.py /path/to/Détail-Table\ 1.csv
```

This regenerates `templates/shortcodes/schedule_en.html` and `schedule_fr.html`. Commit those files.

The CSV must use semicolon (`;`) as delimiter and have these columns:
- `Jour` — day in French (jeudi, vendredi, samedi, dimanche, lundi, mardi, mercredi)
- `faketime` — display time (e.g., `09:00`); rows without a faketime are skipped
- `name_en`, `name_fr` — event name in each language
- `place_en`, `place_fr` — location in each language
- Group columns: `Equipes`, `Deputy leaders`, `Leaders`, `Guides`, `Coordinateurs`
  - `oui` = event applies to this group
  - `opt` = optional for this group
  - empty = not in this group's schedule

---

## Tricks & Gotchas

### Gotcha: URL Auto-Escaping

Tera escapes all `{{ }}` output by default. This means `/` becomes `&#x2F;` and `:` becomes `&#x3A;`. If you output a URL directly, it breaks:

```html
<!-- BROKEN: outputs https:&#x2F;&#x2F;example.com -->
<a href="{{ url }}">link</a>

<!-- CORRECT -->
<a href="{{ url | safe }}">link</a>
```

Any variable containing a URL or path **must** use `| safe`. This includes:
- External URLs passed as shortcode parameters (`url`, `linkedin`, `email`)
- `post.permalink` in templates
- Paths built by string manipulation (lang switcher)

Only use `| safe` on content you control (internal paths, Zola-generated permalinks, hardcoded URLs). Never on arbitrary user input.

### `body | markdown | safe` vs `body | safe`

Shortcode body content is a string. How you render it depends on what the body contains:

| Filter | Use when body contains | Examples |
|---|---|---|
| `body \| markdown \| safe` | Markdown prose (paragraphs, bold, links, lists) | `content_section`, `about_section`, `contact_section` |
| `body \| safe` | Raw HTML (`<li>`, `<div>`, nested shortcode output) | `team_grid`, `sponsor_group`, `regulations` |

If you use `body | markdown | safe` on a body that contains raw HTML tags, Markdown will escape them (e.g., `<li>` → `&lt;li&gt;`). If you use `body | safe` on Markdown text, it won't be converted to HTML. Match the filter to the content type.

### Regulations: CSS Counter Numbering

The regulations page uses CSS counters instead of the browser's native `<ol>` numbering. This allows the `1.`, `1.1.`, `1.2.` hierarchical format and the `A.`, `A.1.` annex format.

The CSS is at the bottom of `static/assets/css/main.css`:

```css
ol.regulations { counter-reset: parent-counter; list-style: none; }
ol.regulations > li { counter-increment: parent-counter; }
ol.regulations > li::marker { content: counter(parent-counter) ". "; }
ol.regulations > li > ol > li::marker {
  content: counter(parent-counter) "." counter(child-counter) ". ";
}
```

For the annex (`ol.regulations-annex`), the same pattern uses `upper-alpha` to produce `A.`, `A.1.` etc.

Because of this, the body of `{% regulations() %}` must be raw `<li>` HTML — if you put Markdown there, the `<li>` tags won't exist and the CSS counters won't apply.

### Adding a Nav Entry

If you add a new top-level page or section that should appear in the navigation:

1. Edit the `<nav>` in `templates/base.html` — add the link using `{{ pfx }}/your-section/`
2. Add a `{% block nav_yoursection %}{% endblock %}` attribute on the `<a>` tag
3. In the page's template (or in `page.html` with a dedicated template), override that block with `class="active"`
4. Add a translation key in `config.toml` under both `[translations]` and `[languages.fr.translations]`

---

## Deployment

```bash
zola build
```

Upload the contents of `public/` to the web server. The `public/` directory is completely regenerated each time, there is no incremental build.

The `public/` directory is gitignored. Never commit it.
