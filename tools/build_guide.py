#!/usr/bin/env python3
"""Builds the user guide, guide/<version>/*.html, from tools/guide/<version>/.

  python3 tools/build_guide.py            # builds every version under tools/guide/

A version's folder holds:
  help.json            the app's own Help pages, exported from the app's source
                       (HELP_EXPORT=…/help.json swift test --filter exportsTheHelpPages), so the
                       reference can't drift from the app
  install.html, quick-start.html, persistent-workspace.html
                       the install page and the walkthroughs, written by hand

The guide is versioned by the app's major version (v0 for 0.x). When a major version changes how
the app works, copy tools/guide/v0 to tools/guide/v1, export its help.json again, set CURRENT below,
and build: guide/v0/ stays as it was, and guide/ sends readers to the current one.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "tools" / "guide"
CURRENT = "v0"
APP_VERSIONS = {"v0": "MicroVM Studio 0.x"}

WALKTHROUGHS = [("install", "Install"), ("quick-start", "Quick start"), ("persistent-workspace", "A workspace that keeps its files")]
# A Help page whose id is taken by a walkthrough gets another file name.
RENAMED = {"persistent-workspace": "persistent-workspace-reference"}

HEADER = """<header class="site-header"><div class="wrap">
<a class="brand" href="../../"><span class="brand-mark" aria-hidden="true"></span>MicroVM Studio</a>
<nav class="site-nav" aria-label="Site">
<a href="../" aria-current="page">User guide</a>
<a href="../../#videos">Walkthroughs</a>
<a href="install.html">Download</a>
</nav></div></header>"""

FOOTER = """<footer class="site-footer"><div class="wrap">
<nav aria-label="Footer"><a href="../">User guide</a><a href="../../privacy.html">Privacy</a><a href="../../eula.html">Licence</a><a href="https://github.com/fabiodouek/microvm-studio/issues">Support</a><a href="https://www.my2cents.ai/">my2cents.ai</a></nav>
<p>Made by Fabio Douek. More from the author at <a href="https://www.my2cents.ai/">my2cents.ai</a>.</p>
<p>MicroVM Studio is an independent project. It isn't affiliated with, endorsed by or sponsored by Amazon Web Services or Anthropic. AWS, AWS Lambda and Amazon EFS are trademarks of Amazon.com, Inc. or its affiliates.</p>
</div></footer>"""


def inline(text, links):
    """The Help pages' inline Markdown (**bold**, `code` and [text](url)), and "See <Page>" as a link."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\[([^\]]+)\]\((https://[^)\s]+)\)", r'<a href="\2">\1</a>', out)
    for title, href in links.items():
        out = re.sub(r"\b[Ss]ee " + re.escape(html.escape(title, quote=False)) + r"\b",
                     lambda m: m.group(0)[:4] + f'<a href="{href}">{html.escape(title, quote=False)}</a>', out)
    return out


def topic_body(topic, links):
    parts = [f"<h1>{html.escape(topic['title'])}</h1>"]
    in_list = False
    own = {k: v for k, v in links.items() if k != topic["title"]}
    for block in topic["blocks"]:
        if block["kind"] == "bullet":
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{inline(block['text'], own)}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        tag = "h2" if block["kind"] == "heading" else "p"
        parts.append(f"<{tag}>{inline(block['text'], own)}</{tag}>")
    if in_list:
        parts.append("</ul>")
    return "\n".join(parts)


