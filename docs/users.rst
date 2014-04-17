User Management
===============

If you do not use an auto user plugin and/or you need to configure a users
google auth plugin, pay attention to the commands below.

Make sure you have first installed and initialized the database.


- Add user::

    ./bin/factored_adduser develop.ini --username=foo@bar.com

- Delete user::

    ./bin/factored_removeuser develop.ini --username=foo@bar.com

- List user info::

    ./bin/factored_listuserinfo develop.ini --username=foo@bar.com

- List users::

    ./bin/factored_listusers develop.ini
