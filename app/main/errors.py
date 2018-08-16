# coding=utf-8

from . import main
from dmapiclient import APIError
from dmutils.errors import render_error_page


@main.app_errorhandler(APIError)
def api_error_handler(e):
    return render_error_page(e.status_code)
