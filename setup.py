#!/usr/bin/env python
from distutils.core import setup

setup (name="TextSnippets",
       version="0.1.0",
       description="TextSnippets is a snippets program for linux using pygtk",
       author="Mark Harrison",
       author_email="mark@mivok.net",
       url="http://github.com/mivok/textsnippets",
       license="ISC",
       package_dir={'': 'src'},
       packages=['textsnippets'],
       package_data={'textsnippets': ['data/*']},
       scripts=['src/ts']
)
