# coding: utf-8
from dmutils.email import generate_token
from ...helpers import BaseApplicationTest
from lxml import html
import mock


EMAIL_EMPTY_ERROR = "You must provide an email address"
EMAIL_INVALID_ERROR = "You must provide a valid email address"

PASSWORD_EMPTY_ERROR = "You must provide your password"


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

    def test_should_redirect_to_dashboard_if_next_url_is_unsafe(self):
        self.login_as_supplier()
        res = self.client.get("/user/login?next=//example.com")
        assert res.status_code == 302
        assert res.location == 'http://localhost/suppliers'

    def test_should_redirect_to_dashboard_if_next_url_is_not_http(self):
        self.login_as_admin()
        res = self.client.get("/user/login?next=file:example.pdf")
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
        res = self.client.post('/user/logout')
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


class TestLoginFormsNotAutofillable(BaseApplicationTest):
    def _forms_and_inputs_not_autofillable(self, url, expected_title, expected_lede=None):
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
    def test_reset_password_form_and_inputs_not_autofillable(self, data_api_client):
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
