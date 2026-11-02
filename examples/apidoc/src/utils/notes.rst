Notes on the utilities
======================

A reST page next to the code. :mat:func:`clamp` limits values; it calls a
private helper, :mat:func:`utils/private/check_range.m`:

.. literalinclude:: clamp.m
   :language: matlab
   :lines: 1-2

The :mat:sidecar:`+demo/getting-started.md` tutorial uses the shapes.
