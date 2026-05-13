from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, flash, current_app
from flask_login import login_required, current_user
from .models import Cube, Card, CardFace, CustomCard
from .extensions import db
import requests as scryfall_requests
from werkzeug.utils import secure_filename
import uuid
import os
import shutil

main = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

    # Map scryfall_id -> db card id for cards already in this cube
    existing = {c.scryfall_id: c.id for c in cube.cards if c.scryfall_id}
    # Fallback: match by name in case a different printing is returned by search
    existing_by_name = {c.name.lower(): c.id for c in cube.cards if c.scryfall_id}

    return render_template("search_cards.html", cube=cube, cards=cards, query=query, error=error, existing=existing, existing_by_name=existing_by_name)

@main.route('/cube/<int:cube_id>/add', methods=['POST'])
@login_required
def add_to_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    
    if cube.owner != current_user:
        return jsonify({"error": "Unauthorized to edit this cube"}), 403

    data = request.get_json()
    raw_text = data.get('text_box', '')
    safe_text = raw_text.replace('\u2212', '-')
    
    safe_name = data.get('name', '').replace('\u2212', '-')

    image_url = data.get('image_url')
    new_card = Card(
        name=safe_name,
        scryfall_id=data.get('scryfall_id'),
        image_url=image_url,
        mana_cost=data.get('mana_cost'),
        type_line=data.get('type_line'),
        text_box=safe_text,
        cube_id=cube_id,
        layout=data.get('layout'),
        power=data.get('power'),
        toughness=data.get('toughness')
    )

    faces = data.get('card_faces', [])
    if faces:
        for face in faces:
            safe_face_text = face.get('oracle_text', face.get('text_box', '')).replace('\u2212', '-')
            safe_face_name = face.get('name', '').replace('\u2212', '-')
            face_image_url = face.get('image_url')
            if not face_image_url and face.get('image_uris'):
                face_image_url = face.get('image_uris', {}).get('normal')
            new_card.card_faces.append(CardFace(
                name=safe_face_name,
                scryfall_id=face.get('scryfall_id'),
                image_url=face_image_url,
                mana_cost=face.get('mana_cost'),
                type_line=face.get('type_line'),
                text_box=safe_face_text
            ))
        if not new_card.image_url and new_card.card_faces:
            new_card.image_url = new_card.card_faces[0].image_url

    db.session.add(new_card)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Added {new_card.name} to {cube.name}!",
        "card_id": new_card.id
    }), 200

