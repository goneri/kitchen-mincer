#!/bin/bash -v

echo deb http://$ubuntu_mirror/ubuntu saucy main > /etc/apt/sources.list
apt-get update

export DEBIAN_FRONTEND=noninteractive
apt-get install -y mysql-server

sed -i "s,bind-address.*,bind-address = 0.0.0.0," /etc/mysql/my.cnf
service mysql restart

mount /dev/vdb1 /srv

# Setup MySQL root password and create a user
cat << EOF | mysql -u root
CREATE DATABASE $db_name;
GRANT ALL PRIVILEGES ON $db_name.* TO '$db_user'@'%'
IDENTIFIED BY '$db_password';
FLUSH PRIVILEGES;
EXIT
EOF
cat /srv/data/mysql/backup_wordpress.sql | mysql -u root wordpress

mkdir /home/stack/.ssh
chmod 700 /home/stack/.ssh
echo $test_public_key >> /home/stack/.ssh/authorized_keys
chmod 600 /home/stack/.ssh/authorized_keys
sudo chown -R stack:stack /home/stack/.ssh/

sed -i s/#AuthorizedKeysFile/AuthorizedKeysFile/g /etc/ssh/sshd_config
service ssh restart

echo "Wordpress database is ready!"
