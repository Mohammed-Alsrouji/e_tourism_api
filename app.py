from db import Base, User, Guide, Driver, Programme, Tour, Tourist  

from flask import Flask, request, jsonify
from flask import request, jsonify

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from werkzeug.security import generate_password_hash, check_password_hash

import json
import jwt
from functools import wraps
from datetime import datetime, timedelta


# Initialize the Flask app
app = Flask(__name__)
SECRET_KEY = "2c2c5accb45b3325628aaddabc387fce75563c0bd3c03321"

# Database setup
engine = create_engine('sqlite:///./e_tourism.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


def get_db_connection():
    session = DBSession() 
    return session


def fix_base64_padding(token):
    padding = len(token) % 4
    if padding != 0:
        token += '=' * (4 - padding)
    return token


@app.route('/')
def index():
    return jsonify({"message": "Welcome to the E_Tourism"}), 200


#### User Registration route
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    fName = data.get('fName')
    lName = data.get('lName')
    description = data.get('description')

    if session.query(User).filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    new_user = User(
        username=username,
        fName=fName,
        lName=lName,
        description=description,
    )
    new_user.set_password(password)  
    session.add(new_user)
    session.commit()

    token = jwt.encode({
        'user_id': new_user.id,
        'exp': datetime.utcnow() + timedelta(hours=3)  
    }, SECRET_KEY, algorithm='HS256')

    return jsonify({"message": "User registered successfully", "token": token}), 201


### Create admin route
@app.route('/create_admin', methods=['POST'])
def create_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    fName = data.get('fName')
    lName = data.get('lName')
    description = data.get('description')

    if session.query(User).filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    new_admin = User(
        username=username,
        fName=fName,
        lName=lName,
        description=description,
        is_admin=True
    )
    new_admin.set_password(password)  
    session.add(new_admin)
    session.commit()
    return jsonify({"message": "Admin user created successfully"}), 201


### Login route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = session.query(User).filter_by(username=username).first()

    if user and user.check_password(password):  # This checks the password
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(hours=3)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({"message": "Login successful", "token": token}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401
        

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"message": "Token is missing"}), 403
        try:
            token = token.split(" ")[1] 
            token = fix_base64_padding(token) 
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = decoded['user_id']
            user = session.query(User).filter_by(id=user_id).first()
        except IndexError:
            return jsonify({"message": "Token format is invalid"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError as e:
            print(f"Invalid token error: {e}") 
            return jsonify({"message": "Invalid token"}), 401

        if user is None:
            return jsonify({"message": "User not found"}), 401
        return f(*args, **kwargs)  
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"error": "Token is missing"}), 403

        try:
            decoded = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=['HS256'])
            user_id = decoded['user_id']
            user = session.query(User).filter_by(id=user_id).first()
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        if user is None or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)
    return decorated_function


@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    return jsonify({"message": "Welcome to the dashboard!"}), 200


@app.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    return jsonify({"message": "Welcome to the admin dashboard!"}), 200


# Registration Endpoints
# Endpoint	                        Method	        Purpose	                                    Auth Required

# /register	                        POST	        Register a user                             No
# /login	                        POST	        Login                                       No

# /create_admin                     POST            Register an admin user                      No

#####################################  Tour routes  ########################################## 

#Add a New Tour (admin only)
@app.route('/tours', methods=['POST'])
@admin_required 
def add_tour():
    data = request.get_json()
    guide_id = data.get('guide_id')
    driver_id = data.get('driver_id')
    programme_id = data.get('programme_id')
    price = data.get('price')
    number = data.get('number')
    start_date = data.get('start_date')
    
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    tour = Tour(guide_id=guide_id, driver_id=driver_id, programme_id=programme_id, price=price, number=number, start_date=start_date)
    
    session.add(tour)
    session.commit()
    
    return jsonify({"message": "Tour created successfully", "tour_id": tour.id}), 201


