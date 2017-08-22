# coding: utf-8
from __future__ import unicode_literals

from dmapiclient import HTTPError
from dmutils.email import generate_token
from dmutils.email.exceptions import EmailError
from ...helpers import BaseApplicationTest
from lxml import html, cssselect
import mock
import pytest

from app.main.views import auth


EMAIL_EMPTY_ERROR = "You must provide an email address"
EMAIL_INVALID_ERROR = "You must provide a valid email address"
PASSWORD_EMPTY_ERROR = "You must provide your password"
PASSWORD_INVALID_ERROR = "Passwords must be between 10 and 50 characters"
PASSWORD_MISMATCH_ERROR = "The passwords you entered do not match"
NEW_PASSWORD_EMPTY_ERROR = "You must enter a new password"
NEW_PASSWORD_CONFIRM_EMPTY_ERROR = "Please confirm your new password"

PASSWORD_RESET_EMAIL_ERROR = "Failed to send password reset."

USER_LINK_EXPIRED_ERROR = "The link you used to create an account may have expired."


class TestLogin(BaseApplicationTest):

    def setup_method(self, method):
        super(TestLogin, self).setup_method(method)

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
        res = self.client.get("/user/login")
        assert res.status_code == 200
        assert "Log in to the Digital Marketplace" in res.get_data(as_text=True)

    def test_should_redirect_to_supplier_dashboard_on_supplier_login(self):
        res = self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'
        assert 'Secure;' in res.headers['Set-Cookie']

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_redirect_to_homepage_on_buyer_login(self, data_api_client):
        with self.app.app_context():
            data_api_client.authenticate_user.return_value = self.user(123, "email@email.com", None, None, 'Name')
            res = self.client.post("/user/login", data={
                'email_address': 'valid@email.com',
                'password': '1234567890'
            })
            assert res.status_code == 302
            assert res.location == 'http://localhost/'
            assert 'Secure;' in res.headers['Set-Cookie']

    def test_should_redirect_logged_in_supplier_to_supplier_dashboard(self):
        self.login_as_supplier()
        res = self.client.get("/user/login")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    def test_should_redirect_logged_in_buyer_to_homepage(self):
        self.login_as_buyer()
        res = self.client.get("/user/login")
        assert res.status_code == 302
        assert res.location == 'http://localhost/'

    def test_should_redirect_logged_in_admin_to_admin_dashboard(self):
        self.login_as_admin()
        res = self.client.get("/user/login")
        assert res.status_code == 302
        assert res.location == 'http://localhost/admin'

    def test_should_redirect_logged_in_admin_to_next_url_if_admin_app(self):
        self.login_as_admin()
        res = self.client.get("/user/login?next=/admin/foo-bar")
        assert res.status_code == 302
        assert res.location == 'http://localhost/admin/foo-bar'

    def test_should_redirect_logged_in_supplier_to_next_url_if_supplier_app(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=/suppliers/foo-bar")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers/foo-bar'

    def test_should_redirect_to_supplier_dashboard_if_next_url_not_supplier_app(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=/foo-bar")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    def test_should_strip_whitespace_surrounding_login_email_address_field(self):
        self.client.post("/user/login", data={
            'email_address': '  valid@email.com  ',
            'password': '1234567890'
        })
        self.data_api_client_mock.authenticate_user.assert_called_with('valid@email.com', '1234567890')

    def test_should_not_strip_whitespace_surrounding_login_password_field(self):
        self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '  1234567890  '
        })
        self.data_api_client_mock.authenticate_user.assert_called_with(
            'valid@email.com', '  1234567890  ')

    def test_ok_next_url_redirects_supplier_on_login(self):
        res = self.client.post("/user/login?next=/suppliers/bar-foo",
                               data={
                                   'email_address': 'valid@email.com',
                                   'password': '1234567890'
                               })
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers/bar-foo'

    @mock.patch('app.main.views.auth.data_api_client')
    def test_ok_next_url_redirects_buyer_on_login(self, data_api_client):
        with self.app.app_context():
            data_api_client.authenticate_user.return_value = self.user(123, "email@email.com", None, None, 'Name')
            res = self.client.post("/user/login?next=/bar-foo",
                                   data={
                                       'email_address': 'valid@email.com',
                                       'password': '1234567890'
                                   })
            assert res.status_code == 302
            assert res.location == 'http://localhost/bar-foo'

    def test_bad_next_url_takes_supplier_user_to_dashboard(self):
        res = self.client.post("/user/login?next=http://badness.com",
                               data={
                                   'email_address': 'valid@email.com',
                                   'password': '1234567890'
                               })
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    @mock.patch('app.main.views.auth.data_api_client')
    def test_bad_next_url_takes_buyer_user_to_homepage(self, data_api_client):
        with self.app.app_context():
            data_api_client.authenticate_user.return_value = self.user(123, "email@email.com", None, None, 'Name')
            res = self.client.post("/user/login?next=http://badness.com",
                                   data={
                                       'email_address': 'valid@email.com',
                                       'password': '1234567890'
                                   })
        assert res.status_code == 302
        assert res.location == 'http://localhost/'

    def test_should_have_cookie_on_redirect(self):
        with self.app.app_context():
            self.app.config['SESSION_COOKIE_DOMAIN'] = '127.0.0.1'
            self.app.config['SESSION_COOKIE_SECURE'] = True
            res = self.client.post("/login", data={
                'email_address': 'valid@email.com',
                'password': '1234567890'
            })
            cookie_value = self.get_cookie_by_name(res, 'dm_session')
            assert cookie_value['dm_session'] is not None
            assert cookie_value['Secure; HttpOnly; Path'] == '/'
            assert cookie_value["Domain"] == "127.0.0.1"

    def test_should_redirect_to_login_on_logout(self):
        res = self.client.get('/user/logout')
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/login'

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_a_403_for_invalid_login(self, data_api_client):
        data_api_client.authenticate_user.return_value = None

        res = self.client.post("/user/login", data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert self.strip_all_whitespace("Make sure you've entered the right email address and password") \
            in self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 403

    def test_should_be_validation_error_if_no_email_or_password(self):
        res = self.client.post("/user/login", data={})
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 400
        assert self.strip_all_whitespace(EMAIL_EMPTY_ERROR) in content
        assert self.strip_all_whitespace(PASSWORD_EMPTY_ERROR) in content

    def test_should_be_validation_error_if_invalid_email(self):
        res = self.client.post("/user/login", data={
            'email_address': 'invalid',
            'password': '1234567890'
        })
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert res.status_code == 400
        assert self.strip_all_whitespace(EMAIL_INVALID_ERROR) in content


class TestResetPassword(BaseApplicationTest):

    _user = None

    def setup_method(self, method):
        super(TestResetPassword, self).setup_method(method)

        data_api_client_config = {'get_user.return_value': self.user(
            123, "email@email.com", 1234, 'name', 'Name'
        )}

        self._user = {
            "user": 123,
            "email": 'email@email.com',
        }

        self._data_api_client = mock.patch(
            'app.main.views.auth.data_api_client', **data_api_client_config
        )
        self.data_api_client_mock = self._data_api_client.start()

    def teardown_method(self, method):
        self._data_api_client.stop()

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

    @mock.patch('app.main.views.auth.send_email')
    def test_redirect_to_same_page_on_success(self, send_email):
        res = self.client.post("/user/reset-password", data={
            'email_address': 'email@email.com'
        })
        assert res.status_code == 302
        assert res.location == 'http://localhost/user/reset-password'

    @mock.patch('app.main.views.auth.send_email')
    def test_show_email_sent_message_on_success(self, send_email):
        res = self.client.post("/user/reset-password", data={
            'email_address': 'email@email.com'
        }, follow_redirects=True)
        assert res.status_code == 200
        content = self.strip_all_whitespace(res.get_data(as_text=True))
        assert self.strip_all_whitespace(auth.EMAIL_SENT_MESSAGE) in content

    @mock.patch('app.main.views.auth.send_email')
    def test_should_strip_whitespace_surrounding_reset_password_email_address_field(self, send_email):
        self.client.post("/user/reset-password", data={
            'email_address': ' email@email.com'
        })
        self.data_api_client_mock.get_user.assert_called_with(email_address='email@email.com')

    def test_email_should_be_decoded_from_token(self):
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])
            url = '/user/reset-password/{}'.format(token)

        res = self.client.get(url)
        assert res.status_code == 200
        assert "Reset password for email@email.com" in res.get_data(as_text=True)

    def test_password_should_not_be_empty(self):
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
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
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])
            url = '/user/reset-password/{}'.format(token)

            res = self.client.post(url, data={
                'password': '123456789',
                'confirm_password': '123456789'
            })
            assert res.status_code == 400
            assert PASSWORD_INVALID_ERROR in res.get_data(as_text=True)

    def test_password_should_be_under_51_chars_long(self):
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
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
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])
            url = '/user/reset-password/{}'.format(token)

            res = self.client.post(url, data={
                'password': '1234567890',
                'confirm_password': '0123456789'
            })
            assert res.status_code == 400
            assert PASSWORD_MISMATCH_ERROR in res.get_data(as_text=True)

    def test_redirect_to_login_page_on_success(self):
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])
            url = '/user/reset-password/{}'.format(token)

            res = self.client.post(url, data={
                'password': '1234567890',
                'confirm_password': '1234567890'
            })
            assert res.status_code == 302
            assert res.location == 'http://localhost/user/login'
            res = self.client.get(res.location)

            assert auth.PASSWORD_UPDATED_MESSAGE in res.get_data(as_text=True)

    def test_password_change_unknown_failure(self):
        self.data_api_client_mock.update_user_password.return_value = False
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])
            url = '/user/reset-password/{}'.format(token)

            res = self.client.post(url, data={
                'password': '1234567890',
                'confirm_password': '1234567890'
            })
            assert res.status_code == 302
            assert res.location == 'http://localhost/user/login'
            res = self.client.get(res.location)

            assert auth.PASSWORD_NOT_UPDATED_MESSAGE in res.get_data(as_text=True)
        self.data_api_client_mock.update_user_password.return_value = True

    def test_should_not_strip_whitespace_surrounding_reset_password_password_field(self):
        with self.app.app_context():
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])
            url = '/user/reset-password/{}'.format(token)

            self.client.post(url, data={
                'password': '  1234567890',
                'confirm_password': '  1234567890'
            })
            self.data_api_client_mock.update_user_password.assert_called_with(
                self._user.get('user'), '  1234567890', self._user.get('email'))

    @mock.patch('app.main.views.auth.data_api_client')
    def test_token_created_before_last_updated_password_cannot_be_used(
            self, data_api_client
    ):
        with self.app.app_context():
            data_api_client.get_user.return_value = self.user(
                123, "email@email.com", 1234, 'email', 'Name', is_token_valid=False
            )
            token = generate_token(
                self._user,
                self.app.config['SECRET_KEY'],
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
            assert auth.BAD_TOKEN_MESSAGE in error_elements[0].text_content()

    @mock.patch('app.main.views.auth.send_email')
    def test_should_call_send_email_with_correct_params(
            self, send_email
    ):
        with self.app.app_context():

            self.app.config['DM_MANDRILL_API_KEY'] = "API KEY"
            self.app.config['RESET_PASSWORD_EMAIL_SUBJECT'] = "SUBJECT"
            self.app.config['RESET_PASSWORD_EMAIL_FROM'] = "EMAIL FROM"
            self.app.config['RESET_PASSWORD_EMAIL_NAME'] = "EMAIL NAME"

            res = self.client.post(
                '/user/reset-password',
                data={'email_address': 'email@email.com'}
            )

            assert res.status_code == 302
            send_email.assert_called_once_with(
                "email@email.com",
                mock.ANY,
                "API KEY",
                "SUBJECT",
                "EMAIL FROM",
                "EMAIL NAME",
                ["password-resets"]
            )

    @mock.patch('app.main.views.auth.send_email')
    def test_should_be_an_error_if_send_email_fails(
            self, send_email
    ):
        with self.app.app_context():

            send_email.side_effect = EmailError(Exception('API is down'))

            res = self.client.post(
                '/user/reset-password',
                data={'email_address': 'email@email.com'}
            )

            assert res.status_code == 503
            assert PASSWORD_RESET_EMAIL_ERROR in res.get_data(as_text=True)


class TestLoginFormsNotAutofillable(BaseApplicationTest):
    def _forms_and_inputs_not_autofillable(
            self, url, expected_title, expected_lede=None
    ):
        response = self.client.get(url)
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//main[@id="content"]//h1/text()')[0].strip()
        assert expected_title == page_title

        if expected_lede:
            page_lede = document.xpath(
                '//main[@id="content"]//p[@class="lede"]/text()')[0].strip()
            assert expected_lede == page_lede

        forms = document.xpath('//main[@id="content"]//form')

        for form in forms:
            assert form.get('autocomplete') == "off"
            non_hidden_inputs = form.xpath('//input[@type!="hidden"]')

            for input in non_hidden_inputs:
                if input.get('type') != 'submit':
                    assert input.get('autocomplete') == "off"

    def test_login_form_and_inputs_not_autofillable(self):
        self._forms_and_inputs_not_autofillable(
            "/user/login",
            "Log in to the Digital Marketplace"
        )

    def test_request_password_reset_form_and_inputs_not_autofillable(self):
        self._forms_and_inputs_not_autofillable(
            "/user/reset-password",
            "Reset password"
        )

    @mock.patch('app.main.views.auth.data_api_client')
    def test_reset_password_form_and_inputs_not_autofillable(
            self, data_api_client
    ):
        data_api_client.get_user.return_value = self.user(
            123, "email@email.com", 1234, 'email', 'name'
        )

        with self.app.app_context():
            token = generate_token(
                {
                    "user": 123,
                    "email": 'email@email.com',
                },
                self.app.config['SECRET_KEY'],
                self.app.config['RESET_PASSWORD_SALT'])

            url = '/user/reset-password/{}'.format(token)

        self._forms_and_inputs_not_autofillable(
            url,
            "Reset password",
            "Reset password for email@email.com"
        )
