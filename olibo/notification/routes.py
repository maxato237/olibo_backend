from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from olibo import db
from olibo.notification.model import Notification
from olibo.users.model import User

notification = Blueprint('notification', __name__)



# Get user notifications
@notification.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        user_id = get_jwt_identity()
        unread_only = request.args.get('unread', 'false').lower() == 'true'
        
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).all()
        
        return jsonify({
            'message': 'Notifications retrieved successfully',
            'total': len(notifications),
            'notifications': [n.to_dict() for n in notifications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Mark notification as read
@notification.route('/<int:notif_id>/read', methods=['POST'])
@jwt_required()
def mark_as_read(notif_id):
    try:
        user_id = get_jwt_identity()
        notification = Notification.query.get(notif_id)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        if notification.user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Notification marked as read',
            'notification': notification.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete notification
@notification.route('/<int:notif_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notif_id):
    try:
        user_id = get_jwt_identity()
        notification = Notification.query.get(notif_id)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        if notification.user_id != user_id:
            user = User.query.get(user_id)
            if user.role != 'super_admin':
                return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({'message': 'Notification deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Mark all user notifications as read
@notification.route('/mark-all-read', methods=['POST'])
@jwt_required()
def mark_all_as_read():
    try:
        user_id = get_jwt_identity()
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()

        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'message': 'Notifications marked as read successfully',
            'total': len(notifications),
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500