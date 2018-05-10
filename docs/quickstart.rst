Quickstart
~~~~~~~~~~

Installation
------------

PyPI is the recommended way.

.. sourcecode:: shell

    $ pip install ring

To browse versions and tarballs, visit:
    `<https://pypi.python.org/pypi/ring/>`_


Though **Ring** includes built-in supports for many backends, they are not
included in ring installation due to the following issues:

  #. Ring supports many backends but users don't use all of them.
  #. Backends packages not only cost storages and time, but also require some
     non-Python packages to be installed, which cannot be automated by pip.
  #. Installing some of them is not easy on some platforms.

Check each backend you use and manually add related packages to `setup.py`
or `requirements.txt`.

If you are new to **Ring** and cache, :func:`ring.func_sync.dict` doesn't
require any dependency. Let's start with it. Moving from dict to another
backend is easy.

For more backends, see :doc:`factory`.

