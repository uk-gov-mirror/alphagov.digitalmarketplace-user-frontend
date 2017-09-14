import mock
import pytest

from collections import namedtuple

from app.main.helpers.login_helpers import is_safe_url


@pytest.fixture()
def host_url(request):
    fake_request = namedtuple('Request', ['host_url'])('http://localhost/')
    request_patch = mock.patch('app.main.helpers.login_helpers.request', fake_request)
    request.addfinalizer(request_patch.stop)

    return request_patch.start()


@pytest.fixture(params=['buyer', 'supplier', 'admin', 'admin-ccs-category'])
def current_user(request):
    fake_user = namedtuple('User', ['role'])(request.param)
    request_patch = mock.patch('app.main.helpers.login_helpers.current_user', fake_user)
    request.addfinalizer(request_patch.stop)

    return request_patch.start()


@pytest.mark.parametrize('next_url', [None, ''])
def test_empty_next_url_is_not_safe(host_url, next_url):
    assert not is_safe_url(next_url)


@pytest.mark.parametrize('next_url', [
    'https://example.com/suppliers',
    'http://localhost:5000/',
    'http://example.com/',
    '//example.com/',
])
def test_external_host_url_is_not_safe(host_url, next_url):
    assert not is_safe_url(next_url)


@pytest.mark.parametrize('next_url', [
    'file://example.pdf',
    'file:example.pdf',
    'mailto:user@example.com',
    'javascript:alert(1);',
    'about:blank',
    'git://localhost/',
])
def test_non_http_scheme_is_not_safe(host_url, next_url):
    assert not is_safe_url(next_url)


@pytest.mark.parametrize('next_url', [
    'http://localhost/suppliers'
    '/suppliers',
    'logout',
    '/admin',
    '../../',
])
def test_same_origin_url_is_safe(host_url, next_url):
    assert is_safe_url(next_url)
