Contribution
~~~~~~~~~~~~

Tips
====

pyenv_ and pyenv-virtualenv_ will save your time, especially when experiencing
compatibility problems between version:wns.

.. _pyenv: https://github.com/pyenv/pyenv#installation
.. _pyenv-virtualenv: https://github.com/pyenv/pyenv-virtualenv

macOS
-----

.. code:: sh

    $ pyenv virtualenv 3.6.3 ring
    $ brew install memcached libmemcached redis
    $ pip install -e '.[tests]'
    $ pytest -vv
