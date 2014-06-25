#!/bin/bash

if [ -z $upstream_git ]; then
    upstream_git="/git/input.git"
    mkdir -p /git/input.git
    git init --bare --shared /git/input.git
    chown -R stack:stack /git/input.git
    git clone /git/input.git /tmp/input
    cd /tmp/input
    cp /etc/fstab /tmp/input
    git add fstab
    git commit -m "initial commit"
    git push /git/input.git master:master
fi

chown -R jenkins:jenkins /var/cache/git/demo.git

cd /root
wget http://localhost:8080/jnlpJars/jenkins-cli.jar

# Install all the .hpi plugin found in the /root/jenkins directory
find /root/jenkins -name '*.hpi' -exec java -jar jenkins-cli.jar -s http://localhost:8080 install-plugin {} \;

java -jar jenkins-cli.jar -s http://localhost:8080 restart

while [ $(curl  -o /dev/null -sL -w "%{http_code}\\n" http://localhost:8080/pluginManager/installed) -ne 200 ]; do
    echo "Waiting for Jenkins"
    sleep 1
done

cat > /tmp/jenkins_job.yaml <<EOF
- job:
    name: 'validate-kitchen'
    description: 'Fetch a remote marmite and test it'
    project-type: freestyle
    wrappers:
      - ansicolor:
          colormap: xterm
    scm:
      - git:
          url: $upstream_git
          refsepc: 'master'
          wipe-workspace: true
    triggers:
      - timed: '@daily'
      - pollscm: "* * * * *"
    builders:
      - shell: |
          set -e
          # Use a HTTP proxy if possible. This is a workaround
          # for the case it's not possible to access external
          # network from a tenant
          if curl -I http://127.0.0.1:3128 2>&1|grep -q squid; then
              export http_proxy=http://127.0.0.1:3128
          fi

          kitchen-mincer --target devtest .
          echo "this is the end"
          git checkout -b master `git log --pretty=%H`
          git push /var/cache/git/demo.git master:master
EOF
jenkins-jobs update /tmp/jenkins_job.yaml


echo "Jenkins is ready!"
