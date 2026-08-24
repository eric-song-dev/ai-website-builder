import html
import json
import re
from urllib.parse import quote

from .models import CodeMode
from .schemas import GeneratedBundle, GeneratedFile, ReviewResult, SitePlan


def _safe(value: str) -> str:
    return html.escape(value, quote=True)


def _asset_uri(asset: dict) -> str:
    return "data:image/svg+xml," + quote(asset["content"])


def _copy(prompt: str, plan: SitePlan) -> dict[str, str]:
    clean = " ".join(prompt.split())
    return {
        "eyebrow": "Designed around your next move",
        "headline": plan.title,
        "lede": clean[:220],
        "cta": "Start the conversation",
    }


def _shared_css(palette: list[str]) -> str:
    primary, accent, ink, paper = (palette + ["#6d5dfc", "#20c997", "#0d1526", "#f7f7fb"])[:4]
    return f"""
:root{{--primary:{primary};--accent:{accent};--ink:{ink};--paper:{paper};--muted:#64748b;--line:#dfe3eb}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif;line-height:1.6}}
a{{color:inherit}}.shell{{width:min(1120px,calc(100% - 40px));margin:auto}}nav{{display:flex;align-items:center;justify-content:space-between;padding:24px 0}}.brand{{display:flex;align-items:center;gap:10px;font-weight:850;text-decoration:none}}.brand-mark{{width:34px;height:34px;border-radius:11px;background:linear-gradient(135deg,var(--primary),var(--accent));box-shadow:0 8px 20px color-mix(in srgb,var(--primary) 25%,transparent)}}.nav-links{{display:flex;gap:24px;align-items:center}}.nav-links a{{text-decoration:none;color:var(--muted);font-weight:650}}.button{{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:999px;background:var(--ink);color:white;padding:13px 21px;font-weight:750;text-decoration:none;cursor:pointer;transition:.2s transform,.2s box-shadow}}.button:hover{{transform:translateY(-2px);box-shadow:0 12px 30px #0f172a22}}.button.alt{{background:transparent;color:var(--ink);border:1px solid var(--line)}}
main{{overflow:hidden}}.hero{{padding:78px 0 100px;display:grid;grid-template-columns:1.05fr .95fr;gap:64px;align-items:center}}.eyebrow{{font-size:.8rem;letter-spacing:.16em;text-transform:uppercase;color:var(--primary);font-weight:850}}h1{{font-size:clamp(3rem,6vw,6.4rem);line-height:.92;letter-spacing:-.07em;margin:18px 0 26px;max-width:12ch}}.lede{{font-size:1.14rem;color:var(--muted);max-width:58ch}}.actions{{display:flex;gap:12px;margin-top:32px;flex-wrap:wrap}}.hero-art{{position:relative;min-height:530px;border-radius:36px;background:linear-gradient(155deg,#fff,#ececfa);border:1px solid white;box-shadow:0 30px 90px #312e8122;overflow:hidden}}.hero-art img{{width:100%;height:100%;object-fit:cover;position:absolute;inset:0}}.floating-card{{position:absolute;left:24px;right:24px;bottom:24px;padding:20px;border-radius:22px;background:#ffffffdd;backdrop-filter:blur(18px);box-shadow:0 18px 50px #0f172a22}}
.section{{padding:95px 0}}.section-label{{color:var(--primary);font-weight:850}}h2{{font-size:clamp(2rem,4vw,4rem);line-height:1;letter-spacing:-.045em;margin:14px 0 44px;max-width:15ch}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}.card{{padding:28px;border-radius:24px;background:white;border:1px solid var(--line);box-shadow:0 18px 50px #0f172a0a}}.card .num{{font-size:.8rem;color:var(--primary);font-weight:850}}.card h3{{font-size:1.28rem;margin:35px 0 8px}}.card p{{color:var(--muted);margin:0}}.proof{{display:grid;grid-template-columns:.8fr 1.2fr;gap:28px;align-items:center}}.proof img{{width:100%;border-radius:28px;background:white}}blockquote{{font-size:clamp(1.6rem,3vw,3rem);line-height:1.2;letter-spacing:-.03em;margin:0}}blockquote footer{{font-size:1rem;color:var(--muted);margin-top:24px}}.cta-panel{{padding:70px;border-radius:36px;background:var(--ink);color:white;display:flex;justify-content:space-between;gap:30px;align-items:center}}.cta-panel h2{{margin:0}}.cta-panel .button{{background:var(--accent);color:var(--ink)}}footer.site-footer{{padding:40px 0;color:var(--muted);display:flex;justify-content:space-between;border-top:1px solid var(--line)}}
@media(max-width:780px){{.nav-links a:not(.button){{display:none}}.hero,.proof{{grid-template-columns:1fr}}.hero{{padding-top:40px}}.hero-art{{min-height:390px}}.grid{{grid-template-columns:1fr}}.cta-panel{{padding:38px;display:block}}h1{{font-size:clamp(3.2rem,16vw,5.2rem)}}}}
@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;transition:none!important}}}}
"""


