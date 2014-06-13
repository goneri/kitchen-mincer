#!/bin/bash

cd /root
wget http://localhost:8080/jnlpJars/jenkins-cli.jar
for plugin in git-client scm-api git; do
    java -jar jenkins-cli.jar -s http://localhost:8080/ install-plugin /root/jenkins/plugins/${plugin}.hpi
done

java -jar jenkins-cli.jar -s http://localhost:8080/ safe-restart
echo "Jenkins is ready!"
