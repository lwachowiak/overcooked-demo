# production without any terminal output
if [[ $1 = prod* ]];
then
    echo "production"
    export BUILD_ENV=production
    # Completely re-build all images from scatch without using build cache
    docker-compose build --no-cache
    docker-compose up --force-recreate -d

# reload the overcooked-ai repository
elif [[ $1 = re* ]];
then
    echo "development"
    export BUILD_ENV=development
    # reload everything
    docker-compose build --no-cache
    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build

# development build with logging in terminal+screenrecording
else   
    echo "development standard"
    export BUILD_ENV=development
    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build
fi
