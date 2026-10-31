import collections, datetime, json, os, re, subprocess, sys, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
FONT = '-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif'
USER = '0001FleX'
DISCORD_INVITE = None
DISCORD_GUILD = None
FALLBACK_LANGS = [('Lua', '#000080'), ('TypeScript', '#3178c6'), ('JavaScript', '#f1e05a'), ('Python', '#3572A5'), ('C#', '#178600')]
LANG_COLORS = dict(FALLBACK_LANGS) | {'HTML': '#e34c26', 'CSS': '#663399', 'SCSS': '#c6538c', 'Shell': '#89e051', 'Batchfile': '#C1F12E', 'PowerShell': '#012456', 'Java': '#b07219', 'Go': '#00ADD8', 'Rust': '#dea584', 'C++': '#f34b7d', 'C': '#555555', 'Vue': '#41b883', 'Svelte': '#ff3e00', 'ShaderLab': '#222c37', 'HLSL': '#aace60'}
THEME = {'light': dict(fa=.22, g1=.70, g2=.25, s1=.95, s2=.35, sh=.10, tint='#7d8fa6', fg='#3b4552', ink='#1f2933', mut='#5c6773', acc='#3b82f6'),
         'dark':  dict(fa=.16, g1=.22, g2=.04, s1=.45, s2=.08, sh=.35, tint='#ffffff', fg='#d0d7de', ink='#e6edf3', mut='#9aa4b2', acc='#79b8ff')}
DISCORD_PATH = None

def discord_online():
    if not DISCORD_INVITE: return None
    for url, key in ((f'https://discord.com/api/v10/invites/{DISCORD_INVITE}?with_counts=true', 'approximate_presence_count'),
                     (f'https://discord.com/api/guilds/{DISCORD_GUILD}/widget.json', 'presence_count')):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'profile-readme-updater'}), timeout=15) as r:
                n = json.load(r).get(key)
                if isinstance(n, int): return n
        except Exception as e:
            print(f'discord: {url.split("/")[-1].split("?")[0]} failed: {e}', file=sys.stderr)
    return None

def github_stats():
    q = '{ viewer { contributionsCollection { totalCommitContributions totalPullRequestContributions contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } } } repositories(first: 100, affiliations: [OWNER], ownerAffiliations: [OWNER], isFork: false) { nodes { nameWithOwner pushedAt languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } } } } }'
    try: out = subprocess.run(['gh', 'api', 'graphql', '-f', f'query={q}'], capture_output=True, text=True)
    except FileNotFoundError: out = None
    if out and not out.returncode: return json.loads(out.stdout)['data']['viewer']
    print('gh api graphql failed, using public data:', (out.stderr.strip() if out else 'gh not found'), file=sys.stderr)
    return public_stats()

def private_repo_languages():
    h = {'User-Agent': 'profile-readme-updater', 'Authorization': 'Bearer ' + os.environ['GH_TOKEN']}
    call = lambda u: json.load(urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=20))
    repos = []
    for r in call('https://api.github.com/user/repos?per_page=100&affiliation=owner&visibility=all'):
        if r['fork']: continue
        repos.append({'nameWithOwner': r['full_name'], 'pushedAt': r['pushed_at'],
                      'languages': {'edges': [{'size': v, 'node': {'name': k, 'color': LANG_COLORS.get(k)}} for k, v in call(r['languages_url']).items()]}})
    return repos

