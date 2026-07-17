from flask import request
from app.blueprints.voice_booking import voice_bp
from app.utils import success_response

@voice_bp.route('/incoming-call', methods=['POST'])
def incoming_call():
    return success_response({'message': 'Voice booking webhook - implementation pending'})

@voice_bp.route('/gather', methods=['POST'])
def gather():
    return success_response({'message': 'Voice gather webhook - implementation pending'})
