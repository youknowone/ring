Contribution
============

First, install **Ring** in editable mode. To install tests requirements, use
'tests' extra.

.. sourcecode:: shell

    $ pip install -e '.[tests]'


Run pytest to check the test is working.

.. sourcecode:: shell

    $ pytest -vv


When all tests passed, edit the code and add new tests for the new or changed
code.


Tips
----

pyenv_ and pyenv-virtualenv_ will save your time, especially when experiencing
compatibility problems between versions.

.. _pyenv: https://github.com/pyenv/pyenv#installation
.. _pyenv-virtualenv: https://github.com/pyenv/pyenv-virtualenv


:note: Can't install `ring[tests]` because of compile errors?
       Don't forget to install and start memcached and redis locally.
       Test codes are using memcached & redis to ensure ring is correctly
       working.


macOS
~~~~~

.. sourcecode:: shell

    $ brew install docker-compose
    $ docker-compose up


Debian/Ubuntu
~~~~~~~~~~~~~

.. sourcecode:: shell

    $ apt install docker-compose
    $ docker-compose up