def get(url, raw=False):
    h = {'User-Agent': 'profile-readme-updater'}
    if os.environ.get('API_TOKEN') and url.startswith('https://api.github.com/'): h['Authorization'] = 'Bearer ' + os.environ['API_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
        b = r.read().decode('utf8'); return b if raw else json.loads(b)

def public_stats():
    html = get(f'https://github.com/users/{USER}/contributions', raw=True)
    tips = {m[0]: m[1] for m in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)', html)}
    days = sorted((m[0], int((re.match(r'(\d+) contribution', tips.get(m[1], '')) or [0, 0])[1]))
                  for m in re.findall(r'data-date="([\d-]+)" id="([^"]+)"', html))
    weeks = [{'contributionDays': [{'date': d, 'contributionCount': n} for d, n in days[i:i+7]]} for i in range(0, len(days), 7)]
    since = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    count = lambda q: get(f'https://api.github.com/search/{q}').get('total_count', 0)
    repos = []
    for r in get(f'https://api.github.com/users/{USER}/repos?per_page=100&type=owner'):
        if r['fork']: continue
        langs = get(r['languages_url'])
        repos.append({'nameWithOwner': r['full_name'], 'pushedAt': r['pushed_at'],
                      'languages': {'edges': [{'size': v, 'node': {'name': k, 'color': LANG_COLORS.get(k)}} for k, v in langs.items()]}})
    return {'contributionsCollection': {'totalCommitContributions': count(f'commits?q=author:{USER}+author-date:>={since}'),
                                        'totalPullRequestContributions': count(f'issues?q=author:{USER}+type:pr+created:>={since}'),
                                        'contributionCalendar': {'totalContributions': sum(n for _, n in days), 'weeks': weeks}},
            'repositories': {'nodes': repos}}

def glass_defs(uid, W, H, rx, t, blur):
    p = THEME[t]
    return f'''<defs>
<clipPath id="c{uid}"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{rx}"/></clipPath>
<linearGradient id="g{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="{p['g1']}"/><stop offset="1" stop-color="#fff" stop-opacity="{p['g2']}"/></linearGradient>
<linearGradient id="s{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="{p['s1']}"/><stop offset="1" stop-color="#fff" stop-opacity="{p['s2']}"/></linearGradient>
<filter id="b{uid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{blur}"/></filter>
<filter id="d{uid}" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="{p['sh']}"/></filter>
</defs>'''

def glass_body(uid, W, H, rx, t, glare, ellipse):
    p = THEME[t]
    return f'''<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{rx}" fill="{p['tint']}" fill-opacity="{p['fa']}" filter="url(#d{uid})"/>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{rx}" fill="url(#g{uid})"/>
<g clip-path="url(#c{uid})">{ellipse.replace('OP', str(glare))}</g>
<rect x="1.5" y="1.5" width="{W-3}" height="{H-3}" rx="{rx-.5}" fill="none" stroke="url(#s{uid})" stroke-width="1"/>'''

def text_width(s): return sum(9.0 if ch.isupper() or ch.isdigit() else 6.2 if ch == ' ' else 7.6 for ch in s)

def discord_badge(t, online):
    p = THEME[t]; label, value = 'DISCORD', (f'{online} ONLINE' if online is not None else None)
    H = 32; lw = text_width(label); vw = text_width(value) if value else 0
    x_logo = 12; x_label = x_logo + 25; x_div = x_label + lw + 10; x_value = x_div + 10
    W = int((x_value + vw + 12) if value else (x_label + lw + 13))
    ell = f'<ellipse cx="{W*0.3:.0f}" cy="2" rx="{W*0.45:.0f}" ry="9" fill="#fff" opacity="OP" filter="url(#b)"/>'
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">', glass_defs('', W, H, 9, t, 6), glass_body('', W, H, 9, t, .5, ell),
         f'<g transform="translate({x_logo} 8) scale(0.6667)"><path d="{DISCORD_PATH}" fill="{p["fg"]}"/></g>',
         f'<text x="{x_label}" y="20.5" font-family="{FONT}" font-size="11.5" font-weight="700" letter-spacing="1.2" fill="{p["fg"]}">{label}</text>']
    if value:
        o.append(f'<line x1="{x_div}" y1="8" x2="{x_div}" y2="{H-8}" stroke="{p["fg"]}" stroke-opacity=".35" stroke-width="1"/>')
        o.append(f'<text x="{x_value}" y="20.5" font-family="{FONT}" font-size="11.5" font-weight="700" letter-spacing="1.2" fill="{p["fg"]}">{value}</text>')
    o.append('</svg>'); return '\n'.join(o)

