# coding: utf-8
from flask_login import (current_user, login_required)
from flask import (
    flash,
    render_template,
    request,
    url_for
)
from .. import main
from ... import data_api_client


@main.route('/notifications/user-research', methods=["GET", "POST"])
@login_required
def user_research_consent():
    if request.method == "POST":
        userResearchOptIn = request.form.get('user_research_opt_in') == "True"
        data_api_client.update_user(
            current_user.id,
            user_research_opted_in=userResearchOptIn,
            updater=current_user.email_address
        )

        flash("Your preference has been saved", 'success')
    else:
        user = data_api_client.get_user(current_user.id)
        userResearchOptIn = user['users']['userResearchOptedIn']

    if current_user.role == 'supplier':
        dashboard_url = url_for('external.supplier_dashboard')
    else:
        dashboard_url = url_for('external.buyer_dashboard')

    additional_headers = []
    cookie_name = 'seen_user_research_message'

    if cookie_name not in request.cookies:
        additional_headers = {'Set-Cookie': "{}=yes; Path=/".format(cookie_name)}

    return render_template(
        "notifications/user-research-consent.html",
        userResearchOptIn=userResearchOptIn,
        dashboard_url=dashboard_url
    ), 200, additional_headers
