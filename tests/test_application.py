import mock
from wtforms import ValidationError
from .helpers import BaseApplicationTest
from werkzeug.exceptions import ServiceUnavailable, BadRequest


class TestApplication(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/user/login')
        assert 200 == response.status_code

    def test_404(self):
        response = self.client.get('/not-found')
        assert 404 == response.status_code

    @mock.patch('app.main.auth.get_errors_from_wtform')
    def test_503_renders_shared_error_template(self, get_errors):
        get_errors.side_effect = ServiceUnavailable()
        self.app.config['DEBUG'] = False

        res = self.client.get('/user/login')
        assert res.status_code == 503
        assert u"Sorry, we’re experiencing technical difficulties" in res.get_data(as_text=True)
        assert "Try again later." in res.get_data(as_text=True)

    def test_trailing_slashes(self):
        response = self.client.get('')
        assert 308 == response.status_code
        assert "http://localhost/" == response.location
        response = self.client.get('/trailing/')
        assert 301 == response.status_code
        assert "http://localhost/trailing" == response.location

    def test_trailing_slashes_with_query_parameters(self):
        response = self.client.get('/search/?q=r&s=t')
        assert 301 == response.status_code
        assert "http://localhost/search?q=r&s=t" == response.location

    def test_header_xframeoptions_set_to_deny(self):
        res = self.client.get('/user/login')
        assert 200 == res.status_code
        assert 'DENY', res.headers['X-Frame-Options']

    @mock.patch('app.main.auth.get_errors_from_wtform')
    def test_non_csrf_400(self, get_errors):
        get_errors.side_effect = BadRequest()

        res = self.client.get('/user/login')

        assert res.status_code == 400
        assert "Sorry, there was a problem with your request" in res.get_data(as_text=True)
        assert "Please do not attempt the same request again." in res.get_data(as_text=True)

    @mock.patch('flask_wtf.csrf.validate_csrf', autospec=True)
    def test_csrf_handler_redirects_to_login(self, validate_csrf):
        self.login_as_buyer()

        with self.app.app_context():
            self.app.config['WTF_CSRF_ENABLED'] = True
            self.client.set_cookie(
                "localhost",
                self.app.config['DM_COOKIE_PROBE_COOKIE_NAME'],
                self.app.config['DM_COOKIE_PROBE_COOKIE_VALUE'],
            )

            # This will raise a CSRFError for us when the form is validated
            validate_csrf.side_effect = ValidationError('The CSRF session token is missing.')

            res = self.client.post(
                '/user/logout', data={'anything': 'really'},
            )

            self.assert_flashes("Your session has expired. Please log in again.", expected_category="error")
            assert res.status_code == 302

            # POST requests will not preserve the request path on redirect
            assert res.location == 'http://localhost/user/login'
            assert validate_csrf.call_args_list == [mock.call(None)]
