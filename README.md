# Factord v5

## Dev Setup Quick-Start

    $ make build
    $ make run

See the Makefile for the details of each command.


## Design

The basic process for interacting with this product:

  1. a user makes a request against a protected url
  2. nginx queries validator with the given jwt token in the request
  3. if the validator approves the user's token, nginx passes the traffic upstream. done.
  4. if the validator deny's the user's token, nginx internal redirects to the authenticator
  5. the authenticator displays an entry field for the userid (typically an email
     address), and a list of all authenticators plugins that are available to
     use (IE 'emaildomains', 'yubikey', 'google auth', 'sms', etc). If only one
     authenticator plugin is active, then no list is shown.

There are several types of plugins to extend and manipulate different functionality
within factored.

  * _finder plugins_ are responsible for determining whether or not a given subject
    in a JWT value can be considered a valid user -- IE is the subject in question
    an actual account and active within the system.
  * _authenticator plugins_ are ultimately responsible for providing confirmation
    and a value to use as a subject when generating a token (jwt). The are
    comprised of 4 parts:
    - get/template/render of the registration form
    - post/submit/handle of the registration form
    - get/template/render of the auth form
    - post/submit/handle of the auth form