def _nav(title: str, prefix: str = "") -> str:
    return f'''<nav class="shell"><a class="brand" href="{prefix}index.html"><span class="brand-mark"></span>{_safe(title[:28])}</a><div class="nav-links"><a href="{prefix}about.html">About</a><a href="{prefix}contact.html">Contact</a><a class="button" href="#contact">Let's talk</a></div></nav>'''


def _home_body(prompt: str, plan: SitePlan, assets: list[dict]) -> str:
    copy = _copy(prompt, plan)
    hero = next(item for item in assets if item["kind"] == "stock")
    diagram = next(item for item in assets if item["kind"] == "diagram")
    return f'''
<main><section class="hero shell"><div><div class="eyebrow">{copy["eyebrow"]}</div><h1>{_safe(copy["headline"])}</h1><p class="lede">{_safe(copy["lede"])}</p><div class="actions"><a class="button" href="#contact">{copy["cta"]}</a><a class="button alt" href="#approach">See our approach</a></div></div><div class="hero-art"><img src="{_asset_uri(hero)}" alt="Abstract gradient landscape"><div class="floating-card"><strong>Built for momentum.</strong><br><span>Clear story, considered details, confident launch.</span></div></div></section>
<section class="section shell" id="approach"><div class="section-label">What makes it work</div><h2>A focused path from idea to impact.</h2><div class="grid"><article class="card"><span class="num">01 / CLARITY</span><h3>Find the signal</h3><p>Turn the raw idea into a message your audience understands in seconds.</p></article><article class="card"><span class="num">02 / CRAFT</span><h3>Shape the experience</h3><p>Build a responsive system with strong hierarchy and a memorable visual voice.</p></article><article class="card"><span class="num">03 / LAUNCH</span><h3>Move with confidence</h3><p>Ship a tested experience that is simple to use, share, and evolve.</p></article></div></section>
<section class="section shell proof"><img src="{_asset_uri(diagram)}" alt="Idea to website process diagram"><blockquote>“The best websites don't ask people to decode them. They make the next step feel inevitable.”<footer>— The design principle behind this build</footer></blockquote></section>
<section class="section shell" id="contact"><div class="cta-panel"><h2>Ready to make the idea real?</h2><a class="button" href="mailto:hello@example.com">Start now →</a></div></section></main>'''


def _document(title: str, css: str, body: str, nav: str, script: str = "") -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="AI-generated, responsive website"><title>{_safe(title)}</title><style>{css}</style></head><body>{nav}{body}<footer class="site-footer shell"><span>© 2026 {_safe(title)}</span><span>Designed with intention.</span></footer>{script}</body></html>"""


def generate_bundle(
    mode: CodeMode, prompt: str, plan: SitePlan, assets: list[dict]
) -> GeneratedBundle:
    palette = next(item.get("palette") for item in assets if item["kind"] == "branding")
    css = _shared_css(palette)
    home = _home_body(prompt, plan, assets)
    if mode == CodeMode.single_html:
        content = _document(
            plan.title,
            css,
            home,
            _nav(plan.title),
            "<script>document.documentElement.classList.add('ready')</script>",
        )
        return GeneratedBundle(files=[GeneratedFile(path="index.html", content=content)])
    if mode == CodeMode.multi_page:
        shared_nav = _nav(plan.title)
        index = _document(
            plan.title,
            "@import url('assets/styles.css');",
            home,
            shared_nav,
            '<script src="assets/app.js"></script>',
        )
        about_body = '<main class="section shell"><div class="section-label">About</div><h1>Work with purpose.</h1><p class="lede">We translate ambitious ideas into clear digital experiences, combining strategy, craft, and pragmatic delivery.</p><div class="grid"><article class="card"><h3>Listen</h3><p>Understand the context and the people.</p></article><article class="card"><h3>Make</h3><p>Prototype the strongest path quickly.</p></article><article class="card"><h3>Learn</h3><p>Use feedback to sharpen the result.</p></article></div></main>'
        contact_body = '<main class="section shell" id="contact"><div class="section-label">Contact</div><h1>Let’s build what’s next.</h1><p class="lede">Share the outcome you want and the constraint keeping you from it.</p><p><a class="button" href="mailto:hello@example.com">hello@example.com</a></p></main>'
        return GeneratedBundle(
            files=[
                GeneratedFile(path="index.html", content=index),
                GeneratedFile(
                    path="about.html",
                    content=_document(
                        f"About — {plan.title}",
                        "@import url('assets/styles.css');",
                        about_body,
                        shared_nav,
                        '<script src="assets/app.js"></script>',
                    ),
                ),
                GeneratedFile(
                    path="contact.html",
                    content=_document(
                        f"Contact — {plan.title}",
                        "@import url('assets/styles.css');",
                        contact_body,
                        shared_nav,
                        '<script src="assets/app.js"></script>',
                    ),
                ),
                GeneratedFile(path="assets/styles.css", content=css),
                GeneratedFile(
                    path="assets/app.js", content="document.documentElement.classList.add('ready');"
                ),
            ]
        )
    app = f"""const features = ["Find the signal", "Shape the experience", "Move with confidence"];
