
import munge
import munge.codec.all
import munge.util
import os


default_conf_dir = '~/.peeringdb'


def default_config():
    conf = {
        'peeringdb': {
            'url': 'https://www.peeringdb.com/api',
            'user': '',
            'password': '',
            'timeout': 0,
        },
        'database': {
            'engine': 'sqlite3',
            'name': 'peeringdb.sqlite3',
            'host': '',
            'port': '',
            'user': '',
            'password': '',
        }
    }
    return conf.copy()


def get_config(conf_dir=default_conf_dir):
    if not conf_dir:
        return default_config()

    conf_path = os.path.expanduser(conf_dir)
    if not os.path.exists(conf_path):
        # only throw if not default
        if conf_dir != default_conf_dir:
            raise IOError("config dir not found at %s" % (conf_path,))

    data = default_config()
    config = munge.load_datafile('config', conf_path, default=None)
    if config:
        munge.util.recursive_update(data, config)
        data['__config_dir__'] = conf_path

    return data


def write_config(data, conf_dir=default_conf_dir, codec=None):
    if not codec:
        codec = munge.get_codec('yaml')()
    conf_dir = os.path.expanduser(conf_dir)
    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)

    codec.dump(data, open(os.path.join(conf_dir, 'config.' + codec.extensions[0]), 'w'))
