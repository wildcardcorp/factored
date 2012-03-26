from setuptools import setup, find_packages

version = '1.1a2'

setup(name='factored',
      version=version,
      description="A WSGI app that allows you to add another factor of "
                  "authentication to any application server.",
      long_description=open("README.txt").read() + "\n" +
                       open("CHANGES.txt").read(),
      classifiers=[
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware'],
      keywords='mutli factor authentication 2factor mutl-factor '
               'auth auth_tkt google otp',
      author='Nathan Van Gheem',
      author_email='vangheem@gmail.com',
      url='http://github.com/vangheem/factored',
      license='GPL2',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'PasteDeploy',
          'PasteScript',
          'webob',
          'WSGIProxy',
          'repoze.who',
          'pyramid',
          'SQLAlchemy',
          'transaction',
          'pyramid_tm',
          'pyramid_debugtoolbar',
          'zope.sqlalchemy',
          'pyramid_simpleform',
          'pyramid_mailer'
      ],
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      simpleproxy = factored.app:SimpleProxy

      [paste.filter_app_factory]
      main = factored.app:Authenticator

      [console_scripts]
      initializedb = factored.scripts.initializedb:main
      adduser = factored.scripts.users:add
      removeuser = factored.scripts.users:remove
      listusers = factored.scripts.users:listusers
      listuserinfo = factored.scripts.users:listuserinfo
      """,
      )
