# This file is part of Blackbird by lft.

# It requires spin from Spindle 2.0 or later.

# We are abusing the make system somewhat: birdcruncher outputs several files,
# and demo.d64 depends on all of them. But we only list one (resident.prg).

SPIN=spin		# Edit this line to point to the spin binary
CRUNCH=birdcruncher	# Edit this line to point to the birdcruncher binary

all:				blackbird-dist-demo.d64

blackbird-dist-demo.d64:	spinscript.txt demo.prg resident.prg
				${SPIN} -o $@ $<

demo.prg:			demo.s
				xa -o $@ $<

resident.prg:			bb.backpack sync.txt
				${CRUNCH} \
					-v \
					-t dist \
					-o $@ \
					-i 0600:initcode.prg \
					-@ sync.txt \
					$<
