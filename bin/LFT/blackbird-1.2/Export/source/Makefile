CFLAGS=-O3 -Wall
VERSION=1.2
MINGW=i686-w64-mingw32-gcc

all:			birdcruncher

birdcruncher:		cruncher.c player.h rplayer.h prghead.h
			${CC} -o $@ ${CFLAGS} -DVERSION=\"${VERSION}\" $<

wincrunch.exe:		cruncher.c player.h rplayer.h prghead.h compat/err.c
			${MINGW} -Wall -O3 -DVERSION=\"${VERSION}\" -idirafter compat -o $@ $< compat/err.c
