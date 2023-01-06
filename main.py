from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, ContactForm
from flask_gravatar import Gravatar
from functools import wraps
import smtplib
from dotenv.main import load_dotenv
import os

load_dotenv()
EMAIL = os.environ['EMAIL']
PASSWORD = os.environ['PASSWORD']

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app=app)

gravatar = Gravatar(
    app, rating='g', size=20, default='retro', force_default=False, force_lower=False, use_ssl=False,
    base_url=None)


def admins_only(func):
    wraps(func)

    def decorated_function(*args, **kwargs):
        if current_user.id == 1:
            return func(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function

def send_mail(name, email, phone, message):
    msg = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}"
    with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
        connection.starttls()
        connection.login(user=EMAIL, password=PASSWORD)
        connection.sendmail(
            from_addr=EMAIL,
            to_addrs="guptakaran094@gmail.com",
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


# db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def home():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


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


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user=user)
                return redirect(url_for('home'))
            flash('Incorrect Password')
        else:
            flash("Email doesn't exist in the database")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    if logout_user():
        return redirect(url_for('home'))


@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = db.session.query(Comment).filter_by(post_id=requested_post.id)
    if form.validate_on_submit():
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
    return render_template("post.html", post=requested_post, form=form, comments=comments, avatar=gravatar)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['POST', 'GET'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        send_mail(form.name.data, form.email.data, form.phone.data, form.message.data) 
        form = ContactForm(formdata=None)
        return render_template("contact.html", msg_sent=True, form=form)

    # if request.method == 'GET':
    #     return render_template("contact.html", msg_sent=False)
    # else:
    #     data = request.form
    #     send_mail(data['name'], data['email'], data["phone"], data["message"])        
    return render_template("contact.html", msg_sent=False, form=form)


@app.route("/new-post", endpoint='add', methods=['GET', 'POST'])
@admins_only
def add():
    form = CreatePostForm()
    if form.validate_on_submit():
        author = current_user.id
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=author,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", endpoint='edit', methods=['GET', 'POST'])
@admins_only
def edit(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, id=post.id)


@app.route("/delete/<int:post_id>")
def delete(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == "__main__":
#     with app.app_context():
#         db.create_all()
    app.run(host='0.0.0.0', port=5000)
