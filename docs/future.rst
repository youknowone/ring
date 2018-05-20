The future of Ring
==================


Flexible controller
-------------------

.. code-block:: python

    import ring

    class A(object):

        @ring.dict({})
        def f(self, a, b):
            ...

        @f.ring.key  # override key creation function
        def f_key(self, a, b):
            ...  # possible __ring_key__ alternative

        @f.ring.on_update  # events
        def f_on_update(self, a, b):
            ...

        @ring.dict({})
        def g(self, a):
            ...

        @g.ring.cascade  # cascading for subsets (and supersets)
        def g_cascade(self):
            return {
                'delete': self.f,
            }


Ring doctor
-----------

.. code-block:: python

    import ring

    @ring.dict({}, 'prefix')
    def f1(a):
        pass

    @ring.dict({}, 'prefix')
    def f2(a):
        pass

    @ring.dict({}, 'overload', overload=True)
    def o1(a):
        pass

    @ring.dict({}, 'overload', overload=2)
    def o2(a):
        pass


    ring.doctor()  # raise error: f1 and f2 has potential key collision
