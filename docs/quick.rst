Quickstart
~~~~~~~~~~

macOS
-----

Install pyenv_ and pyenv-virtualenv_.

.. _pyenv: https://github.com/pyenv/pyenv#installation
.. _pyenv-virtualenv: https://github.com/pyenv/pyenv-virtualenv

also install python 3.6.3 via pyenv.

.. code:: sh

    $ pyenv virtualenv 3.6.3 ring
    $ brew install memcached libmemcached redis
    $ pip install -e '.[tests]'
    $ pytest -vv

That's it!