.. _commandsbuttons:
===============
CommandsButtons
===============

This is the cog guide for the ``CommandsButtons`` cog. This guide contains the collection of commands which you can use in the cog.
Through this guide, ``[p]`` will always represent your prefix. Replace ``[p]`` with your own prefix when you use these commands in Discord.

.. note::

    Ensure that you are up to date by running ``[p]cog update commandsbuttons``.
    If there is something missing, or something that needs improving in this documentation, feel free to create an issue `here <https://github.com/LeDeathAmongst/StarCogs/issues>`_.
    This documentation is generated everytime this cog receives an update.

---------------
About this cog:
---------------

A cog to allow a user to execute a command by clicking on a button!

---------
Commands:
---------

Here are all the commands included in this cog (7):

* ``[p]commandsbuttons``
 Group of commands to use CommandsButtons.

* ``[p]commandsbuttons add <message> <command> [emoji] ["1"|"2"|"3"|"4"=2] [text_button]``
 Add a command-button for a message.

* ``[p]commandsbuttons bulk <message> [commands_buttons]...``
 Add commands-buttons for a message.

* ``[p]commandsbuttons clear <message>``
 Clear all commands-buttons for a message.

* ``[p]commandsbuttons list [message]``
 List all commands-buttons of this server or display the settings for a specific one.

* ``[p]commandsbuttons purge``
 Clear all commands-buttons for a guild.

* ``[p]commandsbuttons remove <message> <config_identifier>``
 Remove a command-button for a message.

------------
Installation
------------

If you haven't added my repo before, lets add it first. We'll call it "StarCogs" here.

.. code-block:: ini

    [p]repo add StarCogs https://github.com/LeDeathAmongst/StarCogs

Now, we can install CommandsButtons.

.. code-block:: ini

    [p]cog install StarCogs commandsbuttons

Once it's installed, it is not loaded by default. Load it by running the following command:

.. code-block:: ini

    [p]load commandsbuttons

----------------
Further Support:
----------------

Check out my docs `here <https://StarCogs.readthedocs.io/en/latest/>`_.
Mention me in the #support_other-cogs in the `cog support server <https://discord.gg/GET4DVk>`_ if you need any help.
Additionally, feel free to open an issue or pull request to this repo.

--------
Credits:
--------

Thanks to Kreusada for the Python code to automatically generate this documentation!