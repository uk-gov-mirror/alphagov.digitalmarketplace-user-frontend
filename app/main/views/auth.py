# coding: utf-8
from flask_login import current_user
from flask import current_app, flash, redirect, render_template, request, url_for, get_flashed_messages, Markup
from flask_login import logout_user, login_user

from dmutils.user import User

from .. import main
from ..forms.auth_forms import LoginForm
from ..helpers import hash_email
from ..helpers.login_helpers import redirect_logged_in_user
from ... import data_api_client


NO_ACCOUNT_MESSAGE = Markup("""Make sure you've entered the right email address and password. Accounts
    are locked after 5 failed attempts. If you think your account has been locked, email
    <a href="mailto:enquiries@digitalmarketplace.service.gov.uk">enquiries@digitalmarketplace.service.gov.uk</a>.""")


@main.route('/login', methods=["GET"])
def render_login():
    next_url = request.args.get('next')
    if current_user.is_authenticated() and not get_flashed_messages():
        return redirect_logged_in_user(next_url)
    return render_template(
        "auth/login.html",
        form=LoginForm(),
        next=next_url), 200


@main.route('/login', methods=["POST"])
def process_login():
    form = LoginForm()
    next_url = request.args.get('next')
    if form.validate_on_submit():
        user_json = data_api_client.authenticate_user(
            form.email_address.data,
            form.password.data)
        if not user_json:
            current_app.logger.info(
                "login.fail: failed to log in {email_hash}",
                extra={'email_hash': hash_email(form.email_address.data)})
            flash(NO_ACCOUNT_MESSAGE, "error")
            return render_template(
                "auth/login.html",
                form=form,
                next=next_url), 403

        user = User.from_json(user_json)

        login_user(user)
        current_app.logger.info("login.success: role={role} user={email_hash}",
                                extra={'role': user.role, 'email_hash': hash_email(form.email_address.data)})
        return redirect_logged_in_user(next_url)

    else:
        return render_template(
            "auth/login.html",
            form=form,
            next=next_url), 400


@main.route('/logout', methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for('.render_login'))
