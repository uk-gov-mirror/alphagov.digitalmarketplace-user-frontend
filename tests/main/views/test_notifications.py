# coding: utf-8
from ...helpers import BaseApplicationTest
import mock


class TestUserResearchNotifications(BaseApplicationTest):

    def setup_method(self, method):
        super(TestUserResearchNotifications, self).setup_method(method)

        data_api_client_config = {'authenticate_user.return_value': self.user(
            123, "email@email.com", 1234, 'name', 'name'
        )}

        self._data_api_client = mock.patch(
            'app.main.views.auth.data_api_client', **data_api_client_config
        )
        self.data_api_client_mock = self._data_api_client.start()

    def teardown_method(self, method):
        self._data_api_client.stop()

    def test_should_show_login_page(self):
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 302

    def test_page_shows_for_supplier(self):
        self.login_as_supplier()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200
        assert 'seen_user_research_message=yes;' in res.headers['Set-Cookie']

    def test_page_shows_for_buyer(self):
        self.login_as_buyer()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200
        assert 'seen_user_research_message=yes;' in res.headers['Set-Cookie']

    def test_page_shows_for_admin(self):
        self.login_as_admin()
        res = self.client.get("/user/notifications/user-research")
        assert res.status_code == 200
        assert 'seen_user_research_message=yes;' in res.headers['Set-Cookie']

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
