Foolseye
========

Foolseye flags new photos that show evidence of digital alteration
(i.e. they've been Photoshopped) and crowdsources the human evaluation
of suspect images.

See ["Protecting Journalistic Integrity Algorithmically"](http://lemonodor.com/archives/2008/02/protecting_journalistic_integrity_algorithmically.html) for more background.

Prerequisites
-------------

    virtualenv env
    env/bin/easy_install Flask
    env/bin/easy_install Flask-Script
    env/bin/easy_install pymongo
    env/bin/easy_install blinker
    sudo apt-get install mongodb
    sudo apt-get install libfreeimage-dev
