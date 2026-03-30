from sqlalchemy.orm import Session
from olibo.match_sheet.model import Invoice_line
from olibo.voting.model import Stock


def process_invoice_line(invoice_line: Invoice_line, db_session: Session):

    designation = invoice_line.designation.strip().lower()

    stock_item = db_session.query(Stock).filter(Stock.name.ilike(designation)).first()

    if not stock_item:
        return {
            'success': False,
            'error': f"Produit '{invoice_line.designation}' introuvable dans le stock."
        }

    if invoice_line.quantity > stock_item.quantity:
        return {
            'success': False,
            'error': f"Stock insuffisant pour '{stock_item.name}': demandé={invoice_line.quantity}, disponible={stock_item.quantity}."
        }

    # Mise à jour du stock
    stock_item.quantity -= invoice_line.quantity
    return {
        'success': True,
        'message': f"Stock mis à jour pour '{stock_item.name}': -{invoice_line.quantity} (reste: {stock_item.quantity})"
    }

def upsert_group_price(group_id, stock_id, price, session):
    """
    Crée ou met à jour un GroupPrice pour un produit donné dans un groupe client.
    - Si le prix existant est inférieur, il est remplacé.
    - Si pas de prix existant, on le crée.
    """
    group_price = session.query(GroupPrice).filter_by(
        group_id=group_id, stock_id=stock_id
    ).first()

    if group_price:
        if price > group_price.price:
            group_price.price = price
            session.add(group_price)
    else:
        new_price = GroupPrice(
            group_id=group_id,
            stock_id=stock_id,
            price=price
        )
        session.add(new_price)
