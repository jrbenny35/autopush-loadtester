# Autopush Load-Tester

The Autopush Load-Tester is an integrated API and load-tester for the Mozilla Services autopush project. It's intented to verify proper functioning of autopush deployments under various load conditions. These tests uuse Python 3 as well as [molotov](https://molotov.readthedocs.io/en/stable/).

## Running the tests

Building a docker image is the advised way to run the test suite.

    $ docker build -t autopush-loadtester -f dockerfile .

To run the tests specify an instance you would like to test against (dev, stage, production) as an environment variable ```AUTOPUSH_ENV```.

    $  docker run --env AUTOPUSH_ENV=dev autopush-loadtester

The load tests should run.