def page(version, title, body, nav, current, pager):
    items = []
    for heading, entries in nav:
        items.append(f"<h2>{heading}</h2><ul>")
        for name, label in entries:
            mark = ' aria-current="page"' if name == current else ""
            items.append(f'<li><a href="{name}.html"{mark}>{html.escape(label)}</a></li>')
        items.append("</ul>")
    prev, nxt = pager
    links = ['<span></span>' if not prev else f'<a href="{prev[0]}.html">← {html.escape(prev[1])}</a>',
             '<span></span>' if not nxt else f'<a href="{nxt[0]}.html">{html.escape(nxt[1])} →</a>']
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)} · MicroVM Studio user guide</title>
<link rel="icon" type="image/png" href="../../assets/favicon.png"><link rel="apple-touch-icon" href="../../assets/apple-touch-icon.png">
<link rel="stylesheet" href="../../assets/site.css"></head><body>
{HEADER}
<div class="wrap guide">
<nav class="guide-nav" aria-label="User guide">
<span class="version">Guide {version} · {html.escape(APP_VERSIONS.get(version, version))}</span>
{''.join(items)}
</nav>
<main class="guide-body">
{body}
<div class="pager">{''.join(links)}</div>
</main>
</div>
{FOOTER}
</body></html>
"""


def build(version):
    source = SOURCES / version
    out = ROOT / "guide" / version
    out.mkdir(parents=True, exist_ok=True)
    topics = json.loads((source / "help.json").read_text())
    names = {t["id"]: RENAMED.get(t["id"], t["id"]) for t in topics}
    links = {t["title"]: names[t["id"]] + ".html" for t in topics}
    nav = [("Start here", [("index", "Overview")] + WALKTHROUGHS),
           ("Reference", [(names[t["id"]], t["title"]) for t in topics])]
    order = [entry for _, entries in nav for entry in entries]

    def pager(name):
        i = [n for n, _ in order].index(name)
        return (order[i - 1] if i > 0 else None, order[i + 1] if i + 1 < len(order) else None)

    reference = "".join(f'<li><a href="{names[t["id"]]}.html">{html.escape(t["title"])}</a></li>' for t in topics)
    overview = f"""<h1>MicroVM Studio user guide</h1>
<p class="lead muted">MicroVM Studio starts AWS Lambda MicroVMs from workspaces you set up, and gives each one a terminal on your Mac.</p>
<p>This is guide <strong>{version}</strong>, for {html.escape(APP_VERSIONS.get(version, version))}. The guide is versioned with the app's major version; older versions stay at their own address when a new one is published. The app opens it from <strong>Help → User Guide</strong>.</p>
<h2>Start here</h2>
<ul>
<li><a href="install.html"><strong>Install</strong></a>: what you need, the download, and the first launch.</li>
<li><a href="quick-start.html"><strong>Quick start</strong></a>: from a new install to a running MicroVM, with GitHub and Claude Code. Needs no VPC.</li>
<li><a href="persistent-workspace.html"><strong>A workspace that keeps its files</strong></a>: a network connector, an EFS file system, and a <code>/workspace</code> that outlives its MicroVMs.</li>
</ul>
<h2>Reference</h2>
<ul>{reference}</ul>
<h2>Words used here</h2>
<ul>
<li><strong>MicroVM:</strong> a small virtual machine run by AWS Lambda, in your account. It bills while it runs, can be suspended, and stops for good after at most 8 hours.</li>
<li><strong>Workspace:</strong> what a MicroVM starts with: its image, repos, sign-ins, secrets, setup and limits. Saved on your Mac; you launch MicroVMs from it.</li>
<li><strong>Image:</strong> what a MicroVM boots from, built in your account. It also sets the MicroVM's memory and CPU.</li>
<li><strong>Network connector:</strong> how a MicroVM reaches the network: AWS's own internet egress, or one in your VPC.</li>
</ul>"""
    (out / "index.html").write_text(page(version, "Overview", overview, nav, "index", pager("index")))
    for name, label in WALKTHROUGHS:
        (out / f"{name}.html").write_text(page(version, label, (source / f"{name}.html").read_text(), nav, name, pager(name)))
    for topic in topics:
        name = names[topic["id"]]
        (out / f"{name}.html").write_text(page(version, topic["title"], topic_body(topic, links), nav, name, pager(name)))
    return len(topics) + len(WALKTHROUGHS) + 1


def main():
    for source in sorted(p for p in SOURCES.iterdir() if p.is_dir()):
        print(f"guide/{source.name}: {build(source.name)} pages")
    # guide/ sends readers to the current version; the app's Help → User Guide opens this address.
    (ROOT / "guide" / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={CURRENT}/">
<link rel="canonical" href="{CURRENT}/"><link rel="icon" type="image/png" href="../assets/favicon.png"><title>MicroVM Studio user guide</title></head>
<body><p>The user guide is at <a href="{CURRENT}/">{CURRENT}/</a>.</p></body></html>
""")


if __name__ == "__main__":
    main()
