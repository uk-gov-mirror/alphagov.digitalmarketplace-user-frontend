# -*- coding: utf-8 -*-

import six

from flask import abort, current_app, flash, redirect, render_template, url_for, Markup

from dmutils.user import User
from dmutils.email import generate_token, decode_password_reset_token, send_email
from dmutils.email.exceptions import EmailError

from .. import main
from ..forms.auth_forms import EmailAddressForm, ChangePasswordForm
from ..helpers import hash_email
from ... import data_api_client

EMAIL_SENT_MESSAGE = Markup(
    """If the email address you've entered belongs to a Digital Marketplace account,
    we'll send a link to reset the password.
    """
)

EXPIRED_PASSWORD_RESET_TOKEN_MESSAGE = Markup(
    """This password reset link has expired. Enter your email address and we’ll send you a new one.
    Password reset links are only valid for 24 hours.
    """
)

PASSWORD_UPDATED_MESSAGE = "You have successfully changed your password."
PASSWORD_NOT_UPDATED_MESSAGE = "Could not update password due to an error."


@main.route('/reset-password', methods=["GET"])
def request_password_reset():
    return render_template("auth/request-password-reset.html",
                           form=EmailAddressForm()), 200


@main.route('/reset-password', methods=["POST"])
def send_reset_password_email():
    form = EmailAddressForm()
    if form.validate_on_submit():
        email_address = form.email_address.data
        user_json = data_api_client.get_user(email_address=email_address)

        if user_json is not None:

            user = User.from_json(user_json)

            token = generate_token(
                {
                    "user": user.id
                },
                current_app.config['SECRET_KEY'],
                current_app.config['RESET_PASSWORD_SALT']
            )

            url = url_for('main.reset_password', token=token, _external=True)

            email_body = render_template(
                "emails/reset_password_email.html",
                url=url,
                locked=user.locked)

            try:
                send_email(
                    user.email_address,
                    email_body,
                    current_app.config['DM_MANDRILL_API_KEY'],
                    current_app.config['RESET_PASSWORD_EMAIL_SUBJECT'],
                    current_app.config['RESET_PASSWORD_EMAIL_FROM'],
                    current_app.config['RESET_PASSWORD_EMAIL_NAME'],
                    ["password-resets"]
                )
            except EmailError as e:
                current_app.logger.error(
                    "Password reset email failed to send. "
                    "error {error} email_hash {email_hash}",
                    extra={'error': six.text_type(e),
                           'email_hash': hash_email(user.email_address)})
                abort(503, response="Failed to send password reset.")

            current_app.logger.info(
                "login.reset-email.sent: Sending password reset email for "
                "supplier_id {supplier_id} email_hash {email_hash}",
                extra={'supplier_id': user.supplier_id,
                       'email_hash': hash_email(user.email_address)})
        else:
            current_app.logger.info(
                "login.reset-email.invalid-email: "
                "Password reset request for invalid supplier email {email_hash}",
                extra={'email_hash': hash_email(email_address)})

        flash(EMAIL_SENT_MESSAGE)
        return redirect(url_for('.request_password_reset'))
    else:
        return render_template("auth/request-password-reset.html",
                               form=form), 400


@main.route('/reset-password/<token>', methods=["GET"])
def reset_password(token):
    decoded = decode_password_reset_token(token, data_api_client)
    if 'error' in decoded:
        flash(EXPIRED_PASSWORD_RESET_TOKEN_MESSAGE, 'error')
        return redirect(url_for('.request_password_reset'))

    email_address = decoded['email']

    return render_template("auth/reset-password.html",
                           email_address=email_address,
                           form=ChangePasswordForm(),
                           token=token), 200


@main.route('/reset-password/<token>', methods=["POST"])
def update_password(token):
    form = ChangePasswordForm()
    decoded = decode_password_reset_token(token, data_api_client)
    if 'error' in decoded:
        flash(EXPIRED_PASSWORD_RESET_TOKEN_MESSAGE, 'error')
        return redirect(url_for('.request_password_reset'))

    user_id = decoded["user"]
    email_address = decoded["email"]
    password = form.password.data

    if form.validate_on_submit():
        if data_api_client.update_user_password(user_id, password, email_address):
            current_app.logger.info(
                "User {user_id} successfully changed their password",
                extra={'user_id': user_id})
            flash(PASSWORD_UPDATED_MESSAGE)
        else:
            flash(PASSWORD_NOT_UPDATED_MESSAGE, 'error')
        return redirect(url_for('.render_login'))
    else:
        return render_template("auth/reset-password.html",
                               email_address=email_address,
                               form=form,
                               token=token), 400
