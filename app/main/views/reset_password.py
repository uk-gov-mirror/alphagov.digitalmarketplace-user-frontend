# -*- coding: utf-8 -*-

from flask import abort, current_app, flash, redirect, render_template, request, url_for, Markup
from flask_login import current_user, login_required

from dmutils.user import User
from dmutils.email import DMNotifyClient, generate_token, decode_password_reset_token, EmailError
from dmutils.email.helpers import hash_string

from .. import main
from ..forms.auth_forms import EmailAddressForm, PasswordResetForm, PasswordChangeForm
from ..helpers.login_helpers import get_user_dashboard_url
from ..helpers.logging_helpers import log_email_error
from ... import data_api_client


EMAIL_SENT_MESSAGE = Markup(
    """If the email address you've entered belongs to a Digital Marketplace account, we'll send a link to reset the
    password. If you don’t receive this, email
    <a href="mailto:enquiries@digitalmarketplace.service.gov.uk">enquiries@digitalmarketplace.service.gov.uk</a>.
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
                current_app.config['SHARED_EMAIL_KEY'],
                current_app.config['RESET_PASSWORD_SALT']
            )

            notify_client = DMNotifyClient(current_app.config['DM_NOTIFY_API_KEY'])

            try:
                notify_client.send_email(
                    user.email_address,
                    template_id=current_app.config['NOTIFY_TEMPLATES']['reset_password'],
                    personalisation={
                        'url': url_for('main.reset_password', token=token, _external=True),
                    },
                    reference='reset-password-{}'.format(hash_string(user.email_address))
                )
            except EmailError as exc:
                log_email_error(
                    exc,
                    "Password reset",
                    "login.reset-email.notify-error",
                    user.email_address
                )
                abort(503, response="Failed to send password reset.")

            current_app.logger.info(
                "{code}: Sending password reset email for email_hash {email_hash}",
                extra={
                    'email_hash': hash_string(user.email_address),
                    'code': 'login.reset-email.sent'
                }
            )
        else:
            current_app.logger.info(
                "{code}: Password reset request for invalid email_hash {email_hash}",
                extra={
                    'email_hash': hash_string(email_address),
                    'code': 'login.reset-email.invalid-email'
                }
            )

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
                           form=PasswordResetForm(),
                           token=token), 200


@main.route('/reset-password/<token>', methods=["POST"])
def update_password(token):
    form = PasswordResetForm()
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


@main.route('/change-password', methods=["GET", "POST"])
@login_required
def change_password():
    form = PasswordChangeForm()
    dashboard_url = get_user_dashboard_url(current_user)

    if request.method == 'POST':
        if form.validate_on_submit():
            # Make sure old password is valid
            user_json = data_api_client.authenticate_user(
                current_user.email_address,
                form.old_password.data)
            if user_json:
                response = data_api_client.update_user_password(
                    current_user.id,
                    form.password.data,
                    updater=current_user.email_address
                )
                if response:
                    current_app.logger.info(
                        "User {user_id} successfully changed their password",
                        extra={'user_id': current_user.id}
                    )

                    notify_client = DMNotifyClient(current_app.config['DM_NOTIFY_API_KEY'])

                    token = generate_token(
                        {
                            "user": current_user.id
                        },
                        current_app.config['SHARED_EMAIL_KEY'],
                        current_app.config['RESET_PASSWORD_SALT']
                    )

                    try:
                        notify_client.send_email(
                            current_user.email_address,
                            template_id=current_app.config['NOTIFY_TEMPLATES']['change_password_alert'],
                            personalisation={
                                'url': url_for('main.reset_password', token=token, _external=True),
                            },
                            reference='change-password-alert-{}'.format(hash_string(current_user.email_address))
                        )

                        current_app.logger.info(
                            "{code}: Password change alert email sent for email_hash {email_hash}",
                            extra={
                                'email_hash': hash_string(current_user.email_address),
                                'code': 'login.password-change-alert-email.sent'
                            }
                        )

                    except EmailError as exc:
                        log_email_error(
                            exc,
                            "Password change alert",
                            "login.password-change-alert-email.notify-error",
                            current_user.email_address
                        )

                    flash(PASSWORD_UPDATED_MESSAGE)
                else:
                    flash(PASSWORD_NOT_UPDATED_MESSAGE, 'error')
                return redirect(dashboard_url)
            else:
                current_app.logger.info(
                    "change_password.fail: failed to authenticate user {email_hash}",
                    extra={'email_hash': hash_string(current_user.email_address)})

                form.old_password.errors.append("Make sure you’ve entered the right password.")

        return render_template("auth/change-password.html", form=form, dashboard_url=dashboard_url), 400

    else:
        return render_template(
            "auth/change-password.html",
            form=PasswordChangeForm(),
            dashboard_url=dashboard_url
        ), 200
