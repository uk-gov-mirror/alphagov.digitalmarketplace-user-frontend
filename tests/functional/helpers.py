from ..helpers import BaseApplicationTest

from app import data_api_client

from unittest import mock
from faker import Faker

from splinter import Browser

class FunctionalTest(BaseApplicationTest):
    def setup(self):
        self.fake = Faker()

    def setup_method(self, method):
        super().setup_method(method)

        self.get_user_patch = None

        self.browser = Browser("flask", app=self.app)

    def teardown_method(self, method):
        if not self.get_user_patch is None:
            self.get_user_patch.stop()

    @mock.patch("app.main.views.auth.data_api_client")
    def login_as(self, users, login_api_client):
        user = users["users"]

        login_api_client.authenticate_user.return_value = users
        self.get_user_patch = mock.patch.object(data_api_client, "get_user", return_value=users)
        self.get_user_patch.start()

        self.browser.visit("/user/login?next=%2Fuser%2Freset-password") # we need to redirect to a page in this app
        self.browser.fill("email_address", user["emailAddress"])
        self.browser.fill("password", self.fake.pystr(min_chars=10, max_chars=20))
        self.browser.find_by_value("Log in").first.click()

    def login_as_supplier(self):
        users = self.user(
            id=self.fake.pyint(),
            email_address=self.fake.email(),
            supplier_id=self.fake.pyint(),
            supplier_name=self.fake.company(),
            name=self.fake.name(),
            role="supplier",
        )

        self.login_as(users)

        return users
