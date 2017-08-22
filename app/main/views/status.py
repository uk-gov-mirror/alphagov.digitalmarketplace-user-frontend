from flask import jsonify, current_app, request

from .. import main
from ... import data_api_client
from dmutils.status import get_flags


@main.route('/_status')
def status():
    if 'ignore-dependencies' in request.args:
        return jsonify(
            status="ok",
        ), 200

    version = current_app.config['VERSION']
    api = {
        'name': '(Data) API',
        'key': 'api_status',
        'status': data_api_client.get_status()
    }

    apis_with_errors = []

    if api['status'] is None or api['status']['status'] != "ok":
        return jsonify(
            {api['key']: api['status']},
            status="error",
            version=version,
            message="Error connecting to the api.",
            flags=get_flags(current_app)
        ), 500

    return jsonify(
        {api['key']: api['status']},
        status="ok",
        version=version,
        flags=get_flags(current_app)
    )
