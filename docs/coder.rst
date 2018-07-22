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


Pre-registered coders
---------------------

**Ring** is distributed with a few pre-registered coders which are common in
modern Python world.

.. autosummary::

    ring.coder.bypass_coder
    ring.coder.JsonCoder
    ring.coder.pickle_coder

:see: :mod:`ring.coder` for the module including pre-registered coders.


Create a new coder
------------------

Users can register new custom coders with aliases.

Related coder types:

  - :class:`ring.coder.Coder`
  - :class:`ring.coder.CoderTuple`

Registry:

  - :data:`ring.coder.registry`
  - :class:`ring.coder.Registry`
  - :meth:`ring.coder.Registry.register`


For example, the float example above can be written as a coder like below:

.. code-block:: python

    class FloatCoder(ring.coder.Coder):

        def encode(self, value):
            return str(value).encode('utf-8')

        def decode(self, data):
            return float(data.decode('utf-8'))


    ring.coder.register('float', FloatCoder)


Now `FloatCoder` is registered as `float`. Use it in a familiar way.

.. code-block:: python

    @ring.dict({}, coder='float')
    def f():
        return 3.1415


:note: `coder` parameter of factories only take one of the registered names of
    coders and actual :class:`ring.coder.Coder` objects. On the other hands,
    :meth:`ring.coder.Registry.register` take raw materials of
    :class:`ring.coder.Coder` or :class:`ring.coder.CoderTuple`. See
    :func:`ring.coder.coderize` for details.


Override a coder
----------------

Sometimes coder is not a reusable part of the code. Do not create coders
for single use. Instead of it, you can redefine encode and decode function
of a ring object.


.. code-block:: python

    @ring.dict({})
    def f():
        return 3.1415

    @f.ring.encode
    def f_encode(value):
        return str(value).encode('utf-8')

    @f.ring.decode
    def f_decode(value):
        return float(data.decode('utf-8'))

