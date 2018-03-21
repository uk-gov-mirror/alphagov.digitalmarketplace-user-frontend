from flask_wtf import Form
from wtforms import BooleanField


class UserResearchOptInForm(Form):
    user_research_opt_in = BooleanField("Send me emails about opportunities to get involved in user research")
