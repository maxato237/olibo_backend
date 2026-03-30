from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from psycopg2 import IntegrityError
from olibo import db
from olibo.article.model import Article
from olibo.users.model import User
from slugify import slugify

article = Blueprint('article', __name__)


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def get_authorized_user() -> User:
    return User.query.get(get_jwt_identity())


def validate_article_payload(data: dict, is_update: bool = False) -> str | None:
    """
    Valide le payload.
    content est désormais un string HTML produit par TinyMCE (plus un JSON array).
    """
    if not is_update:
        for field in ['title', 'content']:
            if not data.get(field):
                return f"'{field}' est requis."

    if 'title' in data and not isinstance(data['title'], str):
        return "'title' doit être une chaîne de caractères."

    if 'content' in data and not isinstance(data['content'], str):
        return "'content' doit être une chaîne HTML (string)."

    if 'status' in data and data['status'] not in ('draft', 'published'):
        return "'status' doit être 'draft' ou 'published'."

    return None


def _generate_unique_slug(title: str, exclude_id: int | None = None) -> str:
    """Génère un slug unique — ajoute un suffixe numérique si déjà pris."""
    base_slug = slugify(title)
    slug      = base_slug
    counter   = 1

    while True:
        query = Article.query.filter_by(slug=slug)
        if exclude_id:
            query = query.filter(Article.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


# ══════════════════════════════════════════════════════════════════
# ROUTES ADMIN (JWT requis)
# ══════════════════════════════════════════════════════════════════

@article.route('/admin/articles', methods=['POST'])
@jwt_required()
def create_article():
    """
    Crée un article.
    - author_id extrait du JWT (pas du payload — plus sécurisé).
    - Slug : utilise celui du frontend si fourni, sinon généré depuis le titre.
    - Réponse : { message, article }
    """
    user = get_authorized_user()
    if not user:
        return jsonify({'error': 'Utilisateur introuvable.'}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Payload JSON manquant.'}), 400

    error = validate_article_payload(data)
    if error:
        return jsonify({'error': error}), 400

    try:
        raw_slug = data.get('slug') or data['title']
        slug     = _generate_unique_slug(raw_slug)

        new_article = Article(
            title        = data['title'].strip(),
            slug         = slug,
            excerpt      = data.get('excerpt') or None,
            cover_image  = data.get('cover_image') or None,
            content      = data['content'],
            status       = data.get('status', 'draft'),
            author_id    = user.id,
            published_at = datetime.utcnow() if data.get('status') == 'published' else None,
        )

        db.session.add(new_article)
        db.session.commit()

        return jsonify({
            'message': 'Article créé avec succès.',
            'article': new_article.to_dict(),
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Conflit de slug ou contrainte unique.'}), 409

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@article.route('/admin/articles', methods=['GET'])
@jwt_required()
def get_all_articles():
    """
    Liste tous les articles (admin).
    Filtre optionnel : ?status=draft|published
    Réponse : { articles, total }
    """
    try:
        status_filter = request.args.get('status')
        query = Article.query

        if status_filter in ('draft', 'published'):
            query = query.filter_by(status=status_filter)

        articles = query.order_by(Article.created_at.desc()).all()

        return jsonify({
            'articles': [a.to_dict() for a in articles],
            'total':    len(articles),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@article.route('/admin/articles/<int:article_id>', methods=['GET'])
@jwt_required()
def get_article_by_id(article_id: int):
    """
    Récupère un article par ID (admin, tous statuts).
    Réponse : { article }
    """
    try:
        found = Article.query.get(article_id)
        if not found:
            return jsonify({'error': 'Article introuvable.'}), 404

        return jsonify({'article': found.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@article.route('/admin/articles/<int:article_id>', methods=['PUT'])
@jwt_required()
def update_article(article_id: int):
    """
    Met à jour un article.
    - PATCH-style : seuls les champs présents sont modifiés.
    - published_at n'est défini qu'une seule fois (pas réécrasé à chaque update).
    - Repasser en draft réinitialise published_at.
    Réponse : { message, article }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Payload JSON manquant.'}), 400

    error = validate_article_payload(data, is_update=True)
    if error:
        return jsonify({'error': error}), 400

    try:
        found = Article.query.get(article_id)
        if not found:
            return jsonify({'error': 'Article introuvable.'}), 404

        # ── Titre & slug ──────────────────────────────────────────
        if 'title' in data:
            found.title  = data['title'].strip()
            raw_slug     = data.get('slug') or found.title
            found.slug   = _generate_unique_slug(raw_slug, exclude_id=article_id)
        elif 'slug' in data and data['slug']:
            found.slug   = _generate_unique_slug(data['slug'], exclude_id=article_id)

        # ── Autres champs ─────────────────────────────────────────
        if 'excerpt'     in data: found.excerpt     = data['excerpt']     or None
        if 'cover_image' in data: found.cover_image = data['cover_image'] or None
        if 'content'     in data: found.content     = data['content']

        if 'status' in data:
            found.status = data['status']
            if data['status'] == 'published' and not found.published_at:
                found.published_at = datetime.utcnow()
            elif data['status'] == 'draft':
                found.published_at = None

        db.session.commit()

        return jsonify({
            'message': 'Article mis à jour avec succès.',
            'article': found.to_dict(),
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Conflit de slug lors de la mise à jour.'}), 409

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@article.route('/admin/articles/<int:article_id>', methods=['DELETE'])
@jwt_required()
def delete_article(article_id: int):
    """Supprime un article. Réponse : { message }"""
    try:
        found = Article.query.get(article_id)
        if not found:
            return jsonify({'error': 'Article introuvable.'}), 404

        db.session.delete(found)
        db.session.commit()

        return jsonify({'message': 'Article supprimé avec succès.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# ROUTES PUBLIQUES (sans JWT — visiteurs)
# ══════════════════════════════════════════════════════════════════

@article.route('/articles', methods=['GET'])
def get_published_articles():
    """
    Liste les articles publiés.
    Réponse : { articles, total }
    """
    try:
        articles = (
            Article.query
            .filter_by(status='published')
            .order_by(Article.published_at.desc())
            .all()
        )
        return jsonify({
            'articles': [a.to_dict() for a in articles],
            'total':    len(articles),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@article.route('/articles/<string:slug>', methods=['GET'])
def get_article_by_slug(slug: str):
    """
    Récupère un article publié par son slug.
    Réponse : { article }
    """
    try:
        found = Article.query.filter_by(slug=slug, status='published').first()
        if not found:
            return jsonify({'error': 'Article introuvable.'}), 404

        return jsonify({'article': found.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500