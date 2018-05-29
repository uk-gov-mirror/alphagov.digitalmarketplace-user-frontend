# coding: utf-8
from flask_login import (current_user, login_required)
from flask import (
    flash,
    render_template,
    request,
    redirect
)

from dmutils.forms import get_errors_from_wtform

from .. import main
from ..forms.user_research import UserResearchOptInForm
from ..helpers.login_helpers import get_user_dashboard_url
from ... import data_api_client
import datetime


@main.route('/notifications/user-research', methods=["GET", "POST"])
@login_required
def user_research_consent():
    """Page where users can opt into/ out of the user research mailing lists."""
    # Set defaults
    form = UserResearchOptInForm(request.form)
    status_code = 200
    errors = {}

    dashboard_url = get_user_dashboard_url(current_user)

    if request.method == "POST":
        if form.validate_on_submit():
            # If the form is valid then set the new value.
            user_research_opt_in = form.data.get('user_research_opt_in')
            data_api_client.update_user(
                current_user.id,
                user_research_opted_in=user_research_opt_in,
                updater=current_user.email_address
            )

            flash("Your preference has been saved", 'success')
            return redirect(dashboard_url)
        else:
            # If the form is not valid set the status code and parse the errors into an acceptable format.
            status_code = 400
            errors = get_errors_from_wtform(form)
    else:
        # Update the form with the existing value if this is not a POST
        user = data_api_client.get_user(current_user.id)
        form = UserResearchOptInForm(user_research_opt_in=user['users']['userResearchOptedIn'])

    # Set the seen_user_research_message cookie if it does not exist.
    # This ensures the user research banner is no longer shown.
    additional_headers = []

    # Changing cookie name will require an update to the following files:
    # digitalmarketplace-frontend-toolkit/toolkit/templates/user-research-consent-banner.html
    # digitalmarketplace-frontend-toolkit/toolkit/javascripts/user-research-consent-banner.js
    cookie_name = 'seen_user_research_message'

    if cookie_name not in request.cookies:
        expiry_date = datetime.datetime.now() + datetime.timedelta(90)
        expiry_date = expiry_date.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        additional_headers = {'Set-Cookie': "{}=yes; Path=/; Expires={}".format(cookie_name, expiry_date)}

    return render_template(
        "notifications/user-research-consent.html",
        form=form,
        errors=errors,
        dashboard_url=dashboard_url
    ), status_code, additional_headers
