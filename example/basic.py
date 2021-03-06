import flask
import tempfile
import flask_sqlalchemy
import flask_praetorian

db = flask_sqlalchemy.SQLAlchemy()
guard = flask_praetorian.Praetorian()


# A generic user model that might be used by an app powered by flask-praetorian
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True)
    password = db.Column(db.Text)
    roles = db.Column(db.Text)
    is_acitve = db.Column(db.Boolean, default=True, server_default='true')

    @property
    def rolenames(self):
        try:
            return self.roles.split(',')
        except:
            return []

    @classmethod
    def lookup(cls, username):
        return cls.query.filter_by(username=username).one_or_none()

    @classmethod
    def identify(cls, id):
        return cls.query.get(id)

    @property
    def identity(self):
        return self.id

    def validate(self):
        if not self.is_active:
            raise Exception("user has been disabled")


# Initialize flask app for the example
app = flask.Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'top secret'

# Initialize the flask-praetorian instance for the app
guard.init_app(app, User)

# Initialize a local database for the example
local_database = tempfile.NamedTemporaryFile(prefix='local', suffix='.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(local_database)
db.init_app(app)

# Add users for the example
with app.app_context():
    db.create_all()
    db.session.add(User(
        username='TheDude',
        password=guard.encrypt_password('abides'),
    ))
    db.session.add(User(
        username='Walter',
        password=guard.encrypt_password('calmerthanyouare'),
        roles='admin'
    ))
    db.session.add(User(
        username='Donnie',
        password=guard.encrypt_password('iamthewalrus'),
        roles='operator'
    ))
    db.session.add(User(
        username='Maude',
        password=guard.encrypt_password('andthorough'),
        roles='operator,admin'
    ))
    db.session.commit()


# Set up some routes for the example

# curl -X POST -d '{"username":"Walter","password":"calmerthanyouare"}' http://localhost/login
@app.route('/login', methods=['POST'])
def login():
    req = flask.request.get_json(force=True)
    username = req.get('username', None)
    password = req.get('password', None)
    user = guard.authenticate(username, password)
    ret = {'access_token': guard.encode_jwt_token(user)}
    return flask.jsonify(ret), 200


# curl -H "Authorization: Bearer <your_token>" http://localhost/refresh
@app.route('/refresh', methods=['GET'])
def refresh():
    old_token = guard.read_token_from_header()
    new_token = guard.refresh_jwt_token(old_token)
    ret = {'access_token': new_token}
    return flask.jsonify(ret), 200


@app.route('/')
def root():
    return flask.jsonify(message='root endpoint')


# curl -H "Authorization: Bearer <your_token>" http://localhost/protected
@app.route('/protected')
@flask_praetorian.auth_required
def protected():
    return flask.jsonify(message='protected endpoint (allowed user {})'.format(
        flask_praetorian.current_user().username,
    ))


# curl -H "Authorization: Bearer <your_token>" http://localhost/protected_admin_required
@app.route('/protected_admin_required')
@flask_praetorian.auth_required
@flask_praetorian.roles_required('admin')
def protected_admin_required():
    return flask.jsonify(message='protected_admin_required endpoint')


# curl -H "Authorization: Bearer <your_token>" http://localhost/protected_admin_accepted
@app.route('/protected_admin_accepted')
@flask_praetorian.auth_required
@flask_praetorian.roles_accepted('admin', 'operator')
def protected_admin_and_operator_accepted():
    return flask.jsonify(message='protected_admin_accepted endpoint')


# Run the example
if __name__ == '__main__':
    app.run()
