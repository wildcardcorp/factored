from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='twofactor',
      version=version,
      description="",
      long_description="",
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
          'webob',
          'gunicorn',
          'WSGIProxy',
          'repoze.who',
          'pyramid',
          'SQLAlchemy',
          'transaction',
          'pyramid_tm',
          'pyramid_debugtoolbar',
          'zope.sqlalchemy'
      ],
      entry_points="""
      # -*- Entry points: -*-
      [paste.app_factory]
      main = twofactor.auth:Authenticator

      [console_scripts]
      initialize_db = twofactor.scripts.initializedb:main
      adduser = twofactor.scripts.users:add
      removeuser = twofactor.scripts.users:remove
      listusers = twofactor.scripts.users:listusers
      """,
      )
