sid_init	= $1000
sid_play	= $1003
sid_sync	= $ed

		.word	loadaddr

		* = $3000
loadaddr
		lda	#<irq
		sta	$fffe
		lda	#>irq
		sta	$ffff
		lda	#$01
		sta	$d01a
		lda	#$ff
		sta	$d012
		lda	#$1b
		sta	$d011

		jsr	sid_init

		lsr	$d019
		cli

		; The first chunk is already in memory (and playing),
		; but we need to load the next one now.
main
		jsr	$c90

		; Tell playroutine that the upcoming chunk has been loaded.

		inc	sid_sync

		; Hang around until next syncpoint.
waitsync
		lda	sid_sync
		bne	waitsync

		; We've reached a syncpoint. Visualise it!

		inc	$d020

		; In this demo, every syncpoint starts a new chunk.
		; Thus, it is safe to overwrite the old chunk now.

		jmp	main

		; (When the song is over, we will remain in waitsync forever.)
irq
		sta	savea+1
		stx	savex+1
		sty	savey+1
		dec	$d020

		jsr	sid_play

		inc	$d020
savea		lda	#0
savex		ldx	#0
savey		ldy	#0
		lsr	$d019
		rti