@main.route('/cube/<int:cube_id>/view', methods=['GET'])
@login_required
def view_cube(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
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

@main.route('/cube/<int:cube_id>/share/generate', methods=['POST'])
@login_required
def generate_share_link(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    if not cube.share_id:
        cube.share_id = str(uuid.uuid4())
        db.session.commit()
    return redirect(url_for('main.dashboard'))


@main.route('/cube/<int:cube_id>/share/revoke', methods=['POST'])
@login_required
def revoke_share_link(cube_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    cube.share_id = None
    db.session.commit()
    flash('Share link revoked.', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/shared/<share_id>')
def shared_cube(share_id):
    cube = Cube.query.filter_by(share_id=share_id).first_or_404()
    cards = cube.cards
    return render_template('shared_cube.html', cube=cube, cards=cards)


@main.route('/shared/<share_id>/copy', methods=['POST'])
@login_required
def copy_shared_cube(share_id):
    source = Cube.query.filter_by(share_id=share_id).first_or_404()
    new_cube = Cube(
        name=f"{source.name} (Copy)",
        description=source.description,
        user_id=current_user.id
    )
    db.session.add(new_cube)
    db.session.flush()

    # Track original custom_card_id -> new CustomCard so we only copy each once
    custom_card_map = {}

    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    for card in source.cards:
        new_custom_card_id = None
        new_image_url = card.image_url

        if card.custom_card_id:
            if card.custom_card_id in custom_card_map:
                # Already copied this custom card during this loop
                new_custom_card_id = custom_card_map[card.custom_card_id].id
                new_image_url = custom_card_map[card.custom_card_id].local_image_path
            else:
                original_cc = card.custom_card
                # Reuse an existing custom card the user already owns with this name
                existing = CustomCard.query.filter_by(
                    user_id=current_user.id, name=original_cc.name
                ).first()
                if existing:
                    new_custom_card_id = existing.id
                    new_image_url = existing.local_image_path
                    custom_card_map[card.custom_card_id] = existing
                else:
                    # Create a new CustomCard for this user and copy the image file
                    new_uuid = str(uuid.uuid4())
                    new_local_image_path = None

                    if original_cc.local_image_path:
                        src_path = os.path.join(
                            current_app.root_path, 'static', original_cc.local_image_path
                        )
                        _, ext = os.path.splitext(original_cc.local_image_path)
                        new_filename = f"{new_uuid}{ext}"
                        dst_path = os.path.join(upload_dir, new_filename)
                        if os.path.exists(src_path):
                            shutil.copy2(src_path, dst_path)
                        new_local_image_path = f"uploads/{new_filename}"

                    new_cc = CustomCard(
                        uuid=new_uuid,
                        name=original_cc.name,
                        local_image_path=new_local_image_path,
                        mana_cost=original_cc.mana_cost,
                        type_line=original_cc.type_line,
                        text_box=original_cc.text_box,
                        power=original_cc.power,
                        toughness=original_cc.toughness,
                        user_id=current_user.id
                    )
                    db.session.add(new_cc)
                    db.session.flush()
                    new_custom_card_id = new_cc.id
                    new_image_url = new_local_image_path
                    custom_card_map[card.custom_card_id] = new_cc

        new_card = Card(
            name=card.name,
            scryfall_id=card.scryfall_id,
            image_url=new_image_url,
            mana_cost=card.mana_cost,
            type_line=card.type_line,
            text_box=card.text_box,
            power=card.power,
            toughness=card.toughness,
            custom_card_id=new_custom_card_id,
            cube_id=new_cube.id
        )

        if card.card_faces:
            for face in card.card_faces:
                new_card.card_faces.append(CardFace(
                    name=face.name,
                    scryfall_id=face.scryfall_id,
                    image_url=face.image_url,
                    mana_cost=face.mana_cost,
                    type_line=face.type_line,
                    text_box=face.text_box,
                    power=face.power,
                    toughness=face.toughness
                ))
            if not new_card.image_url and new_card.card_faces:
                new_card.image_url = new_card.card_faces[0].image_url

        db.session.add(new_card)

    db.session.commit()
    flash(f'"{source.name}" has been copied to your collection.', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/card/<int:card_id>/share')
@login_required
def share_card(card_id):
    card = CustomCard.query.get_or_404(card_id)
    if card.user_id != current_user.id:
        abort(403)
    share_url = url_for('main.shared_card', card_uuid=card.uuid, _external=True)
    return redirect(url_for('main.my_cards', share_url=share_url, shared_card_id=card_id))


@main.route('/shared/card/<card_uuid>')
def shared_card(card_uuid):
    card = CustomCard.query.filter_by(uuid=card_uuid).first_or_404()
    return render_template('shared_card.html', card=card)


@main.route('/shared/card/<card_uuid>/add', methods=['POST'])
@login_required
def add_shared_card(card_uuid):
    original = CustomCard.query.filter_by(uuid=card_uuid).first_or_404()
    
    existing = CustomCard.query.filter_by(name=original.name, user_id=current_user.id).first()
    if existing:
        flash(f'You already have a card named "{original.name}" in your collection.', 'error')
        return redirect(url_for('main.shared_card', card_uuid=card_uuid))
    
    new_uuid = str(uuid.uuid4())
    new_local_image_path = None

    if original.local_image_path:
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        _, ext = os.path.splitext(original.local_image_path)
        new_filename = f"{new_uuid}{ext}"
        src_path = os.path.join(current_app.root_path, 'static', original.local_image_path)
        dst_path = os.path.join(upload_dir, new_filename)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
        new_local_image_path = f"uploads/{new_filename}"

    new_card = CustomCard(
        uuid=new_uuid,
        name=original.name,
        local_image_path=new_local_image_path,
        mana_cost=original.mana_cost,
        type_line=original.type_line,
        text_box=original.text_box,
        power=original.power,
        toughness=original.toughness,
        user_id=current_user.id
    )
    db.session.add(new_card)
    db.session.commit()
    flash(f'"{original.name}" has been added to your custom cards!', 'success')
    return redirect(url_for('main.my_cards'))

@main.route('/create_card', methods=['GET', 'POST'])
@login_required
def create_card():
    if request.method == 'POST':
        name = request.form.get('cardName', '').strip()
        mana_cost = request.form.get('manaCost', '').strip()
        type_line = request.form.get('typeLine', '').strip()
        rules_text = request.form.get('rulesText', '').strip()
        power = request.form.get('power', '').strip()
        toughness = request.form.get('toughness', '').strip()
        
        image = request.files.get('cardImage')
        
        form_data = {
            'name': name,
            'mana_cost': mana_cost,
            'type_line': type_line,
            'rules_text': rules_text,
            'power': power,
            'toughness': toughness
        }
        
        if not name:
            flash("Can't upload card: Card name cannot be blank", "error")
            return render_template('create_card.html', **form_data)
            
        if not image or image.filename == '':
            flash("Can't upload card: Image cannot be blank", "error")
            return render_template('create_card.html', **form_data)

        if not _allowed_file(image.filename):
            flash("Can't upload card: Image must be a PNG, JPG, GIF, or WEBP file", "error")
            return render_template('create_card.html', **form_data)

        existing_card = CustomCard.query.filter_by(name=name, user_id=current_user.id).first()
        if existing_card:
            flash("Can't upload card: Card with that name already exists", "error")
            return render_template('create_card.html', **form_data)
            
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        card_uuid = str(uuid.uuid4())
        
        original_filename = secure_filename(image.filename)
        _, ext = os.path.splitext(original_filename)
        
        unique_filename = f"{card_uuid}{ext}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        image.save(filepath)
        
        local_image_path = f"uploads/{unique_filename}"
        
        new_card = CustomCard(
            uuid=card_uuid,
            name=name,
            local_image_path=local_image_path,
            mana_cost=mana_cost,
            type_line=type_line,
            text_box=rules_text,
            power=power,
            toughness=toughness,
            user_id=current_user.id
        )
        
        db.session.add(new_card)
        db.session.commit()
        
        flash(f"{name} successfully added to your custom cards!", "success")
        return redirect(url_for('main.edit_card', card_id=new_card.id))
        
    return render_template('create_card.html')

@main.route('/my_cards')
@login_required
def my_cards():
    user_cards = CustomCard.query.filter_by(user_id=current_user.id).all()
    user_cubes = current_user.cubes

    enrolled_cubes = {}
    for card in user_cards:
        slots = Card.query.filter_by(custom_card_id=card.id).all()
        enrolled_cubes[card.id] = [slot.cube_id for slot in slots]
        
    return render_template("my_cards.html", 
                           custom_cards=user_cards, 
                           user_cubes=user_cubes, 
                           enrolled_cubes=enrolled_cubes)

@main.route('/delete_custom_card/<int:card_id>', methods=['POST'])
@login_required
def delete_custom_card(card_id):
    card = CustomCard.query.get_or_404(card_id)
    
    if card.user_id != current_user.id:
        flash("You do not have permission to delete this card.", "error")
        return redirect(url_for('main.my_cards')) 
        
    card_name = card.name
    
    Card.query.filter_by(custom_card_id=card.id).delete()
    
    db.session.delete(card)
    db.session.commit()
    
    flash(f"{card_name} deleted from your custom cards.", "success")
    return redirect(url_for('main.my_cards'))

@main.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    card = CustomCard.query.get_or_404(card_id)
    
    if card.user_id != current_user.id:
        flash("You do not have permission to edit this card.", "error")
        return redirect(url_for('main.my_cards'))

    if request.method == 'POST':
        card.name = request.form.get('cardName', '').strip()
        card.mana_cost = request.form.get('manaCost', '').strip()
        card.type_line = request.form.get('typeLine', '').strip()
        card.text_box = request.form.get('rulesText', '').strip()
        card.power = request.form.get('power', '').strip()
        card.toughness = request.form.get('toughness', '').strip()
        
        image = request.files.get('cardImage')
        if image and image.filename != '':
            if not _allowed_file(image.filename):
                flash("Can't update card: Image must be a PNG, JPG, GIF, or WEBP file", "error")
                return redirect(url_for('main.edit_card', card_id=card.id))

            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            original_filename = secure_filename(image.filename)
            _, ext = os.path.splitext(original_filename)
            unique_filename = f"{card.uuid}{ext}"
            filepath = os.path.join(upload_dir, unique_filename)

            image.save(filepath)
            card.local_image_path = f"uploads/{unique_filename}"
            
        db.session.commit()
        flash(f"{card.name} updated successfully!", "success")
        return redirect(url_for('main.edit_card', card_id=card.id))

    return render_template('create_card.html',
                           editMode=True,
                           card_id=card.id,
                           name=card.name,
                           mana_cost=card.mana_cost,
                           type_line=card.type_line,
                           rules_text=card.text_box,
                           power=card.power,
                           toughness=card.toughness,
                           local_image_path=card.local_image_path)

@main.route('/update_card_cubes/<int:card_id>', methods=['POST'])
@login_required
def update_card_cubes(card_id):
    card = CustomCard.query.get_or_404(card_id)
    
    if card.user_id != current_user.id:
        flash("You do not have permission to modify this card.", "error")
        return redirect(url_for('main.my_cards'))

    selected_cube_ids = [int(cid) for cid in request.form.getlist('cube_ids')]

    current_slots = Card.query.filter_by(custom_card_id=card.id).all()
    current_cube_ids = [slot.cube_id for slot in current_slots]

    changes_made = False

    for cid in selected_cube_ids:
        if cid not in current_cube_ids:

            new_slot = Card(
                cube_id=cid,
                custom_card_id=card.id,
                name=card.name,
                image_url=card.local_image_path,
                mana_cost=card.mana_cost,
                type_line=card.type_line,
                power=card.power,                 
                toughness=card.toughness,         
                text_box=card.text_box
            )
            db.session.add(new_slot)
            changes_made = True
            
    for slot in current_slots:
        if slot.cube_id not in selected_cube_ids:
            db.session.delete(slot)
            changes_made = True

    if changes_made:
        db.session.commit()
        flash("Cube enrollment successfully changed.", "success")

    return redirect(url_for('main.my_cards'))

@main.route('/cube/<int:cube_id>/card/<int:card_id>/change_art', methods=['GET', 'POST'])
@login_required
def change_art(cube_id, card_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        abort(403)
    
    card = Card.query.get_or_404(card_id)
    if card.cube_id != cube_id or not card.scryfall_id:
        abort(404)
    
    if request.method == 'POST':
        new_image_url = request.form.get('image_url')
        if new_image_url:
            # For cards with faces, update both front and back face images
            if card.card_faces and card.card_faces[1].image_url:
                card.card_faces[0].image_url = new_image_url
                # For modal_dfc/transform, update back face by replacing /front/ with /back/
                if card.layout in ['modal_dfc', 'transform'] and len(card.card_faces) > 1:
                    card.card_faces[1].image_url = new_image_url.replace('/front/', '/back/')
            else:
                card.image_url = new_image_url
            db.session.commit()
            flash(f"Art for {card.name} updated successfully!", "success")
            return redirect(url_for('main.view_cube', cube_id=cube_id))
    
    # Fetch the card's oracle_id from Scryfall
    try:
        response = scryfall_requests.get(f"https://api.scryfall.com/cards/{card.scryfall_id}")
        if response.status_code == 200:
            card_data = response.json()
            oracle_id = card_data.get('oracle_id')
        else:
            oracle_id = None
    except Exception:
        oracle_id = None
    
    if not oracle_id:
        alternate_cards = []
    else:
        # Fetch alternate versions
        try:
            response = scryfall_requests.get(
                "https://api.scryfall.com/cards/search",
                params={"q": f"oracle_id:{oracle_id}", "unique": "prints"}
            )
            if response.status_code == 200:
                alternate_cards = response.json().get("data", [])
            else:
                alternate_cards = []
        except Exception:
            alternate_cards = []
    
    return render_template('change_art.html', cube=cube, card=card, alternate_cards=alternate_cards)

@main.route('/cube/<int:cube_id>/card/<int:card_id>/alternates')
@login_required
def get_alternates(cube_id, card_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    card = Card.query.get_or_404(card_id)
    if card.cube_id != cube_id or not card.scryfall_id:
        return jsonify({"error": "Card not found"}), 404
    
    # Fetch the card's oracle_id from Scryfall
    try:
        response = scryfall_requests.get(f"https://api.scryfall.com/cards/{card.scryfall_id}")
        if response.status_code == 200:
            card_data = response.json()
            oracle_id = card_data.get('oracle_id')
        else:
            return jsonify({"alternates": [], "current_scryfall_id": card.scryfall_id})
    except Exception:
        return jsonify({"alternates": [], "current_scryfall_id": card.scryfall_id})
    
    if not oracle_id:
        return jsonify({"alternates": [], "current_scryfall_id": card.scryfall_id})
    
    # Fetch alternate versions
    try:
        response = scryfall_requests.get(
            "https://api.scryfall.com/cards/search",
            params={"q": f"oracle_id:{oracle_id}", "unique": "prints"}
        )
        if response.status_code == 200:
            alternates = response.json().get("data", [])
        else:
            alternates = []
    except Exception:
        alternates = []
    
    return jsonify({"alternates": alternates, "current_scryfall_id": card.scryfall_id})

@main.route('/cube/<int:cube_id>/alternates/<scryfall_id>')
@login_required
def get_alternates_by_scryfall(cube_id, scryfall_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        response = scryfall_requests.get(f"https://api.scryfall.com/cards/{scryfall_id}")
        if response.status_code != 200:
            return jsonify({"alternates": [], "current_scryfall_id": scryfall_id})
        oracle_id = response.json().get('oracle_id')
    except Exception:
        return jsonify({"alternates": [], "current_scryfall_id": scryfall_id})

    if not oracle_id:
        return jsonify({"alternates": [], "current_scryfall_id": scryfall_id})

    try:
        response = scryfall_requests.get(
            "https://api.scryfall.com/cards/search",
            params={"q": f"oracle_id:{oracle_id}", "unique": "prints"}
        )
        alternates = response.json().get("data", []) if response.status_code == 200 else []
    except Exception:
        alternates = []

    return jsonify({"alternates": alternates, "current_scryfall_id": scryfall_id})

@main.route('/cube/<int:cube_id>/card/<int:card_id>/update_art', methods=['POST'])
@login_required
def update_art(cube_id, card_id):
    cube = Cube.query.get_or_404(cube_id)
    if cube.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    card = Card.query.get_or_404(card_id)
    if card.cube_id != cube_id or not card.scryfall_id:
        return jsonify({"error": "Card not found"}), 404
    
    data = request.get_json()
    new_scryfall_id = data.get('scryfall_id')
    if not new_scryfall_id:
        return jsonify({"error": "No scryfall_id provided"}), 400
    
    # Fetch the new card data
    try:
        response = scryfall_requests.get(f"https://api.scryfall.com/cards/{new_scryfall_id}")
        if response.status_code == 200:
            new_card_data = response.json()
            
            # Update basic card fields
            card.scryfall_id = new_scryfall_id
            card.name = new_card_data.get('name', card.name)
            card.layout = new_card_data.get('layout', card.layout)
            
            # Handle image URL based on layout
            new_front_face_image = None
            new_back_face_image = None
            if new_card_data.get('card_faces'):
                # For cards with faces, update the front face image
                front_face = new_card_data['card_faces'][0]
                new_front_face_image = front_face.get('image_uris', {}).get('normal')
                new_image_url = new_front_face_image
                if card.card_faces and len(card.card_faces) > 0:
                    card.card_faces[0].image_url = new_front_face_image
                    card.card_faces[0].name = front_face.get('name', card.card_faces[0].name)
                    card.card_faces[0].mana_cost = front_face.get('mana_cost', card.card_faces[0].mana_cost)
                    card.card_faces[0].type_line = front_face.get('type_line', card.card_faces[0].type_line)
                    card.card_faces[0].text_box = front_face.get('oracle_text', card.card_faces[0].text_box)
                    if len(new_card_data['card_faces']) > 1:
                        back_face = new_card_data['card_faces'][1]
                        new_back_face_image = back_face.get('image_uris', {}).get('normal')
                        if card.layout in ['modal_dfc', 'transform'] and len(card.card_faces) > 1:
                            card.card_faces[1].image_url = new_back_face_image or (new_front_face_image and new_front_face_image.replace('/front/', '/back/'))
                            card.card_faces[1].name = back_face.get('name', card.card_faces[1].name)
                            card.card_faces[1].mana_cost = back_face.get('mana_cost', card.card_faces[1].mana_cost)
                            card.card_faces[1].type_line = back_face.get('type_line', card.card_faces[1].type_line)
                            card.card_faces[1].text_box = back_face.get('oracle_text', card.card_faces[1].text_box)
                else:
                    card.image_url = new_front_face_image  # Fallback
            else:
                # For other layouts, use the main image
                new_image_url = new_card_data.get('image_uris', {}).get('normal')
                card.image_url = new_image_url
            
            if new_image_url:
                db.session.commit()
                return jsonify({
                    "success": True,
                    "new_image_url": new_image_url,
                    "new_front_face_image": new_front_face_image,
                    "new_back_face_image": new_back_face_image
                })
            else:
                return jsonify({"error": "No image URL found for the selected card"}), 400
        else:
            return jsonify({"error": "Failed to fetch card data"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500