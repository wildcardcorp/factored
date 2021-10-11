Changelog
=========

4.1.0 (2021-10-11)
------------------

- bump boostrap dependency
- remove jquery dependency
- tweak auth list style to better present buttons


4.0.10 (2019-01-07)
-------------------

- bump requests version


4.0.9 (2018-08-02)
------------------

- fix redirect location generation

4.0.8 (2017-07-27)
------------------

- bug fixes

4.0.7 (unreleased)
------------------

- fix ats plugin to be compatible with ats 7.2.0
- add sms plugin

4.0.6 (2017-04-17)
------------------

- add LDAPAutoUserFinder

4.0.4 (2016-01-27)
------------------

- be able to set valid message ids

4.0.3 (2015-06-08)
------------------

- use waitress in examples instead

4.0.2 (2015-05-18)
------------------

- use form text overrides properly

4.0.1 (2015-04-23)
------------------

- pyramid 1.5 compatibility

4.0a3 (2014-12-11)
------------------

- fix template customization registration

- add factored header

- upgrade bootstrap

- be able to plug in different db backends


3.0.5 (2014-09-10)
------------------

- fix bad packaging


3.0.4 (2014-09-10)
------------------

- do not require specific version of sqlalchemy


3.0.3 (2014-04-18)
------------------

- url decode for web server plugins to properly check auth tkt

3.0.2 (2014-04-18)
------------------

- better error handling for web server plugins

3.0.1 (2014-04-17)
------------------

- distribution fixes

3.0 (2014-04-17)
----------------

- better docs
- change script names
- ats and nginx plugins


2.2 (2014-04-16)
----------------

- move all form logic to plugin so everything can be overridden

2.1 (2013-06-04)
----------------

- script and template fixes

2.0rc1 (2013-01-31)
-------------------

- more robust multi-use environment with database connections

- support more algorythms for auth ticket

- refactor so it's more modular

- be able to easily customize all templates

- be able to customize text

- pull out auth_tkt module of paste so we can customize a bit

1.1a2 (2012-03-26)
------------------

- specify appname to customize google auth code entry.

- redirect to original url if possible

- be able to provide "remember me" functionality


1.1a1 (2012-03-26)
------------------

- add auto user finder support

- add ability to send google code reminders. This
  can work well with the autouserfinder


1.0a1 (2012-03-23)
------------------

- Initial release
