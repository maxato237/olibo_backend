import io
import zipfile

from flask import url_for
from playwright.sync_api import sync_playwright

from olibo.license.model import License
from olibo.season.model import Season
from olibo.team.model import Team, TeamMember

_VIEWPORT = {'width': 860, 'height': 500}
_CARD_SELECTOR = '.card'
_BBOX_JS = (
    "() => {"
    "  const r = document.querySelector('.card').getBoundingClientRect();"
    "  return {x: r.x, y: r.y, width: r.width, height: r.height};"
    "}"
)


class LicenseExportService:

    def _get_license_data(self, license_id: int) -> dict:
        lic = License.query.get(license_id)
        if not lic:
            raise ValueError(f"License {license_id} not found")

        member = lic.member
        team = Team.query.get(member.team_id) if member else None
        season = lic.season

        return {
            "license_id": lic.id,
            "license_number": lic.license_number,
            "issue_date": lic.issue_date.isoformat(),
            "expiry_date": lic.expiry_date.isoformat(),
            "is_valid": lic.is_valid,
            "member": {
                "id": member.id,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "photo": member.photo,
                "position": member.position,
                "jersey_number": member.jersey_number,
                "nationality_label": member.nationality_label,
                "birth_date": member.birth_date.isoformat() if member.birth_date else None,
                "height_cm": member.height_cm,
                "weight_kg": member.weight_kg,
                "gender": member.gender,
                "category": member.category,
                "preferred_foot": member.preferred_foot,
                "is_captain": member.is_captain,
                "role": member.role,
            } if member else {},
            "team_name": team.name if team else "—",
            "season": {
                "id": season.id,
                "label": season.label,
                "name": season.name,
            } if season else {},
        }

    def _render_card_png(self, license_id: int, side: str) -> bytes:
        url = url_for('license_render.render_license', license_id=license_id, side=side, _external=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=_VIEWPORT)
            page.goto(url, wait_until='networkidle')
            page.wait_for_selector(_CARD_SELECTOR)
            rect = page.evaluate(_BBOX_JS)
            png_bytes = page.screenshot(clip=rect)
            browser.close()
        return png_bytes

    def export_single_zip(self, license_id: int) -> bytes:
        recto_png = self._render_card_png(license_id, 'recto')
        verso_png = self._render_card_png(license_id, 'verso')

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('recto.png', recto_png)
            zf.writestr('verso.png', verso_png)
        return buf.getvalue()

    def export_team_zip(self, team_id: int) -> bytes:
        team = Team.query.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        active_season = Season.query.filter_by(is_active=True).first()

        member_ids = [
            m.id for m in TeamMember.query.filter_by(team_id=team_id).all()
        ]
        if not member_ids:
            raise ValueError("No members in this team")

        query = License.query.filter(License.member_id.in_(member_ids))
        if active_season:
            query = query.filter_by(season_id=active_season.id)
        licenses = query.all()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for lic in licenses:
                    member = lic.member
                    folder = f"{member.last_name}_{member.first_name}_{lic.license_number}"
                    for side in ('recto', 'verso'):
                        page = browser.new_page(viewport=_VIEWPORT)
                        url = url_for('license_render.render_license', license_id=lic.id, side=side, _external=True)
                        page.goto(url, wait_until='networkidle')
                        page.wait_for_selector(_CARD_SELECTOR)
                        rect = page.evaluate(_BBOX_JS)
                        png_bytes = page.screenshot(clip=rect)
                        page.close()
                        zf.writestr(f'{folder}/{side}.png', png_bytes)
                browser.close()
        return buf.getvalue()
