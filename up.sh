# production without any terminal output
if [[ $1 = prod* ]];
then
    echo "production"
    export BUILD_ENV=production
    # Completely re-build all images from scatch without using build cache
    docker-compose build --no-cache
    docker-compose up --force-recreate -d & ffmpeg -f x11grab -s wxga -r 25 -i :0.0 -qscale 0 $(date +%Y%d%m_%H%M%S).mpg && fg

# reload the overcooked-ai repository
elif [[ $1 = rel* ]];
then
    echo "development"
    export BUILD_ENV=development
    # reload everything
    docker-compose build --no-cache
    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build & ffmpeg -f x11grab -s wxga -r 25 -i :0.0 -qscale 0 $(date +%Y%d%m_%H%M%S).mpg && fg

# flag to disable screenrecoring
elif [[ $1 = nov* ]];
then
    echo "development"
    export BUILD_ENV=development
    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build 

# development build with logging in terminal+screenrecording
else   
    echo "development"
    export BUILD_ENV=development
    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build & ffmpeg -f x11grab -s wxga -r 25 -i :0.0 -qscale 0 $(date +%Y%d%m_%H%M%S).mpg && fg
fi
