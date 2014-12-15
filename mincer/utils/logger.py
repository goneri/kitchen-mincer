import logging
import logging.handlers

import swiftclient


class RotatingSwiftHandler(logging.handlers.MemoryHandler):

    """Log handler to push messages in Swift."""

    def __init__(self, auth, capacity=1000, container="log",
                 name="name", flushLevel=logging.CRITICAL):
        """RotatingSwiftHandler constructor

        :param auth: the parameter to pass to swiftclient.client.Connection in
                   a dictionnary (user, key, authurl, tenant_name,
                   auth_version)
        :type auth: dict()
        :param capacity: the maximum number of messages per object,
                       default is 1000
        :type capacity: int()
        :param container: the name of the container
        :type container: str()
        :param name: the name of the object, a prefix will be added
                   (e.g: foo-01)
        :type name: str()
        :param flushLevel: messages greater or equal of this severity will
                         force a flush of the message queue
        :type flushLevel: str()

        """
        logging.handlers.MemoryHandler.__init__(
            self, capacity, flushLevel)
        self.swift_client = swiftclient.client.Connection(
            user=auth['user'],
            key=auth['key'],
            authurl=auth['authurl'],
            tenant_name=auth['tenant_name'],
            auth_version='2.0')
        self.container = container
        self.name = name
        self.cpt = 0

    def flush(self):
        """Flush the message queue

        You may want to call this method before the object destruction
        to ensure no message get lost.

        """
        self.acquire()
        if len(self.buffer) == 0:
            return
        try:
            messages = "\n".join([lr.getMessage() for lr in self.buffer])
            self.swift_client.put_object(
                self.container,
                "%s-%02d" % (self.name, self.cpt),
                messages)
            self.buffer = []
            self.cpt += 1
        except Exception as e:
            print(e)
        finally:
            self.release()
