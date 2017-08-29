# coding: utf-8
from __future__ import unicode_literals

import urllib
from freezegun import freeze_time
from dmapiclient import HTTPError
from dmutils.email import generate_token
from dmutils.email.exceptions import EmailError
from ...helpers import BaseApplicationTest
from lxml import html, cssselect
import mock
import pytest

from app.main.views.auth import INVALID_TOKEN_MESSAGE

from app.main.views import auth


EMAIL_EMPTY_ERROR = "You must provide an email address"
EMAIL_INVALID_ERROR = "You must provide a valid email address"
PASSWORD_EMPTY_ERROR = "You must provide your password"
PASSWORD_INVALID_ERROR = "Passwords must be between 10 and 50 characters"
PASSWORD_MISMATCH_ERROR = "The passwords you entered do not match"
NEW_PASSWORD_EMPTY_ERROR = "You must enter a new password"
NEW_PASSWORD_CONFIRM_EMPTY_ERROR = "Please confirm your new password"
PASSWORD_RESET_EMAIL_ERROR = "Failed to send password reset."


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
            assert auth.EXPIRED_PASSWORD_RESET_TOKEN_MESSAGE in error_elements[0].text_content()

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


class TestCreateUser(BaseApplicationTest):

    user_roles = ['buyer', 'supplier']

    def _generate_token(self, email_address='test@email.com', role='buyer',
                        supplier_id='12345', supplier_name='Supplier Name'):
        token_data = {
            'role': role,
            'email_address': email_address
        }

        if role == 'buyer':
            token_data.update({
                "phoneNumber": "020-7930-4832"
            })
        elif role == 'supplier':
            token_data.update({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name
            })

        return generate_token(
            token_data,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['INVITE_EMAIL_SALT']
        )

    def test_should_be_an_error_for_missing_token(self):
        res = self.client.get('/user/create')
        assert res.status_code == 404

    def test_should_be_an_error_for_missing_token_trailing_slash(self):
        res = self.client.get('/user/create/')
        assert res.status_code == 301
        assert res.location == 'http://localhost/user/create'

    def test_should_show_correct_error_page_for_invalid_token(self):
        for role in self.user_roles:
            token = "1234"
            res = self.client.get(
                '/user/create/{}'.format(token)
            )

            assert res.status_code == 400
            assert INVALID_TOKEN_MESSAGE in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_invalid_token_contents_500s(self, data_api_client):
        token = generate_token(
            {
                'this_is_not_expected': 1234
            },
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['INVITE_EMAIL_SALT']
        )

        for role in self.user_roles:
            with pytest.raises(KeyError):
                self.client.get(
                    '/user/create/{}'.format(token)
                )

    def test_should_be_a_bad_request_if_token_expired(self):
        for role in self.user_roles:
            with freeze_time('2016-09-28 16:00:00'):
                token = self._generate_token(role='buyer')
            res = self.client.get(
                '/user/create/{}'.format(token)
            )

            assert res.status_code == 400
            assert 'The link you used to create an account may have expired.' in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_render_create_user_page_if_user_does_not_exist(self, data_api_client):
        data_api_client.get_user.return_value = None
        page_titles = ["Create a new Digital Marketplace account", "Create contributor account"]
        button_values = ['Create account', 'Create contributor account']

        for role, page_title, button_value in zip(self.user_roles, page_titles, button_values):
            token = self._generate_token(role=role)
            res = self.client.get(
                '/user/create/{}'.format(token)
            )
            assert res.status_code == 200

            for message in [
                page_title,
                button_value,
                "test@email.com",
                '<form autocomplete="off" action="/user/create/%s" method="POST" id="createUserForm">'
                    % urllib.parse.quote(token)
            ]:
                assert message in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_render_an_error_if_already_registered_as_a_buyer(self, data_api_client):
        error_messages = [
            'Account already exists',
            'The details you provided are registered with another supplier.'
        ]
        for role, error_message in zip(self.user_roles, error_messages):
            data_api_client.get_user.return_value = self.user(
                123,
                'test@email.com',
                1 if role == 'supplier' else None,
                'Supplier name' if role == 'supplier' else None,
                'Users name'
            )

            token = self._generate_token(role=role)
            res = self.client.get(
                '/user/create/{}'.format(token),
                follow_redirects=True
            )

            assert res.status_code == 400
            assert error_message in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_if_already_registered_as_a_supplier(self, data_api_client):
        page_headings = [
            'Your email address is already registered as an account with ‘Supplier’.',
            'The details you provided are registered with another supplier.'
        ]
        for role, heading in zip(self.user_roles, page_headings):
            data_api_client.get_user.return_value = self.user(
                999,
                'test@email.com',
                1234,
                'Supplier',
                'Different users name'
            )

            token = self._generate_token(role=role)
            res = self.client.get(
                '/user/create/{}'.format(token)
            )
            assert res.status_code == 400
            assert heading in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_if_already_registered_as_an_admin(self, data_api_client):
        for role in self.user_roles:
            data_api_client.get_user.return_value = self.user(
                123,
                'test@email.com',
                None,
                None,
                'Users name',
                role='admin'
            )

            token = self._generate_token(role=role)
            res = self.client.get(
                '/user/create/{}'.format(token)
            )

            assert res.status_code == 400
            assert "Account already exists" in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_with_locked_message_if_user_is_locked(self, data_api_client):
        for role in self.user_roles:
            data_api_client.get_user.return_value = self.user(
                123,
                'test@email.com',
                1 if role == 'supplier' else None,
                'Supplier name' if role == 'supplier' else None,
                'Users name',
                locked=True
            )

            token = self._generate_token(role=role)
            res = self.client.get(
                '/user/create/{}'.format(token)
            )

            assert res.status_code == 400
            assert "Your account has been locked" in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_with_inactive_message_if_user_is_not_active(self, data_api_client):
        for role in self.user_roles:
            data_api_client.get_user.return_value = self.user(
                123,
                'test@email.com',
                1 if role == 'supplier' else None,
                'Supplier name' if role == 'supplier' else None,
                'Users name',
                active=False
            )

            token = self._generate_token(role=role)
            res = self.client.get(
                '/user/create/{}'.format(token)
            )

            assert res.status_code == 400
            assert "Your account has been deactivated" in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_with_wrong_supplier_message_if_invited_by_wrong_supplier(self, data_api_client):  # noqa
        data_api_client.get_user.return_value = self.user(
            123,
            'test@email.com',
            1234,
            'Supplier Name',
            'Users name'
        )

        token = self._generate_token(
            role='supplier',
            supplier_id=9999,
            supplier_name='Different Supplier Name',
            email_address='different_supplier@email.com'
        )

        res = self.client.get(
            '/user/create/{}'.format(token)
        )

        assert res.status_code == 400
        assert u"You were invited by ‘Different Supplier Name’" in res.get_data(as_text=True)
        assert u"Your account is registered with ‘Supplier Name’" in res.get_data(as_text=True)


