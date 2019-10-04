from .helpers import FunctionalTest

from unittest import mock


class TestLogin(FunctionalTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch("app.main.views.auth.data_api_client", autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_page(self, snapshot):
        self.browser.visit("/user/login")
        assert self.browser.is_text_present("Log in to the Digital Marketplace")
        snapshot.assert_match(self.browser.html)

    def test_should_show_flash_message_for_bad_login(self):
        self.data_api_client.authenticate_user.return_value = None

        self.browser.visit("/user/login")

        self.browser.fill("email_address", "not-a-user@user.marketplace.team")
        self.browser.fill("password", "garbage!")

        button = self.browser.find_by_value("Log in").first
        button.click()

        assert self.browser.status_code.code == 403
        assert self.browser.is_text_present("Make sure you've entered the right email address and password.")

    def test_should_have_log_out_link_in_header(self):
        self.login_as_supplier()

        self.browser.visit("/user/reset-password")

        header = self.browser.find_by_css("header").first
        assert header.find_by_css("a:contains('Log out')")
