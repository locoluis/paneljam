# PanelJam download script
Download your PanelJam panels before it's too late!

Requirements:

* Python 3.x
* requests
* bs4
* pystache

This is a quick and dirty Python script to download a player's PanelJam panels.

Usage:

    python3 pjbackup.py [-l] username

Where:

* -l allows you to login as a PanelJam user (doesn't have to be the same as the username). This will allow you to download panels marked as NSFW.
* _username_ is the username of the player whose panels you will download.

This script creates two folders in the current folder:

* players is where the username.html page will be created, pointing to the player's jams.
* jams is where the jams themselves will be downloaded, one subfolder per jam.
