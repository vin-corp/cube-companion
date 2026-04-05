from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user
from .models import Cube, Card
from .extensions import db
import requests as scryfall_requests

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("home.html")


@main.route("/dashboard")
@login_required
def dashboard():
    cubes = Cube.query.filter_by(user_id=current_user.id).order_by(Cube.created_at.desc()).all()
    return render_template("dashboard.html", user=current_user, cubes=cubes)


@main.route("/cube/new", methods=["GET", "POST"])
@login_required
def create_cube():
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        if name:
            cube = Cube(name=name, description=description, user_id=current_user.id)
            db.session.add(cube)
            db.session.commit()
            return redirect(url_for("main.dashboard"))
    return render_template("cube_form.html", cube=None)


@main.route("/cube/<int:cube_id>/edit", methods=["GET", "POST"])
@login_required
def edit_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        if name:
            cube.name = name
            cube.description = description
            db.session.commit()
            return redirect(url_for("main.dashboard"))
    return render_template("cube_form.html", cube=cube)


@main.route("/cube/<int:cube_id>/delete", methods=["POST"])
@login_required
def delete_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    db.session.delete(cube)
    db.session.commit()
    return redirect(url_for("main.dashboard"))

@main.route("/cube/<int:cube_id>/search", methods=["GET", "POST"])
@login_required
def search_cards(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)

    cards = []
    query = ""
    error = None

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                response = scryfall_requests.get(
                    "https://api.scryfall.com/cards/search",
                    params={"q": query}
                )
                if response.status_code == 200:
                    cards = response.json().get("data", [])
                else:
                    error = "No cards found. Try a different search."
            except Exception:
                error = "Could not connect to Scryfall. Try again."

    return render_template("search_cards.html", cube=cube, cards=cards, query=query, error=error)

@main.route('/cube/<int:cube_id>/add', methods=['POST'])
@login_required
def add_to_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    
    if cube.owner != current_user:
        return jsonify({"error": "Unauthorized to edit this cube"}), 403

    data = request.get_json()

    new_card = Card(
        name=data.get('name'),
        scryfall_id=data.get('scryfall_id'),
        image_url=data.get('image_url'),
        mana_cost=data.get('mana_cost'),
        type_line=data.get('type_line'),
        text_box=data.get('text_box'),
        cube_id=cube.id
    )
    
    db.session.add(new_card)
    db.session.commit()
    
    print(f">>> {new_card.name} added to {cube.name}")
    
    return jsonify({
        "success": True,
        "message": f"Added {new_card.name} to {cube.name}!"
    }), 200

@main.route('/cube/<int:cube_id>/view', methods=['GET'])
def view_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    
    cards = Card.query.filter_by(cube_id=cube_id).all()
    
    return render_template('view_cube.html', cube=cube, cards=cards)

@main.route('/cube/<int:cube_id>/remove', methods=['POST'])
@login_required
def remove_from_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    
    if cube.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to edit this cube"}), 403

    data = request.get_json()
    card_id = data.get('card_id')
    card = Card.query.get(card_id)
    if card and card.cube_id == cube.id:
        db.session.delete(card)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Removed {card.name} from {cube.name}!"
        }), 200

    return jsonify({"error": "Card not found or doesn't belong to this cube"}), 404
