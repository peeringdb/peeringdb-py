import io

from peeringdb.whois import WhoisFormat


def _fmt():
    return WhoisFormat(fobj=io.StringIO())


def test_display_field_defaults_label_from_key():
    f = _fmt()
    f.display_field("%-21s: %s", {"asn": 123}, "asn")
    assert "Asn" in f.fobj.getvalue()


def test_display_empty_data():
    f = _fmt()
    f.display("unknown", None)
    assert "unknown: None" in f.fobj.getvalue()


def test_display_mapping_recurses():
    f = _fmt()
    f.display("info", {"a": 1})
    out = f.fobj.getvalue()
    assert "info" in out
    assert "a: 1" in out


def test_display_list_of_scalars():
    f = _fmt()
    f.display("tags", ["x", "y"])
    out = f.fobj.getvalue()
    assert "x" in out
    assert "y" in out


def test_display_scalar_fallback():
    f = _fmt()
    f.display("count", 5)
    assert "count: 5" in f.fobj.getvalue()


def test_print_netixlan_ipv6_only():
    f = _fmt()
    data = [
        {
            "name": "IX-A",
            "asn": 64512,
            "ipaddr4": "",
            "ipaddr6": "2001:db8::1",
            "speed": 1000,
            "ixlan_id": 1,
        }
    ]
    f.print_netixlan_set(data)
    assert "2001:db8::1" in f.fobj.getvalue()
