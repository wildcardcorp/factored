from setuptools import setup, find_packages

version = '0.1'

setup(name='factored',
      version=version,
      description="",
      long_description=open("README.txt").read() + "\n" +
                       open("CHANGES.txt").read(),
      classifiers=[],
      keywords='',
      author='',
      author_email='',
      url='',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'PasteDeploy',
          'PasteScript',
          'webob',
          'gunicorn',
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
      initialize_db = factored.scripts.initializedb:main
      adduser = factored.scripts.users:add
      removeuser = factored.scripts.users:remove
      listusers = factored.scripts.users:listusers
      listuserinfo = factored.scripts.users:listuserinfo
      """,
      )
