from flask import request, current_app
import pickle

from .. import main
from ... import data_api_client
from dmutils.status import get_app_status
from dmutils.flask import timed_render_template as render_template


@main.route('/_status')
def status():
    return get_app_status(data_api_client=data_api_client,
                          search_api_client=None,
                          ignore_dependencies='ignore-dependencies' in request.args)


@main.route('/_status/redis')
def redis_console():
    r = current_app.config['SESSION_REDIS']
    session_cookie = request.cookies.get('dm_session')
    current_session_id = 'session:{}'.format(session_cookie)

    session_list = r.keys()
    sessions = {id_: pickle.loads(r.get(id_)) for id_ in session_list}

    expected_session_keys = [
        '_permanent',
        '_fresh'
    ]
    other_session_keys = [
        'user_id',
        'csrf_token'
    ]

    return render_template(
        "redis_status.html",
        current_session_id=current_session_id,
        sessions=sessions,
        expected_session_keys=expected_session_keys,
        other_session_keys=other_session_keys
    )
