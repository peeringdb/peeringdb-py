from __future__ import print_function

import collections
import sys
from peeringdb.util import pretty_speed


class WhoisFormat(object):
    def __init__(self, fobj=sys.stdout):
        self.fobj = fobj

        self.display_names = {
            'fac_set': 'Facilities',
        }

    def mk_fmt(self, *widths):
        return '%-' + 's %-'.join(map(str, widths)) + 's'

    def mk_set_headers(self, data, columns):
        """ figure out sizes and create header fmt """
        columns = tuple(columns)
        lens = []

        for key in columns:
            value_len = max(len(str(each.get(key, ''))) for each in data)
            # account for header lengths
            lens.append(max(value_len, len(self._get_name(key))))

        fmt = self.mk_fmt(*lens)
        return fmt

    def _get_name(self, key):
        """ get display name for a key, or mangle for display """
        if key in self.display_names:
            return self.display_names[key]

        return key.capitalize()

    def _get_val(self, data, key):
        """ get value from a dict, format if necessary """
        return data.get(key, '')

    def _get_columns(self, data):
        """ get columns from a dict """
        return data.keys()

    def display_section(self, name):
        self._print(name)
        self._print('=' * len(name))
        self._print("")

    def display_headers(self, fmt, headers):
        self._print(fmt % headers)
        self._print(fmt % tuple('-' * len(x) for x in headers))

    def display_set(self, typ, data, columns):
        """ display a list of dicts """
        self.display_section("%s (%d)" % (self._get_name(typ), len(data)))
        headers = tuple(map(self._get_name, columns))
        fmt = self.mk_set_headers(data, columns)
        self.display_headers(fmt, headers)

        for each in data:
            row = tuple(self._get_val(each, k) for k, v in each.items())
            self._print(fmt % row)

        self._print("\n")

    def display_field(self, fmt, obj, field, display=None):
        if not display:
            display = self._get_name(field)
        self._print(fmt % (display, obj[field]))

    def check_set(self, data, name):
        if data.get(name, None):
            if hasattr(self, 'print_' + name):
                getattr(self, 'print_' + name)(data[name])

    def print_net(self, data):
        self.display_section("Network Information")
        fmt = "%-21s: %s"
        self.display_field(fmt, data, 'name', 'Name')
        self.display_field(fmt, data, 'asn', 'Primary ASN')
        self.display_field(fmt, data, 'aka', 'Also Known As')
        self.display_field(fmt, data, 'website', 'Website')
        self.display_field(fmt, data, 'irr_as_set', 'IRR AS-SET')
        self.display_field(fmt, data, 'info_type', 'Network Type')
        self.display_field(fmt, data, 'info_prefixes6', 'Approx IPv6 Prefixes')
        self.display_field(fmt, data, 'info_prefixes4', 'Approx IPv4 Prefixes')
        self.display_field(fmt, data, 'looking_glass', 'Looking Glass')
        self.display_field(fmt, data, 'route_server', 'Route Server')
        self.display_field(fmt, data, 'created', 'Created at')
        self.display_field(fmt, data, 'updated', 'Updated at')
        self._print("\n")

        self.display_section("Peering Policy Information")
        self.display_field(fmt, data, 'policy_url', 'URL')
        self.display_field(fmt, data, 'policy_general', 'General Policy')
        self.display_field(fmt, data, 'policy_locations',
                           'Location Requirement')
        self.display_field(fmt, data, 'policy_ratio', 'Ratio Requirement')
        self.display_field(fmt, data, 'policy_contracts',
                           'Contract Requirement')
        self._print("\n")

        self.check_set(data, 'poc_set')
        self.check_set(data, 'netixlan_set')
        self.check_set(data, 'netfac_set')

    def print_poc_set(self, data):
        self.display_section("Contact Information")
        fmt = self.mk_fmt(6, 20, 15, 20, 14)
        hdr = ('Role', 'Name', 'Email', 'URL', 'Phone')
        self.display_headers(fmt, hdr)

        for poc in data:
            self._print(fmt % (poc.get('role', ''), poc.get('name', ''),
                               poc.get('email', ''), poc.get('url', ''),
                               poc.get('phone', '')))

        self._print("\n")

    def print_netfac_set(self, data):
        self.display_section("Private Peering Facilities (%d)" % len(data))
        fmt = self.mk_fmt(51, 8, 15, 2)
        hdr = ('Facility Name', 'ASN', 'City', 'CO')
        self.display_headers(fmt, hdr)
        for each in data:
            self._print(fmt % (each.get('name', each.get('id')),
                               each.get('local_asn', ''), each.get('city', ''),
                               each.get('country', '')))
        self._print("\n")

    def print_netixlan_set(self, data):
        self.display_section("Public Peering Points (%d)" % len(data))
        fmt = self.mk_fmt(36, 8, 27, 5)
        hdr = ('Exchange Point', 'ASN', 'IP Address', 'Speed')
        self.display_headers(fmt, hdr)
        for ix in data:
            if ix.get('ipaddr4', None):
                self._print(
                    fmt % (ix.get('name', ix.get('ixlan_id')), ix['asn'],
                           ix['ipaddr4'], pretty_speed(ix['speed'])))
            if ix.get('ipaddr6', None):
                if ix.get('ipaddr4', None):
                    self._print(fmt % ('', '', ix['ipaddr6'], ''))
                else:
                    self._print(fmt % (ix['name'], ix['asn'], ix['ipaddr6'],
                                       pretty_speed(ix['speed'])))
        self._print("\n")

    def _print(self, *args):
        """ internal print to self.fobj """
        string = u" ".join(args) + '\n'
        self.fobj.write(string)

    def print(self, typ, data):
        """ *deprecated* - use display() """
        return self.display(typ, data)

    def display(self, typ, data):
        """ display section of typ with data """
        if hasattr(self, 'print_' + typ):
            getattr(self, 'print_' + typ)(data)

        elif not data:
            self._print("%s: %s" % (typ, data))

        elif isinstance(data, collections.Mapping):
            self._print("\n", typ)
            for k, v in data.items():
                self.print(k, v)

        elif isinstance(data, (list, tuple)):
            # tabular data layout for lists of dicts
            if isinstance(data[0], collections.Mapping):
                self.display_set(typ, data, self._get_columns(data[0]))
            else:
                for each in data:
                    self.print(typ, each)
        else:
            self._print("%s: %s" % (typ, data))

        self.fobj.flush()
