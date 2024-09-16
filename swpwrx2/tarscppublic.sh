#/bin/sh
#
#Usage: tarscppublic.sh 
#       Tars up the public directory so it can be synched to Amazon S3
#       Uses scp to copy the archive to stepwise-editorial.querium.com
#	After copying the dist files to stepwise-editorial, you can extract the contents into /var/www/swpwr
d=`date +"%Y%m%d%H%M"`
tar cvfz public-$d.tar.gz public
scp public-$d.tar.gz root@stepwise-editorial.querium.com:/var/www/swpwr/
