from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
from marshmallow import Schema, fields, ValidationError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meat_freshness.db'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

db = SQLAlchemy(app)
jwt = JWTManager(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'manager', 'customer', 'admin'

class ButcherShop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(120), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class MeatData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    butcher_shop_id = db.Column(db.Integer, db.ForeignKey('butcher_shop.id'), nullable=False)
    impedance = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False)
    part = db.Column(db.String(80), nullable=False)
    store_date = db.Column(db.DateTime, default=datetime.utcnow)

class UserSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)
    user_type = fields.String(required=True)

class ButcherShopSchema(Schema):
    name = fields.String(required=True)
    location = fields.String(required=True)
    contact = fields.String()
    manager_id = fields.Integer(required=True)

class MeatDataSchema(Schema):
    impedance = fields.Float(required=True)
    purchase_date = fields.DateTime(required=True)
    butcher_shop_id = fields.Integer(required=True)
    part = fields.String(required=True)

user_schema = UserSchema()
butcher_shop_schema = ButcherShopSchema()
meat_data_schema = MeatDataSchema()

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    try:
        validated_data = user_schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    new_user = User(
        username=validated_data['username'],
        password=validated_data['password'],
        user_type=validated_data['user_type']
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User signed up successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    try:
        validated_data = user_schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    user = User.query.filter_by(username=validated_data['username'], password=validated_data['password']).first()
    if user:
        access_token = create_access_token(identity={"id": user.id, "user_type": user.user_type})
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Bad username or password"}), 401

@app.route('/register_shop', methods=['POST'])
@jwt_required()
def register_shop():
    current_user = get_jwt_identity()
    if current_user['user_type'] != 'manager':
        return jsonify({"msg": "Only managers can register a shop"}), 403
    
    data = request.get_json()
    try:
        validated_data = butcher_shop_schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_shop = ButcherShop(
        name=validated_data['name'],
        location=validated_data['location'],
        contact=validated_data.get('contact'),
        manager_id=current_user['id']
    )
    db.session.add(new_shop)
    db.session.commit()

    return jsonify({"msg": "Butcher shop registered successfully"}), 201

@app.route('/meat_data', methods=['POST'])
@jwt_required()
def store_meat_data():
    current_user = get_jwt_identity()
    if current_user['user_type'] != 'customer':
        return jsonify({"msg": "Only customers can store meat data"}), 403

    user_id = current_user['id']
    data = request.get_json()
    try:
        validated_data = meat_data_schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_meat_data = MeatData(
        user_id=user_id,
        butcher_shop_id=validated_data['butcher_shop_id'],
        impedance=validated_data['impedance'],
        purchase_date=validated_data['purchase_date'],
        part=validated_data['part']
    )
    db.session.add(new_meat_data)
    db.session.commit()

    return jsonify({"msg": "Meat data stored successfully"}), 201

@app.route('/calculate_quality', methods=['POST'])
@jwt_required()
def calculate_quality():
    current_user = get_jwt_identity()
    if current_user['user_type'] != 'customer':
        return jsonify({"msg": "Only customers can calculate quality"}), 403

    user_id = current_user['id']
    data = request.get_json()
    try:
        validated_data = meat_data_schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    old_meat_data = MeatData.query.filter_by(user_id=user_id, part=validated_data['part'], butcher_shop_id=validated_data['butcher_shop_id']).first()
    if not old_meat_data:
        return jsonify({"msg": "No previous data found for this meat"}), 404

    impedance_change = validated_data['impedance'] - old_meat_data.impedance
    quality_degradation = impedance_change / old_meat_data.impedance * 100  # Example formula

    return jsonify({"quality_degradation": quality_degradation}), 200

@app.route('/meat_list', methods=['GET'])
@jwt_required()
def meat_list():
    current_user = get_jwt_identity()
    if current_user['user_type'] != 'customer':
        return jsonify({"msg": "Only customers can view their meat list"}), 403

    user_id = current_user['id']
    meat_data = MeatData.query.filter_by(user_id=user_id).all()
    result = meat_data_schema.dump(meat_data, many=True)
    return jsonify(result), 200

@app.route('/admin/users', methods=['GET'])
@jwt_required()
def admin_users():
    current_user = get_jwt_identity()
    if current_user['user_type'] != 'admin':
        return jsonify({"msg": "Only admins can view users"}), 403

    users = User.query.all()
    result = user_schema.dump(users, many=True)
    return jsonify(result), 200

@app.route('/admin/shops', methods=['GET'])
@jwt_required()
def admin_shops():
    current_user = get_jwt_identity()
    if current_user['user_type'] != 'admin':
        return jsonify({"msg": "Only admins can view shops"}), 403

    shops = ButcherShop.query.all()
    result = butcher_shop_schema.dump(shops, many=True)
    return jsonify(result), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
