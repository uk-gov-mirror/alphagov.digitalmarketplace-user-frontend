# coding: utf-8
from ...helpers import BaseApplicationTest
import mock


class TestUserResearchNotifications(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)

        self.data_api_client_auth_patch = mock.patch('app.main.views.auth.data_api_client', autospec=True)
        self.data_api_client_auth = self.data_api_client_auth_patch.start()
        self.data_api_client_auth.authenticate_user.return_value = self.user(
            123, "email@email.com", 1234, 'name', 'name'
        )

    def teardown_method(self, method):
        self.data_api_client_auth_patch.stop()
        super().teardown_method(method)

    def test_should_show_login_page(self):
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 302

    def test_page_shows_for_supplier(self):
        self.login_as_supplier()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200

    def test_page_shows_for_buyer(self):
        self.login_as_buyer()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200

    def test_page_shows_for_admin(self):
        self.login_as_admin()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200

    def test_subscribe_content(self):
        self.login_as_buyer(user_research_opt_in=False)
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200
        assert "Join the user research" in res.get_data(as_text=True)

    def test_unsubscribe_content(self):
        self.login_as_buyer()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200
        assert "Unsubscribe from the user research mailing list" in res.get_data(as_text=True)

    @mock.patch('app.main.views.notifications.data_api_client', autospec=True)
    def test_user_research_opt_in(self, data_api_client):
        self.login_as_buyer()
        self.client.post("/user/notifications/user-research", data={"user_research_opt_in": "True"})
        self.assert_flashes('Your preference has been saved', expected_category='success')
        assert data_api_client.update_user.call_args_list == [
            mock.call(123, updater='buyer@email.com', user_research_opted_in=True)
        ]

    @mock.patch('app.main.views.notifications.data_api_client', autospec=True)
    def test_user_research_opt_out(self, data_api_client):
        self.login_as_buyer()
        self.client.post("/user/notifications/user-research", data={})
        self.assert_flashes('Your preference has been saved', expected_category='success')
        assert data_api_client.update_user.call_args_list == [
            mock.call(123, updater='buyer@email.com', user_research_opted_in=False)
        ]
