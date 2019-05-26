import functools
import os
import uuid

import requests

import flask

import gitlab

from oauth_system import get_oauth_key

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SERVER_IP'] = os.environ.get('SERVER_IP', '0.0.0.0')
app.config['OAUTH_KEY'], app.config['OAUTH_ID'] = get_oauth_key(app.config['SERVER_IP'])

gl = gitlab.Gitlab('http://gitlab', private_token=os.environ['GITLAB_API_TOKEN'])


def with_login(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not 'gitlab' in flask.session:
            return flask.redirect('/login')
        return f(*args, **kwargs)

    return wrapped


def without_login(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if 'gitlab' in flask.session:
            return flask.redirect('/')
        return f(*args, **kwargs)

    return wrapped


@app.route('/')
def hello():
    result = 'Hello'
    if 'gitlab' in flask.session:
        result += ', {}'.format(flask.session['gitlab']['user'])

    return flask.render_template('index.html', text=result)


@app.route('/register', methods=['GET', 'POST'])
@without_login
def register():
    if flask.request.method == 'GET':
        return flask.render_template('register.html')
    else:
        username = flask.request.values.get('username')
        password = flask.request.values.get('password')
        email = flask.request.values.get('email')
        user_data = dict(
            email=email,
            username=username,
            password=password,
            name=username,
            skip_confirmation=True,
        )
        user = gl.users.create(user_data)
        flask.session['gitlab'] = dict(user=username)
        if not user.projects.list():
            user.projects.create({'name': 'simple_tasks'})
        return flask.redirect('/')


@app.route('/login', methods=['GET'])
@without_login
def login():
    flask.session['state'] = str(uuid.uuid4())
    return flask.redirect('http://{}:8080/oauth/authorize?client_id={}&redirect_uri={}&response_type=code&state={}'.format(
        app.config['SERVER_IP'],
        app.config['OAUTH_ID'],
        'http://{}:5000'.format(app.config['SERVER_IP']) + flask.url_for('login_finish'),
        flask.session['state']
    ))


@app.route('/login_finish', methods=['GET'])
@without_login
def login_finish():
    state = flask.session.pop('state', None)
    if state != flask.request.args.get('state'):
        return flask.redirect('/')

    auth_rsp = requests.post('http://gitlab/oauth/token', data={
        'client_id': app.config['OAUTH_ID'],
        'client_secret': app.config['OAUTH_KEY'],
        'redirect_uri': 'http://{}:5000'.format(app.config['SERVER_IP']) + flask.url_for('login_finish'),
        'grant_type': 'authorization_code',
        'code': flask.request.args['code']
    })

    user_gl = gitlab.Gitlab('http://gitlab', oauth_token=auth_rsp.json()['access_token'])
    user_gl.auth()
    flask.session['gitlab'] = dict(user=user_gl.user.username)
    return flask.redirect('/')


@app.route('/logout', methods=['GET'])
@with_login
def logout():
    del flask.session['gitlab']
    return flask.redirect('/')


class GradeState(object):
    def __init__(self, filename):
        self.filename = filename
        self.grades = dict()

    def load(self):
        if not os.path.exists(self.filename):
            return
        with open(self.filename) as i:
            for line in i:
                user, task = line.strip().split()
                self.grades.setdefault(user, list()).append(task)

    def add(self, user, task):
        if task not in self.grades.get(user, []):
            with open(self.filename, 'a') as o:
                o.write('{}\t{}\n'.format(user, task))
            self.grades.setdefault(user, list()).append(task)


grade_state = GradeState('/secrets/grades')
grade_state.load()


@app.route('/grade', methods=['GET'])
def grade():
    token = flask.request.headers.get('token')
    if token != os.environ['GITLAB_API_TOKEN']:
        pass
    user = os.path.basename(os.path.dirname(flask.request.args.get('user')))
    task = flask.request.args.get('task')
    grade_state.add(user, task)
    return flask.make_response('ok', 200)


@app.route('/my_grades', methods=['GET'])
@with_login
def my_grades():
    return flask.render_template('my_grades.html', tasks=grade_state.grades.get(flask.session['gitlab']['user'], list()))


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
