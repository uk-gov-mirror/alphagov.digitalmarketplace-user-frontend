from flask import Flask, request, redirect, session, abort
from flask_login import LoginManager
from flask_wtf.csrf import CsrfProtect

import dmapiclient
from dmutils import init_app, flask_featureflags
from dmutils.user import User
from dmutils.external import external as external_blueprint

from config import configs


login_manager = LoginManager()
data_api_client = dmapiclient.DataAPIClient()
feature_flags = flask_featureflags.FeatureFlag()
csrf = CsrfProtect()


def create_app(config_name):
    application = Flask(__name__,
                        static_folder='static/',
                        static_url_path=configs[config_name].STATIC_URL_PATH)

    init_app(
        application,
        configs[config_name],
        data_api_client=data_api_client,
        feature_flags=feature_flags,
        login_manager=login_manager
    )

    from .main import main as main_blueprint

    application.register_blueprint(main_blueprint, url_prefix='/user')
    application.register_blueprint(external_blueprint)

    login_manager.login_view = 'main.render_login'
    login_manager.login_message_category = "must_login"
    csrf.init_app(application)

    @csrf.error_handler
    def csrf_handler(reason):
        if 'user_id' not in session:
            application.logger.info(
                u'csrf.session_expired: Redirecting user to log in page'
            )

            return application.login_manager.unauthorized()

        application.logger.info(
            u'csrf.invalid_token: Aborting request, user_id: {user_id}',
            extra={'user_id': session['user_id']})

        abort(400, reason)

    @application.before_request
    def remove_trailing_slash():
        if request.path != '/' and request.path.endswith('/'):
            if request.query_string:
                return redirect(
                    '{}?{}'.format(
                        request.path[:-1],
                        request.query_string.decode('utf-8')
                    ),
                    code=301
                )
            else:
                return redirect(request.path[:-1], code=301)

    @application.before_request
    def refresh_session():
        session.permanent = True
        session.modified = True

    return application


@login_manager.user_loader
def load_user(user_id):
    return User.load_user(data_api_client, user_id)
