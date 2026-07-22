"""
flyer.py
Turns a ranked HR board (DataFrame from hr_model.run) into the stadium-scoreboard
flyer HTML. The per-player "why" line is generated from the model's own factor
columns (base power, park, platoon, opposing-pitcher rate, lineup slot), so the
flyer explains itself without a human writing copy each night.
"""

# Short park names for the notable venues (keyed by MLB Stats-API home team id).
PARK_NAMES = {
    115: "Coors Field", 113: "Great American", 147: "Yankee Stadium",
    143: "Citizens Bank", 158: "American Family", 117: "Daikin Park",
    145: "Rate Field", 119: "Dodger Stadium", 137: "Oracle Park",
    136: "T-Mobile Park", 135: "Petco Park", 146: "loanDepot park",
}


def _why(row):
    """Return (text, is_caution) describing the main drivers of this line."""
    base = float(row.get("base_pct", 0) or 0)
    px = float(row.get("park_x", 1) or 1)
    plx = float(row.get("platoon_x", 1) or 1)
    pitch_x = float(row.get("pitch_x", 1) or 1)
    slot = row.get("slot", "-")
    park = PARK_NAMES.get(row.get("venue_team_id"), "the park")

    power = "elite raw power" if base >= 6.0 else "solid power" if base >= 4.5 else "modest power"

    clauses = []
    if px >= 1.15:
        clauses.append(f"{park} inflates it")
    elif px >= 1.06:
        clauses.append(f"a {park} boost")
    elif px <= 0.90:
        clauses.append("despite a tough park")

    if pitch_x >= 1.20:
        clauses.append("against a homer-prone starter")
    elif pitch_x >= 1.08:
        clauses.append("against a hittable arm")
    elif pitch_x <= 0.85:
        clauses.append("even against a tough arm")

    if plx > 1:
        clauses.append("with the platoon edge")
    elif plx < 1:
        clauses.append("into a same-handed look")

    try:
        if int(slot) <= 2:
            clauses.append("and extra trips up top")
    except (ValueError, TypeError):
        pass

    # Caution: the number is propped up by park/matchup, not the bat.
    caution = base < 4.5 and (px >= 1.15 or pitch_x >= 1.15)

    tail = ", ".join(clauses[:2]) if clauses else "on pure skill"
    if caution:
        return f"Matchup-driven \u2014 {power}, {tail}.", True
    lead = power[0].upper() + power[1:]
    return f"{lead} \u2014 {tail}.", False


