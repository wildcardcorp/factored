from setuptools import setup, find_packages

setup(
    name='factored',
    version='5.0.0.dev6',
    description="Pluggable 2FA Proxy Service",
    long_description="%s\n%s" % (
        open("README.md").read(),
        open("CHANGES.md").read()),
    author='Wildcard Corp.',
    author_email='support@wildcardcorp.com',
    url='https://github.com/wildcardcorp/factored',
    license='GPL2',
    packages=['factored'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pyramid',
        'pyramid_mailer',
        'waitress',
        'yapsy',
        'pyjwt',
        'jinja2',
        'sqlalchemy',
    ],
    extras_require={
        'test':[
            'pytest',
        ],
    },
    entry_points={
        "paste.app_factory": [
            "validator_main = factored.validator:app",
            "authenticator_main = factored.authenticator:app",
        ],
        "console_scripts": [
        ],
    })