# update tour (admin only)
@app.route('/tours/<int:tour_id>', methods=['PUT'])
@admin_required 
def update_tour(tour_id):
    data = request.get_json()
    tour = session.query(Tour).filter_by(id=tour_id).first()
    
    if not tour:
        return jsonify({"error": "Tour not found"}), 404

    if "guide_id" in data: tour.guide_id = data["guide_id"]
    if "driver_id" in data: tour.driver_id = data["driver_id"]
    if "programme_id" in data: tour.programme_id = data["programme_id"]
    if "price" in data: tour.price = data["price"]
    if "number" in data: tour.number = data["number"]
    if "start_date" in data:
        tour.start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
    
    session.commit()
    return jsonify({"message": "Tour updated successfully"}), 200


# delete tour (admin only)
@app.route('/tours/<int:tour_id>', methods=['DELETE'])
@admin_required 
def delete_tour(tour_id):

    tour = session.query(Tour).filter_by(id=tour_id).first()
    if not tour:
        return jsonify({"error": "Tour not found"}), 404

    session.delete(tour)
    session.commit()
    return jsonify({"message": "Tour deleted successfully"}), 200


# Get all tours
@app.route('/tours', methods=['GET'])
@login_required
def get_tours():
    tours = session.query(Tour).all()
    
    response = []
    for tour in tours:
        driver = session.query(Driver).filter_by(id=tour.driver_id).first()
        guide = session.query(Guide).filter_by(id=tour.guide_id).first()
        programme = session.query(Programme).filter_by(id=tour.programme_id).first()

        response.append({
            "id": tour.id,
            "driver": {
                "fName": driver.fName,
                "lName": driver.lName
            },
            "guide": {
                "fName": guide.fName,
                "lName": guide.lName
            },
            "programme": {
                "type": programme.type
            },
            "price": tour.price,
            "number": tour.number,
            "start_date": tour.start_date.strftime("%a, %d %b %Y 00:00:00 GMT")  # Format date as required
        })

    return jsonify(response), 200


# Get all tourists in specific tour
@app.route('/tours/<int:tour_id>/tourists', methods=['GET'])
@login_required
def get_tourists_for_tour(tour_id):
    tour = session.query(Tour).filter_by(id=tour_id).first()

    if not tour:
        return jsonify({"error": "Tour not found"}), 404

    tourists = session.query(Tourist).filter_by(tour_id=tour_id).all()

    guide = session.query(Guide).filter_by(id=tour.guide_id).first()
    driver = session.query(Driver).filter_by(id=tour.driver_id).first()
    programme = session.query(Programme).filter_by(id=tour.programme_id).first()

    tourists_data = [{
        "id": tourist.id,
        "fName": tourist.fName,
        "lName": tourist.lName,
        "description": tourist.description,
        "tour_id": tourist.tour_id
    } for tourist in tourists]

    guide_data = {
        "id": guide.id,
        "fName": guide.fName,
        "lName": guide.lName,
        "address": guide.address,
        "mobile": guide.mobile,
        "description": guide.description
    } if guide else None

    driver_data = {
        "id": driver.id,
        "fName": driver.fName,
        "lName": driver.lName,
        "plateNumber": driver.plateNumber,
        "description": driver.description
    } if driver else None

    programme_data = {
        "id": programme.id,
        "type": programme.type,
        "name": programme.name,
        "description": programme.description
    } if programme else None

    response = {
        "tour_id": tour.id,
        "start_date": tour.start_date,
        "tourists": tourists_data,
        "guide": guide_data,
        "driver": driver_data,
        "programme": programme_data
    }
    return jsonify(response), 200


