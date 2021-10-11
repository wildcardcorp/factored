from setuptools import setup, find_packages

version = '4.1.0'

requires = [
    'WebOb',
    'pyramid',
    'SQLAlchemy',
    'pyramid_simpleform',
    'pyramid_mailer',
    'argparse',
    'pyramid_tm',
    'pyramid_chameleon'
]

setup(name='factored',
      version=version,
      description="A WSGI app that allows you to add another factor of "
                  "authentication to any application server.",
      long_description="%s\n%s" % (
          open("README.rst").read(),
          open("CHANGES.rst").read()),
      classifiers=[
          'Topic :: Internet :: WWW/HTTP :: WSGI',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware'],
      keywords='mutli factor authentication 2factor mutl-factor '
               'auth auth_tkt google otp',
      author='Nathan Van Gheem',
      author_email='vangheem@gmail.com',
      url='https://github.com/wildcardcorp/factored',
      license='GPL2',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires + ['WebTest'],
      extras_require={
          'test': [
              'WebTest',
              'pyramid_debugtoolbar'
          ],
          'proxy': [
              'WSGIProxy'
          ]
      },
      test_suite="factored",
      entry_points={
          'paste.app_factory': [
              'simpleproxy = factored.app:SimpleProxy',
              'main = factored.app:Authenticator'],
          'paste.filter_app_factory': [
              'main = factored.app:Authenticator',
              'sm = factored.sm:make_sm'],
          'console_scripts': [
              'factored_initializedb = factored.scripts.initializedb:main',
              'factored_adduser = factored.scripts.users:add',
              'factored_removeuser = factored.scripts.users:remove',
              'factored_listusers = factored.scripts.users:listusers',
              'factored_listuserinfo = factored.scripts.users:listuserinfo'
          ],
          'factored.db_factory': [
              'sql = factored.sql:factory'
          ]
      })
