#!/usr/bin/env python3
import logging
import os
import subprocess
import time

import gerritlib.gerrit

HTTP_SERVER = "http://os-ci-test7.ring.enovance.com:8500"
DEFAULT_USERNAME = "jenkins2"
RUN_SCRIPT = "./run_script.sh"
KEY = "./id_rsa-jenkins2"
WATCHED_PROJECTS = ("kitchen-mincer",)
OUTPUT_DIR = "/var/www/static"
DEFAULT_SERVER = "gerrit.sf.ring.enovance.com"


class Bottine(object):
    def __init__(self):
        self.gerrit = None
        self.log = logging.getLogger('bottine')
        self.server = DEFAULT_SERVER
        self.port = 29418
        self.username = DEFAULT_USERNAME
        self.keyfile = os.path.expanduser(KEY)
        self.run_script = os.path.abspath(os.path.expanduser(RUN_SCRIPT))
        self.connected = False

    def connect(self):
        # Import here because it needs to happen after daemonization
        try:
            self.gerrit = gerritlib.gerrit.Gerrit(
                self.server, self.username, self.port, self.keyfile)
            self.gerrit.startWatching()
            self.log.info('Start watching Gerrit event stream.')
            self.connected = True
        except Exception:
            self.log.exception('Exception while connecting to gerrit')
            self.connected = False
            # Delay before attempting again.
            time.sleep(1)

    def run_command(self, data):
        if 'change' not in data:
            return
        output_dir = "%s/%s/%s" % (OUTPUT_DIR, data['change']['number'],
                                   data['patchSet']['number'])
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)


        # Vote 0 before starting and notify that we are testing.
        self.gerrit.review(data['change']['project'],
                           "%s,%s" % (data['change']['number'],
                                      data['patchSet']['number']),
                           "Starting kitchenbot tests",
                           action={'verified': "0"},)

        env = {'CHANGE_ID': data['change']['number'],
               'LOG_DIR': output_dir,
               'REF_ID': data['patchSet']['ref'],
               'AUTHOR': data['patchSet']['author']['email']}
        ret = subprocess.call([self.run_script], env=env, shell=True)
        self.log.info("script: %s has exited with return value of %s",
                      self.run_script, ret)
        if ret != 0:
            rets = "FAILED"
            retvote = '-1'
        else:
            rets = "SUCCESS"
            retvote = '+1'

        url = "%s/%s/%s" % (
            HTTP_SERVER, data['change']['number'],
            data['patchSet']['number'])

        msg = "* functionals: %s: %s/output.txt\n" % (rets, url)
        msg += "* coverage: %s/cover/index.html\n" % url
        msg += "* diff-cover: %s/diff-cover-report.html\n" % url
        msg += "* docs: %s/docs/index.html" % url

        self.gerrit.review(data['change']['project'],
                           "%s,%s" % (data['change']['number'],
                                      data['patchSet']['number']),
                           msg,
                           action={'verified': retvote},)

    def _read(self, data):
        check = False
        if data['type'] == 'comment-added' and \
           data['comment'].endswith('\nrecheck'):
            check = True
        elif data['type'] == 'patchset-created':
            check = True

        if 'change' in data and \
           data['change']['project'] not in WATCHED_PROJECTS:
            check = False

        if check:
            self.log.info('Receiving event notification: %r' % data)
            self.run_command(data)

    def run(self):
        while True:
            while not self.connected:
                self.connect()
            try:
                event = self.gerrit.getEvent()
                self.log.info('Received event: %s' % event)
                self._read(event)
            except Exception:
                self.log.exception('Exception encountered in event loop')
                if not self.gerrit.watcher_thread.is_alive():
                    # Start new gerrit connection. Don't need to restart IRC
                    # bot, it will reconnect on its own.
                    self.connected = False


def setup_logging():
    logging.basicConfig(level=logging.INFO)


def main():
    setup_logging()
    k = Bottine()
    k.run()

if __name__ == '__main__':
    main()
