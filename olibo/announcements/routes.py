from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from olibo import db
from olibo.announcements.model import News
from olibo.users.model import User

announcements = Blueprint('announcements', __name__)

# Create news
@announcements.route('', methods=['POST'])
@jwt_required()
def create_news():
    try:
        author_id = get_jwt_identity()
        user = User.query.get(author_id)
        data = request.get_json()
        
        if not all(k in data for k in ['title', 'content']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        news = News(
            title=data['title'],
            content=data['content'],
            author_id=author_id,
            competition_id=data.get('competition_id'),
            featured_image=data.get('featured_image'),
            is_published=data.get('is_published', False)
        )
        
        db.session.add(news)
        db.session.commit()
        
        return jsonify({
            'message': 'News created successfully',
            'news': news.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all news
@announcements.route('', methods=['GET'])
def get_all_news():
    try:
        published_only = request.args.get('published', 'true').lower() == 'true'
        competition_id = request.args.get('competition_id', type=int)
        
        query = News.query
        if published_only:
            query = query.filter_by(is_published=True)
        if competition_id:
            query = query.filter_by(competition_id=competition_id)
        
        news = query.order_by(News.created_at.desc()).all()
        
        return jsonify({
            'message': 'News retrieved successfully',
            'total': len(news),
            'news': [n.to_dict() for n in news]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get news by ID
@announcements.route('/<int:news_id>', methods=['GET'])
def get_news(news_id):
    try:
        news = News.query.get(news_id)
        
        if not news:
            return jsonify({'error': 'News not found'}), 404
        
        return jsonify({
            'message': 'News retrieved successfully',
            'news': news.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update news
@announcements.route('/<int:news_id>', methods=['PUT'])
@jwt_required()
def update_news(news_id):
    try:
        author_id = get_jwt_identity()
        news = News.query.get(news_id)
        
        if not news:
            return jsonify({'error': 'News not found'}), 404
        
        user = User.query.get(author_id)
        if news.author_id != author_id and user.role != 'super_admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        if 'title' in data:
            news.title = data['title']
        if 'content' in data:
            news.content = data['content']
        if 'featured_image' in data:
            news.featured_image = data['featured_image']
        
        news.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'News updated successfully',
            'news': news.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Publish news
@announcements.route('/<int:news_id>/publish', methods=['POST'])
@jwt_required()
def publish_news(news_id):
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        news = News.query.get(news_id)
        
        if not news:
            return jsonify({'error': 'News not found'}), 404
        
        news.is_published = True
        news.published_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'News published successfully',
            'news': news.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete news
@announcements.route('/<int:news_id>', methods=['DELETE'])
@jwt_required()
def delete_news(news_id):
    try:
        user = User.query.get(get_jwt_identity())
        news = News.query.get(news_id)
        
        if not news:
            return jsonify({'error': 'News not found'}), 404
        
        if news.author_id != user.id and user.role != 'super_admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(news)
        db.session.commit()
        
        return jsonify({'message': 'News deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500