CSS = """
:root{--night:#0A1826;--panel:#12293D;--line:#1E3B54;--amber:#FFB43C;
--amber-hi:#FFD98A;--glow:#FF6A3D;--ink:#EEF4FA;--muted:#8AA2B6;--muted2:#5E7688;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:"Inter",system-ui,sans-serif;color:var(--ink);
background:radial-gradient(120% 80% at 12% -8%,rgba(255,180,60,.16),transparent 55%),
radial-gradient(120% 80% at 88% -8%,rgba(255,106,61,.13),transparent 55%),
linear-gradient(180deg,#0A1826,#0C1E30 40%,#0A1826);padding:22px 14px 40px;}
.poster{max-width:860px;margin:0 auto;}
.eyebrow{font-family:"JetBrains Mono",monospace;font-weight:700;font-size:12px;
letter-spacing:.32em;text-transform:uppercase;color:var(--amber);display:flex;align-items:center;gap:10px;}
.eyebrow::before{content:"";width:26px;height:2px;background:var(--amber);}
h1{font-family:"Oswald",sans-serif;font-weight:700;text-transform:uppercase;
font-size:clamp(38px,9vw,64px);line-height:.92;margin:12px 0 6px;}
h1 .yard{color:var(--amber);}
.datestrip{display:flex;flex-wrap:wrap;gap:6px 16px;font-family:"JetBrains Mono",monospace;
font-size:13px;color:var(--muted);padding-bottom:18px;border-bottom:1px solid var(--line);}
.datestrip b{color:var(--ink);}
.hero{position:relative;overflow:hidden;margin:20px 0 10px;border:1px solid var(--line);
border-radius:14px;padding:24px;background:linear-gradient(135deg,#15334B,#102437 70%);}
.hero .arc{position:absolute;inset:0;width:100%;height:100%;opacity:.5;pointer-events:none;}
.hero-top{display:flex;gap:16px;align-items:flex-start;position:relative;z-index:2;}
.bignum{font-family:"Oswald",sans-serif;font-weight:700;font-size:76px;line-height:.8;
color:var(--amber);text-shadow:0 0 26px rgba(255,180,60,.35);}
.hero-name{flex:1;min-width:0;}
.tag{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.16em;
text-transform:uppercase;color:var(--glow);font-weight:700;}
.hero-name h2{font-family:"Oswald",sans-serif;font-weight:600;text-transform:uppercase;
font-size:clamp(28px,6vw,44px);line-height:.95;margin:3px 0 4px;}
.matchup{color:var(--muted);font-size:14px;}.matchup b{color:var(--ink);}
.hero-stats{text-align:right;}
.pct{font-family:"Oswald",sans-serif;font-weight:700;font-size:44px;line-height:1;}
.pct small{font-size:19px;color:var(--muted);}
.odds{font-family:"JetBrains Mono",monospace;font-weight:700;font-size:18px;color:var(--night);
background:var(--amber);border-radius:6px;padding:3px 10px;display:inline-block;margin-top:8px;}
.why{position:relative;z-index:2;margin-top:15px;padding-top:14px;
border-top:1px solid rgba(255,255,255,.08);font-size:15px;color:#CFE0EE;line-height:1.45;}
.board{margin-top:10px;border:1px solid var(--line);border-radius:14px;overflow:hidden;}
.row{display:grid;grid-template-columns:42px 1fr auto;gap:14px;align-items:center;
padding:14px 18px;border-top:1px solid var(--line);}
.row:first-child{border-top:none;}
.rk{font-family:"Oswald",sans-serif;font-weight:600;font-size:28px;color:var(--muted2);text-align:center;}
.who h3{font-family:"Oswald",sans-serif;font-weight:600;text-transform:uppercase;
font-size:20px;line-height:1;margin-bottom:5px;}
.who .mu{font-size:12.5px;color:var(--muted);}.who .mu b{color:#C4D6E4;}
.flag{font-family:"JetBrains Mono",monospace;font-size:9.5px;letter-spacing:.1em;color:var(--night);
background:var(--muted);border-radius:3px;padding:1px 5px;text-transform:uppercase;font-weight:700;margin-left:7px;}
.metrics{display:flex;align-items:center;gap:16px;}
.meter{width:92px;}
.meter .bar{height:7px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden;}
.meter .fill{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--amber),var(--glow));}
.meter .val{font-family:"Oswald",sans-serif;font-weight:600;font-size:16px;margin-top:4px;display:block;}
.rowodds{font-family:"JetBrains Mono",monospace;font-weight:700;font-size:15px;color:var(--amber);
min-width:52px;text-align:right;}
.legend{margin-top:20px;font-size:12px;color:var(--muted);line-height:1.6;display:grid;gap:6px;}
.legend .k{color:var(--amber);font-family:"JetBrains Mono",monospace;font-weight:700;}
.disc{margin-top:12px;font-size:10.5px;color:var(--muted2);}
@media(max-width:560px){.hero-top{flex-wrap:wrap;}.hero-stats{text-align:left;width:100%;
display:flex;gap:14px;align-items:center;margin-top:4px;}.bignum{font-size:58px;}
.row{grid-template-columns:32px 1fr auto;padding:12px 14px;gap:10px;}.rowodds{display:none;}.meter{width:66px;}}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700'
         '&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">')


def _proj(row):
    return "no_lineup" in str(row.get("flags", ""))


def build_flyer(df, date_str, top_n=10):
    """Return a complete HTML document for the top-N board."""
    top = df.head(top_n).reset_index(drop=True)
    if len(top) == 0:
        return "<p>No board to show.</p>"
    max_pct = max(float(top.iloc[0]["p_HR_%"]), 1)

    from datetime import datetime
    try:
        dobj = datetime.strptime(date_str, "%Y-%m-%d")
        nice_date = dobj.strftime("%a \u00b7 %B %-d, %Y")
    except Exception:
        nice_date = date_str
    n_proj = int(sum(_proj(r) for _, r in top.iterrows()))
    proj_note = (f'<span style="color:var(--glow)">Early board \u00b7 {n_proj} of {len(top)} lineups pending</span>'
                 if n_proj else '<span>Confirmed lineups</span>')

    h = top.iloc[0]
    hpark = PARK_NAMES.get(h.get("venue_team_id"))
    htag = ("\u25c6 Confirmed" if not _proj(h) else "\u25c6 Top play") + (f" \u00b7 {hpark}" if hpark else "")
    hwhy, _ = _why(h)
    hero = f"""
  <div class="hero">
    <svg class="arc" viewBox="0 0 860 260" preserveAspectRatio="none" aria-hidden="true">
      <path d="M20 250 C 240 40, 560 40, 840 150" fill="none" stroke="#FFB43C"
            stroke-width="2" stroke-dasharray="3 9" stroke-linecap="round" opacity=".55"/>
      <circle cx="840" cy="150" r="6" fill="#FF6A3D"/>
    </svg>
    <div class="hero-top">
      <div class="bignum">1</div>
      <div class="hero-name">
        <div class="tag">{htag}</div>
        <h2>{h['player']}</h2>
        <div class="matchup">{h['team']} &nbsp;\u00b7&nbsp; vs <b>{h['opp_SP']}</b></div>
      </div>
      <div class="hero-stats">
        <div class="pct">{h['p_HR_%']}<small>%</small></div>
        <div class="odds">{h['fair_odds']}</div>
      </div>
    </div>
    <div class="why">{hwhy}</div>
  </div>"""

    rows = []
    for i in range(1, len(top)):
        r = top.iloc[i]
        why, caution = _why(r)
        color = "var(--muted)" if caution else "var(--amber-hi)"
        flag = '<span class="flag">Proj</span>' if _proj(r) else ""
        width = round(float(r["p_HR_%"]) / max_pct * 100)
        rows.append(f"""
    <div class="row">
      <div class="rk">{i+1}</div>
      <div class="who"><h3>{r['player']} {flag}</h3>
        <div class="mu">{r['team']} \u00b7 vs <b>{r['opp_SP']}</b> \u2014 <span style="color:{color}">{why}</span></div></div>
      <div class="metrics"><div class="meter"><div class="bar"><div class="fill" style="width:{width}%"></div></div>
        <span class="val">{r['p_HR_%']}%</span></div><div class="rowodds">{r['fair_odds']}</div></div>
    </div>""")

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Home Run Board \u2014 {date_str}</title>{FONTS}<style>{CSS}</style></head>
<body><div class="poster">
  <div class="eyebrow">Home Run Probability Board</div>
  <h1>Who Goes <span class="yard">Yard</span> Tonight</h1>
  <div class="datestrip"><span><b>{nice_date}</b></span>{proj_note}
    <span>Top {len(top)} by model HR probability</span></div>
  {hero}
  <div class="board">{''.join(rows)}</div>
  <div class="legend">
    <div><span class="k">%</span> &nbsp;model probability the hitter homers at least once tonight.</div>
    <div><span class="k">+ODDS</span> &nbsp;fair, no-vig price \u2014 a book only offers value when it pays more than this.</div>
    <div><span class="k">PROJ</span> &nbsp;lineup not yet confirmed; spot and plate appearances estimated.</div>
  </div>
  <div class="disc">Model output for entertainment. No weather modeled yet. Not betting advice.</div>
</div></body></html>"""
