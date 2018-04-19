from flask_wtf import FlaskForm
from wtforms import BooleanField


class UserResearchOptInForm(FlaskForm):
    user_research_opt_in = BooleanField("Send me emails about opportunities to get involved in user research")
