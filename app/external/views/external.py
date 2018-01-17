from flask import Blueprint

external = Blueprint('external', __name__)


@external.route('/buyers/create')
def create_buyer_account():
    raise NotImplementedError()


@external.route('/g-cloud/suppliers')
def suppliers_list_by_prefix():
    raise NotImplementedError()


@external.route('/help')
def help():
    raise NotImplementedError()


@external.route('/')
def index():
    raise NotImplementedError()
