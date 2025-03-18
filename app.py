from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_cors import CORS
import os
app = Flask(__name__)
#adds a reource to enable CORS
#CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)# Configurations
cors = CORS(app, resources={
    r"/*": {
        "origins": "*"
    }
}, supports_credentials=True)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://nickson_user:DrHqtHLTOtTlBRIssmNGEx4wQX9APstO@dpg-cv8nrprqf0us73bb0tb0-a.oregon-postgres.render.com/nickson'
# postgresql://denning:1K8nPtTPgJsuFDhmfL3nEl48tl2DJpu3@dpg-csbupntds78s73bg9mk0-a.oregon-postgres.render.com/journal_app_ztyc  # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'heynowbrowncow'
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=7)
UPLOAD_FOLDER = "static/uploads"  # Adjust path as needed
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Models

# User Model
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

    followers = db.relationship(
        'Follower',
        foreign_keys='Follower.followed_id',
        backref='followed',
        lazy=True
    )

    following = db.relationship(
        'Follower',
        foreign_keys='Follower.follower_id',
        backref='follower',
        lazy=True
    )

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Post Model
class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    comments = db.relationship('Comment', backref='post', lazy=True)

# Comment Model
class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

# Follower Model (Association Table)
class Follower(db.Model):
    __tablename__ = 'followers'

    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    follow_date = db.Column(db.DateTime, default=datetime.utcnow)

# REST Endpoints

# User registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    description = data.get('description')

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    new_user = User(username=username, email=email, name=name, description=description)
    new_user.set_password(password)  # Use the hashing method
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()

    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'followers_count': len(user.followers),
        'posts_count': len(user.posts)  # Add posts count
    } for user in users])

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'name': user.name,
        'description': user.description,
        'followers_count': len(user.followers),  # Add followers count
        'posts_count': len(user.posts)  # Add posts count
    }), 200


# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({'message': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=user.id)
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'name': user.name,
        'description': user.description
    }

    return jsonify({
        'user': user_data,
        'access_token': access_token  # Changed from 'token' to 'access_token'
    }), 200

# Get user profile (JWT-protected)
@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)

    # Get counts
    posts_count = len(user.posts)
    followers_count = len(user.followers)
    following_count = len(user.following)
    comments_count = len(user.comments)

    # Return profile data with counts
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'name': user.name,
        'description': user.description,
        'posts_count': posts_count,
        'followers_count': followers_count,
        'following_count': following_count,
        'comments_count': comments_count
    }), 200

@app.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    user_id = get_jwt_identity()

    if "title" not in request.form or "content" not in request.form:
        return jsonify({"message": "Title and content are required"}), 400

    title = request.form["title"]
    content = request.form["content"]
    image_path = None

    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{user_id}_{int(datetime.utcnow().timestamp())}_{filename}"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            file.save(file_path)
            image_path = f"/{file_path}"

    new_post = Post(
        title=title,
        content=content,
        image_url=image_path,
        user_id=user_id
    )
    db.session.add(new_post)
    db.session.commit()

    return jsonify({"message": "Post created", "post_id": new_post.id}), 201

@app.route('/posts', methods=['GET'])
def get_posts():
    posts = Post.query.all()

    return jsonify([{
        'id': post.id,  # Added post ID
        'title': post.title,
        'content': post.content,
        'image_url': post.image_url,
        'created_at': post.created_at,
        'author': post.author.username,
        'number_of_comments': len(post.comments)
    } for post in posts])

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.query.get_or_404(post_id)
    return jsonify({
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'image_url': post.image_url,
        'author': post.author.username,
        'created_at': post.created_at.isoformat(),
        'number_of_comments': len(post.comments),
        'user_id': post.user_id  # Added
    }), 200

@app.route('/posts/<int:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    content = data.get('content')

    if not content:
        return jsonify({'msg': 'Content is required'}), 400

    comment = Comment(content=content, user_id=user_id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()

    return jsonify({'msg': 'Comment created', 'comment': {'id': comment.id, 'content': comment.content, 'created_at': comment.created_at}}), 201

# Endpoint to get comments for a post
@app.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    # Query the post to ensure it exists
    post = Post.query.get_or_404(post_id)

    # Query all comments related to the post
    comments = Comment.query.filter_by(post_id=post.id).all()

    # Return the comments in JSON format
    return jsonify([{
        'id': comment.id,
        'content': comment.content,
        'author': comment.user.username,  # Assuming 'user' is the backref to User model
        'created_at': comment.created_at
    } for comment in comments]), 200
# Endpoint to follow a user
@app.route('/follow/<int:user_id>', methods=['POST'])
@jwt_required()
def follow_user(user_id):
    follower_id = get_jwt_identity()

    # Check if the follower is already following the user
    existing_follow = Follower.query.filter_by(follower_id=follower_id, followed_id=user_id).first()
    if existing_follow:
        return jsonify({'msg': 'You are already following this user'}), 400

    follow = Follower(follower_id=follower_id, followed_id=user_id)
    db.session.add(follow)
    db.session.commit()

    return jsonify({'msg': 'Successfully followed user'}), 201

# Endpoint to unfollow a user
@app.route('/unfollow/<int:user_id>', methods=['DELETE'])
@jwt_required()
def unfollow_user(user_id):
    follower_id = get_jwt_identity()
    
    # Check if the follower is currently following the user
    follow = Follower.query.filter_by(follower_id=follower_id, followed_id=user_id).first()
    if not follow:
        return jsonify({'msg': 'You are not following this user'}), 400

    db.session.delete(follow)
    db.session.commit()

    return jsonify({'msg': 'Successfully unfollowed user'}), 200

if __name__ == '__main__':
    app.run(debug=True)
