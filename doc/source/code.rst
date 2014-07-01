Code architecture
=================

- The entry point of the application is the Main class.
- The Mincer class instantiates the Marmite object and load the provider specified
  in the marmite.yaml file.
- The MediaManager is in charge of collecting the medias from the marmite and
  provisioning each images with the corresponding application code afterwards it
  push them as images in Glance.
- The Provider instantiates the MediaManager and start to deploy the application.



.. blockdiag::

    blockdiag {

	"provider\ninterface" [ stacked  ]
        "tester\ninterface" [ stacked ]
        "medias" [ stacked ]

        main -> mincer
        mincer -> marmite
	mincer -> "provider\ninterface"
        mincer -> "tester\ninterface"
        "tester\ninterface" -> "a first\ntest"
        "tester\ninterface" -> "another\ntest"
	mincer -> environment
	"provider\ninterface" -> "a provider"
	mincer -> medias
        medias -> "an ISO file"
	medias -> "some files and\na git repository"
    }


Providers
=========

The cloud abstraction layer.

Heat
----

.. autoclass:: mincer.providers.heat.Heat

Testers
=======

The test engines.

simple_test
-----------

.. autoclass:: mincer.testers.simple_check.SimpleCheck


Logdispatchers
==============

This is an abstracted class to handle the dispatch of the log files generated
during the stack creation. It allows you to abstract the final storage to
different medium.

Directory
---------

.. autoclass:: mincer.logdispatchers.directory.Directory
