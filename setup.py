from setuptools import setup

version = open('facsimile/VERSION').read().strip()
requirements = open('facsimile/requirements.txt').read().split("\n")
test_requirements = open('facsimile/requirements-test.txt').read().split("\n")

setup(
    name='peeringdb',
    version=version,
    author='PeeringDB',
    author_email='support@peeringdb.com',
    description='peeringdb client and interface',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet',
    ],
    packages=[
        'peeringdb',
    ],
    url='https://github.com/peeringdb/peeringdb-py',
    download_url='https://github.com/peeringdb/peeringdb-py/%s' % version,
    include_package_data=True,
    install_requires=requirements,
    test_requires=test_requirements,
    scripts=['peeringdb/bin/peeringdb'],
# TODO __main__ should make this zipsafe
    zip_safe=False,
)

