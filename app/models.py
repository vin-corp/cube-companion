import uuid
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

NAME_MAX_LENGTH = 200
ID_MAX_LENGTH = 100
URL_MAX_LENGTH = 500
MCOST_MAX_LENGTH = 100
TYPE_MAX_LENGTH = 200
PT_MAX_LENGTH = 10
TEXT_BOX_MAX_LENGTH = 1000
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    cubes = db.relationship("Cube", backref="owner", lazy=True, cascade="all, delete-orphan")
    custom_cards = db.relationship("CustomCard", backref="creator", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Cube(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    share_id = db.Column(db.String(36), unique=True, nullable=True, default=None)
    cards = db.relationship('Card', backref='cube_ref', lazy=True, cascade='all, delete-orphan')

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(NAME_MAX_LENGTH), nullable=False)
    scryfall_id = db.Column(db.String(ID_MAX_LENGTH))
    image_url = db.Column(db.String(URL_MAX_LENGTH))
    mana_cost = db.Column(db.String(MCOST_MAX_LENGTH))
    type_line = db.Column(db.String(TYPE_MAX_LENGTH))
    power = db.Column(db.String(PT_MAX_LENGTH))
    toughness = db.Column(db.String(PT_MAX_LENGTH))
    text_box = db.Column(db.String(TEXT_BOX_MAX_LENGTH))
    layout = db.Column(db.String(ID_MAX_LENGTH))
    card_faces = db.relationship('CardFace', backref='card', lazy=True, cascade='all, delete-orphan', order_by='CardFace.id')
    
    cube_id = db.Column(db.Integer, db.ForeignKey("cube.id"), nullable=False)
    custom_card_id = db.Column(db.Integer, db.ForeignKey("custom_card.id"), nullable=True)
    custom_card = db.relationship('CustomCard')

class CardFace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(NAME_MAX_LENGTH), nullable=False)
    scryfall_id = db.Column(db.String(ID_MAX_LENGTH))
    image_url = db.Column(db.String(URL_MAX_LENGTH))
    mana_cost = db.Column(db.String(MCOST_MAX_LENGTH))
    type_line = db.Column(db.String(TYPE_MAX_LENGTH))
    power = db.Column(db.String(PT_MAX_LENGTH))
    toughness = db.Column(db.String(PT_MAX_LENGTH))
    text_box = db.Column(db.String(TEXT_BOX_MAX_LENGTH))
    
    card_id = db.Column(db.Integer, db.ForeignKey("card.id"), nullable=False)

class CustomCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    local_image_path = db.Column(db.String(500))
    mana_cost = db.Column(db.String(100))
    type_line = db.Column(db.String(200))
    power = db.Column(db.String(10))
    toughness = db.Column(db.String(10))
    text_box = db.Column(db.String(1000))
    
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))