# search for tours
@app.route('/tours/<int:tour_id>', methods=['GET'])
@login_required
def get_tour(tour_id):
    conn = get_db_connection()
    
    tour = conn.execute(text(''' 
        SELECT t.id AS tour_id, 
               t.guide_id, 
               t.driver_id, 
               t.price, 
               t.number, 
               t.start_date, 
               g.fName AS guide_fName, 
               g.lName AS guide_lName,
               d.fName AS driver_fName, 
               d.lName AS driver_lName,
               p.id AS programme_id, 
               p.name AS programme_name,
               p.description AS programme_description
        FROM tour t
        LEFT JOIN guide g ON t.guide_id = g.id
        LEFT JOIN driver d ON t.driver_id = d.id
        LEFT JOIN programme p ON t.programme_id = p.id
        WHERE t.id = :tour_id
    '''), {"tour_id": tour_id}).mappings().fetchone()
    
    conn.close()
    
    if tour:
        return jsonify({
            "id": tour.tour_id,
            "guide": {
                "fName": tour.guide_fName,
                "lName": tour.guide_lName
            },
            "driver": {
                "fName": tour.driver_fName,
                "lName": tour.driver_lName
            },
            "programme": {
                "id": tour.programme_id,
                "name": tour.programme_name,
                "description": tour.programme_description
            },
            "price": tour.price,
            "number": tour.number,
            "start_date": tour.start_date  # Format date as desired
        }), 200
    else:
        return jsonify({"error": "Tour not found"}), 404



# Report: How many tours each bus (driver) conducted between two dates
@app.route('/report/tours_by_bus', methods=['GET'])
@login_required
def report_tours_by_bus():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({"error": "Please provide start_date and end_date in the format YYYY-MM-DD"}), 400

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    conn = get_db_connection()

    tours = conn.execute(text('''
        SELECT 
            t.id AS tour_id, t.price, t.number, t.start_date,
            d.id AS driver_id, d.fName AS driver_first_name, d.lName AS driver_last_name, d.plateNumber AS driver_plate,
            g.id AS guide_id, g.fName AS guide_first_name, g.lName AS guide_last_name, g.address AS guide_address, g.mobile AS guide_mobile,
            p.id AS programme_id, p.name AS programme_name, p.type AS programme_type, p.description AS programme_description
        FROM tour t
        LEFT JOIN driver d ON t.driver_id = d.id
        LEFT JOIN guide g ON t.guide_id = g.id
        LEFT JOIN programme p ON t.programme_id = p.id
        WHERE t.start_date BETWEEN :start_date AND :end_date
    '''), {"start_date": start_date, "end_date": end_date}).mappings().all()
    
    conn.close()

    driver_dict = {}
    for tour in tours:
        driver_id = tour['driver_id']
        if driver_id not in driver_dict:
            driver_dict[driver_id] = {
                "driver_id": driver_id,
                "first_name": tour['driver_first_name'],
                "last_name": tour['driver_last_name'],
                "plate_number": tour['driver_plate'],
                "tour_count": 0,  
                "tours": []
            }
        
        driver_dict[driver_id]["tour_count"] += 1

        driver_dict[driver_id]["tours"].append({
            "tour_id": tour['tour_id'],
            "price": tour['price'],
            "number": tour['number'],
            "start_date": tour['start_date'],
            "guide": {
                "id": tour['guide_id'],
                "first_name": tour['guide_first_name'],
                "last_name": tour['guide_last_name'],
                "address": tour['guide_address'],
                "mobile": tour['guide_mobile']
            },
            "programme": {
                "id": tour['programme_id'],
                "name": tour['programme_name'],
                "type": tour['programme_type'],
                "description": tour['programme_description']
            }
        })

    result = list(driver_dict.values())
    return jsonify(result), 200


# Tour Endpoints
# Endpoint	                                        Method	        Purpose	                                    Auth Required

# /tours	                                        POST	        Add a new tour	                            Yes (Admin)
# /tours/<int:tour_id>	                            PUT	            Update tour details	                        Yes (Admin)
# /tours/<int:tour_id>	                            DELETE	        Delete a specific tour	                    Yes (Admin)

# /tours	                                        GET	            View all tours	                            Yes (User)
# /tours/<int:tour_id>/tourists                     GET             Get all tourists in specific tour           Yes (User)
# /tours/<int:tour_id>                              GET	            Search for specific tour	                Yes (User)
# /report/tours_by_bus?start_date=?&end_date=?      GET	            Report on tour counts per driver (bus)	    Yes (User)


