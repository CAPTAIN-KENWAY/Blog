from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField, TextAreaField
from wtforms.validators import InputRequired, URL, Email, Length, Regexp
from flask_ckeditor import CKEditorField


# WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[InputRequired()])
    subtitle = StringField("Subtitle", validators=[InputRequired()])
    img_url = StringField("Blog Image URL", validators=[InputRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[InputRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    name = StringField('Name', validators=[InputRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField("Let Me In!")


class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[InputRequired()])
    submit = SubmitField("Submit Comment")


class ContactForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()])
    email = EmailField('Email Address', validators=[InputRequired(), Email()])
    phone = StringField(
        'Phone Number',
        validators=[InputRequired(),
                    Length(min=10, max=10),
                    Regexp(regex='^[+-]?[0-9]+$')]
        )
    message = TextAreaField('Message', validators=[InputRequired()])
    submit = SubmitField("SEND")
