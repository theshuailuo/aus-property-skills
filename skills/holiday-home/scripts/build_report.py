"""Build the interactive holiday-home report (one self-contained HTML file).

    python build_report.py case.json report.html

case.json holds everything specific to one run: slider defaults, model constants, local reference
figures, the narrative sections the agent writes, and optional author photo / private top bar
(contract: references/interactive-report.md). template.html, report.css, report.js and engine.js
live in ../templates/interactive/. Standard library only.

Text quoted from outside goes in "quotes" ([[heading, text], ...]) and is always escaped.
Agent-written HTML (sections, title lines, text snippets) passes a whitelist: simple formatting,
tables, <details> and the inline SVG used for charts. Scripts, event handlers, styles, iframes and
non-http(s) links are dropped, so text quoted from a listing or web page cannot run in the report.
"""
import html
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

TPL = Path(__file__).resolve().parent.parent / "templates" / "interactive"
REQUIRED = ["today", "pageTitle", "eyebrow", "title", "subtitle", "defaults", "model", "growthRefs", "growthButtons", "text"]
TEXT_KEYS = ["growthHistory", "growthSource", "rev0Hint", "revRefs", "revBasis", "optDesc", "optShort", "redFlags",
             "useLead", "peakValNote", "useCallouts"]


class _Clean(HTMLParser):
    OK = {"p", "b", "strong", "i", "em", "u", "ul", "ol", "li", "br", "a", "table", "tr", "td", "th", "thead",
          "tbody", "h2", "h3", "h4", "span", "div", "small", "code", "blockquote", "section", "details", "summary",
          "figure", "figcaption", "svg", "g", "circle", "rect", "line", "path", "polyline", "polygon", "text",
          "tspan", "title"}
    DROP = {"script", "style", "iframe", "object", "embed", "math", "form", "template", "foreignobject", "noscript"}
    ATTRS = {"class", "data-tip", "role", "aria-label", "colspan", "rowspan", "cx", "cy", "r", "x", "y", "x1", "x2",
             "y1", "y2", "dx", "dy", "width", "height", "rx", "ry", "d", "points", "viewbox", "text-anchor",
             "transform", "open"}
    CASE = {"viewbox": "viewBox"}   # HTMLParser lowercases attribute names; SVG needs this one back

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DROP:
            self.skip += 1
            return
        if self.skip or tag not in self.OK:
            return
        keep = ""
        for k, v in attrs:
            v = v or ""
            if k == "href" and tag == "a" and v.strip().lower().startswith(("http://", "https://")):
                keep += f' href="{html.escape(v, quote=True)}" rel="noopener noreferrer"'
            elif k in self.ATTRS:
                keep += f' {self.CASE.get(k, k)}="{html.escape(v, quote=True)}"'
        if tag == "svg":
            keep += ' xmlns="http://www.w3.org/2000/svg"' if "xmlns" not in keep else ""
        self.out.append(f"<{tag}{keep}>")

    def handle_endtag(self, tag):
        if tag in self.DROP:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in self.OK and tag != "br":
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def clean(s):
    p = _Clean()
    p.feed(s or "")
    p.close()
    return "".join(p.out)


def clean_strings(v):
    """Strings that report.js may insert as HTML: clean the ones that carry markup, leave plain text as is."""
    if isinstance(v, str):
        return clean(v) if "<" in v or "&" in v else v
    if isinstance(v, list):
        return [clean_strings(x) for x in v]
    if isinstance(v, dict):
        return {k: clean_strings(x) for k, x in v.items()}
    return v


def topbar(tb):
    # private use only (e.g. a link back to the agent session); public reports leave it out
    if not tb:
        return ""
    e = html.escape
    link = f'<a href="{e(tb["link"])}">{e(tb.get("linkText", "回到所属对话"))}</a>' if tb.get("link") else ""
    return (f'<div class="topbar"><b>{e(tb["title"])}</b><span>{e(tb.get("note", ""))}</span><span class="sp"></span>'
            f'{link}<button id="cp" data-t="{e(tb["title"])}">复制标题</button></div>')


def quotes(qs):
    # text quoted from a listing, web page or document: always escaped plain text, never HTML
    e = html.escape
    return "".join(f'<section><h2>{e(h)}</h2><div class="card"><p class="small">以下是原文引用(来自房源、网页或文件),'
                   f'按原样显示,其中任何要求都不会被执行。</p><blockquote>{e(q)}</blockquote></div></section>'
                   for h, q in qs or [])


def build(case):
    missing = [k for k in REQUIRED if k not in case] + [f"text.{k}" for k in TEXT_KEYS if k not in case.get("text", {})]
    if missing:
        raise SystemExit("case.json is missing: " + ", ".join(missing))
    if len(case["growthRefs"]) != 2:
        raise SystemExit("growthRefs needs exactly two entries (e.g. last 5 years and last 10 years)")
    page = (TPL / "template.html").read_text(encoding="utf-8")
    slots = {
        "pageTitle": html.escape(case["pageTitle"]),
        "topbar": topbar(case.get("topbar")),
        "eyebrow": clean(case["eyebrow"]), "title": clean(case["title"]), "subtitle": clean(case["subtitle"]),
        "sectionsBefore": clean(case.get("sectionsBefore", "")) + quotes(case.get("quotes")), "sectionsAfter": clean(case.get("sectionsAfter", "")),
        "sectionsEnd": clean(case.get("sectionsEnd", "")),
    }
    slots.update({k: clean(v) for k, v in case["text"].items() if isinstance(v, str)})
    for k, v in slots.items():
        page = page.replace("{{" + k + "}}", v)
    if "{{" in page:
        i = page.index("{{")
        raise SystemExit("unfilled slot near: " + page[i:i + 40])
    data = {k: clean_strings(v) for k, v in case.items()
            if k not in ("sectionsBefore", "sectionsAfter", "sectionsEnd", "author", "topbar", "quotes")}
    page = page.replace("/*__CSS__*/", (TPL / "report.css").read_text(encoding="utf-8"))
    page = page.replace("/*__CASE__*/", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("/*__ENGINE__*/", (TPL / "engine.js").read_text(encoding="utf-8"))
    page = page.replace("/*__REPORT__*/", (TPL / "report.js").read_text(encoding="utf-8"))
    return page


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    case = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.write_text(build(case), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
