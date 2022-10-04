import hashlib
import uuid
from datetime import datetime, timedelta

from flask.app import Flask
from flask.globals import request
from flask.wrappers import Response
from flask_wtf.form import FlaskForm
from sqlalchemy.dialects.postgresql.dml import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import delete
from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from wtforms.fields.simple import URLField
from wtforms.validators import DataRequired
from wtforms.validators import url as url_validator

from short_url.database import Links, Transitions, engine

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRET_KEY'


class URLForm(FlaskForm):
    url = URLField('url', validators=[DataRequired(), url_validator()])


def generate_code(url):
    salt = uuid.uuid4().hex.encode()
    return hashlib.shake_256(url.encode() + salt).hexdigest(3)


def insert_link(url, session, retry_counter=0):
    if retry_counter > 10:
        abort(500, 'Max number of code generation retries is exceeded')
    link = Links(code=generate_code(url), original_url=url)
    try:
        session.add(link)
        session.commit()
    except IntegrityError:
        session.rollback()
        return insert_link(url, session, retry_counter=retry_counter + 1)
    return link.code


@app.post('/urls')
def generate_short_link():
    form = URLForm(request.form, meta={'csrf': False})
    if not form.validate_on_submit():
        return form.errors
    url = form.url.data
    with Session(engine) as session:
        return f'{request.host_url}urls/{insert_link(url, session)}'


@app.get('/urls/<short_code>')
def get_origin_link(short_code):
    with Session(engine) as session:
        link = session.get(Links, short_code)
        if link is None:
            abort(404)
        transition = Transitions(link=link)
        session.add(transition)
        session.commit()
        return redirect(link.original_url)


@app.put('/urls/<short_code>')
def update_short_code(short_code):
    form = URLForm(request.form, meta={'csrf': False})
    if not form.validate_on_submit():
        return form.errors
    url = form.url.data
    with Session(engine) as session:
        stmt = insert(Links).values(code=short_code, original_url=url)
        stmt = stmt.on_conflict_do_update(index_elements=['code'], set_={'original_url': url})
        session.execute(stmt)
        session.commit()
    return f'{request.host_url}urls/{short_code}'


@app.delete('/urls/<short_code>')
def delete_short_code(short_code):
    with Session(engine) as session:
        session.execute(delete(Links).where(Links.code == short_code))
        session.commit()
    return Response(status=202)


@app.get('/urls/<short_code>/stats')
def get_statistic(short_code):
    with Session(engine) as session:
        count = (
            session.query(Transitions)
            .filter(Transitions.timestamp > datetime.now() - timedelta(days=1))
            .filter(Transitions.link_code == short_code)
            .count()
        )
        return Response(str(count), status=200)


@app.get('/')
def status():
    return {'status': 'OK'}

