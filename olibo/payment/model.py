from datetime import datetime
from olibo import db
from olibo.common.enums import PaymentStatus

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='XAF', nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)  # registration_fee, other
    status = db.Column(db.String(50), default=PaymentStatus.PENDING.value, nullable=False)
    transaction_id = db.Column(db.String(255), unique=True)
    payment_method = db.Column(db.String(50))  # card, mobile_money, bank_transfer, etc
    proof_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relations
    team = db.relationship('Team')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "amount": self.amount,
            "currency": self.currency,
            "payment_type": self.payment_type,
            "status": self.status,
            "transaction_id": self.transaction_id,
            "payment_method": self.payment_method,
            "proof_url": self.proof_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
