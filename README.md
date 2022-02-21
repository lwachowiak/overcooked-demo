# Overcooked Demo
<p align="center">
<img src="./server/static/images/browser_view.png" >
</p>

We adapted ...

## Installation

Building the server image requires [Docker](https://docs.docker.com/get-docker/)

## Usage

The server can be deployed locally using the driver script included in the repo. To run the production server, use the command
```bash
./up.sh production
```

In order to build and run the development server, which includes a deterministic scheduler and helpful debugging logs, run
```bash
./up.sh
```

After running one of the above commands, navigate to http://localhost

In order to kill the production server, run
```bash
./down.sh
```

## Dependencies

The Overcooked-Demo server relies on both the [overcooked-ai](https://github.com/HumanCompatibleAI/overcooked_ai) and [human-aware-rl](https://github.com/HumanCompatibleAI/human_aware_rl) repos. The former contains the game logic, the latter contains the rl training code required for managing agents. Both repos are automatically cloned and installed in the Docker builds.

The branch of `overcooked_ai` and `human_aware_rl` imported in both the development and production servers can be specified by the `OVERCOOKED_BRANCH` and `HARL_BRANCH` environment variables, respectively. For example, to use the branch `foo` from `overcooked-ai` and branch `bar` from `human_aware_rl`, run
```bash
OVERCOOKED_BRANCH=foo HARL_BRANCH=bar ./up.sh
```
We use a custom fork of the overcooked-ai that can be found [here](https://github.com/Ptisni/overcooked_ai)