#####################################  Guide routes  ##########################################

# Add guide route 
@app.route('/guides', methods=['POST'])
@admin_required 
def add_guide():
    data = request.get_json()
    fName = data.get('fName')
    lName = data.get('lName')
    address = data.get('address')
    mobile = data.get('mobile')
    description = data.get('description')

    guide = Guide(fName=fName, lName=lName, address=address, mobile=mobile, description=description)
    
    session.add(guide)
    session.commit()
    return jsonify({"message": "Guide added successfully", "guide_id": guide.id}), 201


# Update guide route
@app.route('/guides/<int:guide_id>', methods=['PUT'])
@admin_required 
def update_guide(guide_id):

    data = request.get_json()
    guide = session.query(Guide).filter_by(id=guide_id).first()
    
    if not guide:
        return jsonify({"error": "Guide not found"}), 404

    if "fName" in data: guide.fName = data["fName"]
    if "lName" in data: guide.lName = data["lName"]
    if "address" in data: guide.address = data["address"]
    if "mobile" in data: guide.mobile = data["mobile"]
    if "description" in data: guide.description = data["description"]
    
    session.commit()
    return jsonify({"message": "Guide updated successfully"}), 200


# Delete guide route 
@app.route('/guides/<int:guide_id>', methods=['DELETE'])
@admin_required 
def delete_guide(guide_id):

    guide = session.query(Guide).filter_by(id=guide_id).first()
    if not guide:
        return jsonify({"error": "Guide not found"}), 404

    session.delete(guide)
    session.commit()
    return jsonify({"message": "Guide deleted successfully"}), 200


# Get all guides 
@app.route('/guides', methods=['GET'])
@login_required
def get_guides():
    conn = get_db_connection()
    
    guides_with_tours = conn.execute(text('''
        SELECT g.id AS guide_id, g.fName, g.lName, g.address, g.mobile, g.description,
               t.id AS tour_id, t.number AS tour_number
        FROM guide g
        LEFT JOIN tour t ON g.id = t.guide_id
    ''')).fetchall()
    
    conn.close()
    
    guide_list = []
    for row in guides_with_tours:
        existing_guide = next((item for item in guide_list if item['id'] == row.guide_id), None)
        
        if existing_guide:
            if row.tour_id:
                existing_guide['tours'].append({
                    'tourId': row.tour_id,
                    'tourNumber': row.tour_number
                })
        else:
            guide_entry = {
                'id': row.guide_id,
                'fName': row.fName,
                'lName': row.lName,
                'address': row.address,
                'mobile': row.mobile,
                'description': row.description,
                'tours': [{
                    'tourId': row.tour_id,
                    'tourNumber': row.tour_number
                }] if row.tour_id else []
            }
            guide_list.append(guide_entry)

    return jsonify(guide_list), 200


    
# Guide Endpoint
# Endpoint	                    Method	    Purpose	                    Auth Required

# /guides	                    POST        Add a new guide	            Yes (Admin)
# /guides/<int:guide_id>	    PUT	        Update guide information	Yes (Admin)
# /guides/<int:guide_id>	    DELETE	    Delete a specific guide	    Yes (Admin)
# /guides                       GET         Get all guides              Yes (User)


#####################################  Driver routes  ##########################################

# Add driver route 
@app.route('/drivers', methods=['POST'])
@admin_required 
def add_driver():

    data = request.get_json()
    fName = data.get('fName')
    lName = data.get('lName')
    plateNumber = data.get('plateNumber')
    description = data.get('description')

    driver = Driver(fName=fName, lName=lName, plateNumber=plateNumber, description=description)
    
    session.add(driver)
    session.commit()
    return jsonify({"message": "Driver added successfully", "driver_id": driver.id}), 201


