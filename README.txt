This file is for you to describe the bastion application. Typically
you would include information such as the information below:

Installation and Setup
======================

Install ``bastion`` using the setup.py script::

    $ cd bastion
    $ python setup.py install

Create the project database for any model classes defined::

    $ paster setup-app development.ini

Start the paste http server::

    $ paster serve development.ini

While developing you may want the server to reload after changes in package files (or its dependencies) are saved. This can be achieved easily by adding the --reload option::

    $ paster serve --reload development.ini

Then you are ready to go.

Purpose of bastion
==================

Bastion was developed as an application to act as an application that
temporarily allows remote IP addresses to connect to the local network.  The
specific problem it solved was to allow users to log in to the website and
then be able to SSH in to the network from that IP address.