def activity_card(t, d):
    p = THEME[t]; c = d['contributionsCollection']
    weeks = c['contributionCalendar']['weeks'][-53:]
    days = [x for w in weeks for x in w['contributionDays']]; active = sum(1 for x in days if x['contributionCount'] > 0)
    streak = best = 0
    for x in days:
        streak = streak + 1 if x['contributionCount'] else 0; best = max(best, streak)
    since = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    lang = collections.Counter()
    for r in d['repositories']['nodes']:
        if r['pushedAt'][:10] < since or r['nameWithOwner'].lower() == f'{USER}/{USER}'.lower(): continue
        for e in r['languages']['edges']: lang[(e['node']['name'], e['node']['color'])] += e['size']
    tot = sum(lang.values()) or 1; top = lang.most_common(5)
    pct = bool(top)
    if not top: top = [(l, 1) for l in FALLBACK_LANGS]; tot = len(top)
    W, H, rx, P = 766, 262, 16, 24
    lab = lambda x, y, s, anchor='start', size=9.5: f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="600" fill="{p["mut"]}" letter-spacing="1">{s}</text>'
    ell = '<ellipse cx="200" cy="0" rx="300" ry="50" fill="#fff" opacity="OP" filter="url(#b)"/>'
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">', glass_defs('', W, H, rx, t, 14), glass_body('', W, H, rx, t, .25, ell)]
    o.append(f'<text x="{P}" y="36" font-size="14" font-weight="700" fill="{p["ink"]}">Last 12 months</text>')
    upd = 'Updated ' + datetime.date.today().strftime('%d %b %Y').lstrip('0')
    pw = len(upd) * 6.3 + 30; px = W - P - pw
    o.append(f'<rect x="{px:.1f}" y="20" width="{pw:.1f}" height="22" rx="11" fill="{p["acc"]}" fill-opacity=".12" stroke="{p["acc"]}" stroke-opacity=".35"/>')
    o.append(f'<circle cx="{px+12:.1f}" cy="31" r="3" fill="{p["acc"]}"/>')
    o.append(f'<text x="{px+21:.1f}" y="35" font-size="11" font-weight="600" fill="{p["acc"]}">{upd}</text>')
    o.append(f'<line x1="{P}" y1="54" x2="{W-P}" y2="54" stroke="{p["ink"]}" stroke-opacity=".08"/>')
    stats = [('Contributions', c['contributionCalendar']['totalContributions']), ('Commits', c['totalCommitContributions']),
             ('Pull requests', c['totalPullRequestContributions']), ('Active days', active)]
    tw, th = 104, 56
    for i, (name, val) in enumerate(stats):
        x = P + (i % 2) * (tw + 8); y = 68 + (i // 2) * (th + 8)
        o.append(f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="10" fill="{p["ink"]}" fill-opacity=".05" stroke="{p["ink"]}" stroke-opacity=".08"/>')
        o.append(f'<text x="{x+12}" y="{y+29}" font-size="22" font-weight="700" fill="{p["ink"]}" letter-spacing="-.5">{val}</text>')
        o.append(lab(x + 12, y + 45, name.upper(), size=8.5))
    hx, hy, step, cell = 262, 84, (W - P - 262) / 53, 7.6
    mx = max((x['contributionCount'] for x in days), default=0) or 1; last = None; lastx = -99
    for i, w in enumerate(weeks):
        cx = hx + i * step
        m = w['contributionDays'][0]['date'][:7]
        if m != last and cx - lastx > 26:
            o.append(lab(f'{cx:.1f}', hy - 8, datetime.date.fromisoformat(m + '-01').strftime('%b').upper(), size=8.5)); lastx = cx
        last = m
        for x in w['contributionDays']:
            r = (datetime.date.fromisoformat(x['date']).weekday() + 1) % 7; v = x['contributionCount']
            fill = f'fill="{p["acc"]}" fill-opacity="{.3 + .7 * min(4, -(-4 * v // mx)) / 4:.2f}"' if v else f'fill="{p["ink"]}" fill-opacity=".07"'
            o.append(f'<rect x="{cx:.1f}" y="{hy + r * step:.1f}" width="{cell}" height="{cell}" rx="2" {fill}><title>{v} on {x["date"]}</title></rect>')
    fy = hy + 7 * step + 14
    o.append(lab(hx, fy + 4, f'LONGEST STREAK  {best} DAYS', size=8.5))
    lx = W - P - 5 * (cell + 3) - 30
    o.append(lab(lx - 6, fy + 4, 'LESS', 'end', 8.5)); o.append(lab(W - P, fy + 4, 'MORE', 'end', 8.5))
    for k in range(5):
        fill = f'fill="{p["acc"]}" fill-opacity="{.3 + .7 * k / 4:.2f}"' if k else f'fill="{p["ink"]}" fill-opacity=".07"'
        o.append(f'<rect x="{lx + k * (cell + 3):.1f}" y="{fy - 4}" width="{cell}" height="{cell}" rx="2" {fill}/>')
    ly, lw = 214, W - 2 * P; x = P
    o.append(lab(P, ly - 8, 'LANGUAGES'))
    o.append(f'<defs><clipPath id="lb"><rect x="{P}" y="{ly}" width="{lw}" height="6" rx="3"/></clipPath></defs><g clip-path="url(#lb)">')
    for (n, col), s in top:
        w_ = lw * s / tot; o.append(f'<rect x="{x:.1f}" y="{ly}" width="{w_ - 2:.1f}" height="6" fill="{col or "#8b949e"}"/>'); x += w_
    o.append('</g>'); x = P
    for (n, col), s in top:
        label = f'{n} {s/tot*100:.0f}%' if pct else n
        o.append(f'<circle cx="{x+4}" cy="{ly+24}" r="4" fill="{col or "#8b949e"}"/><text x="{x+13}" y="{ly+28}" font-size="11.5" fill="{p["ink"]}">{label}</text>')
        x += 13 + len(label) * 6.6 + 22
    o.append('</svg>'); return '\n'.join(o)

def main():
    global DISCORD_PATH
    DISCORD_PATH = re.search(r' d="([^"]+)"', (ROOT / 'assets/icons/light/discord.svg').read_text()).group(1)
    online = discord_online(); print('discord online:', online)
    d = github_stats(); print('contributions:', d['contributionsCollection']['contributionCalendar']['totalContributions'])
    if os.environ.get('GH_TOKEN'): d['repositories']['nodes'] = private_repo_languages(); print('repos with languages:', len(d['repositories']['nodes']))
    for t in ('light', 'dark'):
        (ROOT / f'assets/icons/{t}/discord.svg').write_text(discord_badge(t, online))
        (ROOT / f'assets/stats-{t}.svg').write_text(activity_card(t, d))
    print('written: assets/icons/*/discord.svg, assets/stats-*.svg')

if __name__ == '__main__': main()
