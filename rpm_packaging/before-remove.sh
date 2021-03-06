# find pkg type
if [ -f /usr/lib/systemd/system/goldstone-server-enterprise.service ]; then
  PKGNAME=goldstone-server-enterprise
else
  PKGNAME=goldstone-server
fi

# shut down service
systemctl stop $PKGNAME
systemctl disable $PKGNAME

# stop containers
echo "Stopping containers..."
if [ `docker ps | grep goldstone | wc -l` -gt 0 ]; then
  docker stop -t 15 $(docker ps -a | grep goldstone | awk '{print $1}' | xargs) || /bin/true
fi

# remove stopped containers
echo "Removing containers..."
if [ `docker ps -a | grep goldstone | wc -l` -gt 0 ]; then
  docker rm -f $(docker ps -a | grep goldstone | awk '{print $1}' | xargs) || /bin/true
fi

echo "Removing images..."
if [ `docker images -a | grep goldstone | wc -l` -gt 0 ]; then
  docker rmi -f $(docker images | grep goldstone | awk '{print $3}' | xargs) || /bin/true
fi
