from ml.features import FEATURE_NAMES, extract_features


def test_returns_all_feature_names():
    features = extract_features("http://example.com")
    assert set(features.keys()) == set(FEATURE_NAMES)


def test_plain_legit_url():
    features = extract_features("http://google.com")
    assert features["has_ip_address"] == 0
    assert features["has_at_symbol"] == 0
    assert features["num_subdomains"] == 0
    assert features["is_https"] == 0
    assert features["has_suspicious_word"] == 0


def test_https_scheme_detected():
    assert extract_features("https://google.com")["is_https"] == 1
    assert extract_features("http://google.com")["is_https"] == 0


def test_ip_address_hostname_detected():
    features = extract_features("http://192.168.1.1/login")
    assert features["has_ip_address"] == 1
    assert features["has_suspicious_word"] == 1


def test_at_symbol_redirect_trick_detected():
    features = extract_features("http://real-bank.com@evil-phisher.com/login")
    assert features["has_at_symbol"] == 1


def test_url_shortener_detected():
    assert extract_features("http://bit.ly/abc123")["is_url_shortener"] == 1
    assert extract_features("http://google.com")["is_url_shortener"] == 0


def test_subdomain_count():
    assert extract_features("http://google.com")["num_subdomains"] == 0
    assert extract_features("http://www.google.com")["num_subdomains"] == 1
    assert extract_features("http://a.b.google.com")["num_subdomains"] == 2


def test_query_params_counted():
    features = extract_features("http://example.com/search?q=1&page=2")
    assert features["num_query_params"] == 2


def test_no_query_params_is_zero():
    assert extract_features("http://example.com/path")["num_query_params"] == 0
