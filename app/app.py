import hashlib
import uuid
from datetime import datetime, timedelta

from flask.app import Flask
from flask.globals import request
from flask.wrappers import Response
from flask_wtf.form import FlaskForm
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import delete, update
from werkzeug.utils import redirect
from wtforms.fields.simple import URLField
from wtforms.validators import DataRequired
from wtforms.validators import url as url_validator

from database import Links, Transitions, engine

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRET_KEY'


@app.get('/')
def status():
    return {'status': 'OK'}


class URLForm(FlaskForm):
    url = URLField('url', validators=[DataRequired(), url_validator()])


def get_shortened_link(link: str):
    salt = (
        uuid.uuid4().hex.encode()
    )  # If we need a repeatable short link, we need to use a fixed value here
    return hashlib.shake_256(link.encode() + salt).hexdigest(3)


@app.route('/urls/', methods=['POST'])
def generate_new_url():
    form = URLForm(request.form)
    url = form.url.data
    shortened_link = get_shortened_link(url)
    link = Links(code=shortened_link, original_url=url)
    with Session(engine) as session:
        session.add(link)
        session.commit()
    print(request.host_url)
    return f'{request.host_url}urls/{shortened_link}'


def get_origin_link(short_code):
    with Session(engine) as session:
        print(short_code)
        link = session.get(Links, short_code)
        transition = Transitions(link=link)
        session.add(transition)
        session.commit()
        return redirect(link.original_url)


def update_short_code(short_code):
    form = URLForm(request.form)
    url = form.url.data
    with Session(engine) as session:
        session.execute(
            update(Links).where(Links.code == short_code).values(original_link=url)
        )
        session.commit()
    print(request.host_url)
    return Response(status=201)


def delete_short_code(short_code):
    with Session(engine) as session:
        session.execute(delete(Links).where(Links.code == short_code))
        session.commit()
    print(request.host_url)
    return Response(status=201)


@app.route('/urls/<short_code>', methods=['GET', 'PUT', 'DELETE'])
def main(short_code):
    if request.method == 'GET':
        return get_origin_link(short_code)
    if request.method == 'PUT':
        return update_short_code(short_code)
    if request.method == 'DELETE':
        return delete_short_code(short_code)


@app.route('/urls/<short_code>/stats', methods=['GET'])
def get_statistic(short_code):
    with Session(engine) as session:
        count = (
            session.query(Transitions)
            .filter(Transitions.timestamp > datetime.now() - timedelta(days=1))
            .filter(Transitions.link_code == short_code)
            .count()
        )
        return Response(str(count), status=200)
