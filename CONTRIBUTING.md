# Contributing Guideline

Welcome to the [warnet-gi/WarnetBot](https://github.com/warnet-gi/WarnetBot) 👋\
Thanks for helping out the community!

Before creating your pull request, make sure you already **read the whole guideline**. If you feel that this guideline is not clear enough or have any doubts, feel free to raise it in the [issue](https://github.com/warnet-gi/WarnetBot/issues/new) or by joining our [Discord channel](https://discord.gg/warnet-gi).

## Project Structures

- All bot contents are stored in `/bot`.
  - the `/bot/assets` stores static assets.
  - the `/bot/cogs` stores the bot logic.
  - the `/bot/data` stores script to initialize PostgresSQL database.
  - the `/bot/module` stores our self-made python modules.

## Start Running in Local

**Prerequisites**:

- UV (https://docs.astral.sh/uv/)
- PostgreSQL

**Steps**:

1. Fork or clone this repository.
2. Go to Discord developers section and create a **[New Application](https://discord.com/developers/applications)**.
3. After creating a new app, you will be redirected to the app dashboard. Go to **Bot** menu in the sidebar.
4. Find the **Token** section, then create a token.
5. Copy the generated token and copy paste it to `BOT_TOKEN` in the `.env` file.
6. You can use our provided `.env.example` in the root directory, just rename it to `.env`.
7. Install dependencies using `uv sync`.
8. Next we will create our database by executing the `db.sql` script in the `bot/data` (run this either using pgAdmin or psql).
9. Ensure to set the `BOT_DEBUG=1` in the `.env` file for debugging mode. Set to `BOT_DEBUG=0` for Production only.
10. Start the bot by running `uv run task start`.

## Common Problems

- Got **Invalid literal for int() with base 10: 'YOUR_GUILD_ID'** after running `uv run task start`
  - Define the `GUILD_ID` value in `.env` file with your Discord Server ID.

## Sending Pull Request(s)

Before sending a pull request, **ensure to stage all the commit inside a new branch**. Adding a prefix in your branch name will help us to recognize your pull request earlier (e.g. `fix/general-welcome-message` or `feat/delete-server-command`).

Run the linting and type check first to make sure your code follow our rules by:

- Running `format` by executing `uv run ruff format`.
- Running `linting` by executing `uv run ruff check`.
- RUnning `type check` by executing `uv run pyright`.

As we want to have standardize commit messages, please follow this [commit message convention guide](https://www.conventionalcommits.org/en/v1.0.0/#summary) and [50/72 commit message rule format](https://initialcommit.com/blog/git-commit-messages-best-practices).
