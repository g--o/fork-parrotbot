#!/usr/bin/env python3

# ParrotBot -- Discord bot for quoting messages.
# Copyright (C) 2017 Martin W.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import discord
import asyncio
import datetime
import json
import re
import urllib.request

class ParrotBot(discord.Client):
    """Extend discord.Client with an event listener and additional methods."""

    def __init__(self, config, *args, **kwargs):
        """
        Extend class attributes of discord.Client.

        Pass all arguments except for config to discord.Client.__init__() and
        define new class attributes.

        Parameters
        ----------
        configs : dict
            Configuration object for the bot, created from the Configuration
            file. Gets turned into a class attribute.
        *args
            Non-keyworded arguments passed to the class upon initialisation.
        **kwargs
            Keyworded arguments passed to the class upon initialisation.
        """
        super(ParrotBot, self).__init__(*args, **kwargs)

        # Configuration object.
        self.config = config

        # Regular expression object to recognise quotes.
        self.re_quote = re.compile(r"(?P<author>.*?)\s*>\s*(?P<content>.+)")

        # How many messages are fetched at most by search_message_by_quote().
        self.log_fetch_limit = 100

    async def post_server_count(self):
        """
        Post how many servers are connected to Discord bot list sites.

        Create a JSON string containing how many servers are connected right
        now and post it to discordbots.org and bots.discord.pw using the
        respective tokens from the config file. If the token for a site is not
        given, ignore that site.
        """
        count_json = json.dumps({
            "server_count": len(self.servers)
        })

        # discordbots.org
        if self.config["discordbots_org_token"]:
            # Resolve HTTP redirects
            dbotsorg_redirect_url = urllib.request.urlopen(
                "http://discordbots.org/api/bots/%s/stats" % (self.user.id)
            ).geturl()

            # Construct request and post server count
            dbotsorg_req = urllib.request.Request(dbotsorg_redirect_url)

            dbotsorg_req.add_header(
                "Content-Type",
                "application/json"
            )
            dbotsorg_req.add_header(
                "Authorization",
                self.config["discordbots_org_token"]
            )

            urllib.request.urlopen(dbotsorg_req, count_json.encode("ascii"))

        # bots.discord.pw
        if self.config["bots_discord_pw_token"]:
            # Resolve HTTP redirects
            botsdpw_redirect_url_req = urllib.request.Request(
                "http://bots.discord.pw/api/bots/%s/stats" % (self.user.id)
            )

            botsdpw_redirect_url_req.add_header(
                "Authorization",
                self.config["bots_discord_pw_token"]
            )

            botsdpw_redirect_url = urllib.request.urlopen(
                botsdpw_redirect_url_req
            ).geturl()

            # Construct request and post server count
            botsdpw_req = urllib.request.Request(botsdpw_redirect_url)

            botsdpw_req.add_header(
                "Content-Type",
                "application/json"
            )
            botsdpw_req.add_header(
                "Authorization",
                self.config["bots_discord_pw_token"]
            )

            urllib.request.urlopen(botsdpw_req, count_json.encode("ascii"))

    async def is_same_user(self, user_obj, user_str):
        """
        Check if a given string represents a given User.

        Check if:
            1. the given string is (the beginning of) the user's id.
            2. the given string is (contained in) the user's full user name.
            3. the given string is (contained in) the user's display name.

        If any of that is true, return True, otherwise return False.

        Parameters
        ----------
        user_obj : discord.User
        user_str : str

        Returns
        -------
        boolean
        """
        # Escape user input
        user_str = re.escape(user_str)

        user_obj_full_name = user_obj.name + '#' + user_obj.discriminator

        if user_obj.id.find(user_str) == 0 \
        or re.search(user_str, user_obj_full_name, flags=re.IGNORECASE) \
        or re.search(user_str, user_obj.display_name, flags=re.IGNORECASE):
            return True
        else:
            return False

    async def search_message_by_quote(self, quote):
        """
        Finds a quote in a given channel and returns the found Message.

        Fetch an amount of messages older than the given quote from the channel
        the quote originates from, depending on self.log_fetch_limit. Then
        search for a message containing the quote and return it if found. If an
        author is given in the quote, only consider posts of that author. If no
        matching message is found, return None.

        Parameters
        ----------
        quote : discord.Message
            Message object containing a quote from another Message from the
            same channel.

        Returns
        -------
        discord.Message or None
        """
        match = self.re_quote.fullmatch(quote.content).groupdict()

        async for message in self.logs_from( \
            quote.channel, \
            limit=self.log_fetch_limit, \
            before=quote \
        ):
            if not match["author"] \
            or await self.is_same_user(message.author, match["author"]):
                if re.search( \
                    re.escape(match["content"]), \
                    message.content, \
                    flags=re.IGNORECASE \
                ):
                    return message

        return None

    async def create_quote_embed(self, quoting_user, quote):
        """
        Create a discord.Embed object that can then be posted to a channel.

        Generate a label containing the display name of the quoting user and
        whether the quoted message has been edited.

        Create a new discord.Embed object and map:
            1. the display name of the author of the quote to Embed.author.name
            2. their avatar to Embed.author.icon_url
            3. the quote's content to Embed.description
            4. the label generated earlier to Embed.footer.text
            5. the avatar of the quoting user to Embed.footer.icon_url
            6. the timestamp of the quoted message to Embed.timestamp.
        Return the object.

        Parameters
        ----------
        quoting_user : discord.User
            The user originally quoting the other message.
        quote : discord.Message
            The quoted message.

        Returns
        -------
        discord.Embed
        """

        quote_embed = discord.Embed(description=quote.content)
        quote_embed.set_author(
            name=quote.author.display_name,
            icon_url=quote.author.avatar_url
        )

        footertext = "Quoted by %s." % (quoting_user.display_name)

        if quote.edited_timestamp: # Message was edited
            footertext += " Edited."

        quote_embed.set_footer(
            text=footertext,
            icon_url=quoting_user.avatar_url
        )

        quote_embed.timestamp = quote.timestamp

        return quote_embed

    async def quote_message(self, quote):
        """
        Try to find the quoted message and post an according embed message.

        Try to find the quoted message by passing quote to
        self.search_message_by_quote(). If a fitting message was found and the
        bot is allowed to send messages in the channel, construct an according
        discord.Embed object and post it to the channel the quote originates
        from, then delete the original quoting message if allowed. If no fitting
        message was found, don't do anything.

        Parameters
        ----------
        quote : discord.Message
            Message that could contain a quote from another message.
        """
        quoted_message = await self.search_message_by_quote(quote)

        # Find own member object on the server.
        bot_member = quote.server.get_member(self.user.id)

        # Check if the bot is allowed to send messages in that channel.
        bot_may_send = quote.channel.permissions_for(bot_member).send_messages

        if quoted_message and bot_may_send:
            quote_embed = await self.create_quote_embed(
                quote.author,
                quoted_message
            )

            await self.send_message(quote.channel, embed=quote_embed)

            try:
                await self.delete_message(quote)
            except discord.Forbidden:
                pass


    # Event listeners.

    async def on_ready(self):
        """
        Print ready message, post server count and set the bot's presence.

        Print a message saying that the server is ready and how many servers it
        is connected to. If the according value in the config file is set to
        True, also list all connected servers. Post the amount of connected
        servers to bot list sites, if according tokens are fiven in the config
        file. Finally set the bot's presence (game status) if one is specified
        in the config file.
        """
        print("ParrotBot is ready.")
        print("\nConnected Servers: %d" % (len(self.servers)))

        if self.config["server_list"]:
            for server in self.servers:
                print("%s - %s" % (server.id, server.name))

        print()

        await self.post_server_count()

        if "presence" in self.config:
            presence = discord.Game()
            presence.name = self.config["presence"]
            await self.change_presence(game=presence)

    async def on_server_join(self, server):
        """Print number of connected servers when connecting to a new server."""
        print("Joined Server %s -- %s." % (server.id, server.name))
        print("Connected Servers: %d\n" % (len(self.servers)))
        await self.post_server_count()

    async def on_server_remove(self, server):
        """Print number of connected servers when leaving a server."""
        print("Left Server %s -- %s." % (server.id, server.name))
        print("Connected Servers: %d\n" % (len(self.servers)))
        await self.post_server_count()

    async def on_message(self, message):
        """Check if message matches the quotation regex and quote it if so."""
        if self.re_quote.fullmatch(message.content):
            await self.quote_message(message)


