from setuptools import setup, find_packages

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
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet',
    ],
    packages=['peeringdb'],
    url='https://github.com/peeringdb/peeringdb-py',
    download_url='https://github.com/peeringdb/peeringdb-py/%s' % version,
    include_package_data=True,
    install_requires=requirements,
    test_requires=test_requirements,
    entry_points={
        'console_scripts': [
            'peeringdb=peeringdb.cli:main',
        ]
    },
    zip_safe=True,
)

