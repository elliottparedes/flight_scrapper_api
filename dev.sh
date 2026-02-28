#!/bin/bash

IMAGE="fast-flights"
CONTAINER="fast-flights"

case "$1" in
  start)
    docker stop $CONTAINER 2>/dev/null; docker rm $CONTAINER 2>/dev/null
    docker build -t $IMAGE .
    docker run -d --name $CONTAINER -p 8000:8000 $IMAGE
    echo "Running at http://localhost:8000"
    ;;
  stop)
    docker stop $CONTAINER && docker rm $CONTAINER
    ;;
  rebuild)
    docker stop $CONTAINER 2>/dev/null; docker rm $CONTAINER 2>/dev/null
    docker build -t $IMAGE .
    docker run -d --name $CONTAINER -p 8000:8000 $IMAGE
    echo "Rebuilt and running at http://localhost:8000"
    ;;
  logs)
    docker logs -f $CONTAINER
    ;;
  *)
    echo "Usage: ./dev.sh [start|stop|rebuild|logs]"
    ;;
esac
