from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from olibo import db
from olibo.common.enums import PaymentStatus
from olibo.payment.model import Payment
from olibo.users.model import User

payment = Blueprint('payment', __name__)


# Create payment request
@payment.route('', methods=['POST'])
@jwt_required()
def create_payment():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not all(k in data for k in ['amount', 'payment_type']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if data['amount'] <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400
        
        payment = Payment(
            user_id=user_id,
            team_id=data.get('team_id'),
            amount=data['amount'],
            currency=data.get('currency', 'XAF'),
            payment_type=data['payment_type'],
            payment_method=data.get('payment_method'),
            proof_url=data.get('proof_url')
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'message': 'Payment created successfully',
            'payment': payment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get all payments
@payment.route('', methods=['GET'])
@jwt_required()
def get_all_payments():
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        status = request.args.get('status')
        query = Payment.query
        
        if status:
            query = query.filter_by(status=status)
        
        payments = query.all()
        
        return jsonify({
            'message': 'Payments retrieved successfully',
            'total': len(payments),
            'payments': [p.to_dict() for p in payments]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user payments
@payment.route('/my-payments', methods=['GET'])
@jwt_required()
def get_my_payments():
    try:
        user_id = get_jwt_identity()
        payments = Payment.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'message': 'Payments retrieved successfully',
            'total': len(payments),
            'payments': [p.to_dict() for p in payments]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Confirm payment
@payment.route('/<int:payment_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_payment(payment_id):
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        data = request.get_json()
        payment.status = PaymentStatus.COMPLETED.value
        payment.transaction_id = data.get('transaction_id')
        payment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment confirmed successfully',
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Reject payment
@payment.route('/<int:payment_id>/reject', methods=['POST'])
@jwt_required()
def reject_payment(payment_id):
    try:
        user = User.query.get(get_jwt_identity())
        
        if user.role not in ['super_admin', 'admin_competition']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        payment.status = PaymentStatus.FAILED.value
        payment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Payment rejected successfully',
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
