import base64
import io
import os
import unicodedata

import qrcode
from flask import Blueprint, abort, render_template_string, request

from olibo.license.model import License
from olibo.team.model import Team

_LOGO_PATH = os.path.join(os.path.dirname(__file__), 'olibologo.png')
try:
    with open(_LOGO_PATH, 'rb') as _f:
        _LOGO_B64 = base64.b64encode(_f.read()).decode()
except FileNotFoundError:
    _LOGO_B64 = ''

license_render = Blueprint('license_render', __name__, url_prefix='/internal')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _qr_b64(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def _mrz(member, lic) -> tuple:
    def clean(s):
        if not s:
            return ''
        s = unicodedata.normalize('NFD', str(s))
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        return ''.join(c if c.isalpha() else '<' for c in s.upper())

    nat = (member.nationality or 'XXX').upper()[:3].ljust(3, '<')
    last = clean(member.last_name)
    first = clean(member.first_name)
    line1 = f"OL<{nat}<{last}<<{first}".ljust(44, '<')[:44]

    lic_num = ''.join(c for c in (lic.license_number or '') if c.isalnum())[:9].ljust(9, '<')
    bd = member.birth_date.strftime('%y%m%d') if member.birth_date else '000000'
    gender = (member.gender or 'X')[0].upper()
    exp = lic.expiry_date.strftime('%y%m%d')
    line2 = f"{lic_num}<{bd}{gender}<{exp}{nat}".ljust(44, '<')[:44]

    return line1, line2


def _nationality_display(member) -> str:
    parts = [p for p in [
        (member.nationality or '').upper() or None,
        member.nationality_label,
    ] if p]
    return ' · '.join(parts) if parts else '—'


def _category_display(member) -> str:
    parts = [p for p in [
        member.category.capitalize() if member.category else None,
        member.gender.upper() if member.gender else None,
    ] if p]
    return ' · '.join(parts) if parts else '—'


def _foot_label(f: str) -> str:
    return {'right': 'Droit', 'left': 'Gauche', 'both': 'Les deux'}.get(f or '', f or '—')


def _height_weight(member) -> str:
    parts = []
    if member.height_cm is not None:
        parts.append(f"{member.height_cm} cm")
    if member.weight_kg is not None:
        parts.append(f"{member.weight_kg} kg")
    return ' · '.join(parts) if parts else '—'


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

RECTO_HTML = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;700;800&family=Barlow:wght@300;400;500;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #1a1a2e;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    font-family: 'Barlow', sans-serif;
  }

  .card {
    width: 724px;
    height: 340px;
    border-radius: 6px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 30px 80px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.06);
    display: flex;
  }

  /* ── LEFT RED PANEL ── */
  .panel-left {
    width: 240px;
    flex-shrink: 0;
    background: linear-gradient(160deg, #c0392b 0%, #922b21 60%, #7b241c 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 22px 18px 18px;
    position: relative;
    gap: 10px;
  }
  .panel-left::after {
    content: '';
    position: absolute;
    top: 8px; left: 8px; right: 8px; bottom: 8px;
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 3px;
    pointer-events: none;
  }

  .fed-label {
    text-align: center;
    color: rgba(255,255,255,.6);
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 9.5px;
    letter-spacing: 3px;
    text-transform: uppercase;
  }
  .fed-label span {
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    display: block;
    margin-top: 1px;
  }
  .diamonds { color: rgba(255,255,255,.5); font-size: 8px; letter-spacing: 6px; }

  .photo-wrap {
    position: relative;
    width: 136px;
    height: 160px;
    border: 2px solid rgba(255,255,255,.35);
    border-radius: 3px;
    overflow: hidden;
    flex-shrink: 0;
  }
  .photo-wrap img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
  .photo-ph {
    width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 48px; font-weight: 800;
    color: rgba(255,255,255,.4);
    background: rgba(0,0,0,.2);
  }
  .jersey-badge {
    position: absolute;
    top: -1px; right: -1px;
    background: #1a1a1a;
    color: #fff;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 10px; font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 7px;
    border-bottom-left-radius: 3px;
  }
  .photo-date {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    background: rgba(0,0,0,.55);
    color: rgba(255,255,255,.65);
    font-family: 'Share Tech Mono', monospace;
    font-size: 9px; text-align: center;
    padding: 3px 0; letter-spacing: 1px;
  }

  .big-number {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 68px; font-weight: 800;
    color: rgba(255,255,255,.18);
    line-height: 1; letter-spacing: -2px;
  }
  .dossard-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 9px; letter-spacing: 4px;
    color: rgba(255,255,255,.4); text-transform: uppercase;
    margin-top: -8px;
  }

  /* ── MAIN DARK PANEL ── */
  .panel-main {
    flex: 1;
    background: #111214;
    display: flex;
    flex-direction: column;
    padding: 22px 28px 20px;
    position: relative;
  }

  .licence-tag {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 10.5px; letter-spacing: 3px;
    color: rgba(255,255,255,.35); text-transform: uppercase;
    display: flex; align-items: center;
    gap: 8px; margin-bottom: 4px;
  }
  .licence-tag::before { content: '\25C6'; color: #c0392b; font-size: 7px; }

  .status-badge {
    margin-left: auto;
    display: flex; align-items: center; gap: 5px;
    background: rgba(39,174,96,.15);
    border: 1px solid rgba(39,174,96,.4);
    border-radius: 3px; padding: 3px 10px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px; letter-spacing: 2px;
    color: #2ecc71; text-transform: uppercase;
  }
  .status-badge.invalid {
    background: rgba(231,76,60,.15);
    border-color: rgba(231,76,60,.4);
    color: #e74c3c;
  }
  .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #2ecc71; }
  .status-dot.invalid { background: #e74c3c; }

  .player-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 44px; font-weight: 800;
    color: #fff; line-height: 1;
    letter-spacing: -1px; margin-bottom: 4px;
  }
  .player-sub {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px; letter-spacing: 3px;
    color: rgba(255,255,255,.4); text-transform: uppercase;
    display: flex; gap: 8px; align-items: center;
    margin-bottom: 16px;
  }
  .player-sub span { color: #c0392b; }

  .sep { border: none; border-top: 1px solid rgba(255,255,255,.07); margin: 0 0 14px; }

  .data-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px 16px;
    margin-bottom: 14px;
  }
  .field { display: flex; flex-direction: column; gap: 2px; }
  .field-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 8.5px; letter-spacing: 2.5px;
    color: rgba(255,255,255,.28); text-transform: uppercase;
  }
  .field-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 15px; font-weight: 600;
    color: #e8e8e8; letter-spacing: .3px;
  }
  .field-value.accent { color: #c0392b; letter-spacing: 1px; }
  .field-value.warn { color: #e67e22; }

  .mrz {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 3px; padding: 8px 12px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px; color: rgba(255,255,255,.3);
    letter-spacing: 1px; line-height: 1.6;
  }
</style>
</head>
<body>
<div class="card">

  <!-- LEFT RED PANEL -->
  <div class="panel-left">
    <div class="fed-label">
      <div class="diamonds">&#9670; &nbsp; &#9670;</div>
      Fédération
      <span>Olibo League</span>
    </div>

    <div class="photo-wrap">
      {% if photo_url %}
      <img src="{{ photo_url }}" alt="" crossorigin="anonymous">
      {% else %}
      <div class="photo-ph">{{ initials }}</div>
      {% endif %}
      {% if jersey_number is not none %}
      <div class="jersey-badge">N°{{ jersey_number }}</div>
      {% endif %}
      <div class="photo-date">PHOTO · {{ photo_date }}</div>
    </div>

    {% if jersey_number is not none %}
    <div class="big-number">{{ jersey_number }}</div>
    {% endif %}
    <div class="dossard-label">Dossard Officiel</div>
  </div>

  <!-- MAIN DARK PANEL -->
  <div class="panel-main">

    <div class="licence-tag">
      Licence Amateur · Saison {{ season_label or '—' }}
      <div class="status-badge {{ '' if is_valid else 'invalid' }}">
        <div class="status-dot {{ '' if is_valid else 'invalid' }}"></div>
        {{ 'Active' if is_valid else 'Inactive' }}
      </div>
    </div>

    <div class="player-name">{{ first_name }} {{ last_name }}</div>
    <div class="player-sub">
      {{ position or 'Joueur' }} <span>·</span> {{ team_name or '—' }}
    </div>

    <hr class="sep">

    <div class="data-grid">
      <div class="field">
        <div class="field-label">N° Licence</div>
        <div class="field-value accent">{{ license_number }}</div>
      </div>
      <div class="field">
        <div class="field-label">Date Émission</div>
        <div class="field-value">{{ issue_date_display }}</div>
      </div>
      <div class="field">
        <div class="field-label">Date Expiration</div>
        <div class="field-value warn">{{ expiry_date_display }}</div>
      </div>
      <div class="field">
        <div class="field-label">Date de Naissance</div>
        <div class="field-value">{{ birth_date_display }}</div>
      </div>
      <div class="field">
        <div class="field-label">Nationalité</div>
        <div class="field-value">{{ nationality_display }}</div>
      </div>
      <div class="field">
        <div class="field-label">Catégorie</div>
        <div class="field-value">{{ category_display }}</div>
      </div>
      <div class="field">
        <div class="field-label">Poste Principal</div>
        <div class="field-value">{{ position or '—' }}</div>
      </div>
      <div class="field">
        <div class="field-label">Pied Fort</div>
        <div class="field-value">{{ foot_label }}</div>
      </div>
      <div class="field">
        <div class="field-label">Taille / Poids</div>
        <div class="field-value">{{ height_weight }}</div>
      </div>
    </div>

    <div class="mrz">
      {{ mrz_line1 }}<br>{{ mrz_line2 }}
    </div>

  </div>
</div>
</body>
</html>"""


VERSO_HTML = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;700;800&family=Barlow:wght@300;400;500;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #1a1a2e;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    font-family: 'Barlow', sans-serif;
  }

  .card {
    width: 724px;
    height: 340px;
    border-radius: 6px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 30px 80px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.06);
    background: #111214;
    display: flex;
  }

  /* corner brackets */
  .corner-tl, .corner-tr, .corner-bl, .corner-br {
    position: absolute;
    width: 14px; height: 14px;
    border-color: rgba(255,255,255,.22);
    border-style: solid;
  }
  .corner-tl { top: 6px; left: 6px; border-width: 1px 0 0 1px; }
  .corner-tr { top: 6px; right: 6px; border-width: 1px 1px 0 0; }
  .corner-bl { bottom: 6px; left: 6px; border-width: 0 0 1px 1px; }
  .corner-br { bottom: 6px; right: 6px; border-width: 0 1px 1px 0; }

  .inner {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 60px;
    padding: 30px;
  }

  /* QR block */
  .qr-block { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .qr-wrap {
    background: #fff;
    padding: 6px;
    border-radius: 2px;
    width: 140px; height: 140px;
    display: flex; align-items: center; justify-content: center;
  }
  .qr-wrap img { width: 128px; height: 128px; display: block; }
  .scan-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 9px; letter-spacing: 3px;
    color: rgba(255,255,255,.25); text-transform: uppercase;
  }

  /* seal block */
  .seal-block { display: flex; flex-direction: column; align-items: center; gap: 14px; }

  .logo-wrap {
    width: 100px;
    display: flex; align-items: center; justify-content: center;
  }
  .logo-wrap img { width: 100%; height: auto; display: block; }

  .cert-text {
    text-align: center;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 10px; letter-spacing: 1.5px;
    color: rgba(255,255,255,.25); text-transform: uppercase;
    line-height: 1.6;
  }
  .cert-text strong { color: rgba(255,255,255,.6); font-size: 11px; }

  .lic-info {
    font-family: 'Share Tech Mono', monospace;
    font-size: 9px; color: rgba(255,255,255,.18);
    letter-spacing: 1px; text-align: center; line-height: 1.6;
  }
</style>
</head>
<body>
<div class="card">
  <div class="corner-tl"></div>
  <div class="corner-tr"></div>
  <div class="corner-bl"></div>
  <div class="corner-br"></div>

  <div class="inner">
    <!-- QR block -->
    <div class="qr-block">
      <div class="qr-wrap">
        <img src="data:image/png;base64,{{ qr_b64 }}" alt="QR">
      </div>
      <div class="scan-label">Scan to Verify</div>
    </div>

    <!-- Seal block -->
    <div class="seal-block">
      <div class="logo-wrap">
        <img src="data:image/png;base64,{{ logo_b64 }}" alt="Olibo League">
      </div>
      <div class="cert-text">
        Certifié par<br>
        <strong>Olibo League</strong><br>
        Sign. Numérique
      </div>
      <div class="lic-info">
        {{ license_number }}<br>
        {{ nationality_code }} · {{ season_label or '—' }}
      </div>
    </div>
  </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@license_render.route('/license-render/<int:license_id>', methods=['GET'])
def render_license(license_id):
    if request.remote_addr != '127.0.0.1':
        abort(403)

    side = request.args.get('side', 'recto')
    if side not in ('recto', 'verso'):
        abort(400)

    lic = License.query.get(license_id)
    if not lic:
        abort(404)
    member = lic.member
    if not member:
        abort(404)

    team = Team.query.get(member.team_id)
    season = lic.season

    initials = (member.first_name[0] + member.last_name[0]).upper() \
        if member.first_name and member.last_name else '?'

    if side == 'recto':
        mrz1, mrz2 = _mrz(member, lic)
        return render_template_string(
            RECTO_HTML,
            photo_url=member.photo,
            initials=initials,
            first_name=member.first_name,
            last_name=member.last_name,
            jersey_number=member.jersey_number,
            photo_date=lic.issue_date.strftime('%d.%m.%Y'),
            season_label=season.label if season else None,
            is_valid=lic.is_valid,
            position=member.position,
            team_name=team.name if team else '—',
            license_number=lic.license_number,
            issue_date_display=lic.issue_date.strftime('%d / %m / %Y'),
            expiry_date_display=lic.expiry_date.strftime('%d / %m / %Y'),
            birth_date_display=member.birth_date.strftime('%d / %m / %Y') if member.birth_date else '—',
            nationality_display=_nationality_display(member),
            category_display=_category_display(member),
            foot_label=_foot_label(member.preferred_foot),
            height_weight=_height_weight(member),
            mrz_line1=mrz1,
            mrz_line2=mrz2,
        )

    return render_template_string(
        VERSO_HTML,
        qr_b64=_qr_b64(lic.license_number),
        license_number=lic.license_number,
        nationality_code=(member.nationality or '').upper() or '—',
        season_label=season.label if season else None,
        logo_b64=_LOGO_B64,
    )
