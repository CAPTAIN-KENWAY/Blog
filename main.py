# IMPORT MODULES
from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, ContactForm
from flask_gravatar import Gravatar
from functools import wraps
import smtplib
from dotenv.main import load_dotenv
import os

# SETUP APP AND VARIABLES
BLOGGERS = (1,3)
load_dotenv()
EMAIL = os.environ['EMAIL']
PASSWORD = os.environ['PASSWORD']

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite3:///blog')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# CREATE FLASK LOGIN
login_manager = LoginManager()
login_manager.init_app(app=app)

# AVATAR FOR COMMENTS
gravatar = Gravatar(
    app, rating='g', size=20, default='retro', force_default=False, force_lower=False, use_ssl=False,
    base_url=None)


# DECORATOR FUNCTION FOR ADMINS ONLY
def admins_only(func):
    wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_anonymous and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function


# DECORATOR FUNCTION FOR BLOGGERS TO CREATE POST AND EDIT
def bloggers(func):
    wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_anonymous and current_user.id in BLOGGERS:
            return func(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function

# SEND CONTACT MESSAGE AS MAIL
def send_mail(name, email, phone, message):
    msg = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}"
    with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
        connection.starttls()
        connection.login(user=EMAIL, password=PASSWORD)
        connection.sendmail(
            from_addr=EMAIL,
            to_addrs="youremail@gmail.com",
            msg=msg.encode('utf-8')
        )


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    #author = db.relationship('User', back_populates='posts')
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post')


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = db.relationship('BlogPost', backref='author')
    comments = db.relationship('Comment', backref='user')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))

# NEEDED WHEN RUNNING FOR FIRST TIME TO CREATE DATABASES
# with app.app_context():
#         db.create_all()


# USER LOADER FUNCTION TO LOGIN USER
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# HOME ROUTE FOR MAINPAGE OF BLOG
@app.route('/')
def home():
    authorid = request.args.get('author_id')
    if authorid:
        posts = db.session.query(BlogPost).filter_by(author_id=authorid)
        return render_template("index.html", all_posts=posts, author_posts=True, bloggers=BLOGGERS)
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, author_posts=False, bloggers=BLOGGERS)

# REGISTER ROUTE TO ADD NEW USERS
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if db.session.query(User).filter_by(email=form.email.data).first():
            flash("Email already exist in database. Please login instead.")
            return redirect(url_for('login'))
        hash_password = generate_password_hash(
            password=form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            password=hash_password,
            name=form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(user=new_user)
        return redirect(url_for('home'))
    return render_template("register.html", form=form)

# LOGIN ROUTE TO SIGN IN USERS IN THE BLOG
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(email=form.email.data).first()
        # CHECKING EMAIL AND PASSWORD
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user=user)
                return redirect(url_for('home'))
            flash('Incorrect Password')
        else:
            flash("Email doesn't exist in the database")
    return render_template("login.html", form=form)

# LOGOUT ROUTE TO SIGN OUT USERS
@app.route('/logout')
def logout():
    if logout_user():
        return redirect(url_for('home'))

# POST ROUTE TO SHOW INDIVIDUAL POST
@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = db.session.query(Comment).filter_by(post_id=requested_post.id)
    if form.validate_on_submit():
        # CHECKING IF USER IS LOGGED IN FOR WRITING COMMENTS
        if current_user.is_authenticated:
            user = current_user.id
            post = requested_post.id
            new_comment = Comment(
                comment=form.comment.data,
                user_id=user,
                post_id=post
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=requested_post.id))
        else:
            flash("Please Login. If New User, Please Register First")
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, form=form, comments=comments, avatar=gravatar)

# ABOUT ROUTE TO SHOW ABOUT PAGE
@app.route("/about")
def about():
    return render_template("about.html")

# CONTACT ROUTE TO SEND MESSAGE AS MAIL
@app.route("/contact", methods=['POST', 'GET'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        send_mail(form.name.data, form.email.data, form.phone.data, form.message.data) 
        form = ContactForm(formdata=None)
        return render_template("contact.html", msg_sent=True, form=form)

    return render_template("contact.html", msg_sent=False, form=form)

# NEW POST ROUTE TO CREATE NEW POSTS IN BLOG
@app.route("/new-post", endpoint='add', methods=['GET', 'POST'])
@bloggers
def add():
    form = CreatePostForm()
    if form.validate_on_submit():
        # CHECKING IF POST WITH SAME TITLE ALREADY PRESENT
        if db.session.query(BlogPost).filter_by(title=form.title.data).first():
            flash("Post with same title already exists.")
            return render_template("make-post.html", form=form)

        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()                  
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form)

# EDIT ROUTE TO EDIT THE POSTS IN THE BLOG
@app.route("/edit-post/<int:post_id>", endpoint='edit', methods=['GET', 'POST'])
@bloggers
def edit(post_id):
    post = BlogPost.query.get(post_id)
    # CHECKING IF THE SAME USER IS EDITING THE POST 
    if post.author_id != current_user.id:
        flash("Sorry, You cannot edit this post.")
        return redirect(url_for("show_post", post_id=post.id))

    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id)) 

    return render_template("make-post.html", form=edit_form, id=post.id)

# DELETE ROUTE TO DELETE THE POSTS WITH THEIR COMMENTS
@admins_only
@app.route("/delete/<int:post_id>")
def delete(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    post_comments = db.session.query(Comment).filter_by(post_id=post_id)
    for comment in post_comments:
        db.session.delete(comment)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('home'))

# DELETE COMMENT ROUTE TO DELETE PARTICULAR COMMENT
@admins_only
@app.route('/delete-comment/<int:comment_id>', methods= ['POST', "GET"])
def delete_comment(comment_id):
    comment_to_delete = Comment.query.get(comment_id)
    post_id = comment_to_delete.post_id
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))

# STARTING APP IN MAIN FILE
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