export default function App() {{ return <><nav className="shell"><a className="brand" href="#top"><span className="brand-mark" />{json.dumps(plan.title[:28])}</a><div className="nav-links"><a href="#approach">Approach</a><a className="button" href="#contact">Let's talk</a></div></nav><main id="top"><section className="hero shell"><div><div className="eyebrow">Designed around your next move</div><h1>{json.dumps(plan.title)}</h1><p className="lede">{json.dumps(prompt[:220])}</p><div className="actions"><a className="button" href="#contact">Start the conversation</a><a className="button alt" href="#approach">See our approach</a></div></div><div className="hero-art"><img src={json.dumps(_asset_uri(next(item for item in assets if item["kind"] == "stock")))} alt="Abstract gradient landscape"/><div className="floating-card"><strong>Built for momentum.</strong><br/>Clear story, considered details, confident launch.</div></div></section><section className="section shell" id="approach"><div className="section-label">What makes it work</div><h2>A focused path from idea to impact.</h2><div className="grid">{{features.map((feature,index)=><article className="card" key={{feature}}><span className="num">0{{index+1}} / SYSTEM</span><h3>{{feature}}</h3><p>Every decision supports clarity, trust, and the next useful action.</p></article>)}}</div></section><section className="section shell" id="contact"><div className="cta-panel"><h2>Ready to make the idea real?</h2><a className="button" href="mailto:hello@example.com">Start now →</a></div></section></main><footer className="site-footer shell"><span>© 2026 {json.dumps(plan.title)}</span><span>Designed with intention.</span></footer></> }}"""
    return GeneratedBundle(
        files=[
            GeneratedFile(path="src/App.tsx", content=app),
            GeneratedFile(path="src/styles.css", content=css),
        ]
    )


def review_bundle(bundle: GeneratedBundle, mode: CodeMode) -> ReviewResult:
    issues: list[str] = []
    contents = "\n".join(file.content for file in bundle.files)
    if mode != CodeMode.react and "<!doctype html>" not in contents.lower():
        issues.append("Missing HTML document declaration")
    if "<h1" not in contents and "<h1" not in contents.replace("className", "class"):
        issues.append("Missing primary heading")
    if "viewport" not in contents and mode != CodeMode.react:
        issues.append("Missing responsive viewport")
    if "@media" not in contents:
        issues.append("Missing responsive rules")
    return ReviewResult(approved=not issues, issues=issues, score=max(0, 100 - len(issues) * 20))


def repair_bundle(bundle: GeneratedBundle, issues: list[str]) -> GeneratedBundle:
    repaired = bundle.model_copy(deep=True)
    for file in repaired.files:
        if file.path.endswith(".css"):
            file.content += "\n/* automated review repair */\nimg{max-width:100%;height:auto}"
        elif file.path.endswith(".html") and "viewport" not in file.content:
            file.content = file.content.replace(
                "<head>",
                '<head><meta name="viewport" content="width=device-width,initial-scale=1">',
            )
    return repaired


def revise_bundle(
    bundle: GeneratedBundle, mode: CodeMode, instruction: str, selected: dict | None
) -> GeneratedBundle:
    revised = bundle.model_copy(deep=True)
    note = _safe(instruction[:120])
    selector = (selected or {}).get("selector", "the selected section")
    css_note = f"\n/* Revision: {re.sub(r'[^\w .,-]', '', instruction[:100])} */\n"
    if any(word in instruction.lower() for word in ["dark", "深色", "darker"]):
        css_note += ":root{--paper:#0b1020;--ink:#f8fafc;--muted:#aeb8cc;--line:#26324a}.card{background:#121a2d}.button.alt{color:var(--ink)}}"
    else:
        css_note += ".revision-accent{outline:3px solid var(--accent);outline-offset:4px}"
    css_target = next((file for file in revised.files if file.path.endswith("styles.css")), None)
    if css_target:
        css_target.content += css_note
    else:
        html_target = next(file for file in revised.files if file.path.endswith(".html"))
        html_target.content = html_target.content.replace("</style>", css_note + "</style>")
    target = next(
        (file for file in revised.files if file.path in {"index.html", "src/App.tsx"}),
        revised.files[0],
    )
    if target.path.endswith(".html"):
        banner = f'<aside class="floating-card" style="position:fixed;z-index:20;left:20px;right:auto" aria-label="Latest revision"><strong>Updated:</strong> {note}<br><small>{_safe(selector)}</small></aside>'
        target.content = target.content.replace("</body>", banner + "</body>")
    else:
        target.content = target.content.replace(
            '<main id="top">',
            f'<aside className="floating-card" style={{{{position:"fixed",zIndex:20,left:20,right:"auto"}}}}><strong>Updated:</strong> {json.dumps(note)}</aside><main id="top">',
        )
    return revised
