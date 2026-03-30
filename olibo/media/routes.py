from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from olibo import db
from olibo.media.model import Media
from olibo.users.model import User

media = Blueprint('media', __name__)


# Upload media
@media.route('', methods=['POST'])
@jwt_required()
def upload_media():
    try:
        uploader_id = get_jwt_identity()
        data = request.get_json()
        
        if not all(k in data for k in ['title', 'file_url', 'file_type']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if data['file_type'] not in ['image', 'video']:
            return jsonify({'error': 'File type must be image or video'}), 400
        
        media = Media(
            title=data['title'],
            description=data.get('description'),
            file_url=data['file_url'],
            file_type=data['file_type'],
            uploaded_by_id=uploader_id,
            competition_id=data.get('competition_id'),
            match_id=data.get('match_id'),
            is_published=data.get('is_published', False)
        )
        
        db.session.add(media)
        db.session.commit()
        
        return jsonify({
            'message': 'Media uploaded successfully',
            'media': media.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all media
@media.route('', methods=['GET'])
def get_all_media():
    try:
        published_only = request.args.get('published', 'true').lower() == 'true'
        file_type = request.args.get('file_type')
        
        query = Media.query
        if published_only:
            query = query.filter_by(is_published=True)
        if file_type:
            query = query.filter_by(file_type=file_type)
        
        media = query.all()
        
        return jsonify({
            'message': 'Media retrieved successfully',
            'total': len(media),
            'media': [m.to_dict() for m in media]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get media by ID
@media.route('/<int:media_id>', methods=['GET'])
def get_media(media_id):
    try:
        media = Media.query.get(media_id)
        
        if not media:
            return jsonify({'error': 'Media not found'}), 404
        
        return jsonify({
            'message': 'Media retrieved successfully',
            'media': media.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Publish media
@media.route('/<int:media_id>/publish', methods=['POST'])
@jwt_required()
def publish_media(media_id):
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        media = Media.query.get(media_id)
        
        if not media:
            return jsonify({'error': 'Media not found'}), 404
        
        media.is_published = True
        media.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Media published successfully',
            'media': media.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete media
@media.route('/<int:media_id>', methods=['DELETE'])
@jwt_required()
def delete_media(media_id):
    try:
        user = User.query.get(get_jwt_identity())
        media = Media.query.get(media_id)
        
        if not media:
            return jsonify({'error': 'Media not found'}), 404
        
        if media.uploaded_by_id != user.id:
            if user.role != 'super_admin':
                return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(media)
        db.session.commit()
        
        return jsonify({'message': 'Media deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
