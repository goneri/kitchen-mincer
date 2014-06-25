#!/bin/bash -v

echo deb http://$ubuntu_mirror/ubuntu saucy main > /etc/apt/sources.list
apt-get update

export DEBIAN_FRONTEND=noninteractive
apt-get install -y libapache2-mod-php5 php5-mysql

mount /dev/vdb1 /srv
rm -r /var/www
cp -pr /srv/data/wordpress /var/www
mv /var/www/wp-config-sample.php /var/www/wp-config.php
sed -i s/database_name_here/$db_name/ /var/www/wp-config.php
sed -i s/username_here/$db_user/      /var/www/wp-config.php
sed -i s/password_here/$db_password/  /var/www/wp-config.php
sed -i s/localhost/$db_ipaddr/        /var/www/wp-config.php

mkdir /home/stack/.ssh
echo $test_public_key >> /home/stack/.ssh/authorized_keys

chmod 700 /home/stack/.ssh
chmod 600 /home/stack/.ssh/authorized_keys
chown -R stack:stack /home/stack/.ssh/

echo "Wordpress is ready!"
