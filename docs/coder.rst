Save and load rich data
~~~~~~~~~~~~~~~~~~~~~~~

In this document, you will learn:

  #. What `coder` is. What it does.
  #. About built-in coders.
  #. Common tips to use.
  #. How to create a custom coder.


Concept of coder
----------------

Though the most basic data type in **Ring** is :class:`bytes` which is mostly
common between various storages, modern services handle more complicated data
types.

**Ring** factory has coder layer - which provides customizable interface to
encode before saving and to decode after loading. For example, let's say our
function `f` returns :class:`float` type but we only have :class:`bytes`
storage. This is a demonstration without Ring.

.. code-block:: python

    def f():
        return 3.1415

    # straightforward way
    storage = {}  # suppose this is bytes-only db
    result = f()  # run function
    # set
    encoded = str(result).encode('utf-8')  # encoding: to bytes
    storage.set('key', encoded)
    # get
    encoded = storage.get('key')
    decoded = float(encoded.decode('utf-8'))  # decoding: to float

    assert result == decoded

You see `encoding` and `decoding` steps. The pair of them is called `coder`
in **Ring**.

Coder is one of configurable layers in **Ring**.

Built-in coders
---------------

:see: :mod:`ring.coder`

Common tips
-----------

Create a new coder
------------------

Users can register new custom coders with aliases.