# Print GNU GPL notice
print("""ParrotBot  Copyright (C) 2017  Martin W.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.\n""")

# Configuration object.
config = {}

# Will be set to True if config.json misses keys or does not exist yet.
configfile_needs_update = False

# Try to read configuration file.
try:
    with open("config.json", "r") as configfile:
        config = json.load(configfile)
except FileNotFoundError:
    print("Configuration file not found!")
    configfile_needs_update = True

# Check for token.txt for backwards compatibility. If found, get the token file
# from it and use it for the new configuration, if that does not contain a token
# yet.
try:
    with open("token.txt", "r") as tokenfile:
        token_from_txt = tokenfile.readline().rstrip()
        print(
            "token.txt found. Usage of this file is deprecated; the token will "
            "be written to the new config.json file."
        )
        if "discord-token" not in config:
            config["discord-token"] = token_from_txt
            configfile_needs_update = True
except FileNotFoundError:
    pass

# Check if the loaded configuration misses keys. If so, ask for user input or
# assume a default value.

# Discord API token.
if "discord-token" not in config:
    configfile_needs_update = True
    config["discord-token"] = input(
        "Discord API token not found. Please enter your API token: "
    )

# discordbots.org API token
if "discordbots_org_token" not in config:
    configfile_needs_update = True
    config["discordbots_org_token"] = input(
        "discordbots.org API token not found. Please enter your API token "
        "(leave empty to ignore discordbots.org): "
    )