class TestSubmitCreateUser(BaseApplicationTest):

    user_roles = ['buyer', 'supplier']

    def _generate_token(self, email_address='test@email.com', role='buyer'):
        token_data = {
            'role': role,
            'email_address': email_address
        }

        if role == 'buyer':
            token_data.update({
                "phoneNumber": "020-7930-4832"
            })
        elif role == 'supplier':
            token_data.update({
                "supplier_id": '12345'
            })

        return generate_token(
            token_data,
            self.app.config['SHARED_EMAIL_KEY'],
            self.app.config['INVITE_EMAIL_SALT']
        )

    def test_should_fail_if_incorrect_role_param(self):
        token = self._generate_token()
        res = self.client.post(
            '/user/create-notathing/{}'.format(token)
        )
        assert res.status_code == 404

    def test_should_be_an_error_if_invalid_token(self):
        for role in self.user_roles:
            res = self.client.post(
                '/user/create/invalidtoken'.format(role),
                data={
                    'password': '123456789',
                    'name': 'name',
                    'email_address': 'valid@test.com'
                }
            )

            assert res.status_code == 400
            assert 'Bad request - Digital Marketplace' in res.get_data(as_text=True)
            assert INVALID_TOKEN_MESSAGE in res.get_data(as_text=True)

    def test_should_be_a_bad_request_if_token_expired(self):
        for role in self.user_roles:
            with freeze_time('2016-09-28 16:00:00'):
                token = self._generate_token(role='buyer')
            res = self.client.post(
                '/user/create/{}'.format(token)
            )

            assert res.status_code == 400
            assert 'The link you used to create an account may have expired.' in res.get_data(as_text=True)

    def test_should_be_an_error_if_missing_name_and_password(self):
        validation_messages = ["You must enter a name", "You must enter a password"]

        for role in self.user_roles:
            token = self._generate_token(role=role)
            res = self.client.post(
                '/user/create/{}'.format(token),
                data={}
            )

            assert res.status_code == 400
            for message in validation_messages:
                assert message in res.get_data(as_text=True)

    def test_should_be_an_error_if_too_short_name_and_password(self):
        validation_messages = ["You must enter a name", "Passwords must be between 10 and 50 characters"]

        for role in self.user_roles:
            token = self._generate_token(role=role)
            res = self.client.post(
                '/user/create/{}'.format(token),
                data={
                    'password': "123456789",
                    'name': ""
                }
            )

            assert res.status_code == 400
            for message in validation_messages:
                assert message in res.get_data(as_text=True)

    def test_should_be_an_error_if_too_long_name_and_password(self):
        page_headings = [
            "Create a new Digital Marketplace account",
            "Create contributor account"
        ]
        for role, page_heading in zip(self.user_roles, page_headings):
            with self.app.app_context():
                token = self._generate_token(role=role)
                twofiftysix = "a" * 256
                fiftyone = "a" * 51

                res = self.client.post(
                    '/user/create/{}'.format(token),
                    data={
                        'password': fiftyone,
                        'name': twofiftysix
                    }
                )
                assert res.status_code == 400
                for message in [
                    page_heading,
                    "Names must be between 1 and 255 characters",
                    "Passwords must be between 10 and 50 characters",
                    "test@email.com"
                ]:
                    assert message in res.get_data(as_text=True)

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_create_buyer_user_if_user_does_not_exist(self, data_api_client):
        data_api_client.create_user.return_value = {
            "users": {
                "id": "1234",
                "emailAddress": "test@email.com",
                "name": "valid name",
                "role": "buyer"
            }
        }
        data_api_client.get_user.return_value = None

        token = self._generate_token(role='buyer')
        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'name': 'valid name',
                'phone_number': '020-7930-4832'
            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'buyer',
            'password': 'validpassword',
            'emailAddress': 'test@email.com',
            'phoneNumber': '020-7930-4832',
            'name': 'valid name'
        })

        assert res.status_code == 302
        assert res.location == 'http://localhost/'
        self.assert_flashes('account-created', 'flag')

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_create_suplier_user_if_user_does_not_exist(self, data_api_client):
        data_api_client.create_user.return_value = {
            "users": {
                "id": "1234",
                "emailAddress": "test@email.com",
                "name": "valid name",
                "role": "supplier",
                "supplier": {
                    "supplierId": "12345",
                    "name": "Valid supplier"
                }
            }
        }
        token = self._generate_token(role='supplier')

        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'name': 'valid name'
            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'supplier',
            'password': 'validpassword',
            'emailAddress': 'test@email.com',
            'name': 'valid name',
            'supplierId': '12345'
        })

        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'
        self.assert_flashes('account-created', 'flag')

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_if_buyer_user_exists(self, data_api_client):
        data_api_client.create_user.side_effect = HTTPError(mock.Mock(status_code=409))

        token = self._generate_token(role='buyer')
        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'phone_number': '020-7930-4832',
                'name': 'valid name'
            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'buyer',
            'password': 'validpassword',
            'emailAddress': 'test@email.com',
            'phoneNumber': '020-7930-4832',
            'name': 'valid name'
        })

        assert res.status_code == 400

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_if_supplier_user_exists(self, data_api_client):
        data_api_client.create_user.side_effect = HTTPError(mock.Mock(status_code=409))

        token = self._generate_token(role='supplier')
        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'name': 'valid name'
            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'supplier',
            'password': 'validpassword',
            'emailAddress': 'test@email.com',
            'name': 'valid name',
            'supplierId': '12345'
        })

        assert res.status_code == 400

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_create_buyer_user_if_no_phone_number(self, data_api_client):

        token = self._generate_token(role='buyer')
        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'name': 'valid name',
                'phone_number': None
            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'buyer',
            'password': 'validpassword',
            'emailAddress': 'test@email.com',
            'phoneNumber': '',
            'name': 'valid name'
        })

        assert res.status_code == 302
        assert res.location == 'http://localhost/'

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_return_an_error_if_bad_phone_number(self, data_api_client):

        token = self._generate_token(role='buyer')
        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'name': 'valid name',
                'phone_number': 'Not a number'
            }
        )

        assert res.status_code == 400

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_strip_whitespace_surrounding_create_user_name_field(self, data_api_client):
        data_api_client.get_user.return_value = None
        token = self._generate_token(role='buyer')
        self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'name': '  valid name  ',
                'phone_number': '020-7930-4832'
            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'buyer',
            'password': 'validpassword',
            'emailAddress': 'test@email.com',
            'phoneNumber': '020-7930-4832',
            'name': 'valid name'
        })

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_not_strip_whitespace_surrounding_create_user_password_field(self, data_api_client):
        data_api_client.get_user.return_value = None
        token = self._generate_token(role='buyer')
        self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': '  validpassword  ',
                'name': 'valid name  ',
                'phone_number': '020-7930-4832'

            }
        )

        data_api_client.create_user.assert_called_once_with({
            'role': 'buyer',
            'password': '  validpassword  ',
            'emailAddress': 'test@email.com',
            'name': 'valid name',
            'phoneNumber': '020-7930-4832',
        })

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_be_a_503_if_api_fails(self, data_api_client):
        with self.app.app_context():
            data_api_client.create_user.side_effect = HTTPError("bad email")

            token = self._generate_token(role='buyer')
            res = self.client.post(
                '/user/create/{}'.format(token),
                data={
                    'password': 'validpassword',
                    'name': 'valid name'
                }
            )
            assert res.status_code == 503

    @mock.patch('app.main.views.auth.data_api_client')
    def test_should_render_error_page_if_invalid_buyer_domain(self, data_api_client):
        data_api_client.create_user.side_effect = HTTPError(mock.Mock(status_code=400), message='invalid_buyer_domain')

        token = self._generate_token(role='buyer')
        res = self.client.post(
            '/user/create/{}'.format(token),
            data={
                'password': 'validpassword',
                'phone_number': '020-7930-4832',
                'name': 'valid name'
            }
        )

        assert res.status_code == 400
        assert 'You must use a public sector email address' in res.get_data(as_text=True)
