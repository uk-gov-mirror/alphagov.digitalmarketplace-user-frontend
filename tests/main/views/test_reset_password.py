import mock
from lxml import html, cssselect

from dmutils.email import generate_token
from dmutils.email.exceptions import EmailError

from ...helpers import BaseApplicationTest, MockMatcher

from app.main.views import reset_password

EMAIL_EMPTY_ERROR = "You must provide an email address"
EMAIL_INVALID_ERROR = "You must provide a valid email address"

PASSWORD_INVALID_ERROR = "Passwords must be between 10 and 50 characters"
PASSWORD_MISMATCH_ERROR = "The passwords you entered do not match"
NEW_PASSWORD_EMPTY_ERROR = "You must enter a new password"
NEW_PASSWORD_CONFIRM_EMPTY_ERROR = "Please confirm your new password"
PASSWORD_RESET_EMAIL_ERROR = "Failed to send password reset."


class TestResetPassword(BaseApplicationTest):

    _user = None

    def setup_method(self, method):
        super().setup_method(method)

        data_api_client_config = {'get_user.return_value': self.user(
            123, "email@email.com", 1234, 'name', 'Name'
        )}

        self._user = {
            "user": 123,
            "email": 'email@email.com',
        }

        self.data_api_client_patch = mock.patch(
            'app.main.views.reset_password.data_api_client', **data_api_client_config
        )
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_email_should_not_be_empty(self):
        res = self.client.post("/user/reset-password", data={})
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 400
        assert self.strip_all_whitespace(EMAIL_EMPTY_ERROR) in content

    def test_email_should_be_valid(self):
        res = self.client.post("/user/reset-password", data={
            'email_address': 'invalid'
        })
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 400
        assert self.strip_all_whitespace(EMAIL_INVALID_ERROR) in content

    @mock.patch('app.main.views.reset_password.DMNotifyClient.send_email')
    def test_redirect_to_same_page_on_success(self, send_email):
        res = self.client.post("/user/reset-password", data={
            'email_address': 'email@email.com'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/reset-password'

    @mock.patch('app.main.views.reset_password.DMNotifyClient.send_email')
    def test_show_email_sent_message_on_success(self, send_email):
        res = self.client.post("/user/reset-password", data={
            'email_address': 'email@email.com'
        }, follow_redirects=True)
        assert res.status_code == 200
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert self.strip_all_whitespace(reset_password.EMAIL_SENT_MESSAGE) in content

    @mock.patch('app.main.views.reset_password.DMNotifyClient.send_email')
    def test_should_strip_whitespace_surrounding_reset_password_email_address_field(self, send_email):
        self.client.post("/user/reset-password", data={
            'email_address': ' email@email.com'
        })
        self.data_api_client.get_user.assert_called_with(email_address='email@email.com')

    def test_email_should_be_decoded_from_token(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.get(url)
        assert res.status_code == 200
        assert "Reset password for email@email.com" in res.get_data(as_text=True)

    def test_password_should_not_be_empty(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password': '',
            'confirm_password': ''
        })
        assert res.status_code == 400
        assert NEW_PASSWORD_EMPTY_ERROR in res.get_data(as_text=True)
        assert NEW_PASSWORD_CONFIRM_EMPTY_ERROR in res.get_data(as_text=True)

    def test_password_should_be_over_ten_chars_long(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password': '123456789',
            'confirm_password': '123456789'
        })
        assert res.status_code == 400
        assert PASSWORD_INVALID_ERROR in res.get_data(as_text=True)

    def test_password_should_be_under_51_chars_long(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password':
                '123456789012345678901234567890123456789012345678901',
            'confirm_password':
                '123456789012345678901234567890123456789012345678901'
        })
        assert res.status_code == 400
        assert PASSWORD_INVALID_ERROR in res.get_data(as_text=True)

    def test_passwords_should_match(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password': '1234567890',
            'confirm_password': '0123456789'
        })
        assert res.status_code == 400
        assert PASSWORD_MISMATCH_ERROR in res.get_data(as_text=True)

    def test_redirect_to_login_page_on_success(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password': '1234567890',
            'confirm_password': '1234567890'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login'
        res = self.client.get(res.location)

        assert reset_password.PASSWORD_UPDATED_MESSAGE in res.get_data(as_text=True)

    def test_password_change_unknown_failure(self):
        self.data_api_client.update_user_password.return_value = False
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password': '1234567890',
            'confirm_password': '1234567890'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login'
        res = self.client.get(res.location)

        assert reset_password.PASSWORD_NOT_UPDATED_MESSAGE in res.get_data(as_text=True)
        self.data_api_client.update_user_password.return_value = True

    def test_should_not_strip_whitespace_surrounding_reset_password_password_field(self):
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        self.client.post(url, data={
            'password': '  1234567890',
            'confirm_password': '  1234567890'
        })
        self.data_api_client.update_user_password.assert_called_with(
            self._user.get('user'), '  1234567890', self._user.get('email'))

    def test_token_created_before_last_updated_password_cannot_be_used(self):
        self.data_api_client.get_user.return_value = self.user(
            123, "email@email.com", 1234, 'email', 'Name', is_token_valid=False
        )
        token = generate_token(
            self._user,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['RESET_PASSWORD_SALT'])
        url = '/user/reset-password/{}'.format(token)

        res = self.client.post(url, data={
            'password': '1234567890',
            'confirm_password': '1234567890'
        }, follow_redirects=True)

        assert res.status_code == 200
        document = html.fromstring(res.get_data(as_text=True))
        error_selector = cssselect.CSSSelector('div.banner-destructive-without-action')
        error_elements = error_selector(document)
        assert len(error_elements) == 1
        assert reset_password.EXPIRED_PASSWORD_RESET_TOKEN_MESSAGE in error_elements[0].text_content()

    @mock.patch('app.main.views.reset_password.DMNotifyClient.send_email')
    def test_should_call_send_email_with_correct_params(self, send_email):
        res = self.client.post(
            '/user/reset-password',
            data={'email_address': 'email@email.com'}
        )

        assert res.status_code == 302
        send_email.assert_called_once_with(
            "email@email.com",
            template_id='7501026e-d0ba-4cd1-b64f-6a19e1f0913f',
            personalisation={
                'url': MockMatcher(lambda x: '/user/reset-password/gAAAA' in x),
            },
            reference='reset-password-8yc90Y2VvBnVHT5jVuSmeebxOCRJcnKicOe7VAsKu50='
        )

    @mock.patch('app.main.views.reset_password.DMNotifyClient.send_email')
    def test_should_be_an_error_if_send_email_fails(self, send_email):
        send_email.side_effect = EmailError(Exception('API is down'))

        res = self.client.post(
            '/user/reset-password',
            data={'email_address': 'email@email.com'}
        )

        assert res.status_code == 503
        assert PASSWORD_RESET_EMAIL_ERROR in res.get_data(as_text=True)


class TestChangePassword(BaseApplicationTest):

    _user = None

    def setup_method(self, method):
        super().setup_method(method)

        data_api_client_config = {'get_user.return_value': self.user(
            123, "email@email.com", 1234, 'name', 'Name'
        )}

        self._user = {
            "user": 123,
            "email": 'email@email.com',
        }

        self.data_api_client_patch = mock.patch(
            'app.main.views.reset_password.data_api_client', **data_api_client_config
        )
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_change_password_page_displays_correctly(self):
        response = self.client.get('/user/change-password')

        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        form_labels = document.xpath('//form//label/text()')

        for label in ['Old password', 'New password', 'Confirm new password']:
            assert label in form_labels

    def test_user_can_change_password(self):
        response = self.client.post(
            '/user/change-password',
            data={
                'old_password': '0987654321',
                'password': '1234567890',
                'confirm_password': '1234567890'
            }
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/suppliers'