# bots.discord.pw API token
if "bots_discord_pw_token" not in config:
    configfile_needs_update = True
    config["bots_discord_pw_token"] = input(
        "bots.discord.pw API token not found. Please enter your API token "
        "(leave empty to ignore bots.discord.pw): "
    )

# presence (game status)
if "presence" not in config:
    configfile_needs_update = True
    config["presence"] = input(
        "Please specify a presence or game status. This will be shown in the "
        "bot's user profile (leave empty to disable this feature): "
    )

# whether the server list should be displayed on startup
if "server_list" not in config:
    configfile_needs_update = True

    answer = None

    while answer == None or answer.lower() not in ("y", "yes", "n", "no", ""):
        answer = input(
            "Should the bot list all connected servers on startup? [Y/n]: "
        )

        if answer.lower() not in ("y", "yes", "n", "no", ""):
            print("\nPlease answer with either yes or no.\n")

    if answer.lower() in ("y", "yes", ""):
        config["server_list"] = True
    else:
        config["server_list"] = False

# (Re)write configuration file if it didn't exist or missed keys.
if configfile_needs_update:
    with open("config.json", "w") as configfile:
        json.dump(config, configfile, indent=2)
        print("Configuration file updated.")

# Initialise client object with the loaded configuration.
client = ParrotBot(config)

while True:
    try:
        # Start bot session.
        print("Start bot session with token %s" % (config["discord-token"]))
        client.run(config["discord-token"])
    except ConnectionResetError:
        print("\n--------------------------------------------")
        print("Lost Connection. Retrying in 5 seconds ...")
        print("--------------------------------------------\n")

        sleep(5)
