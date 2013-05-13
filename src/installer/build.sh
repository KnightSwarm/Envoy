cd xmppd
tar -czf - * | pysfx -as "python install.py" - ../xmppd_sfx.py