# update driver route 
@app.route('/drivers/<int:driver_id>', methods=['PUT'])
@admin_required 
def update_driver(driver_id):

    data = request.get_json()
    driver = session.query(Driver).filter_by(id=driver_id).first()
    
    if not driver:
        return jsonify({"error": "Driver not found"}), 404

    if "fName" in data: driver.fName = data["fName"]
    if "lName" in data: driver.lName = data["lName"]
    if "plateNumber" in data: driver.plateNumber = data["plateNumber"]
    if "description" in data: driver.description = data["description"]
    
    session.commit()
    return jsonify({"message": "Driver updated successfully"}), 200


# delete driver route 
@app.route('/drivers/<int:driver_id>', methods=['DELETE'])
@admin_required 
def delete_driver(driver_id):

    driver = session.query(Driver).filter_by(id=driver_id).first()
    if not driver:
        return jsonify({"error": "Driver not found"}), 404

    session.delete(driver)
    session.commit()
    return jsonify({"message": "Driver deleted successfully"}), 200


# Get all drivers
@app.route('/drivers', methods=['GET'])
@login_required
def get_drivers():
    conn = get_db_connection()
    
    drivers_with_tours = conn.execute(text('''
        SELECT d.id AS driver_id, d.fName, d.lName, d.plateNumber, d.description,
               t.id AS tour_id, t.number AS tour_number
        FROM driver d
        LEFT JOIN tour t ON d.id = t.driver_id
    ''')).mappings().fetchall()
    
    conn.close()
    
    driver_list = []
    for driver in drivers_with_tours:
        existing_driver = next((d for d in driver_list if d['id'] == driver['driver_id']), None)
        
        if existing_driver:
            if driver['tour_id']:
                existing_driver['tours'].append({
                    'tourId': driver['tour_id'],
                    'tourNumber': driver['tour_number']
                })
        else:
            driver_list.append({
                'id': driver['driver_id'],
                'fName': driver['fName'],
                'lName': driver['lName'],
                'plateNumber': driver['plateNumber'],
                'description': driver['description'],
                'tours': [{
                    'tourId': driver['tour_id'],
                    'tourNumber': driver['tour_number']
                }] if driver['tour_id'] else []
            })
    
    return jsonify(driver_list)



# Driver Endpoint
# Endpoint	                Method	    Purpose	                    Auth Required

# /drivers	                POST        Add a new driver	        Yes (Admin)
# /drivers/<int:driver_id>	PUT	        Update driver information	Yes (Admin)
# /drivers/<int:driver_id>	DELETE	    Delete a specific driver	Yes (Admin)
# /drivers	                GET         Get all drivers	            Yes (User)


#####################################  Programme routes  ##########################################

# add programme route 
@app.route('/programmes', methods=['POST'])
@admin_required 
def add_programme():

    data = request.get_json()
    programme_type = data.get('type')
    name = data.get('name')
    description = data.get('description')

    programme = Programme(type=programme_type, name=name, description=description)
    
    session.add(programme)
    session.commit()
    return jsonify({"message": "Programme added successfully", "programme_id": programme.id}), 201


# update programme route 
@app.route('/programmes/<int:programme_id>', methods=['PUT'])
@admin_required 
def update_programme(programme_id):

    data = request.get_json()
    programme = session.query(Programme).filter_by(id=programme_id).first()
    
    if not programme:
        return jsonify({"error": "Programme not found"}), 404

    if "type" in data: programme.type = data["type"]
    if "name" in data: programme.name = data["name"]
    if "description" in data: programme.description = data["description"]
    
    session.commit()
    return jsonify({"message": "Programme updated successfully"}), 200


# delete programme route 
@app.route('/programmes/<int:programme_id>', methods=['DELETE'])
@admin_required 
def delete_programme(programme_id):

    programme = session.query(Programme).filter_by(id=programme_id).first()
    if not programme:
        return jsonify({"error": "Programme not found"}), 404

    session.delete(programme)
    session.commit()
    return jsonify({"message": "Programme deleted successfully"}), 200


