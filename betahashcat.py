# __________                  __             __     ________             .___ 
# \______   \  ____    ____  |  | __  ____ _/  |_  /  _____/   ____    __| _/ 
#  |       _/ /  _ \ _/ ___\ |  |/ /_/ __ \\   __\/   \  ___  /  _ \  / __ |  
#  |    |   \(  <_> )\  \___ |    < \  ___/ |  |  \    \_\  \(  <_> )/ /_/ |  
#  |____|_  / \____/  \___  >|__|_ \ \___  >|__|   \______  / \____/ \____ |  
#         \/              \/      \/     \/               \/              \/  
#
# Discord bot for Hashcat password cracking by RocketGod
# https://github.com/RocketGod-git/hashcat-discord-bot

import json
import logging
import os
import asyncio
import sys
import psutil
import re

import discord
from discord.ui import Select, Button, View, Modal
from discord import ButtonStyle
from discord.ext import commands

logging.basicConfig(level=logging.INFO)


def load_config():
    try:
        with open('config.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return None


config = load_config()
discord_bot_token = config["discord_bot_token"]


if sys.platform == "win32":
    hashcat_exec = os.path.abspath("..\hashcat.exe")
else:
    hashcat_exec = os.path.abspath("../hashcat")


class HashcatArgumentsModal(discord.ui.Modal, title="Hashcat Command Arguments"):
    arguments = discord.ui.TextInput(
        label="Arguments", 
        placeholder="Enter your Hashcat arguments here"
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Processing your request...", ephemeral=True)
        
        args = self.arguments.value.split()  
        await execute_hashcat(interaction, args)  # Call execute_hashcat with the arguments


async def execute_hashcat(interaction, args):
    try:
        sanitized_args = []
        for arg in args:
            # Remove potentially dangerous characters or patterns
            # Only allow alphanumeric, dashes, and equals for parameter arguments
            safe_arg = re.sub(r'[^a-zA-Z0-9\-=:,./\\]', '', arg)
            sanitized_args.append(safe_arg)

        # Construct the Hashcat command line using sanitized arguments
        cmd = [hashcat_exec] + sanitized_args

        # Execute Hashcat as a subprocess
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()

        # Handle Hashcat output
        if process.returncode == 0:
            result_message = stdout.decode().strip() or "Hashcat execution completed successfully."
        else:
            result_message = f"Error executing Hashcat: {stderr.decode().strip()}"

        # Send the result back to the user
        await interaction.followup.send(result_message, ephemeral=True)

    except Exception as e:
        logging.error(f"Error in execute_hashcat: {e}")
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


async def show_help(interaction):
    with open('instructions.txt', 'r') as file:
        instructions = file.read()
    await interaction.response.send_message(instructions, ephemeral=True)


class HashcatBot(discord.Client):
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(intents=intents, *args, **kwargs)  
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.add_command(hashcat_command)

    async def on_ready(self):
        logging.info(f"Bot {self.user} is running!")
        logging.info(f"Bot name: {self.user.name}")
        logging.info(f"Bot is in {len(self.guilds)} servers.")
        for guild in self.guilds:
            logging.info(f" - {guild.name} (ID: {guild.id})")
        await self.tree.sync()


class HashcatView(View):
    def __init__(self):
        super().__init__()

        # Arguments Button
        arguments_button = discord.ui.Button(label="Arguments", style=discord.ButtonStyle.primary, custom_id="unique_arguments_button")
        arguments_button.callback = self.arguments_button_callback
        self.add_item(arguments_button)

        # Instructions Button
        instructions_button = discord.ui.Button(label="Instructions", style=discord.ButtonStyle.secondary, custom_id="unique_instructions_button")
        instructions_button.callback = self.instructions_button_callback
        self.add_item(instructions_button)

    async def arguments_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(HashcatArgumentsModal())

    async def instructions_button_callback(self, interaction: discord.Interaction):
        try:
            # Open 'instructions.txt' and create a File object to send as an attachment
            with open('instructions.txt', 'rb') as file:
                instructions_file = discord.File(file, filename="instructions.txt")
            await interaction.response.send_message("Here are the instructions:", file=instructions_file)
        except Exception as e:
            # If there's an error, send a follow-up message indicating the failure
            await interaction.followup.send("Failed to load instructions. Please try again later.", ephemeral=True)
            print(f"Failed to send instructions: {e}")  # Print the error to the terminal for debugging


@discord.app_commands.command(name="hashcat", description="Execute Hashcat commands.")
async def hashcat_command(interaction: discord.Interaction):
    view = HashcatView()
    await interaction.response.send_message("Choose an option:", view=view, ephemeral=True)


async def handle_errors(interaction, error, error_type="Error", detailed_error=None):
    error_message = f"{error_type}: {error}"
    if detailed_error:
        error_message += f"\nDetails: {detailed_error}"
    logging.error(f"Error for user {interaction.user}: {error_message}")  

    try:
        if interaction.response.is_done():
            await interaction.channel.send(error_message)
        else:
            await interaction.response.send_message(error_message, ephemeral=False)
    except discord.HTTPException as http_err:
        logging.warning(f"HTTP error while responding to {interaction.user}: {http_err}")
    except Exception as unexpected_err:
        logging.error(f"Unexpected error while responding to {interaction.user}: {unexpected_err}")


async def run():
    bot = HashcatBot(intents=discord.Intents.default())
    async with bot:
        await bot.start(discord_bot_token)


if __name__ == "__main__":
    try:
        bot = HashcatBot()
        bot.run(discord_bot_token)
    except Exception as e:
        print(f"Error starting bot: {e}")
