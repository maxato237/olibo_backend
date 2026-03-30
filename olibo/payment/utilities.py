#validateur d'adresse ip
import re
from olibo import db
from flask import jsonify, request
from olibo.public.model import Session


def is_valid_ip(ip):
  ip_regex = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
  return re.match(ip_regex, ip) is not None


def create_session(user_id,token):

  # Récupérer l'adresse IP cliente
  client_ip = request.remote_addr
  
  # Récupérer le User-Agent
  user_agent = request.user_agent.string

  # Créer une nouvelle session
  new_session = Session(
    user_id=user_id,
    token=token,
    ip_address=client_ip,
    user_agent=user_agent
  )
  
  # Ajouter la session à la base de données
  db.session.add(new_session)
  db.session.commit()
  
  return jsonify({'message': 'Session créée avec succès'}), 201