# Get all programmes with related tours route
@app.route('/programmes', methods=['GET'])
@login_required
def get_programmes():
    conn = get_db_connection()
    
    programmes_with_tours = conn.execute(text(''' 
        SELECT p.id AS programme_id, 
               p.type, 
               p.name, 
               p.description,
               t.id AS tour_id, 
               t.price, 
               t.number 
        FROM programme p 
        LEFT JOIN tour t ON p.id = t.programme_id 
    ''')).mappings().fetchall()
    
    conn.close()
    
    programme_list = []
    for programme in programmes_with_tours:
        existing_programme = next((item for item in programme_list if item['id'] == programme.programme_id), None)
        
        if existing_programme:
            existing_programme['tours'].append({  # Use dictionary access instead of attribute
                'tour_id': programme.tour_id,
                'price': programme.price,
                'number': programme.number
            })
        else:
            programme_list.append({
                'id': programme.programme_id,
                'type': programme.type,
                'name': programme.name,
                'description': programme.description,
                'tours': [{
                    'tour_id': programme.tour_id,
                    'price': programme.price,
                    'number': programme.number
                }] if programme.tour_id else []
            })
    
    return jsonify(programme_list)



# Programme Endpoint
# Endpoint	                            Method      Purpose	                        Auth Required

# /programmes	                        POST	    Add a new programme	            Yes (Admin)
# /programmes/<int:programme_id>	    PUT	        Update programme information	Yes (Admin)
# /programmes/<int:programme_id>	    DELETE	    Delete a specific programme	    Yes (Admin)
# /programmes                           GET         Get all programmes              Yes (User)


#####################################  Tourist  routes  ##########################################

# Add tourist (for a specific tour)
@app.route('/tourists', methods=['POST'])
@login_required
def add_tourist():
    data = request.get_json()
    id = data.get('id')  
    fName = data.get('fName')
    lName = data.get('lName')
    description = data.get('description')
    tour_id = data.get('tour_id')  

    tourist = Tourist(fName=fName, lName=lName, description=description, tour_id=tour_id)

    session.add(tourist)
    session.commit()
    return jsonify({"message": "Tourist added successfully", "tourist_id": tourist.id}), 201


#Update Tourist
@app.route('/tourists/<int:tourist_id>', methods=['PUT'])
@login_required
def update_tourist(tourist_id):
    data = request.get_json()
    tourist = session.query(Tourist).filter_by(id=tourist_id).first()

    if not tourist:
        return jsonify({"error": "Tourist not found"}), 404

    if "fName" in data:
        tourist.fName = data["fName"]
    if "lName" in data:
        tourist.lName = data["lName"]
    if "description" in data:
        tourist.description = data["description"]
    if "tour_id" in data:
        tourist.tour_id = data["tour_id"]

    session.commit()
    return jsonify({"message": "Tourist updated successfully"}), 200


# Delete Tourist
@app.route('/tourists/<int:tourist_id>', methods=['DELETE'])
@login_required
def delete_tourist(tourist_id):
    tourist = session.query(Tourist).filter_by(id=tourist_id).first()
    
    if not tourist:
        return jsonify({"error": "Tourist not found"}), 404
    
    session.delete(tourist)
    session.commit()
    return jsonify({"message": "Tourist deleted successfully"}), 200


# Get all tourists
@app.route('/tourists', methods=['GET'])
@login_required
def get_all_tourists():
    tourists = session.query(Tourist).all()
    result = [{
        "id": tourist.id,
        "fName": tourist.fName,
        "lName": tourist.lName,
        "description": tourist.description,
        "tour_id": tourist.tour_id
    } for tourist in tourists]
    
    return jsonify(result), 200


# Tourist Endpoint
# Endpoint	                    Method      Purpose	                                    Auth Required

# /tourists	                    POST	    Add a new tourist for a specific tour	    Yes (User)
# /tourists/<int:tourist_id>	PUT	        Update a specific tourist	                Yes (User)
# /tourists/<int:tourist_id>	DELETE	    Delete a specific tourist	                Yes (User)
# /tourists	                    GET	        Show all tourists	                        Yes (User)