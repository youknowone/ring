Save and load rich data
=======================

The concept of coder
--------------------

Though the most basic data type in **Ring** is :class:`bytes` which is very
common among various storages, modern services handle more complicated data
types.

**Ring** factory has coder layer - which provides a customizable interface to
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

Coder is one of the configurable layers in **Ring**.


Pre-registered coders
---------------------

**Ring** is distributed with a few pre-registered coders which are common in
modern Python world.

.. autosummary::

    ring.coder.bypass_coder
    ring.coder.JsonCoder
    ring.coder.pickle_coder

:see: :mod:`ring.coder` for details.


Create a new coder
------------------

Users can register new custom coders with aliases.

Related coder types:

  - :class:`ring.coder.Coder`
  - :class:`ring.coder.CoderTuple`

Registry:

  - :data:`ring.coder.registry`
  - :class:`ring.coder.Registry`

:see: :doc:`extend`