# coding: utf-8
from flask_login import (current_user, login_required)
from flask import (
    flash,
    request,
    redirect
)

from dmutils.flask import timed_render_template as render_template
from dmutils.forms.helpers import get_errors_from_wtform

from .. import main
from ..forms.user_research import UserResearchOptInForm
from ..helpers.login_helpers import get_user_dashboard_url
from ... import data_api_client


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

            flash("Your preference has been saved", "success")
            return redirect(dashboard_url)
        else:
            # If the form is not valid set the status code and parse the errors into an acceptable format.
            status_code = 400
            errors = get_errors_from_wtform(form)
    else:
        # Update the form with the existing value if this is not a POST
        user = data_api_client.get_user(current_user.id)
        form = UserResearchOptInForm(user_research_opt_in=user['users']['userResearchOptedIn'])

    return render_template(
        "notifications/user-research-consent.html",
        form=form,
        errors=errors,
        dashboard_url=dashboard_url
    ), status_code
