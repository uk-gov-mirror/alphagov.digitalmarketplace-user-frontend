from flask import request

from .. import main
from ... import data_api_client
from dmutils.status import get_app_status


@main.route('/_status')
def status():
    return get_app_status(data_api_client=data_api_client,
                          search_api_client=None,
                          ignore_dependencies='ignore-dependencies' in request.args)
