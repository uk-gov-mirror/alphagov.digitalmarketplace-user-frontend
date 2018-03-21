# coding: utf-8
from flask_login import (current_user, login_required)
from flask import (
    flash,
    render_template,
    request,
    redirect,
    url_for
)
from .. import main
from ..forms.user_research import UserResearchOptInForm
from ... import data_api_client


@main.route('/notifications/user-research', methods=["GET", "POST"])
@login_required
def user_research_consent():
    """Page where users can opt into/ out of the user research mailing lists."""
    # Set defaults
    form = UserResearchOptInForm(request.form)
    status_code = 200
    errors = {}

    # Determine the correct dashboard url.
    if current_user.role == 'supplier':
        dashboard_url = url_for('external.supplier_dashboard')
    elif current_user.role == "buyer":
        dashboard_url = url_for('external.buyer_dashboard')
    else:
        dashboard_url = url_for('external.index')

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
            errors = {
                key: {'question': form[key].label.text, 'input_name': key, 'message': form[key].errors[0]}
                for key, value in form.errors.items()
            }
    else:
        # Update the form with the existing value if this is not a POST
        user = data_api_client.get_user(current_user.id)
        form = UserResearchOptInForm(user_research_opt_in=user['users']['userResearchOptedIn'])

    # Set the seen_user_research_message cookie if it does not exist.
    # This ensures the user research banner is no longer shown.
    additional_headers = []
    cookie_name = 'seen_user_research_message'

    if cookie_name not in request.cookies:
        additional_headers = {'Set-Cookie': "{}=yes; Path=/".format(cookie_name)}

    return render_template(
        "notifications/user-research-consent.html",
        form=form,
        errors=errors,
        dashboard_url=dashboard_url
    ), status_code, additional_headers
