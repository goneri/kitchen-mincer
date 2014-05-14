#!/bin/bash
mkdir -p /var/www/ubuntu
while ! mount /dev/vdb1 /var/www/ubuntu; do
    sleep 1
    date >> /tmp/george_michael_was_here
done

echo deb file:/var/www/ubuntu saucy main > /etc/apt/sources.list
apt-get update
apt-get install -y apache2
echo "APT mirror is ready!"
