# Prompt for requirement 001

Add an FMSAT capability to copy Football Manager 26 tactics, filters, player
headshots (`*.png`) and the player `config.xml` from Andy-PC's Steam games area
to the equivalent TV-PC Steam games area.

Use `rsync` for the large headshot collection and incremental additions. Support
capturing the smaller files in a stored `tar.gz` archive and releasing them later,
so that both computers do not need to be online at the same time. Do not include
the headshot collection in the archive by default because it is too large.

If using 'rsync' include a test to make sure the destination pc is online before starting the transfer. If the destination pc is offline then abort the operation and display an appropriate error message.
