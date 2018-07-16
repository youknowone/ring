Extend Ring to meet your own needs
==================================

Creating new coders
-------------------

Users can register new custom coders with aliases. Once a coder is registered
to global registry, passing its alias to `coder` parameter of each factory
is identical to passing the coder object to `coder` parameter.

:see: :doc:`coder` for details


Creating new factory functions
------------------------------

To create a new factory, basic understanding of factory bases is required.
Let's see one by one with examples.

General factory: :func:`ring.func.base.factory`


Creating simple shortcuts
+++++++++++++++++++++++++

:see: :ref:`factory.shortcut` to create shortcuts of existing factories.


New storage interface
+++++++++++++++++++++

The most important component is the ``storage_interface`` parameter,
which is expected to inherit :class:`ring.func.base.BaseStorage`.
The abstract class defines common basic operations of storage.

(TBD)


New sub-function semantics
++++++++++++++++++++++++++



